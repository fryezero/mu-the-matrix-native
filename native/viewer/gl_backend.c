/* OpenGL fixed-function backend. See gl_backend.h. */
#include "gl_backend.h"

#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

void mu_gl_upload(mu_gl_backend *gl, const mu_textures *textures, int linear)
{
    const int32_t count = textures ? textures->count : 0;
    gl->count = count;
    gl->textures = calloc((size_t)(count ? count : 1), sizeof *gl->textures);
    if (!gl->textures)
        return;
    for (int32_t i = 0; i < count; ++i) {
        const mu_image *image = textures->slots[i];
        if (!image || !image->rgba)
            continue;
        const GLint filter = linear ? GL_LINEAR : (GLint)textures->filter[i];
        const GLint wrap = (GLint)textures->wrap[i];
        GLuint name = 0;
        glGenTextures(1, &name);
        glBindTexture(GL_TEXTURE_2D, name);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, image->width, image->height, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                     image->rgba);
        gl->textures[i] = name;
    }
}

void mu_gl_release(mu_gl_backend *gl)
{
    for (int32_t i = 0; i < gl->count; ++i)
        if (gl->textures && gl->textures[i]) {
            GLuint name = gl->textures[i];
            glDeleteTextures(1, &name);
        }
    free(gl->textures);
    gl->textures = NULL;
    gl->count = 0;
}

static void set(GLenum capability, int on)
{
    if (on)
        glEnable(capability);
    else
        glDisable(capability);
}

static void prepare(void *context, const mu_meshdraw_state *s, int32_t slot)
{
    mu_gl_backend *gl = context;
    set(GL_BLEND, s->blend);
    glBlendFunc((GLenum)s->src, (GLenum)s->dst);  /* the client's GL enums */
    set(GL_DEPTH_TEST, s->depth_test);
    glDepthMask(s->depth_mask ? GL_TRUE : GL_FALSE);
    set(GL_CULL_FACE, s->cull);
    glFrontFace(gl->front_cw ? GL_CW : GL_CCW);
    set(GL_ALPHA_TEST, s->alpha_test);
    set(GL_FOG, s->fog);  /* the client's fog flag is only ever written 0 */
    GLuint name = (gl->textures && slot >= 0 && slot < gl->count) ? gl->textures[slot] : 0;
    set(GL_TEXTURE_2D, s->texture && name != 0);
    glBindTexture(GL_TEXTURE_2D, name);
    glPolygonMode(GL_FRONT_AND_BACK, gl->wireframe ? GL_LINE : GL_FILL);
}

static void begin(void *context) { (void)context; glBegin(GL_TRIANGLES); }
static void end(void *context) { (void)context; glEnd(); }
static void texcoord(void *context, float s, float t) { (void)context; glTexCoord2f(s, t); }
static void color3(void *context, const float c[3]) { (void)context; glColor3fv(c); }
static void color4(void *context, float r, float g, float b, float a) { (void)context; glColor4f(r, g, b, a); }
static void vertex(void *context, const float v[3]) { (void)context; glVertex3fv(v); }

void mu_gl_backend_bind(mu_gl_backend *gl, mu_render_backend *backend)
{
    memset(backend, 0, sizeof *backend);
    backend->context = gl;
    backend->prepare = prepare;
    backend->begin = begin;
    backend->end = end;
    backend->sink.context = gl;
    backend->sink.texcoord = texcoord;
    backend->sink.color3 = color3;
    backend->sink.color4 = color4;
    backend->sink.vertex = vertex;
}

void mu_gl_frame(int32_t width, int32_t height, const uint8_t background[4], const float view[16],
                 const float projection[16])
{
    glViewport(0, 0, width, height);
    glClearColor((float)background[0] / 255.0f, (float)background[1] / 255.0f, (float)background[2] / 255.0f,
                 (float)background[3] / 255.0f);
    glClearDepth(1.0);
    glDepthMask(GL_TRUE);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glMatrixMode(GL_PROJECTION);
    glLoadMatrixf(projection);
    glMatrixMode(GL_MODELVIEW);
    glLoadMatrixf(view);
    glShadeModel(GL_SMOOTH);
    glDepthFunc(GL_LEQUAL);
    glCullFace(GL_BACK);
    glAlphaFunc(GL_GREATER, 0.25f);
    glDisable(GL_LIGHTING);
    glDisable(GL_FOG);
    glDisable(GL_DITHER);
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
    glColor4f(1.0f, 1.0f, 1.0f, 1.0f);
    glTexCoord2f(0.0f, 0.0f);
}

void mu_gl_read(int32_t width, int32_t height, uint8_t *rgba)
{
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    size_t row = (size_t)width * 4;
    uint8_t *flipped = malloc(row * (size_t)height);
    if (!flipped)
        return;
    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, flipped);
    for (int32_t y = 0; y < height; ++y)
        memcpy(rgba + row * (size_t)y, flipped + row * (size_t)(height - 1 - y), row);
    free(flipped);
}
