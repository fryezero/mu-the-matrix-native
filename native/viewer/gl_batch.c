/* Draw batching for the immediate-mode 3D streams (NATIVE-PERF-001). See gl_batch.h. */
#include "gl_batch.h"

#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#define GL_GLEXT_PROTOTYPES 1
#include <GL/gl.h>
#include <GL/glext.h>
#endif

enum { CAP_BLEND, CAP_DEPTH, CAP_CULL, CAP_ALPHA, CAP_FOG, CAP_TEXTURE, CAPS };
#define STRIDE 9   /* x y z s t r g b a */

struct mu_gl_batch {
    /* state shadow (-1 unknown) */
    int cap[CAPS];
    int64_t blend_src, blend_dst, depth_mask, front_face, polygon_mode, texture;
    /* immediate-mode current values */
    float color[4], texcoord[2];
    /* pending draw */
    uint32_t mode;           /* 0 none */
    float *v;
    int32_t count, capacity;
    GLint *first;
    GLsizei *counts;
    int32_t fans, first_capacity, counts_capacity;
    int in_begin;
    uint32_t prim_mode;
    int32_t prim_first;
    uintptr_t array_base; /* client pointer state, invalidated at each session */
    int reference004;
    int arrays;              /* client arrays enabled in this session */
    mu_gl_batch_stats stats;
};

static GLenum cap_enum(int i)
{
    static const GLenum caps[CAPS] = {GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE, GL_ALPHA_TEST, GL_FOG, GL_TEXTURE_2D};
    return caps[i];
}

static int cap_index(uint32_t capability)
{
    for (int i = 0; i < CAPS; ++i)
        if (cap_enum(i) == capability)
            return i;
    return -1;
}

static void forget(mu_gl_batch *b)
{
    for (int i = 0; i < CAPS; ++i)
        b->cap[i] = -1;
    b->blend_src = b->blend_dst = b->depth_mask = b->front_face = b->polygon_mode = b->texture = -1;
}

mu_gl_batch *mu_gl_batch_new(void)
{
    mu_gl_batch *b = calloc(1, sizeof *b);
    if (b)
        forget(b);
    return b;
}

void mu_gl_batch_free(mu_gl_batch *b)
{
    if (!b)
        return;
    free(b->v);
    free(b->first);
    free(b->counts);
    free(b);
}

void mu_gl_batch_flush(mu_gl_batch *b)
{
    if (!b->mode || !b->count) {
        b->mode = 0;
        b->count = 0;
        b->fans = 0;
        return;
    }
    if (!b->arrays) {
        glEnableClientState(GL_VERTEX_ARRAY);
        glEnableClientState(GL_TEXTURE_COORD_ARRAY);
        glEnableClientState(GL_COLOR_ARRAY);
        b->arrays = 1;
    }
    /* GL reads current client-memory contents on every draw. Pointer state
     * only changes after storage moves or another session may have used GL. */
    if (b->reference004 || b->array_base != (uintptr_t)b->v) {
        const GLsizei stride = (GLsizei)(STRIDE * sizeof(float));
        glVertexPointer(3, GL_FLOAT, stride, b->v);
        glTexCoordPointer(2, GL_FLOAT, stride, b->v + 3);
        glColorPointer(4, GL_FLOAT, stride, b->v + 5);
        b->array_base = (uintptr_t)b->v;
    }
    if (b->mode == GL_TRIANGLE_FAN) {
        if (b->fans == 1)
            glDrawArrays(GL_TRIANGLE_FAN, b->first[0], b->counts[0]);
        else
            glMultiDrawArrays(GL_TRIANGLE_FAN, b->first, b->counts, b->fans);
    } else {
        glDrawArrays((GLenum)b->mode, 0, b->count);
    }
    b->stats.draws++;
    b->mode = 0;
    b->count = 0;
    b->fans = 0;
}

void mu_gl_batch_session_begin(mu_gl_batch *b)
{
    forget(b);
    b->mode = 0;
    b->count = 0;
    b->fans = 0;
    b->in_begin = 0;
    b->arrays = 0;
    b->array_base = 0;
    const char *reference = getenv("MU_PERF_004_BASELINE");
    b->reference004 = reference && reference[0] == '1';
    glGetFloatv(GL_CURRENT_COLOR, b->color);
    float t[4];
    glGetFloatv(GL_CURRENT_TEXTURE_COORDS, t);
    b->texcoord[0] = t[0];
    b->texcoord[1] = t[1];
}

void mu_gl_batch_session_end(mu_gl_batch *b)
{
    mu_gl_batch_flush(b);
    if (b->arrays) {
        glDisableClientState(GL_VERTEX_ARRAY);
        glDisableClientState(GL_TEXTURE_COORD_ARRAY);
        glDisableClientState(GL_COLOR_ARRAY);
        b->arrays = 0;
    }
    /* immediate mode would have left the last glColor/glTexCoord current */
    glColor4f(b->color[0], b->color[1], b->color[2], b->color[3]);
    glTexCoord2f(b->texcoord[0], b->texcoord[1]);
}

/* ---- state ---- */

void mu_gl_batch_enable(mu_gl_batch *b, uint32_t capability, int on)
{
    b->stats.state_calls++;
    on = on != 0;
    int i = cap_index(capability);
    if (i >= 0 && b->cap[i] == on)
        return;
    mu_gl_batch_flush(b);
    if (on)
        glEnable((GLenum)capability);
    else
        glDisable((GLenum)capability);
    if (i >= 0)
        b->cap[i] = on;
    b->stats.state_applied++;
}

void mu_gl_batch_blend_func(mu_gl_batch *b, uint32_t src, uint32_t dst)
{
    b->stats.state_calls++;
    if (b->blend_src == (int64_t)src && b->blend_dst == (int64_t)dst)
        return;
    mu_gl_batch_flush(b);
    glBlendFunc((GLenum)src, (GLenum)dst);
    b->blend_src = src;
    b->blend_dst = dst;
    b->stats.state_applied++;
}

void mu_gl_batch_depth_mask(mu_gl_batch *b, int on)
{
    b->stats.state_calls++;
    on = on != 0;
    if (b->depth_mask == on)
        return;
    mu_gl_batch_flush(b);
    glDepthMask(on ? GL_TRUE : GL_FALSE);
    b->depth_mask = on;
    b->stats.state_applied++;
}

void mu_gl_batch_front_face(mu_gl_batch *b, uint32_t mode)
{
    b->stats.state_calls++;
    if (b->front_face == (int64_t)mode)
        return;
    mu_gl_batch_flush(b);
    glFrontFace((GLenum)mode);
    b->front_face = mode;
    b->stats.state_applied++;
}

void mu_gl_batch_polygon_mode(mu_gl_batch *b, uint32_t mode)
{
    b->stats.state_calls++;
    if (b->polygon_mode == (int64_t)mode)
        return;
    mu_gl_batch_flush(b);
    glPolygonMode(GL_FRONT_AND_BACK, (GLenum)mode);
    b->polygon_mode = mode;
    b->stats.state_applied++;
}

void mu_gl_batch_bind_texture(mu_gl_batch *b, uint32_t name)
{
    b->stats.state_calls++;
    if (b->texture == (int64_t)name)
        return;
    mu_gl_batch_flush(b);
    glBindTexture(GL_TEXTURE_2D, (GLuint)name);
    b->texture = name;
    b->stats.state_applied++;
}

/* ---- immediate mode ---- */

static int grow(void **p, int32_t *capacity, int32_t need, size_t item)
{
    if (need <= *capacity)
        return 1;
    int32_t c = *capacity ? *capacity : 1024;
    while (c < need)
        c *= 2;
    void *q = realloc(*p, (size_t)c * item);
    if (!q)
        return 0;
    *p = q;
    *capacity = c;
    return 1;
}

void mu_gl_batch_begin(mu_gl_batch *b, uint32_t mode)
{
    if (b->mode && b->mode != mode)
        mu_gl_batch_flush(b);
    b->mode = mode;
    b->in_begin = 1;
    b->prim_mode = mode;
    b->prim_first = b->count;
    b->stats.primitives++;
}

void mu_gl_batch_texcoord(mu_gl_batch *b, float s, float t)
{
    b->texcoord[0] = s;
    b->texcoord[1] = t;
}

void mu_gl_batch_color4(mu_gl_batch *b, float r, float g, float bl, float a)
{
    b->color[0] = r;
    b->color[1] = g;
    b->color[2] = bl;
    b->color[3] = a;
}

void mu_gl_batch_vertex(mu_gl_batch *b, const float xyz[3])
{
    if (!b->in_begin)
        return;   /* glVertex outside glBegin/glEnd: no effect */
    if (!grow((void **)&b->v, &b->capacity, b->count + 1, STRIDE * sizeof(float)))
        return;
    float *p = b->v + (size_t)b->count * STRIDE;
    p[0] = xyz[0];
    p[1] = xyz[1];
    p[2] = xyz[2];
    p[3] = b->texcoord[0];
    p[4] = b->texcoord[1];
    memcpy(p + 5, b->color, sizeof b->color);
    b->count++;
    b->stats.vertices++;
}

void mu_gl_batch_end(mu_gl_batch *b)
{
    if (!b->in_begin)
        return;
    b->in_begin = 0;
    int32_t n = b->count - b->prim_first;
    /* incomplete primitives draw nothing in immediate mode; drop them so they do not shift the next ones */
    int32_t keep = n;
    if (b->prim_mode == GL_QUADS)
        keep = n - n % 4;
    else if (b->prim_mode == GL_TRIANGLES)
        keep = n - n % 3;
    else if (b->prim_mode == GL_TRIANGLE_FAN && n < 3)
        keep = 0;
    b->count = b->prim_first + keep;
    if (b->prim_mode == GL_TRIANGLE_FAN && keep) {
        if (!grow((void **)&b->first, &b->first_capacity, b->fans + 1, sizeof *b->first) ||
            !grow((void **)&b->counts, &b->counts_capacity, b->fans + 1, sizeof *b->counts)) {
            b->count = b->prim_first;
            return;
        }
        b->first[b->fans] = b->prim_first;
        b->counts[b->fans] = keep;
        b->fans++;
    }
}

void mu_gl_batch_stats_get(const mu_gl_batch *b, mu_gl_batch_stats *out)
{
    *out = b->stats;
}

void mu_gl_batch_stats_reset(mu_gl_batch *b)
{
    memset(&b->stats, 0, sizeof b->stats);
}
