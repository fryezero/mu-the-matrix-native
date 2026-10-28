//! Opt-in queue timestamps around the entire shared movie render call, including
//! offscreen/filter flushes. Intervals include CPU encoding gaps and queue bubbles;
//! they are not GPU busy time. No added waits, 64 in-flight slots globally.
//! MU_GFX_GPU_LOG is a private JSONL path. Missing samples are never zero time.
use std::fs::File;
use std::io::Write;
use std::sync::{Arc, Mutex, OnceLock};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use ruffle_render_wgpu::wgpu;

static FRAME: AtomicU64 = AtomicU64::new(0);
static SUBMISSIONS: AtomicU64 = AtomicU64::new(0);
static LOG: OnceLock<Option<Arc<Mutex<File>>>> = OnceLock::new();
fn log() -> Option<Arc<Mutex<File>>> {
    LOG.get_or_init(|| std::env::var_os("MU_GFX_GPU_LOG").and_then(|p| {
        match File::create(p) {
            Ok(file) => Some(Arc::new(Mutex::new(file))),
            Err(e) => { eprintln!("mugfx GPU log: {e}"); None }
        }
    })).clone()
}

/// Optional ABI-3 extension. The host tags all submissions with its render frame.
#[unsafe(no_mangle)]
pub extern "C" fn mugfx_perf_frame(frame: u64) {
    FRAME.store(frame, Ordering::Relaxed);
    SUBMISSIONS.store(0, Ordering::Relaxed);
}

/// End marker distinguishes a cached frame (zero submissions) from lost data.
#[unsafe(no_mangle)]
pub extern "C" fn mugfx_perf_end() {
    if let Some(log) = log() {
        let _ = writeln!(log.lock().unwrap(), "{{\"frame\":{},\"event\":\"end\",\"submissions\":{}}}",
            FRAME.load(Ordering::Relaxed), SUBMISSIONS.load(Ordering::Relaxed));
    }
}

struct Slot {
    resolve: wgpu::Buffer,
    read: wgpu::Buffer,
    ready: Arc<AtomicBool>,
}

pub struct Timer { query: wgpu::QuerySet, slots: Vec<Slot>, movie: u32, log: Arc<Mutex<File>>, marker: wgpu::TextureView, pipeline: wgpu::RenderPipeline }
impl Timer {
    pub fn new(device: &wgpu::Device, movie: u32) -> Option<Self> {
        let log = log()?;
        let supported = device.features().contains(wgpu::Features::TIMESTAMP_QUERY);
        let _ = writeln!(log.lock().unwrap(), "{{\"movie\":{movie},\"supported\":{supported}}}");

        if !supported { return None; }
        // One Metal counter sample buffer. A QuerySet per slot exhausts the
        // driver's counter-buffer allocation before the first movie renders.
        let query = device.create_query_set(&wgpu::QuerySetDescriptor {
            label: Some("mugfx perf"), ty: wgpu::QueryType::Timestamp, count: 128,
        });
        let slots = (0..64).map(|_| Slot {
            resolve: device.create_buffer(&wgpu::BufferDescriptor {
                label: Some("mugfx perf resolve"), size: 16,
                usage: wgpu::BufferUsages::QUERY_RESOLVE | wgpu::BufferUsages::COPY_SRC,
                mapped_at_creation: false,
            }),
            read: device.create_buffer(&wgpu::BufferDescriptor {
                label: Some("mugfx perf read"), size: 16,
                usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
                mapped_at_creation: false,
            }),
            ready: Arc::new(AtomicBool::new(true)),
        }).collect();
        let marker = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("mugfx timestamp marker"),
            size: wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 1 },
            mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2,
            format: wgpu::TextureFormat::Rgba8Unorm,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT, view_formats: &[],
        }).create_view(&Default::default());
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("mugfx timer"),
            source: wgpu::ShaderSource::Wgsl(r#"
                @vertex fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
                    let p = array(vec2f(-1., -1.), vec2f(3., -1.), vec2f(-1., 3.));
                    return vec4f(p[i], 0., 1.);
                }
                @fragment fn fs() -> @location(0) vec4f { return vec4f(0.); }
            "#.into()),
        });
        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("mugfx timer"), layout: None,
            vertex: wgpu::VertexState { module: &shader, entry_point: Some("vs"),
                compilation_options: Default::default(), buffers: &[] },
            primitive: Default::default(), depth_stencil: None, multisample: Default::default(),
            fragment: Some(wgpu::FragmentState { module: &shader, entry_point: Some("fs"),
                compilation_options: Default::default(), targets: &[Some(wgpu::ColorTargetState {
                    format: wgpu::TextureFormat::Rgba8Unorm, blend: None, write_mask: wgpu::ColorWrites::ALL,
                })] }), multiview_mask: None, cache: None,
        });
        Some(Self { query, slots, movie, log, marker, pipeline })
    }
    pub fn begin(&self, device: &wgpu::Device) -> Option<(usize, wgpu::CommandBuffer, wgpu::CommandBuffer)> {
        SUBMISSIONS.fetch_add(1, Ordering::Relaxed);
        let Some((i, s)) = self.slots.iter().enumerate().find(|(_, s)| s.ready.swap(false, Ordering::Acquire)) else {
            let _ = writeln!(self.log.lock().unwrap(), "{{\"frame\":{},\"movie\":{},\"dropped\":true}}",
                FRAME.load(Ordering::Relaxed), self.movie);
            return None;
        };
        let mut begin = device.create_command_encoder(&Default::default());
        // Pass-boundary timestamps work with Apple's counter sampling and
        // Ruffle's GL-ES limits, which intentionally disable compute shaders.
        self.mark(&mut begin, i as u32 * 2);
        let mut end = device.create_command_encoder(&Default::default());
        self.mark(&mut end, i as u32 * 2 + 1);
        end.resolve_query_set(&self.query, i as u32 * 2..i as u32 * 2 + 2, &s.resolve, 0);
        end.copy_buffer_to_buffer(&s.resolve, 0, &s.read, 0, 16);
        Some((i, begin.finish(), end.finish()))
    }
    fn mark(&self, encoder: &mut wgpu::CommandEncoder, index: u32) {
        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("mugfx timestamp"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: &self.marker, depth_slice: None, resolve_target: None,
                ops: wgpu::Operations { load: wgpu::LoadOp::Clear(wgpu::Color::TRANSPARENT),
                    store: wgpu::StoreOp::Store },
            })],
            depth_stencil_attachment: None, occlusion_query_set: None,
            timestamp_writes: Some(wgpu::RenderPassTimestampWrites {
                query_set: &self.query, beginning_of_pass_write_index: if index % 2 == 0 { Some(index) } else { None },
                end_of_pass_write_index: if index % 2 == 1 { Some(index) } else { None },
            }), multiview_mask: None,
        });
        pass.set_pipeline(&self.pipeline);
        pass.draw(0..3, 0..1);
    }
    pub fn submitted(&self, i: usize, period: f32) {
        let s = &self.slots[i];
        let read = s.read.clone();
        let ready = s.ready.clone();
        let log = self.log.clone();
        let movie = self.movie;
        let frame = FRAME.load(Ordering::Relaxed);
        s.read.slice(..).map_async(wgpu::MapMode::Read, move |result| {
            if result.is_ok() {
                let bytes = read.slice(..).get_mapped_range().expect("mapped timer buffer");
                let start = u64::from_ne_bytes(bytes[0..8].try_into().unwrap());
                let end = u64::from_ne_bytes(bytes[8..16].try_into().unwrap());
                if end < start || start == 0 || end == 0 {
                    let _ = writeln!(log.lock().unwrap(), "{{\"frame\":{frame},\"movie\":{movie},\"invalid\":true,\"start\":{start},\"end\":{end}}}");
                    drop(bytes);
                    read.unmap();
                    ready.store(true, Ordering::Release);
                    return;
                }
                let ms = (end - start) as f64 * period as f64 / 1.0e6;
                let _ = writeln!(log.lock().unwrap(), "{{\"frame\":{frame},\"movie\":{movie},\"gpu_ms\":{ms}}}");
                drop(bytes);
                read.unmap();
            } else {
                let _ = writeln!(log.lock().unwrap(), "{{\"frame\":{frame},\"movie\":{movie},\"map_error\":true}}");
            }
            ready.store(true, Ordering::Release);
        });
    }
}

/// Bracket all Ruffle submissions, including ActiveFrame::submit_direct flushes.
/// Keep normal rendering byte-for-byte on the old path when logging is disabled.
pub fn render(f: impl FnOnce()) {
    static TIMER: OnceLock<Option<Timer>> = OnceLock::new();
    let timer = TIMER.get_or_init(|| {
        if log().is_none() { return None; }
        crate::descriptors().ok().and_then(|d| Timer::new(&d.device, 0))
    });
    let Some(timer) = timer else { f(); return };
    let d = crate::descriptors().unwrap();
    let timing = timer.begin(&d.device);
    if let Some((i, begin, end)) = timing {
        d.queue.submit([begin]);
        f();
        d.queue.submit([end]);
        timer.submitted(i, d.queue.get_timestamp_period());
    } else { f(); }
}
