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
    query: wgpu::QuerySet,
    resolve: wgpu::Buffer,
    read: wgpu::Buffer,
    ready: Arc<AtomicBool>,
}

pub struct Timer { slots: Vec<Slot>, movie: u32, log: Arc<Mutex<File>>, marker: wgpu::ComputePipeline }
impl Timer {
    pub fn new(device: &wgpu::Device, movie: u32) -> Option<Self> {
        let log = log()?;
        let supported = device.features().contains(wgpu::Features::TIMESTAMP_QUERY);
        let _ = writeln!(log.lock().unwrap(), "{{\"movie\":{movie},\"supported\":{supported}}}");

        let slots = (0..if supported { 64 } else { 0 }).map(|_| Slot {
            query: device.create_query_set(&wgpu::QuerySetDescriptor {
                label: Some("mugfx perf"), ty: wgpu::QueryType::Timestamp, count: 2,
            }),
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
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("mugfx timestamp marker"),
            source: wgpu::ShaderSource::Wgsl("@compute @workgroup_size(1) fn main() {}".into()),
        });
        let marker = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("mugfx timestamp marker"), layout: None, module: &shader,
            entry_point: Some("main"), compilation_options: Default::default(), cache: None,
        });
        Some(Self { slots, movie, log, marker })
    }
    pub fn begin(&self, device: &wgpu::Device) -> Option<(usize, wgpu::CommandBuffer, wgpu::CommandBuffer)> {
        SUBMISSIONS.fetch_add(1, Ordering::Relaxed);
        let Some((i, s)) = self.slots.iter().enumerate().find(|(_, s)| s.ready.swap(false, Ordering::Acquire)) else {
            let _ = writeln!(self.log.lock().unwrap(), "{{\"frame\":{},\"movie\":{},\"dropped\":true}}",
                FRAME.load(Ordering::Relaxed), self.movie);
            return None;
        };
        let mut begin = device.create_command_encoder(&Default::default());
        // Apple GPUs expose pass-boundary timestamps, not encoder timestamps.
        { let mut pass = begin.begin_compute_pass(&wgpu::ComputePassDescriptor {
            label: Some("mugfx perf begin"),
            timestamp_writes: Some(wgpu::ComputePassTimestampWrites {
                query_set: &s.query, beginning_of_pass_write_index: Some(0), end_of_pass_write_index: None,
            }),
        });
        pass.set_pipeline(&self.marker);
        pass.dispatch_workgroups(1, 1, 1); }
        let mut end = device.create_command_encoder(&Default::default());
        { let mut pass = end.begin_compute_pass(&wgpu::ComputePassDescriptor {
            label: Some("mugfx perf end"),
            timestamp_writes: Some(wgpu::ComputePassTimestampWrites {
                query_set: &s.query, beginning_of_pass_write_index: None, end_of_pass_write_index: Some(1),
            }),
        });
        pass.set_pipeline(&self.marker);
        pass.dispatch_workgroups(1, 1, 1); }
        end.resolve_query_set(&s.query, 0..2, &s.resolve, 0);
        end.copy_buffer_to_buffer(&s.resolve, 0, &s.read, 0, 16);
        Some((i, begin.finish(), end.finish()))
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
                if end < start {
                    let _ = writeln!(log.lock().unwrap(), "{{\"frame\":{frame},\"movie\":{movie},\"invalid\":true}}");
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
