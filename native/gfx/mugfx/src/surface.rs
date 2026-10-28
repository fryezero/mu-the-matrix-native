//! IOSurface render target (macOS, NATIVE-GFX-002).
//!
//! Ruffle renders through wgpu's Metal backend.  This target backs the wgpu
//! render texture with an IOSurface (BGRA8, premultiplied alpha), the same
//! memory the host's OpenGL context can bind with `CGLTexImageIOSurface2D`.
//! A frame therefore reaches the GL compositor without the GPU -> CPU -> GL
//! copy of `TextureTarget`: the only synchronisation is waiting for the
//! frame's command buffer to complete (`wait_idle`).
//!
//! NATIVE-GFX-003: with `set_double`, the target alternates between two
//! surfaces.  A frame renders into the back surface while the host keeps
//! sampling the last completed one (`display`); the host then needs no
//! GPU wait before compositing, at one frame of latency at most.

use std::fmt;
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::{Arc, Mutex};

use objc2_core_foundation::{CFDictionary, CFNumber, CFRetained, CFString};
use objc2_io_surface::{
    IOSurfaceLockOptions, IOSurfaceRef, kIOSurfaceBytesPerElement, kIOSurfaceHeight, kIOSurfacePixelFormat,
    kIOSurfaceWidth,
};
use objc2_metal::{
    MTLDevice, MTLPixelFormat, MTLStorageMode, MTLTextureDescriptor, MTLTextureType, MTLTextureUsage,
};
use ruffle_render_wgpu::target::{RenderTarget, RenderTargetFrame};
use ruffle_render_wgpu::wgpu;

static SEED: AtomicU32 = AtomicU32::new(1);

const FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Bgra8Unorm;

struct Buffer {
    surface: CFRetained<IOSurfaceRef>,
    texture: wgpu::Texture,
    seed: u32,
    done: Arc<AtomicBool>,
}

#[derive(Default)]
struct Flip {
    back: usize,            // the surface the next frame renders into
    display: usize,         // the surface the host samples
    pending: Option<usize>, // submitted, not known complete
}

pub struct SurfaceTarget {
    bufs: Vec<Buffer>,
    flip: Mutex<Flip>,
    want_double: AtomicBool,
    size: (u32, u32),
    last: Mutex<Option<wgpu::SubmissionIndex>>,
    timer: Option<crate::perf::Timer>,
}

impl fmt::Debug for SurfaceTarget {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("SurfaceTarget").field("size", &self.size).field("buffers", &self.bufs.len()).finish()
    }
}

fn buffer(device: &wgpu::Device, size: (u32, u32)) -> Result<Buffer, String> {
    let (surface, texture) = create(device, size)?;
    Ok(Buffer { surface, texture, seed: SEED.fetch_add(1, Ordering::Relaxed), done: Arc::new(AtomicBool::new(true)) })
}

#[derive(Debug)]
pub struct SurfaceFrame(wgpu::TextureView);

impl RenderTargetFrame for SurfaceFrame {
    fn into_view(self) -> wgpu::TextureView {
        self.0
    }

    fn view(&self) -> &wgpu::TextureView {
        &self.0
    }
}

fn create(device: &wgpu::Device, (w, h): (u32, u32)) -> Result<(CFRetained<IOSurfaceRef>, wgpu::Texture), String> {
    let (wn, hn, bpe) = (CFNumber::new_i32(w as i32), CFNumber::new_i32(h as i32), CFNumber::new_i32(4));
    let fmt = CFNumber::new_i32(i32::from_be_bytes(*b"BGRA"));
    let keys: [&CFString; 4] =
        unsafe { [kIOSurfaceWidth, kIOSurfaceHeight, kIOSurfaceBytesPerElement, kIOSurfacePixelFormat] };
    let values: [&CFNumber; 4] = [&wn, &hn, &bpe, &fmt];
    let dict = CFDictionary::<CFString, CFNumber>::from_slices(&keys, &values);
    let surface = unsafe { IOSurfaceRef::new(dict.as_opaque()) }.ok_or("IOSurfaceCreate failed")?;

    let hal_device = unsafe { device.as_hal::<wgpu::hal::api::Metal>() }.ok_or("the wgpu device is not Metal")?;
    let desc = unsafe {
        MTLTextureDescriptor::texture2DDescriptorWithPixelFormat_width_height_mipmapped(
            MTLPixelFormat::BGRA8Unorm,
            w as usize,
            h as usize,
            false,
        )
    };
    desc.setUsage(MTLTextureUsage::RenderTarget | MTLTextureUsage::ShaderRead);
    desc.setStorageMode(MTLStorageMode::Shared);
    let raw = hal_device
        .raw_device()
        .newTextureWithDescriptor_iosurface_plane(&desc, &surface, 0)
        .ok_or("newTextureWithDescriptor:iosurface: failed")?;
    let hal_texture = unsafe {
        wgpu::hal::metal::Device::texture_from_raw(
            raw,
            FORMAT,
            MTLTextureType::Type2D,
            1,
            1,
            wgpu::hal::CopyExtent { width: w, height: h, depth: 1 },
            None,
        )
    };
    drop(hal_device);
    let texture = unsafe {
        device.create_texture_from_hal::<wgpu::hal::api::Metal>(
            hal_texture,
            &wgpu::TextureDescriptor {
                label: Some("mugfx IOSurface target"),
                size: wgpu::Extent3d { width: w, height: h, depth_or_array_layers: 1 },
                mip_level_count: 1,
                sample_count: 1,
                dimension: wgpu::TextureDimension::D2,
                format: FORMAT,
                usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING,
                view_formats: &[],
            },
            wgpu::wgt::TextureUses::UNINITIALIZED,
        )
    };
    Ok((surface, texture))
}

impl SurfaceTarget {
    pub fn new(device: &wgpu::Device, size: (u32, u32)) -> Result<Self, String> {
        let size = (size.0.max(1), size.1.max(1));
        Ok(Self {
            bufs: vec![buffer(device, size)?],
            flip: Mutex::new(Flip::default()),
            want_double: AtomicBool::new(false),
            size,
            last: Mutex::new(None),
            timer: crate::perf::Timer::new(device, SEED.fetch_add(1, Ordering::Relaxed)),
        })
    }

    /// Ask for two alternating surfaces (true) or one (false); applied when
    /// the next frame starts.
    pub fn set_double(&self, on: bool) {
        self.want_double.store(on, Ordering::Release);
    }

    fn apply_double(&mut self, device: &wgpu::Device, on: bool) -> Result<(), String> {
        self.wait_idle(device);
        if on && self.bufs.len() == 1 {
            self.bufs.push(buffer(device, self.size)?);
            *self.flip.lock().unwrap() = Flip { back: 1, display: 0, pending: None };
        } else if !on && self.bufs.len() == 2 {
            let display = self.flip.lock().unwrap().display;
            let keep = self.bufs.swap_remove(display);
            self.bufs = vec![keep];
            *self.flip.lock().unwrap() = Flip::default();
        }
        Ok(())
    }

    pub fn size(&self) -> (u32, u32) {
        self.size
    }

    /// The surface the host shows: in double mode the last completed frame
    /// (checks the pending one without blocking).
    fn display(&self, device: &wgpu::Device) -> &Buffer {
        let mut f = self.flip.lock().unwrap();
        if let Some(p) = f.pending {
            if !self.bufs[p].done.load(Ordering::Acquire) {
                let _ = device.poll(wgpu::PollType::Poll);
            }
            if self.bufs[p].done.load(Ordering::Acquire) {
                f.display = p;
                f.pending = None;
            }
        }
        &self.bufs[f.display]
    }

    pub fn seed(&self) -> u32 {
        self.display(&crate::descriptors().unwrap().device).seed
    }

    pub fn iosurface_ptr(&self) -> *mut std::ffi::c_void {
        let b = self.display(&crate::descriptors().unwrap().device);
        CFRetained::as_ptr(&b.surface).as_ptr().cast()
    }

    /// Block until the last submitted frame has completed on the GPU (it
    /// becomes the displayed one).
    pub fn wait_idle(&self, device: &wgpu::Device) {
        let index = self.last.lock().unwrap().take();
        if index.is_some() {
            let _ = device.poll(wgpu::PollType::Wait { submission_index: index, timeout: None });
        }
        let mut f = self.flip.lock().unwrap();
        if let Some(p) = f.pending.take() {
            self.bufs[p].done.store(true, Ordering::Release);
            f.display = p;
        }
    }

    /// Copy the surface into straight-alpha RGBA (tests and headless renders).
    pub fn read_rgba(&self, out: &mut [u8]) -> bool {
        let device = &crate::descriptors().unwrap().device;
        self.wait_idle(device);
        let (w, h) = (self.size.0 as usize, self.size.1 as usize);
        if out.len() < w * h * 4 {
            return false;
        }
        let surface = &self.bufs[self.flip.lock().unwrap().display].surface;
        unsafe { surface.lock(IOSurfaceLockOptions::ReadOnly, std::ptr::null_mut()) };
        let stride = surface.bytes_per_row();
        let base = surface.base_address().as_ptr() as *const u8;
        for y in 0..h {
            let row = unsafe { std::slice::from_raw_parts(base.add(y * stride), w * 4) };
            for x in 0..w {
                let (b, g, r, a) = (row[x * 4], row[x * 4 + 1], row[x * 4 + 2], row[x * 4 + 3]);
                let o = &mut out[(y * w + x) * 4..(y * w + x) * 4 + 4];
                if a == 0 {
                    o.copy_from_slice(&[0, 0, 0, 0]);
                } else {
                    let un = |c: u8| ((c as u32 * 255 + a as u32 / 2) / a as u32).min(255) as u8;
                    o.copy_from_slice(&[un(r), un(g), un(b), a]);
                }
            }
        }
        unsafe { surface.unlock(IOSurfaceLockOptions::ReadOnly, std::ptr::null_mut()) };
        true
    }
}

impl RenderTarget for SurfaceTarget {
    type Frame = SurfaceFrame;

    fn resize(&mut self, device: &wgpu::Device, width: u32, height: u32) {
        let size = (width.max(1), height.max(1));
        if size == self.size {
            return;
        }
        self.wait_idle(device);
        let n = self.bufs.len();
        let mut bufs = Vec::with_capacity(n);
        for _ in 0..n {
            match buffer(device, size) {
                Ok(b) => bufs.push(b),
                Err(e) => {
                    tracing::error!("mugfx: IOSurface resize to {size:?} failed: {e}");
                    return;
                }
            }
        }
        self.bufs = bufs;
        self.size = size;
        *self.flip.lock().unwrap() = if n == 2 { Flip { back: 1, display: 0, pending: None } } else { Flip::default() };
    }

    fn format(&self) -> wgpu::TextureFormat {
        FORMAT
    }

    fn width(&self) -> u32 {
        self.size.0
    }

    fn height(&self) -> u32 {
        self.size.1
    }

    fn get_next_texture(&mut self) -> Option<Self::Frame> {
        let want = self.want_double.load(Ordering::Acquire);
        if want != (self.bufs.len() == 2) {
            if let Err(e) = self.apply_double(&crate::descriptors().unwrap().device, want) {
                tracing::error!("mugfx: double buffering: {e}");
                self.want_double.store(false, Ordering::Release);
            }
        }
        if self.bufs.len() == 2 {
            // The back surface must not be the displayed one: if the last
            // frame has not completed yet, wait for it (it then displays).
            let (back, display, pending) = {
                let f = self.flip.lock().unwrap();
                (f.back, f.display, f.pending)
            };
            if back == display && pending.is_some() {
                self.wait_idle(&crate::descriptors().unwrap().device);
            }
            let mut f = self.flip.lock().unwrap();
            if f.back == f.display {
                f.back ^= 1;
            }
        }
        let back = self.flip.lock().unwrap().back;
        Some(SurfaceFrame(self.bufs[back].texture.create_view(&Default::default())))
    }

    fn submit<I: IntoIterator<Item = wgpu::CommandBuffer>>(
        &self,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        command_buffers: I,
        _frame: Self::Frame,
    ) -> wgpu::SubmissionIndex {
        let timing = self.timer.as_ref().and_then(|t| t.begin(device));
        let index = if let Some((i, begin, end)) = timing {
            let index = queue.submit(std::iter::once(begin).chain(command_buffers).chain(std::iter::once(end)));
            self.timer.as_ref().unwrap().submitted(i, queue.get_timestamp_period());
            index
        } else { queue.submit(command_buffers) };
        *self.last.lock().unwrap() = Some(index.clone());
        if self.bufs.len() == 2 {
            let mut f = self.flip.lock().unwrap();
            let b = f.back;
            let done = self.bufs[b].done.clone();
            done.store(false, Ordering::Release);
            queue.on_submitted_work_done(move || done.store(true, Ordering::Release));
            f.pending = Some(b);
            f.back = b ^ 1;
        }
        index
    }
}
