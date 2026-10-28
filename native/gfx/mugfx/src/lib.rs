//! mugfx: a C ABI that plays one converted GFx movie with Ruffle (NATIVE-GFX-001, NATIVE-GFX-002).
//!
//! The native client creates one `mugfx` per GFx window, like the client's
//! GFx manager creates one movie per window.  The game side talks to the
//! movie through the same two channels GFx offers:
//!
//! * movie -> game: `ExternalInterface.call(name, args...)` arrives at the
//!   registered C callback as `(name, JSON array)`; its optional JSON reply is
//!   returned to ActionScript.  `fscommand(cmd, arg)` arrives as the name
//!   `"fscommand"` with `[cmd, arg]`;
//! * game -> movie: `mugfx_invoke(path, method, JSON args)` (GFx
//!   `Movie::Invoke` / `Value::Invoke`) and `mugfx_set_variable` (GFx
//!   `SetVariable`).  Both go through the `__mu_*` bridge callbacks that
//!   `native/gfx/gfxconvert.py --bridge` adds to the converted SWF.
//!
//! Calls made from inside the C callback (while the player is running) are
//! queued and run after the current advance, so callbacks may invoke freely.
//!
//! NATIVE-GFX-002 adds keyboard and text input, GFx-style hit testing and
//! cursor shapes (through the GFx extensions of the pinned Ruffle patch
//! series, `native/gfx/ruffle-patches`), device fonts, window-sized players
//! (`mugfx_set_view`) and, on macOS, rendering straight into an IOSurface
//! that the host's OpenGL compositor samples (`mugfx_open_shared`), which
//! removes the GPU -> CPU -> GL copy.
//!
//! NATIVE-GFX-003 (ABI 3) lets movies load other movies (`loadClip`) from
//! the root movie's directory (`navigator.rs`), as the client's base movie,
//! UI loader and item windows (`Icons.swf`) do, and lets the host supply the
//! game images of a movie (`mugfx_set_image`, GFx's game-provided external
//! images such as base.swf's `image0`, through the patch series).

use std::any::Any;
use std::cell::{Cell, RefCell};
use std::collections::HashMap;
use std::ffi::{CStr, CString, c_char, c_int, c_void};
use std::path::Path;
use std::rc::Rc;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::{Duration, Instant};

use ruffle_core::backend::locale::DeterministicLocaleBackend;
use ruffle_core::backend::navigator::NullExecutor;
use ruffle_core::backend::log::LogBackend;
use ruffle_core::backend::ui::{
    DialogResultFuture, FileFilter, FontDefinition, FullscreenError, LanguageIdentifier, MouseCursor,
    MultiDialogResultFuture, US_ENGLISH, UiBackend,
};
use ruffle_core::context::UpdateContext;
use ruffle_core::events::{
    ImeEvent, KeyDescriptor, KeyLocation, LogicalKey, MouseButton, NamedKey, PhysicalKey, TextControlCode,
};
use ruffle_core::external::{
    ExternalInterfaceProvider, FsCommandProvider, Value as ExternalValue,
};
use ruffle_core::font::{FontFileData, FontQuery};
use ruffle_core::limits::ExecutionLimit;
use ruffle_core::tag_utils::movie_from_path;
use ruffle_core::{FloatDuration, Player, PlayerBuilder, PlayerEvent, StageAlign, StageScaleMode,
                  ViewportDimensions};
use ruffle_render_wgpu::backend::{WgpuRenderBackend, create_wgpu_instance, request_adapter_and_device};
use ruffle_render_wgpu::descriptors::Descriptors;
use ruffle_render_wgpu::target::TextureTarget;
use ruffle_render_wgpu::wgpu;
use url::Url;

#[cfg(target_os = "macos")]
mod surface;
mod perf;
mod navigator;

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

// --------------------------------------------------------------------------- device fonts

/// Device font name (lowercase) -> font files `(path, bold, italic)`.  The
/// host may add entries (`mugfx_register_font`); the defaults map the
/// client's device font names to fonts that ship with macOS.
static FONTS: OnceLock<Mutex<HashMap<String, Vec<(String, bool, bool)>>>> = OnceLock::new();

const SUPPLEMENTAL: &str = "/System/Library/Fonts/Supplemental";

fn default_fonts() -> HashMap<String, Vec<(String, bool, bool)>> {
    let family = |stem: &str| -> Vec<(String, bool, bool)> {
        [("", false, false), (" Bold", true, false), (" Italic", false, true), (" Bold Italic", true, true)]
            .iter()
            .map(|(suffix, b, i)| (format!("{SUPPLEMENTAL}/{stem}{suffix}.ttf"), *b, *i))
            .filter(|(p, _, _)| Path::new(p).exists())
            .collect()
    };
    let unicode = vec![(format!("{SUPPLEMENTAL}/Arial Unicode.ttf"), false, false)];
    let mut map = HashMap::new();
    // Names used by the client's movies (static, gfx_inventory.py): Times New
    // Roman (26 movies), Agency FB, MS PGothic, Slate Mobile, plus the GFx
    // font map's Arial Unicode MS and common Windows UI fonts.
    map.insert("times new roman".into(), family("Times New Roman"));
    map.insert("arial".into(), family("Arial"));
    map.insert("tahoma".into(), family("Tahoma"));
    map.insert("verdana".into(), family("Verdana"));
    map.insert("agency fb".into(), family("Arial Narrow"));
    map.insert("arial narrow".into(), family("Arial Narrow"));
    map.insert("arial unicode ms".into(), unicode.clone());
    map.insert("ms pgothic".into(), unicode.clone());
    map.insert("nanumgothic".into(), unicode.clone());
    map.insert("nanumgothic bold".into(), unicode.clone());
    map.insert("slate mobile".into(), family("Arial"));
    map.insert("*".into(), unicode);
    map
}

fn fonts() -> &'static Mutex<HashMap<String, Vec<(String, bool, bool)>>> {
    FONTS.get_or_init(|| Mutex::new(default_fonts()))
}

fn font_file_cache() -> &'static Mutex<HashMap<String, Arc<Vec<u8>>>> {
    static CACHE: OnceLock<Mutex<HashMap<String, Arc<Vec<u8>>>>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(HashMap::new()))
}

fn read_font(path: &str) -> Option<Arc<Vec<u8>>> {
    let mut cache = font_file_cache().lock().unwrap();
    if let Some(data) = cache.get(path) {
        return Some(data.clone());
    }
    let data = Arc::new(std::fs::read(path).ok()?);
    cache.insert(path.to_string(), data.clone());
    Some(data)
}

/// Shared state between the UI backend (owned by the player) and the handle.
#[derive(Default)]
struct UiState {
    cursor: Cell<u8>,
    clipboard: RefCell<String>,
    fonts_loaded: RefCell<Vec<String>>,
}

struct MuUi(Rc<UiState>);

impl UiBackend for MuUi {
    fn mouse_visible(&self) -> bool {
        true
    }

    fn set_mouse_visible(&mut self, _visible: bool) {}

    fn set_mouse_cursor(&mut self, cursor: MouseCursor) {
        self.0.cursor.set(match cursor {
            MouseCursor::Arrow => 0,
            MouseCursor::Hand => 1,
            MouseCursor::IBeam => 2,
            MouseCursor::Grab => 3,
        });
    }

    fn clipboard_content(&mut self) -> String {
        self.0.clipboard.borrow().clone()
    }

    fn set_clipboard_content(&mut self, content: String) {
        *self.0.clipboard.borrow_mut() = content;
    }

    fn set_fullscreen(&mut self, _is_full: bool) -> Result<(), FullscreenError> {
        Ok(())
    }

    fn display_root_movie_download_failed_message(&self, _invalid_swf: bool, _fetch_error: String) {}

    fn message(&self, _message: &str) {}

    fn display_unsupported_video(&self, _url: Url) {}

    fn load_device_font(&self, query: &FontQuery, register: &mut dyn FnMut(FontDefinition)) {
        let entries = {
            let map = fonts().lock().unwrap();
            map.get(&query.lowercase_name).or_else(|| map.get("*")).cloned().unwrap_or_default()
        };
        // Prefer the requested style, then the regular face.
        let pick = entries
            .iter()
            .find(|(_, b, i)| *b == query.is_bold && *i == query.is_italic)
            .or_else(|| entries.iter().find(|(_, b, i)| !*b && !*i))
            .or(entries.first());
        if let Some((path, _, _)) = pick
            && let Some(data) = read_font(path)
        {
            self.0.fonts_loaded.borrow_mut().push(format!("{} <- {}", query.name, path));
            register(FontDefinition::FontFile {
                name: query.name.clone(),
                is_bold: query.is_bold,
                is_italic: query.is_italic,
                data: FontFileData::new((*data).clone()),
                index: 0,
            });
        }
    }

    fn sort_device_fonts(&self, _query: &FontQuery, _register: &mut dyn FnMut(FontDefinition)) -> Vec<FontQuery> {
        Vec::new()
    }

    fn open_virtual_keyboard(&self) {}

    fn close_virtual_keyboard(&self) {}

    fn language(&self) -> LanguageIdentifier {
        US_ENGLISH.clone()
    }

    fn display_file_open_dialog(&mut self, _filters: Vec<FileFilter>) -> Option<DialogResultFuture> {
        None
    }

    fn display_file_open_dialog_multiple(&mut self, _filters: Vec<FileFilter>) -> Option<MultiDialogResultFuture> {
        None
    }

    fn display_file_save_dialog(&mut self, _file_name: String, _title: String) -> Option<DialogResultFuture> {
        None
    }

    fn close_file_dialog(&mut self) {}
}

// --------------------------------------------------------------------------- host callback

struct CallbackSlot {
    callback: MuGfxCallback,
    user: *mut c_void,
    calls: u64,
}

fn call_host(slot: &Mutex<CallbackSlot>, name: &str, json: String) -> Option<String> {
    let (callback, user) = {
        let mut slot = slot.lock().unwrap();
        slot.calls += 1;
        (slot.callback, slot.user)
    };
    let callback = callback?;
    let (Ok(name), Ok(json)) = (CString::new(name), CString::new(json)) else { return None };
    let reply = unsafe { callback(user, name.as_ptr(), json.as_ptr()) };
    if reply.is_null() {
        return None;
    }
    Some(unsafe { CStr::from_ptr(reply) }.to_string_lossy().into_owned())
}

struct Provider(Arc<Mutex<CallbackSlot>>);

impl ExternalInterfaceProvider for Provider {
    fn call_method(&self, _context: &mut UpdateContext<'_>, name: &str, args: &[ExternalValue]) -> ExternalValue {
        let json = serde_json::Value::Array(args.iter().map(to_json).collect()).to_string();
        match call_host(&self.0, name, json) {
            None => ExternalValue::Undefined,
            Some(text) => serde_json::from_str::<serde_json::Value>(&text)
                .map(|v| from_json(&v))
                .unwrap_or(ExternalValue::Null),
        }
    }

    fn on_callback_available(&self, _name: &str) {}

    fn get_id(&self) -> Option<String> {
        None
    }
}

/// `fscommand(cmd, arg)`: the client's movies use `TextInput` (IME focus) and
/// `GFxApplyLanguage`.  Forwarded to the host as `fscommand [cmd, arg]`.
struct FsCommands(Arc<Mutex<CallbackSlot>>);

impl FsCommandProvider for FsCommands {
    fn on_fs_command(&self, command: &str, args: &str) -> bool {
        let json = serde_json::json!([command, args]).to_string();
        call_host(&self.0, "fscommand", json);
        true
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

#[derive(Clone, Copy, PartialEq, Eq)]
enum TargetKind {
    Readback,
    #[cfg(target_os = "macos")]
    Surface,
}

pub struct MuGfx {
    player: Arc<Mutex<Player>>,
    slot: Arc<Mutex<CallbackSlot>>,
    ui: Rc<UiState>,
    pending: RefCell<Vec<Pending>>,
    kind: TargetKind,
    width: Cell<u32>,
    height: Cell<u32>,
    reply: RefCell<CString>,
    stats: RefCell<MuGfxStats>,
    /// Futures of `loadClip` and other loads (polled after each player step).
    executor: RefCell<NullExecutor>,
    /// Directory of the root movie (base of relative loads).
    base: std::path::PathBuf,
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
        let was = IN_PLAYER.with(|c| c.replace(true));
        let r = f(&mut self.player.lock().unwrap());
        IN_PLAYER.with(|c| c.set(was));
        r
    }

    fn run_pending(&self) {
        if IN_PLAYER.with(|c| c.get()) {
            return;
        }
        // Finish movie loads first: their futures lock the player.
        self.executor.borrow_mut().run();
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

    fn event(&self, event: PlayerEvent) -> bool {
        let handled = self.with_player(|p| p.handle_event(event));
        self.run_pending();
        handled
    }
}

fn build_player(path: &str, w: u32, h: u32, kind: TargetKind) -> Result<Box<MuGfx>, String> {
    let descriptors = descriptors()?;
    let movie = movie_from_path(Path::new(path), None).map_err(|e| e.to_string())?;
    let slot = Arc::new(Mutex::new(CallbackSlot { callback: None, user: std::ptr::null_mut(), calls: 0 }));
    let ui = Rc::new(UiState::default());
    let executor = NullExecutor::new();
    let base = Path::new(path).parent().filter(|p| !p.as_os_str().is_empty()).unwrap_or(Path::new("."));
    let builder = PlayerBuilder::new().with_navigator(navigator::MuNavigator::new(base, &executor));
    let builder = match kind {
        TargetKind::Readback => {
            let target = TextureTarget::new(&descriptors.device, (w, h)).map_err(|e| e.to_string())?;
            builder.with_renderer(WgpuRenderBackend::new(descriptors, target).map_err(|e| e.to_string())?)
        }
        #[cfg(target_os = "macos")]
        TargetKind::Surface => {
            let target = surface::SurfaceTarget::new(&descriptors.device, (w, h))?;
            builder.with_renderer(WgpuRenderBackend::new(descriptors, target).map_err(|e| e.to_string())?)
        }
    };
    let player = builder
        .with_ui(MuUi(ui.clone()))
        .with_locale(DeterministicLocaleBackend::default())
        .with_log(TraceLog(std::env::var_os("MUGFX_TRACE").is_some()))
        .with_movie(movie)
        .with_viewport_dimensions(w, h, 1.0)
        .with_scale_mode(StageScaleMode::NoScale, true)
        .with_align(StageAlign::TOP | StageAlign::LEFT, true)
        .with_autoplay(true)
        .with_external_interface(Box::new(Provider(slot.clone())))
        .with_fs_commands(Box::new(FsCommands(slot.clone())))
        .with_max_execution_duration(Duration::from_secs(5))
        .build();
    {
        let mut p = player.lock().unwrap();
        p.set_window_mode("transparent");
        p.set_viewport_dimensions(ViewportDimensions { width: w, height: h, scale_factor: 1.0 });
        // The client's movies run with keyboard focus (GFx movies get key
        // events from the game as long as they are shown).
        p.handle_event(PlayerEvent::FocusGained);
    }
    Ok(Box::new(MuGfx {
        player,
        slot,
        ui,
        pending: RefCell::new(Vec::new()),
        kind,
        width: Cell::new(w),
        height: Cell::new(h),
        reply: RefCell::new(CString::default()),
        stats: RefCell::new(MuGfxStats::default()),
        executor: RefCell::new(executor),
        base: base.to_path_buf(),
    }))
}

fn open_with(path: *const c_char, width: c_int, height: c_int, err: *mut c_char, err_cap: usize,
             kind: TargetKind) -> *mut MuGfx {
    let Some(path) = (unsafe { cstr(path) }) else {
        write_error(err, err_cap, "invalid path");
        return std::ptr::null_mut();
    };
    let (w, h) = (width.max(1) as u32, height.max(1) as u32);
    init_logging();
    match build_player(path, w, h, kind) {
        Ok(g) => Box::into_raw(g),
        Err(e) => {
            write_error(err, err_cap, &e);
            std::ptr::null_mut()
        }
    }
}

/// Load a converted SWF.  `width`/`height` are the viewport in pixels (the
/// movie sees them as Stage.width/height: no scaling, top-left aligned, as the
/// client's GFx windows lay themselves out).  Frames are read back with
/// `mugfx_render`.  Returns NULL on error.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_open(path: *const c_char, width: c_int, height: c_int, err: *mut c_char,
                                    err_cap: usize) -> *mut MuGfx {
    open_with(path, width, height, err, err_cap, TargetKind::Readback)
}

/// Like `mugfx_open`, but the movie renders into an IOSurface (BGRA,
/// premultiplied alpha) that the host binds as a GL texture
/// (`CGLTexImageIOSurface2D`, `GL_TEXTURE_RECTANGLE`); see
/// `mugfx_render_shared` and `mugfx_iosurface`.  macOS only: elsewhere it
/// returns NULL with an error.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_open_shared(path: *const c_char, width: c_int, height: c_int, err: *mut c_char,
                                           err_cap: usize) -> *mut MuGfx {
    #[cfg(target_os = "macos")]
    {
        open_with(path, width, height, err, err_cap, TargetKind::Surface)
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = (path, width, height);
        write_error(err, err_cap, "shared textures need macOS (IOSurface)");
        std::ptr::null_mut()
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_close(g: *mut MuGfx) {
    if !g.is_null() {
        perf::flush();
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
    g.stats.borrow_mut().last_advance_ms = t.elapsed().as_secs_f64() * 1000.0;
}

/// Render the current frame and copy it (straight-alpha RGBA, top row first,
/// width*height*4 bytes of the current viewport) into `rgba`.  Returns 0 on
/// success.  For a shared (IOSurface) movie the surface is read instead.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_render(g: *mut MuGfx, rgba: *mut u8, capacity: usize) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return -1 };
    let need = (g.width.get() * g.height.get() * 4) as usize;
    if rgba.is_null() || capacity < need {
        return -2;
    }
    let t = Instant::now();
    g.with_player(|p| p.render());
    let t_render = t.elapsed();
    let out = unsafe { std::slice::from_raw_parts_mut(rgba, need) };
    let ok = match g.kind {
        TargetKind::Readback => {
            let image = g.with_player(|p| {
                let renderer = <dyn Any>::downcast_mut::<WgpuRenderBackend<TextureTarget>>(p.renderer_mut())?;
                renderer.capture_frame()
            });
            match image {
                Some(image) if image.as_raw().len() == need => {
                    out.copy_from_slice(image.as_raw());
                    true
                }
                _ => false,
            }
        }
        #[cfg(target_os = "macos")]
        TargetKind::Surface => g.with_player(|p| {
            let renderer =
                <dyn Any>::downcast_mut::<WgpuRenderBackend<surface::SurfaceTarget>>(p.renderer_mut());
            renderer.map(|r| r.target().read_rgba(out)).unwrap_or(false)
        }),
    };
    if !ok {
        return -3;
    }
    let t_total = t.elapsed();
    let mut s = g.stats.borrow_mut();
    s.frames_rendered += 1;
    s.last_render_ms = t_render.as_secs_f64() * 1000.0;
    s.last_capture_ms = (t_total - t_render).as_secs_f64() * 1000.0;
    0
}

/// Shared (IOSurface) movies: render the current frame into the surface.
/// With `wait`, block until the GPU has finished it, so the host's GL draw
/// that samples the surface sees the complete frame; without, the host
/// renders several movies and calls `mugfx_gpu_wait` once before drawing.
/// Returns 0 on success.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_render_shared(g: *mut MuGfx, wait: c_int) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return -1 };
    #[cfg(target_os = "macos")]
    if g.kind == TargetKind::Surface {
        let t = Instant::now();
        perf::render(|| g.with_player(|p| p.render()));
        let t_render = t.elapsed();
        let ok = g.with_player(|p| {
            let renderer =
                <dyn Any>::downcast_mut::<WgpuRenderBackend<surface::SurfaceTarget>>(p.renderer_mut());
            renderer
                .map(|r| {
                    if wait != 0 {
                        r.target().wait_idle(&descriptors().unwrap().device)
                    }
                })
                .is_some()
        });
        let t_total = t.elapsed();
        let mut s = g.stats.borrow_mut();
        s.frames_rendered += 1;
        s.last_render_ms = t_render.as_secs_f64() * 1000.0;
        s.last_capture_ms = (t_total - t_render).as_secs_f64() * 1000.0;
        return if ok { 0 } else { -3 };
    }
    -2
}

/// Double-buffered shared surface (NATIVE-GFX-003): 1 makes the movie
/// render into one of two IOSurfaces while `mugfx_iosurface` keeps
/// returning the last completed frame (its seed changes when the shown
/// surface flips), so the host needs no `mugfx_gpu_wait` before drawing;
/// frames show at most one frame later.  0 returns to one surface.
/// Returns 0, or -2 for a non-shared movie.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_set_double_buffer(g: *mut MuGfx, on: c_int) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return -1 };
    #[cfg(target_os = "macos")]
    if g.kind == TargetKind::Surface {
        return g.with_player(|p| {
            let Some(r) = <dyn Any>::downcast_mut::<WgpuRenderBackend<surface::SurfaceTarget>>(p.renderer_mut())
            else {
                return -3;
            };
            r.target().set_double(on != 0);
            0
        });
    }
    let _ = on;
    -2
}

/// Block until every frame submitted so far (all movies share one GPU
/// queue) has completed.
#[unsafe(no_mangle)]
pub extern "C" fn mugfx_gpu_wait() {
    if let Ok(d) = descriptors() {
        let _ = d.device.poll(wgpu::PollType::Wait { submission_index: None, timeout: None });
    }
}

/// The IOSurfaceRef of a shared movie (NULL otherwise), its size and a seed
/// that changes whenever the surface is replaced (after `mugfx_set_view`
/// changed the size): the host rebinds its GL texture when the seed changes.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_iosurface(g: *mut MuGfx, width: *mut c_int, height: *mut c_int,
                                         seed: *mut u32) -> *mut c_void {
    let Some(g) = (unsafe { g.as_ref() }) else { return std::ptr::null_mut() };
    #[cfg(target_os = "macos")]
    if g.kind == TargetKind::Surface {
        return g.with_player(|p| {
            let Some(r) = <dyn Any>::downcast_mut::<WgpuRenderBackend<surface::SurfaceTarget>>(p.renderer_mut())
            else {
                return std::ptr::null_mut();
            };
            let t = r.target();
            unsafe {
                if !width.is_null() {
                    *width = t.size().0 as c_int;
                }
                if !height.is_null() {
                    *height = t.size().1 as c_int;
                }
                if !seed.is_null() {
                    *seed = t.seed();
                }
            }
            t.iosurface_ptr()
        });
    }
    let _ = (width, height, seed);
    std::ptr::null_mut()
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

/// Mouse input in viewport pixels.  `kind`: 0 move, 1 down, 2 up, 3 wheel
/// (`button` = lines, positive up); `button`: 0 left, 1 right, 2 middle.
/// Returns 1 when the movie handled it.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_mouse(g: *mut MuGfx, kind: c_int, button: c_int, x: f64, y: f64) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    let mb = match button {
        1 => MouseButton::Right,
        2 => MouseButton::Middle,
        _ => MouseButton::Left,
    };
    let event = match kind {
        1 => PlayerEvent::MouseDown { x, y, button: mb, index: None },
        2 => PlayerEvent::MouseUp { x, y, button: mb },
        3 => PlayerEvent::MouseWheel { delta: ruffle_core::events::MouseWheelDelta::Lines(button as f64) },
        4 => PlayerEvent::MouseLeave,
        _ => PlayerEvent::MouseMove { x, y },
    };
    g.event(event) as c_int
}

/// GFx `Movie::HitTest(x, y, HitTest_Shapes)`: 1 when a visible shape of the
/// movie that is not under a `hitTestDisable` clip covers the viewport point.
/// The host uses it to decide whether a click belongs to the interface or to
/// the 3D world.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_hit_test(g: *mut MuGfx, x: f64, y: f64) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    g.with_player(|p| p.gfx_hit_test(x, y)) as c_int
}

/// The cursor shape the movie asked for: 0 arrow, 1 hand, 2 I-beam, 3 grab
/// (`Mouse.setCursorType`, buttons, text fields).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_cursor(g: *mut MuGfx) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    g.ui.cursor.get() as c_int
}

fn vk_to_keys(vk: c_int, codepoint: u32) -> (PhysicalKey, LogicalKey, KeyLocation) {
    use NamedKey as N;
    use PhysicalKey as P;
    let ch = char::from_u32(codepoint).filter(|c| !c.is_control());
    let named = |p: PhysicalKey, n: NamedKey| (p, LogicalKey::Named(n), KeyLocation::Standard);
    match vk {
        8 => named(P::Backspace, N::Backspace),
        9 => named(P::Tab, N::Tab),
        13 => named(P::Enter, N::Enter),
        16 => (P::ShiftLeft, LogicalKey::Named(N::Shift), KeyLocation::Left),
        17 => (P::ControlLeft, LogicalKey::Named(N::Control), KeyLocation::Left),
        18 => (P::AltLeft, LogicalKey::Named(N::Alt), KeyLocation::Left),
        20 => named(P::CapsLock, N::CapsLock),
        27 => named(P::Escape, N::Escape),
        32 => (P::Space, LogicalKey::Character(' '), KeyLocation::Standard),
        33 => named(P::PageUp, N::PageUp),
        34 => named(P::PageDown, N::PageDown),
        35 => named(P::End, N::End),
        36 => named(P::Home, N::Home),
        37 => named(P::ArrowLeft, N::ArrowLeft),
        38 => named(P::ArrowUp, N::ArrowUp),
        39 => named(P::ArrowRight, N::ArrowRight),
        40 => named(P::ArrowDown, N::ArrowDown),
        45 => named(P::Insert, N::Insert),
        46 => named(P::Delete, N::Delete),
        48..=57 => {
            let digits = [P::Digit0, P::Digit1, P::Digit2, P::Digit3, P::Digit4, P::Digit5, P::Digit6, P::Digit7,
                          P::Digit8, P::Digit9];
            let c = ch.unwrap_or((b'0' + (vk - 48) as u8) as char);
            (digits[(vk - 48) as usize], LogicalKey::Character(c), KeyLocation::Standard)
        }
        65..=90 => {
            let letters = [P::KeyA, P::KeyB, P::KeyC, P::KeyD, P::KeyE, P::KeyF, P::KeyG, P::KeyH, P::KeyI, P::KeyJ,
                           P::KeyK, P::KeyL, P::KeyM, P::KeyN, P::KeyO, P::KeyP, P::KeyQ, P::KeyR, P::KeyS, P::KeyT,
                           P::KeyU, P::KeyV, P::KeyW, P::KeyX, P::KeyY, P::KeyZ];
            let c = ch.unwrap_or((b'a' + (vk - 65) as u8) as char);
            (letters[(vk - 65) as usize], LogicalKey::Character(c), KeyLocation::Standard)
        }
        112..=123 => {
            let f = [(P::F1, N::F1), (P::F2, N::F2), (P::F3, N::F3), (P::F4, N::F4), (P::F5, N::F5), (P::F6, N::F6),
                     (P::F7, N::F7), (P::F8, N::F8), (P::F9, N::F9), (P::F10, N::F10), (P::F11, N::F11),
                     (P::F12, N::F12)];
            let (p, n) = f[(vk - 112) as usize];
            named(p, n)
        }
        _ => (P::Unknown, ch.map(LogicalKey::Character).unwrap_or(LogicalKey::Unknown), KeyLocation::Standard),
    }
}

fn text_control(vk: c_int, mods: c_int) -> Option<TextControlCode> {
    let shift = mods & 1 != 0;
    let ctrl = mods & 2 != 0;
    let word = mods & 4 != 0;
    Some(match (vk, shift, ctrl) {
        (8, _, _) if word => TextControlCode::BackspaceWord,
        (8, _, _) => TextControlCode::Backspace,
        (46, _, _) if word => TextControlCode::DeleteWord,
        (46, _, _) => TextControlCode::Delete,
        (13, _, _) => TextControlCode::Enter,
        (37, false, _) if word => TextControlCode::MoveLeftWord,
        (37, true, _) if word => TextControlCode::SelectLeftWord,
        (37, false, false) => TextControlCode::MoveLeft,
        (37, true, false) => TextControlCode::SelectLeft,
        (37, false, true) => TextControlCode::MoveLeftLine,
        (37, true, true) => TextControlCode::SelectLeftLine,
        (39, false, _) if word => TextControlCode::MoveRightWord,
        (39, true, _) if word => TextControlCode::SelectRightWord,
        (39, false, false) => TextControlCode::MoveRight,
        (39, true, false) => TextControlCode::SelectRight,
        (39, false, true) => TextControlCode::MoveRightLine,
        (39, true, true) => TextControlCode::SelectRightLine,
        (36, false, _) => TextControlCode::MoveLeftLine,
        (36, true, _) => TextControlCode::SelectLeftLine,
        (35, false, _) => TextControlCode::MoveRightLine,
        (35, true, _) => TextControlCode::SelectRightLine,
        (65, _, true) => TextControlCode::SelectAll,
        (67, _, true) => TextControlCode::Copy,
        (86, _, true) => TextControlCode::Paste,
        (88, _, true) => TextControlCode::Cut,
        _ => return None,
    })
}

/// Keyboard input.  `kind`: 0 down, 1 up.  `vk` is the Windows virtual key
/// code the client and Flash use (`Key.getCode()`, `onHotKey` keyCode: 'I' =
/// 73, Enter = 13, ...); `codepoint` the key's character (0 if none);
/// `mods`: 1 shift, 2 control/command, 4 alt/option.  On key down, editing
/// keys (Backspace, Delete, arrows, Home, End, Enter, Ctrl+A/C/V/X) are also
/// sent to a focused text field.  Typed text arrives with `mugfx_text`.
/// Returns 1 when the movie handled the key.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_key(g: *mut MuGfx, kind: c_int, vk: c_int, codepoint: u32, mods: c_int) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    let (physical_key, logical_key, key_location) = vk_to_keys(vk, codepoint);
    let key = KeyDescriptor { physical_key, logical_key, key_location };
    if kind == 1 {
        return g.event(PlayerEvent::KeyUp { key }) as c_int;
    }
    let mut handled = g.event(PlayerEvent::KeyDown { key });
    if let Some(code) = text_control(vk, mods) {
        handled |= g.event(PlayerEvent::TextControl { code });
    }
    handled as c_int
}

/// Text typed by the user (UTF-8, e.g. SDL_TEXTINPUT or an IME commit) for
/// the focused text field.  Returns 1 when the movie handled it.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_text(g: *mut MuGfx, utf8: *const c_char) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    let Some(text) = (unsafe { cstr(utf8) }) else { return 0 };
    let mut handled = false;
    for codepoint in text.chars() {
        handled |= g.event(PlayerEvent::TextInput { codepoint });
    }
    handled as c_int
}

/// IME composition for the focused text field (NATIVE-GFX-003): `commit`
/// 0 shows `utf8` as the composing text (SDL_TEXTEDITING; the caret at the
/// UTF-8 byte offset `cursor`, -1 hides it; "" ends the composition), 1
/// inserts it.  Returns 1 when the movie handled it.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_ime(g: *mut MuGfx, utf8: *const c_char, cursor: c_int, commit: c_int) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    let text = unsafe { cstr(utf8) }.unwrap_or("").to_string();
    let event = if commit != 0 {
        ImeEvent::Commit(text)
    } else {
        let at = if cursor < 0 { None } else { Some(((cursor as usize).min(text.len()), (cursor as usize).min(text.len()))) };
        ImeEvent::Preedit(text, at)
    };
    g.event(PlayerEvent::Ime(event)) as c_int
}

/// 1 when a text field of the movie has keyboard focus (the host then sends
/// keys to the movie instead of using them as game hotkeys).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_text_focus(g: *mut MuGfx) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return 0 };
    g.with_player(|p| {
        p.mutate_with_update_context(|ctx| ctx.focus_tracker.get_as_edit_text().is_some())
    }) as c_int
}

/// Show only a part of the stage (a window-sized player) and set the
/// backing scale.  The movie keeps a `stage_w` x `stage_h` stage in points
/// (what it lays itself out against); the render target becomes
/// `w * scale` x `h * scale` pixels showing the stage area at (`x`, `y`)
/// points.  Mouse coordinates passed to the movie are viewport pixels.
/// `w` or `h` <= 0 shows the whole stage.  `scale` <= 0 means 1 (a Retina
/// window passes 2 so the interface keeps its size and draws sharp).
/// Returns 0.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_set_view(g: *mut MuGfx, stage_w: c_int, stage_h: c_int, x: c_int, y: c_int,
                                        w: c_int, h: c_int, scale: f64) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return -1 };
    let scale = if scale > 0.0 { scale } else { 1.0 };
    let (vw, vh, view) = if w > 0 && h > 0 {
        (w as f64, h as f64, Some([stage_w as f64, stage_h as f64, x as f64, y as f64]))
    } else {
        (stage_w.max(1) as f64, stage_h.max(1) as f64, Some([stage_w as f64, stage_h as f64, 0.0, 0.0]))
    };
    let (pw, ph) = ((vw * scale).round().max(1.0) as u32, (vh * scale).round().max(1.0) as u32);
    g.with_player(|p| {
        p.set_viewport_dimensions(ViewportDimensions { width: pw, height: ph, scale_factor: scale });
        p.set_gfx_view(view);
    });
    g.width.set(pw);
    g.height.set(ph);
    g.run_pending();
    0
}

/// The current viewport size in pixels.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_size(g: *mut MuGfx, width: *mut c_int, height: *mut c_int) {
    let Some(g) = (unsafe { g.as_ref() }) else { return };
    unsafe {
        if !width.is_null() {
            *width = g.width.get() as c_int;
        }
        if !height.is_null() {
            *height = g.height.get() as c_int;
        }
    }
}

/// Map a device font name used by the movies (e.g. "Times New Roman") to a
/// font file for every player opened afterwards.  `style`: 0 regular, 1 bold,
/// 2 italic, 3 bold italic.  `name` "*" sets the fallback for unknown names.
/// Returns 0, or -1 when the file cannot be read.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_register_font(name: *const c_char, path: *const c_char, style: c_int) -> c_int {
    let (Some(name), Some(path)) = (unsafe { cstr(name) }, unsafe { cstr(path) }) else { return -1 };
    if read_font(path).is_none() {
        return -1;
    }
    let mut map = fonts().lock().unwrap();
    let list = map.entry(name.to_lowercase()).or_default();
    list.retain(|(_, b, i)| (*b, *i) != (style & 1 != 0, style & 2 != 0));
    list.insert(0, (path.to_string(), style & 1 != 0, style & 2 != 0));
    0
}

/// Device fonts this movie resolved so far ("name <- file" lines, for logs).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_fonts_used(g: *mut MuGfx) -> *const c_char {
    let Some(g) = (unsafe { g.as_ref() }) else { return std::ptr::null() };
    let text = g.ui.fonts_loaded.borrow().join("\n");
    *g.reply.borrow_mut() = CString::new(text).unwrap_or_default();
    g.reply.borrow().as_ptr()
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_stats(g: *mut MuGfx, out: *mut MuGfxStats) {
    let (Some(g), false) = (unsafe { g.as_ref() }, out.is_null()) else { return };
    let mut s = *g.stats.borrow();
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

/// ABI version of this library (the host checks it after dlopen).
#[unsafe(no_mangle)]
pub extern "C" fn mugfx_abi_version() -> c_int {
    3
}

/// Supply or update a game image of the movie (GFx: the bitmaps a game
/// provides for a movie's external images, for example base.swf's render
/// targets `image0`..`image7`).  `BitmapData.loadBitmap(name)` in the movie
/// (and the movies it loaded) returns it and shares its pixels.  `rgba` is
/// straight-alpha RGBA, `stride` bytes per row (0: width*4), top row first.
/// Returns 0 on success.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_set_image(g: *mut MuGfx, name: *const c_char, width: c_int, height: c_int,
                                         rgba: *const u8, stride: c_int) -> c_int {
    let Some(g) = (unsafe { g.as_ref() }) else { return -1 };
    let Some(name) = (unsafe { cstr(name) }) else { return -1 };
    if width <= 0 || height <= 0 || rgba.is_null() || IN_PLAYER.with(|c| c.get()) {
        return -2;
    }
    let (w, h) = (width as usize, height as usize);
    let stride = if stride <= 0 { w * 4 } else { stride as usize };
    if stride < w * 4 {
        return -2;
    }
    let src = unsafe { std::slice::from_raw_parts(rgba, stride * (h - 1) + w * 4) };
    let mut packed = Vec::with_capacity(w * h * 4);
    for y in 0..h {
        packed.extend_from_slice(&src[y * stride..y * stride + w * 4]);
    }
    g.with_player(|p| p.set_gfx_image(name, w as u32, h as u32, &packed));
    0
}

/// The local file a movie-relative name (as a movie passes it to `loadClip`)
/// resolves to for the movie `g`, written to `out`; returns its length or -1.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn mugfx_resolve(g: *mut MuGfx, name: *const c_char, out: *mut c_char, cap: usize) -> c_int {
    let (Some(g), Some(name)) = (unsafe { g.as_ref() }, unsafe { cstr(name) }) else { return -1 };
    let base = g.base.clone();
    match navigator::local_file(&base, name) {
        Some(p) => {
            let s = p.to_string_lossy();
            write_error(out, cap, &s);
            s.len() as c_int
        }
        None => -1,
    }
}
