//! Opt-in GPU timestamps around every IOSurface movie submission, including
//! filters and copies. Diagnostic only: no waits, four in-flight slots per movie.
//! MU_GFX_GPU_LOG is a private JSONL path. Missing samples are never zero time.
use std::fs::File;
use std::io::Write;
use std::sync::{Arc, Mutex, OnceLock};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use ruffle_render_wgpu::wgpu;

static FRAME: AtomicU64 = AtomicU64::new(0);
static LOG: OnceLock<Option<Arc<Mutex<File>>>> = OnceLock::new();
fn log() -> Option<Arc<Mutex<File>>> {
    LOG.get_or_init(|| std::env::var_os("MU_GFX_GPU_LOG").map(|p| {
        Arc::new(Mutex::new(File::create(p).expect("MU_GFX_GPU_LOG must be writable")))
    })).clone()
}

/// Optional ABI-3 extension. The host tags all submissions with its render frame.
#[unsafe(no_mangle)]
pub extern "C" fn mugfx_perf_frame(frame: u64) { FRAME.store(frame, Ordering::Relaxed); }

struct Slot {
    query: wgpu::QuerySet,
    resolve: wgpu::Buffer,
    read: wgpu::Buffer,
    ready: Arc<AtomicBool>,
}

pub struct Timer { slots: Vec<Slot>, movie: u32, log: Arc<Mutex<File>> }
impl Timer {
    pub fn new(device: &wgpu::Device, movie: u32) -> Option<Self> {
        let log = log()?;
        let supported = device.features().contains(wgpu::Features::TIMESTAMP_QUERY |
            wgpu::Features::TIMESTAMP_QUERY_INSIDE_ENCODERS);
        writeln!(log.lock().unwrap(), "{{\"movie\":{movie},\"supported\":{supported}}}").unwrap();
        if !supported { return None; }
        let slots = (0..4).map(|_| Slot {
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
        Some(Self { slots, movie, log })
    }
    pub fn begin(&self, device: &wgpu::Device) -> Option<(usize, wgpu::CommandBuffer, wgpu::CommandBuffer)> {
        let Some((i, s)) = self.slots.iter().enumerate().find(|(_, s)| s.ready.swap(false, Ordering::Acquire)) else {
            writeln!(self.log.lock().unwrap(), "{{\"frame\":{},\"movie\":{},\"dropped\":true}}",
                FRAME.load(Ordering::Relaxed), self.movie).unwrap();
            return None;
        };
        let mut begin = device.create_command_encoder(&Default::default());
        begin.write_timestamp(&s.query, 0);
        let mut end = device.create_command_encoder(&Default::default());
        end.write_timestamp(&s.query, 1);
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
                let bytes = read.slice(..).get_mapped_range();
                let start = u64::from_ne_bytes(bytes[0..8].try_into().unwrap());
                let end = u64::from_ne_bytes(bytes[8..16].try_into().unwrap());
                let ms = end.saturating_sub(start) as f64 * period as f64 / 1.0e6;
                writeln!(log.lock().unwrap(), "{{\"frame\":{frame},\"movie\":{movie},\"gpu_ms\":{ms}}}").unwrap();
                drop(bytes);
                read.unmap();
            } else {
                writeln!(log.lock().unwrap(), "{{\"frame\":{frame},\"movie\":{movie},\"map_error\":true}}").unwrap();
            }
            ready.store(true, Ordering::Release);
        });
    }
}
