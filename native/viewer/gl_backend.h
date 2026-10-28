#ifndef MU_GL_BACKEND_H
#define MU_GL_BACKEND_H

#include <stdint.h>

#include "../core/mu_image.h"
#include "../core/mu_scene.h"
#include "../core/mu_textures.h"

/* OpenGL 1.x/2.1 fixed-function backend: the scene driver's calls map 1:1 to
 * glBindTexture/glEnable/glBlendFunc/glDepthMask/glBegin(GL_TRIANGLES)/
 * glTexCoord2f/glColor3fv/glColor4f/glVertex3fv/glEnd, i.e. the call stream of
 * the client's mesh draw (compared with the actual routine under Unicorn,
 * docs/research/client-meshdraw-exec.md). The effective state is re-applied
 * before each glBegin, which equals the literal stream plus the viewer's
 * alpha-test/cull/wireframe overrides.
 *
 * Client values (static readings): textures uploaded at level 0 without
 * mipmaps with each texture's MIN/MAG filter and wrap (model textures
 * GL_NEAREST/GL_REPEAT), GL_MODULATE, glAlphaFunc(GL_GREATER, 0.25) and
 * glDepthFunc(GL_LEQUAL) from the scene setup 0x0184adc7, fog off. Viewer
 * choices: `linear` forces GL_LINEAR for every texture, clear colour, camera,
 * front-face winding. */
/* Optional profiling query lifecycle, with a current GL context. */
void mu_gl_perf_begin(void);
void mu_gl_perf_end(void);
void mu_gl_perf_free(void);

struct mu_gl_batch;

typedef struct mu_gl_backend {
    uint32_t *textures;        /* GL names per mu_textures slot, 0 when missing */
    int32_t count;
    int front_cw;
    int wireframe;
    /* NATIVE-PERF-001: when set (before mu_gl_backend_bind), the stream goes through this batch
     * (viewer/gl_batch.h): redundant state dropped, equal-state draws merged; the caller opens and
     * closes the batch session around the draws. */
    struct mu_gl_batch *batch;
} mu_gl_backend;

/* Uploads every slot of `textures` (model slots, then the environment
 * bitmaps); `linear` overrides the per-texture filters with GL_LINEAR. */
void mu_gl_upload(mu_gl_backend *gl, const mu_textures *textures, int linear);
void mu_gl_release(mu_gl_backend *gl);
void mu_gl_backend_bind(mu_gl_backend *gl, mu_render_backend *backend);
/* Viewport, clear, matrices and global fixed-function state for one frame. */
void mu_gl_frame(int32_t width, int32_t height, const uint8_t background[4], const float view[16],
                 const float projection[16]);
/* Reads the framebuffer into rgba (top row first). */
void mu_gl_read(int32_t width, int32_t height, uint8_t *rgba);

#endif
