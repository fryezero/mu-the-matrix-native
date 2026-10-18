//! mugfx-shot: load one converted GFx movie with Ruffle, run it, optionally
//! invoke methods through the bridge, and write a PNG (NATIVE-GFX-001).
//!
//!   mugfx-shot IN.swf OUT.png [--size WxH] [--frames N] [--invoke PATH METHOD JSON]...
//!
//! ExternalInterface calls from the movie are printed as `call NAME ARGS`;
//! with MUGFX_LOG=warn Ruffle's warnings (unimplemented Flash APIs) go to
//! stderr.  Prints one JSON summary line on stdout.
use std::ffi::{CStr, CString, c_char, c_void};
use std::time::Instant;

use mugfx::*;

unsafe extern "C" fn on_call(_user: *mut c_void, name: *const c_char, args: *const c_char) -> *const c_char {
    let (name, args) = unsafe { (CStr::from_ptr(name).to_string_lossy(), CStr::from_ptr(args).to_string_lossy()) };
    println!("call {name} {args}");
    std::ptr::null()
}

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    if argv.len() < 3 {
        eprintln!("usage: mugfx-shot IN.swf OUT.png [--size WxH] [--frames N] [--invoke PATH METHOD JSON]...");
        std::process::exit(2);
    }
    let (mut w, mut h, mut frames) = (1024, 768, 10);
    let mut invokes = Vec::new();
    let mut i = 3;
    while i < argv.len() {
        match argv[i].as_str() {
            "--size" => {
                let (a, b) = argv[i + 1].split_once('x').expect("WxH");
                w = a.parse().unwrap();
                h = b.parse().unwrap();
                i += 2;
            }
            "--frames" => {
                frames = argv[i + 1].parse().unwrap();
                i += 2;
            }
            "--invoke" => {
                invokes.push((argv[i + 1].clone(), argv[i + 2].clone(), argv[i + 3].clone()));
                i += 4;
            }
            other => panic!("unknown option {other}"),
        }
    }
    let path = CString::new(argv[1].clone()).unwrap();
    let mut err = vec![0 as c_char; 512];
    let t0 = Instant::now();
    let g = unsafe { mugfx_open(path.as_ptr(), w, h, err.as_mut_ptr(), err.len()) };
    if g.is_null() {
        let msg = unsafe { CStr::from_ptr(err.as_ptr()) }.to_string_lossy();
        println!("{{\"ok\": false, \"error\": {:?}}}", msg.to_string());
        std::process::exit(1);
    }
    unsafe {
        mugfx_set_callback(g, Some(on_call), std::ptr::null_mut());
        mugfx_start(g);
    }
    let load_ms = t0.elapsed().as_secs_f64() * 1000.0;
    for (p, m, a) in &invokes {
        let (p, m, a) = (CString::new(p.as_str()).unwrap(), CString::new(m.as_str()).unwrap(),
                         CString::new(a.as_str()).unwrap());
        let r = unsafe { mugfx_invoke(g, p.as_ptr(), m.as_ptr(), a.as_ptr()) };
        let r = if r.is_null() { "(queued)".into() } else { unsafe { CStr::from_ptr(r) }.to_string_lossy() };
        println!("invoke {} {} -> {}", p.to_string_lossy(), m.to_string_lossy(), r);
    }
    let t1 = Instant::now();
    for _ in 0..frames {
        unsafe { mugfx_advance(g, 1000.0 / 30.0) };
    }
    let advance_ms = t1.elapsed().as_secs_f64() * 1000.0 / frames.max(1) as f64;
    let mut rgba = vec![0u8; (w * h * 4) as usize];
    let t2 = Instant::now();
    let rc = unsafe { mugfx_render(g, rgba.as_mut_ptr(), rgba.len()) };
    let render_ms = t2.elapsed().as_secs_f64() * 1000.0;
    if rc == 0 {
        image::save_buffer(&argv[2], &rgba, w as u32, h as u32, image::ExtendedColorType::Rgba8).unwrap();
    }
    let mut st = MuGfxStats::default();
    unsafe {
        mugfx_stats(g, &mut st);
        mugfx_close(g);
    }
    let opaque = rgba.chunks(4).filter(|p| p[3] != 0).count();
    println!(
        "{{\"ok\": {}, \"load_ms\": {:.1}, \"advance_ms\": {:.3}, \"render_ms\": {:.2}, \"external_calls\": {}, \
         \"drawn_pixels\": {}}}",
        rc == 0, load_ms, advance_ms, render_ms, st.external_calls, opaque
    );
}
