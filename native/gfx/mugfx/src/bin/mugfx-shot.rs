//! mugfx-shot: load one converted GFx movie with Ruffle, run a script of
//! game-side operations and input on it, and write PNGs (NATIVE-GFX-001/002).
//!
//!   mugfx-shot IN.swf OUT.png [--size WxH] [--shared] [--frames N] [OPS...]
//!
//! OPS run in order before the final `--frames` advance and render:
//!   --invoke PATH METHOD JSON   GFx Invoke (prints the JSON result)
//!   --set PATH JSON / --get PATH
//!   --advance N                 N frames of 1/30 s
//!   --mouse move|down|up|wheel X Y [BUTTON]   (BUTTON 0 left, 1 right, 2 middle; wheel: lines)
//!   --click X Y [BUTTON]        down + up
//!   --key VK [down|up|press] [CHAR]
//!   --text STRING               typed text
//!   --hit X Y                   GFx hit test -> 0/1
//!   --cursor / --focus          cursor shape / text focus
//!   --view SW SH X Y W H [S]    window-sized player, backing scale S (see mugfx_set_view)
//!   --font NAME PATH STYLE      register a device font
//!   --shot PATH                 render now and write a PNG
//!
//! ExternalInterface calls from the movie are printed as `call NAME ARGS`;
//! with MUGFX_LOG=warn Ruffle's warnings (unimplemented Flash APIs) go to
//! stderr.  Prints one JSON summary line on stdout at the end.
use std::ffi::{CStr, CString, c_char, c_int, c_void};
use std::time::Instant;

use mugfx::*;

unsafe extern "C" fn on_call(_user: *mut c_void, name: *const c_char, args: *const c_char) -> *const c_char {
    let (name, args) = unsafe { (CStr::from_ptr(name).to_string_lossy(), CStr::from_ptr(args).to_string_lossy()) };
    println!("call {name} {args}");
    std::ptr::null()
}

fn c(s: &str) -> CString {
    CString::new(s).unwrap()
}

fn reply(r: *const c_char) -> String {
    if r.is_null() { "(queued)".into() } else { unsafe { CStr::from_ptr(r) }.to_string_lossy().into_owned() }
}

fn shot(g: *mut MuGfx, path: &str) -> (bool, usize, f64) {
    let (mut w, mut h): (c_int, c_int) = (0, 0);
    unsafe { mugfx_size(g, &mut w, &mut h) };
    let mut rgba = vec![0u8; (w * h * 4) as usize];
    let t = Instant::now();
    let rc = unsafe { mugfx_render(g, rgba.as_mut_ptr(), rgba.len()) };
    let ms = t.elapsed().as_secs_f64() * 1000.0;
    if rc == 0 && path != "-" {
        image::save_buffer(path, &rgba, w as u32, h as u32, image::ExtendedColorType::Rgba8).unwrap();
    }
    (rc == 0, rgba.chunks(4).filter(|p| p[3] != 0).count(), ms)
}

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    if argv.len() < 3 {
        eprintln!("usage: mugfx-shot IN.swf OUT.png [--size WxH] [--shared] [--frames N] [OPS...]");
        std::process::exit(2);
    }
    let (mut w, mut h, mut frames, mut shared) = (1024, 768, 10, false);
    // Global options first.
    let mut i = 3;
    let mut ops = Vec::new();
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
            "--shared" => {
                shared = true;
                i += 1;
            }
            _ => {
                ops.push(argv[i].clone());
                i += 1;
            }
        }
    }
    let path = c(&argv[1]);
    let mut err = vec![0 as c_char; 512];
    let t0 = Instant::now();
    let g = unsafe {
        if shared {
            mugfx_open_shared(path.as_ptr(), w, h, err.as_mut_ptr(), err.len())
        } else {
            mugfx_open(path.as_ptr(), w, h, err.as_mut_ptr(), err.len())
        }
    };
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
    let mut k = 0;
    let arg = |k: usize| -> &str { ops.get(k).map(|s| s.as_str()).unwrap_or("") };
    let num = |k: usize| -> f64 { arg(k).parse().unwrap_or(0.0) };
    while k < ops.len() {
        let op = arg(k).to_string();
        match op.as_str() {
            "--invoke" => {
                let r = unsafe { mugfx_invoke(g, c(arg(k + 1)).as_ptr(), c(arg(k + 2)).as_ptr(), c(arg(k + 3)).as_ptr()) };
                println!("invoke {} {} -> {}", arg(k + 1), arg(k + 2), reply(r));
                k += 4;
            }
            "--set" => {
                unsafe { mugfx_set_variable(g, c(arg(k + 1)).as_ptr(), c(arg(k + 2)).as_ptr()) };
                k += 3;
            }
            "--get" => {
                let r = unsafe { mugfx_get_variable(g, c(arg(k + 1)).as_ptr()) };
                println!("get {} -> {}", arg(k + 1), reply(r));
                k += 2;
            }
            "--advance" => {
                for _ in 0..num(k + 1) as i32 {
                    unsafe { mugfx_advance(g, 1000.0 / 30.0) };
                }
                k += 2;
            }
            "--mouse" => {
                let kind = match arg(k + 1) {
                    "down" => 1,
                    "up" => 2,
                    "wheel" => 3,
                    _ => 0,
                };
                let mut n = 4;
                let button = if ops.get(k + 4).is_some_and(|s| !s.starts_with("--")) {
                    n = 5;
                    num(k + 4) as c_int
                } else {
                    0
                };
                let r = unsafe { mugfx_mouse(g, kind, button, num(k + 2), num(k + 3)) };
                println!("mouse {} {} {} {} -> {}", arg(k + 1), arg(k + 2), arg(k + 3), button, r);
                k += n;
            }
            "--click" => {
                let mut n = 3;
                let button = if ops.get(k + 3).is_some_and(|s| !s.starts_with("--")) {
                    n = 4;
                    num(k + 3) as c_int
                } else {
                    0
                };
                unsafe {
                    mugfx_mouse(g, 0, 0, num(k + 1), num(k + 2));
                    mugfx_mouse(g, 1, button, num(k + 1), num(k + 2));
                    mugfx_mouse(g, 2, button, num(k + 1), num(k + 2));
                }
                println!("click {} {} {}", arg(k + 1), arg(k + 2), button);
                k += n;
            }
            "--key" => {
                let vk = num(k + 1) as c_int;
                let mut n = 2;
                let mut mode = "press";
                if matches!(arg(k + 2), "down" | "up" | "press") {
                    mode = arg(k + 2);
                    n = 3;
                }
                let mut ch = 0u32;
                if ops.get(k + n).is_some_and(|s| !s.starts_with("--")) {
                    ch = arg(k + n).chars().next().map(|c| c as u32).unwrap_or(0);
                    n += 1;
                }
                let mut r = 0;
                unsafe {
                    if mode != "up" {
                        r |= mugfx_key(g, 0, vk, ch, 0);
                    }
                    if mode != "down" {
                        r |= mugfx_key(g, 1, vk, ch, 0);
                    }
                }
                println!("key {vk} {mode} -> {r}");
                k += n;
            }
            "--text" => {
                let r = unsafe { mugfx_text(g, c(arg(k + 1)).as_ptr()) };
                println!("text {:?} -> {r}", arg(k + 1));
                k += 2;
            }
            "--hit" => {
                let r = unsafe { mugfx_hit_test(g, num(k + 1), num(k + 2)) };
                println!("hit {} {} -> {r}", arg(k + 1), arg(k + 2));
                k += 3;
            }
            "--cursor" => {
                println!("cursor {}", unsafe { mugfx_cursor(g) });
                k += 1;
            }
            "--focus" => {
                println!("focus {}", unsafe { mugfx_text_focus(g) });
                k += 1;
            }
            "--view" => {
                let v: Vec<c_int> = (1..=6).map(|j| num(k + j) as c_int).collect();
                let mut n = 7;
                let scale = if ops.get(k + 7).is_some_and(|s| !s.starts_with("--")) {
                    n = 8;
                    num(k + 7)
                } else {
                    1.0
                };
                unsafe { mugfx_set_view(g, v[0], v[1], v[2], v[3], v[4], v[5], scale) };
                println!("view {v:?} x{scale}");
                k += n;
            }
            "--font" => {
                let r = unsafe { mugfx_register_font(c(arg(k + 1)).as_ptr(), c(arg(k + 2)).as_ptr(), num(k + 3) as c_int) };
                println!("font {} -> {r}", arg(k + 1));
                k += 4;
            }
            "--shot" => {
                let (ok, drawn, _) = shot(g, arg(k + 1));
                println!("shot {} ok={ok} drawn={drawn}", arg(k + 1));
                k += 2;
            }
            other => panic!("unknown option {other}"),
        }
    }
    let t1 = Instant::now();
    for _ in 0..frames {
        unsafe { mugfx_advance(g, 1000.0 / 30.0) };
    }
    let advance_ms = t1.elapsed().as_secs_f64() * 1000.0 / frames.max(1) as f64;
    let (ok, opaque, render_ms) = shot(g, &argv[2]);
    let mut st = MuGfxStats::default();
    let fonts = reply(unsafe { mugfx_fonts_used(g) });
    unsafe {
        mugfx_stats(g, &mut st);
        mugfx_close(g);
    }
    println!(
        "{{\"ok\": {}, \"load_ms\": {:.1}, \"advance_ms\": {:.3}, \"render_ms\": {:.2}, \"external_calls\": {}, \
         \"drawn_pixels\": {}, \"device_fonts\": {:?}}}",
        ok, load_ms, advance_ms, render_ms, st.external_calls, opaque, fonts
    );
}
