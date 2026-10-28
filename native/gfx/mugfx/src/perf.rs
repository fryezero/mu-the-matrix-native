//! Opt-in Metal queue interval for the complete host GFx frame, including
//! Ruffle's offscreen/filter flushes. Includes CPU encoding gaps, not GPU busy
//! time. Two four-byte copy markers bracket the same queue. No frame waits; only diagnostic shutdown drains outstanding samples.

#[cfg(target_os = "macos")]
mod metal {
    use std::fs::File;
    use std::io::Write;
    use objc2::rc::Retained;
    use objc2::runtime::ProtocolObject;
    use objc2_metal::{MTLCommandBuffer, MTLCommandBufferStatus};
    use ruffle_render_wgpu::wgpu;
    type Raw = Retained<ProtocolObject<dyn MTLCommandBuffer>>;
    struct Sample { frame: u64, begin: Raw, end: Raw }
    pub struct State {
        log: File,
        frame: u64,
        active: Option<Raw>,
        attempted: bool,
        pending: Vec<Sample>,
        src: wgpu::Buffer,
        dst: wgpu::Buffer,
    }
    impl State {
        pub fn new() -> Option<Self> {
            let path = std::env::var_os("MU_GFX_GPU_LOG")?;
            let mut log = File::create(path).ok()?;
            let d = crate::descriptors().ok()?;
            let supported = unsafe { d.device.as_hal::<wgpu::hal::api::Metal>() }.is_some();
            let _ = writeln!(log, "{{\"supported\":{supported}}}");
            if !supported { return None; }
            let src = d.device.create_buffer(&wgpu::BufferDescriptor {
                label: Some("GFx timer source"), size: 4, usage: wgpu::BufferUsages::COPY_SRC,
                mapped_at_creation: false,
            });
            let dst = d.device.create_buffer(&wgpu::BufferDescriptor {
                label: Some("GFx timer destination"), size: 4, usage: wgpu::BufferUsages::COPY_DST,
                mapped_at_creation: false,
            });
            Some(Self { log, frame: 0, active: None, attempted: false, pending: Vec::new(), src, dst })
        }
        fn marker(&self) -> Option<Raw> {
            let d = crate::descriptors().ok()?;
            let mut encoder = d.device.create_command_encoder(&Default::default());
            encoder.copy_buffer_to_buffer(&self.src, 0, &self.dst, 0, 4);
            // Retain for read-only status/timestamp access after wgpu submits it.
            // Never commit, mutate or release wgpu's reference to this buffer.
            let raw = unsafe { encoder.as_hal_mut::<wgpu::hal::api::Metal, _, _>(|e| {
                e.and_then(|e| e.raw_command_buffer()).and_then(|raw| {
                    Retained::retain(raw as *const _ as *mut ProtocolObject<dyn MTLCommandBuffer>)
                })
            }) };
            d.queue.submit([encoder.finish()]);
            raw
        }
        pub fn frame(&mut self, frame: u64) { self.drain(false); self.frame = frame; }
        pub fn begin(&mut self) {
            if self.attempted { return; }
            self.attempted = true;
            if self.pending.len() < 64 { self.active = self.marker(); }
            if self.active.is_none() {
                let _ = writeln!(self.log, "{{\"frame\":{},\"dropped\":true}}", self.frame);
            }
        }
        pub fn end(&mut self) {
            if let Some(begin) = self.active.take() {
                if let Some(end) = self.marker() {
                    self.pending.push(Sample { frame: self.frame, begin, end });
                }
            }
            let submissions = u32::from(self.attempted);
            self.attempted = false;
            let _ = writeln!(self.log, "{{\"frame\":{},\"event\":\"end\",\"submissions\":{submissions}}}", self.frame);
            self.drain(false);
        }
        pub fn drain(&mut self, wait: bool) {
            self.pending.retain(|s| {
                if wait { s.end.waitUntilCompleted(); }
                if s.end.status() < MTLCommandBufferStatus::Completed { return true; }
                let start = s.begin.GPUStartTime();
                let end = s.end.GPUEndTime();
                if s.begin.status() == MTLCommandBufferStatus::Completed &&
                    s.end.status() == MTLCommandBufferStatus::Completed && start > 0.0 && end >= start {
                    let ms = (end - start) * 1000.0;
                    let _ = writeln!(self.log, "{{\"frame\":{},\"gpu_ms\":{ms}}}", s.frame);
                } else {
                    let _ = writeln!(self.log, "{{\"frame\":{},\"invalid\":true}}", s.frame);
                }
                false
            });
        }
    }
}

#[cfg(target_os = "macos")]
fn with_state(f: impl FnOnce(&mut metal::State)) {
    thread_local! { static STATE: std::cell::RefCell<Option<metal::State>> = std::cell::RefCell::new(metal::State::new()); }
    STATE.with(|state| { if let Some(s) = state.borrow_mut().as_mut() { f(s); } });
}

#[unsafe(no_mangle)]
pub extern "C" fn mugfx_perf_frame(frame: u64) {
    #[cfg(target_os = "macos")]
    with_state(|s| s.frame(frame));
    #[cfg(not(target_os = "macos"))]
    let _ = frame;
}
#[unsafe(no_mangle)]
pub extern "C" fn mugfx_perf_end() {
    #[cfg(target_os = "macos")]
    with_state(|s| s.end());
}
pub fn render(f: impl FnOnce()) {
    #[cfg(target_os = "macos")]
    with_state(|s| s.begin());
    f();
}
pub fn flush() {
    #[cfg(target_os = "macos")]
    with_state(|s| s.drain(true));
}
