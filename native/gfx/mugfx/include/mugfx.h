/* mugfx: C ABI of native/gfx/mugfx (Rust, links the pinned Ruffle).
 * One handle plays one converted GFx movie (gfxconvert.py --bridge). */
#ifndef MUGFX_H
#define MUGFX_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct MuGfx MuGfx;

/* ExternalInterface.call(name, ...) from the movie; args_json is a JSON array.
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
/* kind 0 move, 1 down, 2 up; button 0 left, 1 right, 2 middle. */
int mugfx_mouse(MuGfx *g, int kind, int button, double x, double y);
void mugfx_stats(MuGfx *g, MuGfxStats *out);
void mugfx_adapter(char *out, size_t cap);

#ifdef __cplusplus
}
#endif

#endif
