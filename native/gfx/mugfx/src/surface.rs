//! IOSurface render target (macOS, NATIVE-GFX-002).
//!
//! Ruffle renders through wgpu's Metal backend.  This target backs the wgpu
//! render texture with an IOSurface (BGRA8, premultiplied alpha), the same
//! memory the host's OpenGL context can bind with `CGLTexImageIOSurface2D`.
//! A frame therefore reaches the GL compositor without the GPU -> CPU -> GL
//! copy of `TextureTarget`: the only synchronisation is waiting for the
//! frame's command buffer to complete (`wait_idle`).

use std::fmt;
use std::sync::Mutex;
use std::sync::atomic::{AtomicU32, Ordering};

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

pub struct SurfaceTarget {
    surface: CFRetained<IOSurfaceRef>,
    texture: wgpu::Texture,
    size: (u32, u32),
    seed: u32,
    last: Mutex<Option<wgpu::SubmissionIndex>>,
}

impl fmt::Debug for SurfaceTarget {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("SurfaceTarget").field("size", &self.size).field("seed", &self.seed).finish()
    }
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
        let (surface, texture) = create(device, size)?;
        Ok(Self { surface, texture, size, seed: SEED.fetch_add(1, Ordering::Relaxed), last: Mutex::new(None) })
    }

    pub fn size(&self) -> (u32, u32) {
        self.size
    }

    pub fn seed(&self) -> u32 {
        self.seed
    }

    pub fn iosurface_ptr(&self) -> *mut std::ffi::c_void {
        CFRetained::as_ptr(&self.surface).as_ptr().cast()
    }

    /// Block until the last submitted frame has completed on the GPU.
    pub fn wait_idle(&self, device: &wgpu::Device) {
        let index = self.last.lock().unwrap().take();
        if index.is_some() {
            let _ = device.poll(wgpu::PollType::Wait { submission_index: index, timeout: None });
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
        unsafe { self.surface.lock(IOSurfaceLockOptions::ReadOnly, std::ptr::null_mut()) };
        let stride = self.surface.bytes_per_row();
        let base = self.surface.base_address().as_ptr() as *const u8;
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
        unsafe { self.surface.unlock(IOSurfaceLockOptions::ReadOnly, std::ptr::null_mut()) };
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
        match create(device, size) {
            Ok((surface, texture)) => {
                self.surface = surface;
                self.texture = texture;
                self.size = size;
                self.seed = SEED.fetch_add(1, Ordering::Relaxed);
            }
            Err(e) => tracing::error!("mugfx: IOSurface resize to {size:?} failed: {e}"),
        }
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
        Some(SurfaceFrame(self.texture.create_view(&Default::default())))
    }

    fn submit<I: IntoIterator<Item = wgpu::CommandBuffer>>(
        &self,
        _device: &wgpu::Device,
        queue: &wgpu::Queue,
        command_buffers: I,
        _frame: Self::Frame,
    ) -> wgpu::SubmissionIndex {
        let index = queue.submit(command_buffers);
        *self.last.lock().unwrap() = Some(index.clone());
        index
    }
}
