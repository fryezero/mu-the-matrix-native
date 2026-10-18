/* mugfx: C ABI of native/gfx/mugfx (Rust, links the pinned Ruffle with the
 * GFx patch series native/gfx/ruffle-patches).
 * One handle plays one converted GFx movie (gfxconvert.py --bridge).
 * NATIVE-GFX-001: open, advance, render (read back), invoke, variables, mouse.
 * NATIVE-GFX-002: keyboard/text input, GFx hit test, cursor, device fonts,
 * window-sized players, IOSurface sharing (macOS), ABI version.
 * NATIVE-GFX-003 (ABI 3): movies load other movies (loadClip) from the root
 * movie's directory; game images (mugfx_set_image). */
#ifndef MUGFX_H
#define MUGFX_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct MuGfx MuGfx;

#define MUGFX_ABI_VERSION 3

/* ExternalInterface.call(name, ...) from the movie; args_json is a JSON array.
 * fscommand(cmd, arg) arrives as name "fscommand" with [cmd, arg].
 * Return a JSON reply (or NULL) that stays valid until the next callback. */
typedef const char *(*mugfx_callback)(void *user, const char *name, const char *args_json);

typedef struct MuGfxStats {
    uint64_t frames_rendered;
    uint64_t external_calls;
    double last_advance_ms;
    double last_render_ms;   /* Ruffle display list -> wgpu command submission */
    double last_capture_ms;  /* GPU completion + readback into the caller's buffer */
} MuGfxStats;

MuGfx *mugfx_open(const char *swf_path, int width, int height, char *err, size_t err_cap);
void mugfx_close(MuGfx *g);
void mugfx_set_callback(MuGfx *g, mugfx_callback cb, void *user);
void mugfx_start(MuGfx *g);
void mugfx_advance(MuGfx *g, double dt_ms);
int mugfx_needs_render(MuGfx *g);
/* Straight-alpha RGBA, top row first, width*height*4 bytes. 0 on success. */
int mugfx_render(MuGfx *g, uint8_t *rgba, size_t capacity);
/* GFx Invoke on an AS2 path; JSON array args; returns JSON (NULL when queued). */
const char *mugfx_invoke(MuGfx *g, const char *path, const char *method, const char *args_json);
int mugfx_set_variable(MuGfx *g, const char *path, const char *value_json);
const char *mugfx_get_variable(MuGfx *g, const char *path);
/* kind 0 move, 1 down, 2 up, 3 wheel (button = lines, + up), 4 leave;
 * button 0 left, 1 right, 2 middle.  Right/middle buttons reach the movie's
 * GFx onPressAux/onReleaseAux handlers (button index 1/2). */
int mugfx_mouse(MuGfx *g, int kind, int button, double x, double y);
void mugfx_stats(MuGfx *g, MuGfxStats *out);
void mugfx_adapter(char *out, size_t cap);
int mugfx_abi_version(void);

/* macOS: render into an IOSurface (BGRA, premultiplied alpha) instead of a
 * read-back texture.  mugfx_render_shared renders (and with wait, waits for
 * the GPU; else call mugfx_gpu_wait once after rendering all movies);
 * mugfx_iosurface returns the IOSurfaceRef with its size and a seed that
 * changes when the surface is replaced (rebind the GL texture then).
 * mugfx_render still works (reads the surface) for headless captures. */
MuGfx *mugfx_open_shared(const char *swf_path, int width, int height, char *err, size_t err_cap);
int mugfx_render_shared(MuGfx *g, int wait);
/* Wait for every frame submitted so far (one GPU queue for all movies). */
void mugfx_gpu_wait(void);
void *mugfx_iosurface(MuGfx *g, int *width, int *height, uint32_t *seed);

/* GFx Movie::HitTest with shapes: 1 when a visible shape not under a
 * hitTestDisable clip covers the viewport point. */
int mugfx_hit_test(MuGfx *g, double x, double y);
/* Cursor shape requested by the movie: 0 arrow, 1 hand, 2 I-beam, 3 grab. */
int mugfx_cursor(MuGfx *g);
/* Keyboard: kind 0 down, 1 up; vk = Windows/Flash key code ('I' = 73,
 * Enter 13, Esc 27, arrows 37..40); codepoint = the key's character or 0;
 * mods 1 shift, 2 ctrl/cmd, 4 alt.  Editing keys also reach a focused text
 * field.  Typed text goes through mugfx_text (UTF-8). */
int mugfx_key(MuGfx *g, int kind, int vk, uint32_t codepoint, int mods);
int mugfx_text(MuGfx *g, const char *utf8);
/* 1 when a text field of the movie has keyboard focus. */
int mugfx_text_focus(MuGfx *g);
/* Window-sized player and backing scale: the movie keeps a stage_w x
 * stage_h stage (points); the render target becomes w*scale x h*scale
 * pixels showing the stage area at (x, y) points; mouse coordinates are
 * viewport pixels.  w or h <= 0 shows the whole stage; scale <= 0 means 1
 * (Retina: 2, the interface keeps its size and draws sharp). */
int mugfx_set_view(MuGfx *g, int stage_w, int stage_h, int x, int y, int w, int h, double scale);
void mugfx_size(MuGfx *g, int *width, int *height);
/* Device fonts: map a font name used by the movies to a font file (style 0
 * regular, 1 bold, 2 italic, 3 bold italic; name "*" = fallback).  Defaults
 * map the client's names to macOS fonts. */
int mugfx_register_font(const char *name, const char *path, int style);
const char *mugfx_fonts_used(MuGfx *g);

/* NATIVE-GFX-003.  Movies load other movies with MovieClipLoader.loadClip
 * (the client's base movie, UI loader and Icons.swf): names resolve in the
 * root movie's directory, '\\' as separator, then the file name alone, also
 * case-insensitively.  mugfx_resolve reports the file a name maps to.
 * Game images: GFx lets the game provide the bitmaps of a movie's external
 * images (base.swf's render targets image0..image7);
 * BitmapData.loadBitmap(name) returns the image given here and shares its
 * pixels (straight-alpha RGBA, stride bytes per row or 0, top row first). */
int mugfx_set_image(MuGfx *g, const char *name, int width, int height, const uint8_t *rgba, int stride);
int mugfx_resolve(MuGfx *g, const char *name, char *out, size_t cap);
/* IME composition (SDL_TEXTEDITING) for the focused text field: commit 0
 * shows utf8 as composing text with the caret at byte offset cursor (-1
 * hidden; "" ends it), commit 1 inserts it. */
int mugfx_ime(MuGfx *g, const char *utf8, int cursor, int commit);
/* Shared movies: on 1 renders into two alternating IOSurfaces;
 * mugfx_iosurface returns the last completed frame (its seed changes when
 * it flips), so no mugfx_gpu_wait is needed before drawing (one frame of
 * latency at most).  0 returns to one surface. */
int mugfx_set_double_buffer(MuGfx *g, int on);

#ifdef __cplusplus
}
#endif

#endif
