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

enum command_kind { C_DRAW, C_ENABLE, C_BLEND, C_DEPTH, C_FRONT, C_POLYGON, C_TEXTURE };
typedef struct command {
    enum command_kind kind;
    uint32_t a, b;
    int32_t first, count, fan_first, fan_count;
} command;

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
    float *bank;
    int32_t bank_count, bank_capacity;
    GLint *bank_first;
    GLsizei *bank_counts;
    int32_t bank_fans, bank_first_capacity, bank_counts_capacity;
    command *commands;
    int32_t command_count, command_capacity;
    GLuint upload_buffer;
    GLint saved_array_buffer;
    int session_active;
    int stream, stream_disabled;
    long uploads, upload_failures;
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
    if (b->upload_buffer) glDeleteBuffers(1, &b->upload_buffer);
    free(b->bank);
    free(b->bank_first);
    free(b->bank_counts);
    free(b->commands);
    free(b->v);
    free(b->first);
    free(b->counts);
    free(b);
}

static int grow(void **p, int32_t *capacity, int32_t need, size_t item);

/* Replay owns an immutable vertex bank. Explicit flushes remain submission
 * barriers; only state changes internal to the batch can defer a draw. */
static void flush_capture(mu_gl_batch *b)
{
    if (!b->command_count) return;
    GLint previous_array_buffer;
    glGetIntegerv(GL_ARRAY_BUFFER_BINDING, &previous_array_buffer);
    int uploaded = 0;
    if (b->bank_count) {
        if (!b->arrays) {
            glEnableClientState(GL_VERTEX_ARRAY);
            glEnableClientState(GL_TEXTURE_COORD_ARRAY);
            glEnableClientState(GL_COLOR_ARRAY);
            b->arrays = 1;
        }
        if (!b->stream_disabled) {
            if (!b->upload_buffer) glGenBuffers(1, &b->upload_buffer);
            if (b->upload_buffer) {
                glBindBuffer(GL_ARRAY_BUFFER, b->upload_buffer);
                GLsizeiptr bytes = (GLsizeiptr)((size_t)b->bank_count * STRIDE * sizeof(float));
                glBufferData(GL_ARRAY_BUFFER, bytes, b->bank, GL_STREAM_DRAW);
                uploaded = glGetError() == GL_NO_ERROR;
            }
            if (uploaded) ++b->uploads;
            else { ++b->upload_failures; b->stream_disabled = 1; }
        }
        if (uploaded) {
            const GLsizei stride = (GLsizei)(STRIDE * sizeof(float));
            glVertexPointer(3, GL_FLOAT, stride, (const void *)(uintptr_t)0);
            glTexCoordPointer(2, GL_FLOAT, stride, (const void *)(uintptr_t)(3 * sizeof(float)));
            glColorPointer(4, GL_FLOAT, stride, (const void *)(uintptr_t)(5 * sizeof(float)));
        }
    }
    for (int32_t i = 0; i < b->command_count; ++i) {
        const command *c = &b->commands[i];
        switch (c->kind) {
        case C_ENABLE:
            if (c->b) glEnable((GLenum)c->a); else glDisable((GLenum)c->a);
            break;
        case C_BLEND: glBlendFunc((GLenum)c->a, (GLenum)c->b); break;
        case C_DEPTH: glDepthMask(c->a ? GL_TRUE : GL_FALSE); break;
        case C_FRONT: glFrontFace((GLenum)c->a); break;
        case C_POLYGON: glPolygonMode(GL_FRONT_AND_BACK, (GLenum)c->a); break;
        case C_TEXTURE: glBindTexture(GL_TEXTURE_2D, c->a); break;
        case C_DRAW:
            if (!uploaded) { /* identical client arrays after an upload failure */
                const GLsizei stride = (GLsizei)(STRIDE * sizeof(float));
                glBindBuffer(GL_ARRAY_BUFFER, 0);
                glVertexPointer(3, GL_FLOAT, stride, b->bank);
                glTexCoordPointer(2, GL_FLOAT, stride, b->bank + 3);
                glColorPointer(4, GL_FLOAT, stride, b->bank + 5);
            }
            if (c->a == GL_TRIANGLE_FAN) {
                if (c->fan_count == 1)
                    glDrawArrays(GL_TRIANGLE_FAN, b->bank_first[c->fan_first], b->bank_counts[c->fan_first]);
                else
                    glMultiDrawArrays(GL_TRIANGLE_FAN, b->bank_first + c->fan_first,
                                      b->bank_counts + c->fan_first, c->fan_count);
            } else glDrawArrays((GLenum)c->a, c->first, c->count);
            ++b->stats.draws;
            break;
        }
    }
    glBindBuffer(GL_ARRAY_BUFFER, (GLuint)previous_array_buffer);
    b->bank_count = b->bank_fans = b->command_count = 0;
    if (b->stream_disabled) b->stream = 0;
}

static int capture_draw(mu_gl_batch *b)
{
    /* Split only at an existing draw boundary, never inside a primitive. */
    if (b->bank_count && (int64_t)b->bank_count + b->count > 65536)
        flush_capture(b);
    if (!b->stream) return 0;
    int64_t vertices = (int64_t)b->bank_count + b->count;
    if (vertices > INT32_MAX ||
        !grow((void **)&b->bank, &b->bank_capacity, (int32_t)vertices, STRIDE * sizeof(float)) ||
        !grow((void **)&b->commands, &b->command_capacity, b->command_count + 1, sizeof(command)) ||
        !grow((void **)&b->bank_first, &b->bank_first_capacity, b->bank_fans + b->fans, sizeof(GLint)) ||
        !grow((void **)&b->bank_counts, &b->bank_counts_capacity, b->bank_fans + b->fans, sizeof(GLsizei)))
        return 0;
    command c = {C_DRAW, b->mode, 0, b->bank_count, b->count, b->bank_fans, b->fans};
    memcpy(b->bank + (size_t)b->bank_count * STRIDE, b->v, (size_t)b->count * STRIDE * sizeof(float));
    for (int32_t i = 0; i < b->fans; ++i) {
        b->bank_first[b->bank_fans + i] = b->bank_count + b->first[i];
        b->bank_counts[b->bank_fans + i] = b->counts[i];
    }
    b->commands[b->command_count++] = c;
    b->bank_count = (int32_t)vertices;
    b->bank_fans += b->fans;
    return 1;
}

static void disable_capture(mu_gl_batch *b)
{
    flush_capture(b);
    if (!b->stream_disabled) ++b->upload_failures;
    b->stream = 0;
    b->stream_disabled = 1;
}

static int capture_state(mu_gl_batch *b, enum command_kind kind, uint32_t a, uint32_t value)
{
    if (!b->stream) return 0;
    if (!grow((void **)&b->commands, &b->command_capacity, b->command_count + 1, sizeof(command))) {
        disable_capture(b);
        return 0;
    }
    command c = {kind, a, value, 0, 0, 0, 0};
    b->commands[b->command_count++] = c;
    return 1;
}

static void flush_pending(mu_gl_batch *b)
{
    if (!b->mode || !b->count) {
        b->mode = 0; b->count = 0; b->fans = 0;
        return;
    }
    if (b->stream) {
        if (capture_draw(b)) {
            b->mode = 0; b->count = 0; b->fans = 0;
            return;
        }
        disable_capture(b); /* old pending vertices are still intact */
    }
    if (!b->arrays) {
        glEnableClientState(GL_VERTEX_ARRAY);
        glEnableClientState(GL_TEXTURE_COORD_ARRAY);
        glEnableClientState(GL_COLOR_ARRAY);
        b->arrays = 1;
    }
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    const GLsizei stride = (GLsizei)(STRIDE * sizeof(float));
    glVertexPointer(3, GL_FLOAT, stride, b->v);
    glTexCoordPointer(2, GL_FLOAT, stride, b->v + 3);
    glColorPointer(4, GL_FLOAT, stride, b->v + 5);
    if (b->mode == GL_TRIANGLE_FAN) {
        if (b->fans == 1) glDrawArrays(GL_TRIANGLE_FAN, b->first[0], b->counts[0]);
        else glMultiDrawArrays(GL_TRIANGLE_FAN, b->first, b->counts, b->fans);
    } else glDrawArrays((GLenum)b->mode, 0, b->count);
    ++b->stats.draws;
    b->mode = 0; b->count = 0; b->fans = 0;
}

void mu_gl_batch_flush(mu_gl_batch *b)
{
    flush_pending(b);
    flush_capture(b);
}

void mu_gl_batch_session_begin(mu_gl_batch *b)
{
    forget(b);
    b->mode = 0;
    b->count = 0;
    b->fans = 0;
    b->in_begin = 0;
    b->arrays = 0;
    const char *reference = getenv("MU_PERF_004_BASELINE");
    const char *vbo_reference = getenv("MU_PERF_004_VBO_BASELINE");
    b->stream = !b->stream_disabled && !(reference && reference[0] == '1') &&
                !(vbo_reference && vbo_reference[0] == '1');
    b->bank_count = b->bank_fans = b->command_count = 0;
    glGetIntegerv(GL_ARRAY_BUFFER_BINDING, &b->saved_array_buffer);
    b->session_active = 1;
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
    if (b->session_active) glBindBuffer(GL_ARRAY_BUFFER, (GLuint)b->saved_array_buffer);
    b->session_active = 0;
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
    flush_pending(b);
    if (!capture_state(b, C_ENABLE, capability, (uint32_t)on)) {
        if (on) glEnable((GLenum)capability); else glDisable((GLenum)capability);
    }
    if (i >= 0)
        b->cap[i] = on;
    b->stats.state_applied++;
}

void mu_gl_batch_blend_func(mu_gl_batch *b, uint32_t src, uint32_t dst)
{
    b->stats.state_calls++;
    if (b->blend_src == (int64_t)src && b->blend_dst == (int64_t)dst)
        return;
    flush_pending(b);
    if (!capture_state(b, C_BLEND, src, dst)) glBlendFunc((GLenum)src, (GLenum)dst);
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
    flush_pending(b);
    if (!capture_state(b, C_DEPTH, (uint32_t)on, 0)) glDepthMask(on ? GL_TRUE : GL_FALSE);
    b->depth_mask = on;
    b->stats.state_applied++;
}

void mu_gl_batch_front_face(mu_gl_batch *b, uint32_t mode)
{
    b->stats.state_calls++;
    if (b->front_face == (int64_t)mode)
        return;
    flush_pending(b);
    if (!capture_state(b, C_FRONT, mode, 0)) glFrontFace((GLenum)mode);
    b->front_face = mode;
    b->stats.state_applied++;
}

void mu_gl_batch_polygon_mode(mu_gl_batch *b, uint32_t mode)
{
    b->stats.state_calls++;
    if (b->polygon_mode == (int64_t)mode)
        return;
    flush_pending(b);
    if (!capture_state(b, C_POLYGON, mode, 0)) glPolygonMode(GL_FRONT_AND_BACK, (GLenum)mode);
    b->polygon_mode = mode;
    b->stats.state_applied++;
}

void mu_gl_batch_bind_texture(mu_gl_batch *b, uint32_t name)
{
    b->stats.state_calls++;
    if (b->texture == (int64_t)name)
        return;
    flush_pending(b);
    if (!capture_state(b, C_TEXTURE, name, 0)) glBindTexture(GL_TEXTURE_2D, (GLuint)name);
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
        flush_pending(b);
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

void mu_gl_batch_upload_stats(const mu_gl_batch *b, long *uploads, long *failures)
{
    *uploads = b->uploads;
    *failures = b->upload_failures;
}
