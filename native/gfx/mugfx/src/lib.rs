//! mugfx: a C ABI that plays one converted GFx movie with Ruffle (NATIVE-GFX-001).
//!
//! The native client creates one `mugfx` per GFx window, like the client's
//! GFx manager creates one movie per window.  The game side talks to the
//! movie through the same two channels GFx offers:
//!
//! * movie -> game: `ExternalInterface.call(name, args...)` arrives at the
//!   registered C callback as `(name, JSON array)`; its optional JSON reply is
//!   returned to ActionScript;
//! * game -> movie: `mugfx_invoke(path, method, JSON args)` (GFx
//!   `Movie::Invoke` / `Value::Invoke`) and `mugfx_set_variable` (GFx
//!   `SetVariable`).  Both go through the `__mu_*` bridge callbacks that
//!   `native/gfx/gfxconvert.py --bridge` adds to the converted SWF.
//!
//! Calls made from inside the C callback (while the player is running) are
//! queued and run after the current advance, so callbacks may invoke freely.

use std::any::Any;
use std::cell::{Cell, RefCell};
use std::ffi::{CStr, CString, c_char, c_int, c_void};
use std::path::Path;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::{Duration, Instant};

use ruffle_core::backend::locale::DeterministicLocaleBackend;
use ruffle_core::backend::log::LogBackend;
use ruffle_core::context::UpdateContext;
use ruffle_core::events::MouseButton;
use ruffle_core::external::{ExternalInterfaceProvider, Value as ExternalValue};
use ruffle_core::limits::ExecutionLimit;
use ruffle_core::tag_utils::movie_from_path;
use ruffle_core::{FloatDuration, Player, PlayerBuilder, PlayerEvent, StageAlign, StageScaleMode,
                  ViewportDimensions};
use ruffle_render_wgpu::backend::{WgpuRenderBackend, create_wgpu_instance, request_adapter_and_device};
use ruffle_render_wgpu::descriptors::Descriptors;
use ruffle_render_wgpu::target::TextureTarget;
use ruffle_render_wgpu::wgpu;

/// `const char *callback(void *user, const char *name, const char *args_json)`.
/// The returned string (JSON, may be NULL) must stay valid until the next call.
pub type MuGfxCallback =
    Option<unsafe extern "C" fn(*mut c_void, *const c_char, *const c_char) -> *const c_char>;

thread_local! {
    static IN_PLAYER: Cell<bool> = const { Cell::new(false) };
}

static DESCRIPTORS: OnceLock<Result<Arc<Descriptors>, String>> = OnceLock::new();
static LOGGING: OnceLock<()> = OnceLock::new();

/// MUGFX_LOG=<tracing filter> (e.g. `warn`) prints Ruffle's log, including
/// "Encountered stub" warnings for unimplemented Flash APIs, to stderr.
fn init_logging() {
    LOGGING.get_or_init(|| {
        if let Ok(filter) = std::env::var("MUGFX_LOG") {
            let _ = tracing_subscriber::fmt()
                .with_env_filter(tracing_subscriber::EnvFilter::new(filter))
                .with_writer(std::io::stderr)
                .with_ansi(false)
                .without_time()
                .try_init();
        }
    });
}

/// ActionScript trace() and AVM warnings; printed when MUGFX_TRACE is set.
struct TraceLog(bool);

impl LogBackend for TraceLog {
    fn avm_trace(&self, message: &str) {
        if self.0 {
            eprintln!("[trace] {message}");
        }
    }

    fn avm_warning(&self, message: &str) {
        if self.0 {
            eprintln!("[avm-warning] {message}");
        }
    }
}

fn descriptors() -> Result<Arc<Descriptors>, String> {
    DESCRIPTORS
        .get_or_init(|| {
            let backends = wgpu::Backends::PRIMARY;
            let instance = create_wgpu_instance(backends, wgpu::BackendOptions::default(), None);
            let (adapter, device, queue) = futures::executor::block_on(request_adapter_and_device(
                backends,
                &instance,
                None,
                wgpu::PowerPreference::HighPerformance,
            ))
            .map_err(|e| e.to_string())?;
            Ok(Arc::new(Descriptors::new(instance, adapter, device, queue)))
        })
        .clone()
}

struct CallbackSlot {
    callback: MuGfxCallback,
    user: *mut c_void,
    calls: u64,
}

struct Provider(Arc<Mutex<CallbackSlot>>);

impl ExternalInterfaceProvider for Provider {
    fn call_method(&self, _context: &mut UpdateContext<'_>, name: &str, args: &[ExternalValue]) -> ExternalValue {
        let (callback, user) = {
            let mut slot = self.0.lock().unwrap();
            slot.calls += 1;
            (slot.callback, slot.user)
        };
        let Some(callback) = callback else { return ExternalValue::Null };
        let json = serde_json::Value::Array(args.iter().map(to_json).collect()).to_string();
        let (Ok(name), Ok(json)) = (CString::new(name), CString::new(json)) else { return ExternalValue::Null };
        let reply = unsafe { callback(user, name.as_ptr(), json.as_ptr()) };
        if reply.is_null() {
            return ExternalValue::Undefined;
        }
        let text = unsafe { CStr::from_ptr(reply) }.to_string_lossy();
        serde_json::from_str::<serde_json::Value>(&text).map(|v| from_json(&v)).unwrap_or(ExternalValue::Null)
    }

    fn on_callback_available(&self, _name: &str) {}

    fn get_id(&self) -> Option<String> {
        None
    }
}

fn to_json(value: &ExternalValue) -> serde_json::Value {
    match value {
        ExternalValue::Undefined | ExternalValue::Null => serde_json::Value::Null,
        ExternalValue::Bool(b) => (*b).into(),
        ExternalValue::Number(n) => serde_json::Number::from_f64(*n).map(Into::into).unwrap_or(serde_json::Value::Null),
        ExternalValue::String(s) => s.clone().into(),
        ExternalValue::List(l) => serde_json::Value::Array(l.iter().map(to_json).collect()),
        ExternalValue::Object(o) => {
            serde_json::Value::Object(o.iter().map(|(k, v)| (k.clone(), to_json(v))).collect())
        }
    }
}

fn from_json(value: &serde_json::Value) -> ExternalValue {
    match value {
        serde_json::Value::Null => ExternalValue::Null,
        serde_json::Value::Bool(b) => ExternalValue::Bool(*b),
        serde_json::Value::Number(n) => ExternalValue::Number(n.as_f64().unwrap_or(0.0)),
        serde_json::Value::String(s) => ExternalValue::String(s.clone()),
        serde_json::Value::Array(a) => ExternalValue::List(a.iter().map(from_json).collect()),
        serde_json::Value::Object(o) => {
            ExternalValue::Object(o.iter().map(|(k, v)| (k.clone(), from_json(v))).collect())
        }
    }
}

enum Pending {
    Invoke(String, String, ExternalValue),
    Set(String, ExternalValue),
}

pub struct MuGfx {
    player: Arc<Mutex<Player>>,
    slot: Arc<Mutex<CallbackSlot>>,
    pending: RefCell<Vec<Pending>>,
    width: u32,
    height: u32,
    reply: RefCell<CString>,
    stats: RefCell<Stats>,
}

#[derive(Default, Clone, Copy)]
#[repr(C)]
pub struct MuGfxStats {
    pub frames_rendered: u64,
    pub external_calls: u64,
    pub last_advance_ms: f64,
    pub last_render_ms: f64,
    pub last_capture_ms: f64,
}

#[derive(Default)]
struct Stats(MuGfxStats);

fn write_error(err: *mut c_char, cap: usize, msg: &str) {
    if err.is_null() || cap == 0 {
        return;
    }
    let bytes = msg.as_bytes();
    let n = bytes.len().min(cap - 1);
    unsafe {
        std::ptr::copy_nonoverlapping(bytes.as_ptr(), err as *mut u8, n);
        *err.add(n) = 0;
    }
}

unsafe fn cstr<'a>(p: *const c_char) -> Option<&'a str> {
    if p.is_null() { None } else { unsafe { CStr::from_ptr(p) }.to_str().ok() }
}

impl MuGfx {
    fn with_player<R>(&self, f: impl FnOnce(&mut Player) -> R) -> R {
        IN_PLAYER.with(|c| c.set(true));
        let r = f(&mut self.player.lock().unwrap());
        IN_PLAYER.with(|c| c.set(false));
        r
    }

    fn run_pending(&self) {
        loop {
            let jobs: Vec<Pending> = self.pending.borrow_mut().drain(..).collect();
            if jobs.is_empty() {
                break;
            }
            for job in jobs {
                match job {
                    Pending::Invoke(path, method, args) => {
                        self.call_bridge("__mu_invoke", vec![path.into(), method.into(), args]);
                    }
                    Pending::Set(path, value) => {
                        self.call_bridge("__mu_set", vec![path.into(), value]);
                    }
                }
            }
        }
    }

    fn call_bridge(&self, name: &str, args: Vec<ExternalValue>) -> ExternalValue {
        self.with_player(|p| p.call_internal_interface(name, args))
    }
}

/// Load a converted SWF.  `width`/`height` are the viewport in pixels (the
/// movie sees them as Stage.width/height: no scaling, top-left aligned, as the
/// client's GFx windows lay themselves out).  Returns NULL on error.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_open(path: *const c_char, width: c_int, height: c_int, err: *mut c_char,
                                    err_cap: usize) -> *mut MuGfx {
    let Some(path) = (unsafe { cstr(path) }) else {
        write_error(err, err_cap, "invalid path");
        return std::ptr::null_mut();
    };
    let (w, h) = (width.max(1) as u32, height.max(1) as u32);
    init_logging();
    let result = (|| -> Result<Box<MuGfx>, String> {
        let descriptors = descriptors()?;
        let movie = movie_from_path(Path::new(path), None).map_err(|e| e.to_string())?;
        let target = TextureTarget::new(&descriptors.device, (w, h)).map_err(|e| e.to_string())?;
        let renderer = WgpuRenderBackend::new(descriptors, target).map_err(|e| e.to_string())?;
        let slot = Arc::new(Mutex::new(CallbackSlot { callback: None, user: std::ptr::null_mut(), calls: 0 }));
        let player = PlayerBuilder::new()
            .with_renderer(renderer)
            .with_locale(DeterministicLocaleBackend::default())
            .with_log(TraceLog(std::env::var_os("MUGFX_TRACE").is_some()))
            .with_movie(movie)
            .with_viewport_dimensions(w, h, 1.0)
            .with_scale_mode(StageScaleMode::NoScale, true)
            .with_align(StageAlign::TOP | StageAlign::LEFT, true)
            .with_autoplay(true)
            .with_external_interface(Box::new(Provider(slot.clone())))
            .with_max_execution_duration(Duration::from_secs(5))
            .build();
        {
            let mut p = player.lock().unwrap();
            p.set_window_mode("transparent");
            p.set_viewport_dimensions(ViewportDimensions { width: w, height: h, scale_factor: 1.0 });
        }
        Ok(Box::new(MuGfx {
            player,
            slot,
            pending: RefCell::new(Vec::new()),
            width: w,
            height: h,
            reply: RefCell::new(CString::default()),
            stats: RefCell::new(Stats::default()),
        }))
    })();
    match result {
        Ok(g) => Box::into_raw(g),
        Err(e) => {
            write_error(err, err_cap, &e);
            std::ptr::null_mut()
        }
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_close(g: *mut MuGfx) {
    if !g.is_null() {
        drop(unsafe { Box::from_raw(g) });
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_set_callback(g: *mut MuGfx, callback: MuGfxCallback, user: *mut c_void) {
    let Some(g) = (unsafe { g.as_ref() }) else { return };
    let mut slot = g.slot.lock().unwrap();
    slot.callback = callback;
    slot.user = user;
}

/// Run the first frame(s) without waiting for time to pass (preload + one
/// frame), so the movie's onLoad handlers and bridge are in place.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_start(g: *mut MuGfx) {
    let Some(g) = (unsafe { g.as_ref() }) else { return };
    g.with_player(|p| {
        p.preload(&mut ExecutionLimit::none());
        p.run_frame();
    });
    g.run_pending();
}

/// Advance the movie by `dt_ms` of real time (frames, timers, tweens).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_advance(g: *mut MuGfx, dt_ms: f64) {
    let Some(g) = (unsafe { g.as_ref() }) else { return };
    let t = Instant::now();
    g.with_player(|p| p.tick(FloatDuration::from_millis(dt_ms)));
    g.run_pending();
    g.stats.borrow_mut().0.last_advance_ms = t.elapsed().as_secs_f64() * 1000.0;
}

/// Render the current frame and copy it (straight-alpha RGBA, top row first,
/// width*height*4 bytes) into `rgba`.  Returns 0 on success.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_render(g: *mut MuGfx, rgba: *mut u8, capacity: usize) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return -1 };
    let need = (g.width * g.height * 4) as usize;
    if rgba.is_null() || capacity < need {
        return -2;
    }
    let t = Instant::now();
    g.with_player(|p| p.render());
    let t_render = t.elapsed();
    let image = g.with_player(|p| {
        let renderer = <dyn Any>::downcast_mut::<WgpuRenderBackend<TextureTarget>>(p.renderer_mut())?;
        renderer.capture_frame()
    });
    let t_total = t.elapsed();
    let Some(image) = image else { return -3 };
    let raw = image.as_raw();
    if raw.len() != need {
        return -4;
    }
    unsafe { std::ptr::copy_nonoverlapping(raw.as_ptr(), rgba, need) };
    let mut s = g.stats.borrow_mut();
    s.0.frames_rendered += 1;
    s.0.last_render_ms = t_render.as_secs_f64() * 1000.0;
    s.0.last_capture_ms = (t_total - t_render).as_secs_f64() * 1000.0;
    0
}

/// GFx `Invoke`: call `method` on the object at the AS2 path `path` (for
/// example `_root.g_mcInventory`) with a JSON array of arguments.  Returns
/// the JSON result (valid until the next call on this movie) or NULL when the
/// call was queued (made from inside a callback).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_invoke(g: *mut MuGfx, path: *const c_char, method: *const c_char,
                                      args_json: *const c_char) -> *const c_char {
    let Some(g) = (unsafe { g.as_ref() }) else { return std::ptr::null() };
    let (Some(path), Some(method)) = (unsafe { cstr(path) }, unsafe { cstr(method) }) else {
        return std::ptr::null();
    };
    let args = unsafe { cstr(args_json) }
        .and_then(|s| serde_json::from_str::<serde_json::Value>(s).ok())
        .map(|v| from_json(&v))
        .unwrap_or(ExternalValue::List(vec![]));
    let args = match args {
        ExternalValue::List(_) => args,
        other => ExternalValue::List(vec![other]),
    };
    if IN_PLAYER.with(|c| c.get()) {
        g.pending.borrow_mut().push(Pending::Invoke(path.into(), method.into(), args));
        return std::ptr::null();
    }
    let result = g.call_bridge("__mu_invoke", vec![path.into(), method.into(), args]);
    g.run_pending();
    let text = to_json(&result).to_string();
    *g.reply.borrow_mut() = CString::new(text).unwrap_or_default();
    g.reply.borrow().as_ptr()
}

/// GFx `SetVariable(path, value)` with a JSON value.  Returns 0 (or 1 when queued).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_set_variable(g: *mut MuGfx, path: *const c_char, value_json: *const c_char) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return -1 };
    let Some(path) = (unsafe { cstr(path) }) else { return -1 };
    let value = unsafe { cstr(value_json) }
        .and_then(|s| serde_json::from_str::<serde_json::Value>(s).ok())
        .map(|v| from_json(&v))
        .unwrap_or(ExternalValue::Null);
    if IN_PLAYER.with(|c| c.get()) {
        g.pending.borrow_mut().push(Pending::Set(path.into(), value));
        return 1;
    }
    g.call_bridge("__mu_set", vec![path.into(), value]);
    g.run_pending();
    0
}

/// GFx `GetVariable(path)` as JSON (valid until the next call on this movie).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_get_variable(g: *mut MuGfx, path: *const c_char) -> *const c_char {
    let Some(g) = (unsafe { g.as_ref() }) else { return std::ptr::null() };
    let Some(path) = (unsafe { cstr(path) }) else { return std::ptr::null() };
    if IN_PLAYER.with(|c| c.get()) {
        return std::ptr::null();
    }
    let result = g.call_bridge("__mu_get", vec![path.into()]);
    *g.reply.borrow_mut() = CString::new(to_json(&result).to_string()).unwrap_or_default();
    g.reply.borrow().as_ptr()
}

/// Mouse input in viewport pixels.  `kind`: 0 move, 1 down, 2 up;
/// `button`: 0 left, 1 right, 2 middle.  Returns 1 when the movie handled it.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_mouse(g: *mut MuGfx, kind: c_int, button: c_int, x: f64, y: f64) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    let button = match button {
        1 => MouseButton::Right,
        2 => MouseButton::Middle,
        _ => MouseButton::Left,
    };
    let event = match kind {
        1 => PlayerEvent::MouseDown { x, y, button, index: None },
        2 => PlayerEvent::MouseUp { x, y, button },
        _ => PlayerEvent::MouseMove { x, y },
    };
    let handled = g.with_player(|p| p.handle_event(event));
    g.run_pending();
    handled as c_int
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_stats(g: *mut MuGfx, out: *mut MuGfxStats) {
    let (Some(g), false) = (unsafe { g.as_ref() }, out.is_null()) else { return };
    let mut s = g.stats.borrow().0;
    s.external_calls = g.slot.lock().unwrap().calls;
    unsafe { *out = s };
}

/// The adapter Ruffle renders with (for logs), e.g. "Apple M5 (Metal)".
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_adapter(out: *mut c_char, cap: usize) {
    let text = match descriptors() {
        Ok(d) => {
            let info = d.adapter.get_info();
            format!("{} ({:?})", info.name, info.backend)
        }
        Err(e) => format!("no adapter: {e}"),
    };
    write_error(out, cap, &text);
}

/// 1 when the movie changed since the last render (Ruffle's invalidation).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_needs_render(g: *mut MuGfx) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    g.with_player(|p| p.needs_render()) as c_int
}
