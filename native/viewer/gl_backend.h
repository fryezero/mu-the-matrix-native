#ifndef MU_GL_BACKEND_H
#define MU_GL_BACKEND_H

#include <stdint.h>

#include "../core/mu_image.h"
#include "../core/mu_scene.h"

/* OpenGL 1.x/2.1 fixed-function backend: the scene driver's calls map 1:1 to
 * glBindTexture/glEnable/glBlendFunc/glBegin(GL_TRIANGLES)/glTexCoord2f/
 * glColor3fv/glColor4f/glVertex3fv/glEnd, i.e. the client's own immediate-mode
 * sequence. Texture parameters (GL_LINEAR, GL_REPEAT, no mipmaps, top row
 * first) and GL_LEQUAL/GL_MODULATE/alpha GREATER 0.25 are viewer choices that
 * match the software rasterizer; the client's own values are unrecovered. */
typedef struct mu_gl_backend {
    uint32_t *textures;        /* GL names per mesh, 0 when missing */
    int32_t count;
    int front_cw;
    int wireframe;
} mu_gl_backend;

void mu_gl_upload(mu_gl_backend *gl, const mu_image *const *images, int32_t count, int nearest);
void mu_gl_release(mu_gl_backend *gl);
void mu_gl_backend_bind(mu_gl_backend *gl, mu_render_backend *backend);
/* Viewport, clear, matrices and global fixed-function state for one frame. */
void mu_gl_frame(int32_t width, int32_t height, const uint8_t background[4], const float view[16],
                 const float projection[16]);
/* Reads the framebuffer into rgba (top row first). */
void mu_gl_read(int32_t width, int32_t height, uint8_t *rgba);

#endif
