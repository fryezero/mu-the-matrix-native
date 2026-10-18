/* Deterministic software rasterizer. See mu_raster.h. */
#include "mu_raster.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

int mu_raster_init(mu_raster *r, int32_t width, int32_t height)
{
    memset(r, 0, sizeof *r);
    if (width <= 0 || height <= 0 || width > 8192 || height > 8192)
        return 1;
    r->width = width;
    r->height = height;
    r->color = calloc((size_t)width * (size_t)height, 4);
    r->depth = calloc((size_t)width * (size_t)height, sizeof(float));
    r->linear = 0;
    r->texture_slot = -1;
    r->alpha_reference = 0.25f;
    r->front_ccw = 1;
    r->current_color[0] = r->current_color[1] = r->current_color[2] = r->current_color[3] = 1.0f;
    if (!r->color || !r->depth) {
        mu_raster_free(r);
        return 1;
    }
    return 0;
}

void mu_raster_free(mu_raster *r)
{
    free(r->color);
    free(r->depth);
    free(r->vertices);
    memset(r, 0, sizeof *r);
}

void mu_raster_clear(mu_raster *r, const uint8_t rgba[4])
{
    size_t count = (size_t)r->width * (size_t)r->height;
    for (size_t i = 0; i < count; ++i) {
        memcpy(r->color + 4 * i, rgba, 4);
        r->depth[i] = 1.0f;
    }
}

typedef struct clip_vertex {
    float c[4], t[2], col[4];
} clip_vertex;

static void transform(const mu_raster *r, const float p[3], float out[4])
{
    float eye[4];
    for (int row = 0; row < 4; ++row) {
        float s = r->view[row] * p[0];
        s = s + r->view[4 + row] * p[1];
        s = s + r->view[8 + row] * p[2];
        s = s + r->view[12 + row];
        eye[row] = s;
    }
    for (int row = 0; row < 4; ++row) {
        float s = r->projection[row] * eye[0];
        s = s + r->projection[4 + row] * eye[1];
        s = s + r->projection[8 + row] * eye[2];
        s = s + r->projection[12 + row] * eye[3];
        out[row] = s;
    }
}

static clip_vertex lerp_vertex(const clip_vertex *a, const clip_vertex *b, float t)
{
    clip_vertex v;
    for (int k = 0; k < 4; ++k)
        v.c[k] = a->c[k] + (b->c[k] - a->c[k]) * t;
    for (int k = 0; k < 2; ++k)
        v.t[k] = a->t[k] + (b->t[k] - a->t[k]) * t;
    for (int k = 0; k < 4; ++k)
        v.col[k] = a->col[k] + (b->col[k] - a->col[k]) * t;
    return v;
}

static int clip_plane(const clip_vertex *in, int count, clip_vertex *out, int far)
{
    int n = 0;
    for (int i = 0; i < count; ++i) {
        const clip_vertex *a = &in[i], *b = &in[(i + 1) % count];
        float da = far ? a->c[3] - a->c[2] : a->c[2] + a->c[3];
        float db = far ? b->c[3] - b->c[2] : b->c[2] + b->c[3];
        if (da >= 0)
            out[n++] = *a;
        if ((da >= 0) != (db >= 0)) {
            float t = da / (da - db);
            out[n++] = lerp_vertex(a, b, t);
        }
    }
    return n;
}

static void sample(const mu_raster *r, float s, float t, float out[4])
{
    const mu_image *image = r->texture;
    if (!image || !r->state.texture) {
        out[0] = out[1] = out[2] = out[3] = 1.0f;
        return;
    }
    const int32_t w = image->width, h = image->height;
    /* r->clamp: GL_CLAMP terrain-side bitmaps (decals, NATIVE-TERRAIN-002) */
    const int clamp = r->clamp ||
                      (r->texture_wrap && r->texture_slot >= 0 && r->texture_wrap[r->texture_slot] == 0x2900u);
    if (clamp) {
        s = s < 0.0f ? 0.0f : (s > 1.0f ? 1.0f : s);
        t = t < 0.0f ? 0.0f : (t > 1.0f ? 1.0f : t);
    }
    const int linear = r->linear ||
                       (r->texture_filter && r->texture_slot >= 0 && r->texture_filter[r->texture_slot] == 0x2601u);
    if (!linear) {
        double x = floor((double)s * w), y = floor((double)t * h);
        long long xi = (long long)fmod(x, (double)w), yi = (long long)fmod(y, (double)h);
        if (xi < 0) xi += w;
        if (yi < 0) yi += h;
        if (clamp) {
            xi = (long long)(x < 0 ? 0 : (x >= w ? w - 1 : x));
            yi = (long long)(y < 0 ? 0 : (y >= h ? h - 1 : y));
        }
        const uint8_t *p = image->rgba + 4 * ((size_t)yi * (size_t)w + (size_t)xi);
        for (int k = 0; k < 4; ++k)
            out[k] = (float)p[k] / 255.0f;
        return;
    }
    float u = s * (float)w - 0.5f, v = t * (float)h - 0.5f;
    double fu = floor((double)u), fv = floor((double)v);
    float ax = (float)((double)u - fu), ay = (float)((double)v - fv);
    long long x0 = (long long)fmod(fu, (double)w), y0 = (long long)fmod(fv, (double)h);
    if (x0 < 0) x0 += w;
    if (y0 < 0) y0 += h;
    long long x1 = (x0 + 1) % w, y1 = (y0 + 1) % h;
    const uint8_t *p00 = image->rgba + 4 * ((size_t)y0 * (size_t)w + (size_t)x0);
    const uint8_t *p10 = image->rgba + 4 * ((size_t)y0 * (size_t)w + (size_t)x1);
    const uint8_t *p01 = image->rgba + 4 * ((size_t)y1 * (size_t)w + (size_t)x0);
    const uint8_t *p11 = image->rgba + 4 * ((size_t)y1 * (size_t)w + (size_t)x1);
    for (int k = 0; k < 4; ++k) {
        float top = (float)p00[k] + ((float)p10[k] - (float)p00[k]) * ax;
        float bottom = (float)p01[k] + ((float)p11[k] - (float)p01[k]) * ax;
        out[k] = (top + (bottom - top) * ay) / 255.0f;
    }
}

static float factor(uint32_t which, const float src[4], const float dst[4], int channel)
{
    switch (which) {
    case MU_GL_ZERO: return 0.0f;
    case MU_GL_ONE: return 1.0f;
    case MU_GL_SRC_COLOR: return src[channel];
    case MU_GL_ONE_MINUS_SRC_COLOR: return 1.0f - src[channel];
    case MU_GL_SRC_ALPHA: return src[3];
    case MU_GL_ONE_MINUS_SRC_ALPHA: return 1.0f - src[3];
    case 0x306: return dst[channel];   /* GL_DST_COLOR: effect multiply blending (NATIVE-FX-001) */
    default: return 1.0f;
    }
}

static float clamp01(float v) { return v < 0.0f ? 0.0f : (v > 1.0f ? 1.0f : v); }

static float edge(const float a[2], const float b[2], float px, float py)
{
    float left = (b[0] - a[0]) * (py - a[1]);
    float right = (b[1] - a[1]) * (px - a[0]);
    return left - right;
}

static int top_left(const float a[2], const float b[2])
{
    float dx = b[0] - a[0], dy = b[1] - a[1];
    return dy < 0.0f || (dy == 0.0f && dx > 0.0f);
}

static void raster_triangle(mu_raster *r, const clip_vertex *in[3])
{
    float s[3][2], z[3], iw[3];
    for (int k = 0; k < 3; ++k) {
        iw[k] = 1.0f / in[k]->c[3];
        float nx = in[k]->c[0] * iw[k], ny = in[k]->c[1] * iw[k], nz = in[k]->c[2] * iw[k];
        s[k][0] = (nx + 1.0f) * 0.5f * (float)r->width;
        s[k][1] = (ny + 1.0f) * 0.5f * (float)r->height;
        z[k] = (nz + 1.0f) * 0.5f;
    }
    float area = edge(s[0], s[1], s[2][0], s[2][1]);
    if (!(area != 0.0f))
        return;
    int front = r->front_ccw ? area > 0.0f : area < 0.0f;
    if (r->state.cull && !front)
        return;
    int order[3] = {0, 1, 2};
    if (area < 0.0f) {
        order[1] = 2;
        order[2] = 1;
        area = -area;
    }
    const float *a = s[order[0]], *b = s[order[1]], *c = s[order[2]];
    float minx = a[0], maxx = a[0], miny = a[1], maxy = a[1];
    for (int k = 1; k < 3; ++k) {
        const float *q = s[order[k]];
        if (q[0] < minx) minx = q[0];
        if (q[0] > maxx) maxx = q[0];
        if (q[1] < miny) miny = q[1];
        if (q[1] > maxy) maxy = q[1];
    }
    long x0 = (long)ceil((double)minx - 0.5), x1 = (long)floor((double)maxx - 0.5);
    long y0 = (long)ceil((double)miny - 0.5), y1 = (long)floor((double)maxy - 0.5);
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > r->width - 1) x1 = r->width - 1;
    if (y1 > r->height - 1) y1 = r->height - 1;
    const int tl0 = top_left(b, c), tl1 = top_left(c, a), tl2 = top_left(a, b);
    const clip_vertex *va = in[order[0]], *vb = in[order[1]], *vc = in[order[2]];
    const float za = z[order[0]], zb = z[order[1]], zc = z[order[2]];
    const float wa = iw[order[0]], wb = iw[order[1]], wc = iw[order[2]];
    r->triangles++;
    for (long py = y0; py <= y1; ++py) {
        float cy = (float)py + 0.5f;
        size_t row = (size_t)(r->height - 1 - py) * (size_t)r->width;
        for (long px = x0; px <= x1; ++px) {
            float cx = (float)px + 0.5f;
            float e0 = edge(b, c, cx, cy), e1 = edge(c, a, cx, cy), e2 = edge(a, b, cx, cy);
            if (e0 < 0.0f || e1 < 0.0f || e2 < 0.0f)
                continue;
            if ((e0 == 0.0f && !tl0) || (e1 == 0.0f && !tl1) || (e2 == 0.0f && !tl2))
                continue;
            float l0 = e0 / area, l1 = e1 / area, l2 = e2 / area;
            float depth = l0 * za;
            depth = depth + l1 * zb;
            depth = depth + l2 * zc;
            size_t index = row + (size_t)px;
            if (r->state.depth_test && !(depth <= r->depth[index]))
                continue;
            float q0 = l0 * wa, q1 = l1 * wb, q2 = l2 * wc;
            float inv = q0 + q1;
            inv = inv + q2;
            float tex[2], col[4];
            for (int k = 0; k < 2; ++k) {
                float v = q0 * va->t[k];
                v = v + q1 * vb->t[k];
                v = v + q2 * vc->t[k];
                tex[k] = v / inv;
            }
            for (int k = 0; k < 4; ++k) {
                float v = q0 * va->col[k];
                v = v + q1 * vb->col[k];
                v = v + q2 * vc->col[k];
                col[k] = clamp01(v / inv);
            }
            float texel[4], src[4];
            sample(r, tex[0], tex[1], texel);
            for (int k = 0; k < 4; ++k)
                src[k] = texel[k] * col[k];
            if (r->state.alpha_test && !(src[3] > r->alpha_reference))
                continue;
            uint8_t *out = r->color + 4 * index;
            float result[4];
            if (r->state.blend) {
                float dst[4];
                for (int k = 0; k < 4; ++k)
                    dst[k] = (float)out[k] / 255.0f;
                for (int k = 0; k < 4; ++k) {
                    float v = src[k] * factor(r->state.src, src, dst, k);
                    v = v + dst[k] * factor(r->state.dst, src, dst, k);
                    result[k] = clamp01(v);
                }
            } else {
                for (int k = 0; k < 4; ++k)
                    result[k] = clamp01(src[k]);
            }
            for (int k = 0; k < 4; ++k)
                out[k] = (uint8_t)(result[k] * 255.0f + 0.5f);
            if (r->state.depth_test && r->state.depth_mask)
                r->depth[index] = depth;
            r->fragments++;
        }
    }
}

static void emit_triangle(mu_raster *r, const mu_raster_vertex *v)
{
    clip_vertex polygon[8], scratch[8];
    for (int k = 0; k < 3; ++k) {
        transform(r, v[k].position, polygon[k].c);
        memcpy(polygon[k].t, v[k].texcoord, sizeof polygon[k].t);
        memcpy(polygon[k].col, v[k].color, sizeof polygon[k].col);
    }
    int n = clip_plane(polygon, 3, scratch, 0);
    if (n < 3)
        return;
    n = clip_plane(scratch, n, polygon, 1);
    if (n < 3)
        return;
    for (int k = 1; k + 1 < n; ++k) {
        const clip_vertex *tri[3] = {&polygon[0], &polygon[k], &polygon[k + 1]};
        raster_triangle(r, tri);
    }
}

/* Backend callbacks. */
static void prepare(void *context, const mu_meshdraw_state *state, int32_t texture)
{
    mu_raster *r = context;
    r->state = *state;
    r->texture_slot = (r->textures && texture >= 0 && texture < r->texture_count) ? texture : -1;
    r->texture = r->texture_slot >= 0 ? r->textures[texture] : NULL;
}

static void begin(void *context) { ((mu_raster *)context)->vertex_count = 0; }

static void end(void *context)
{
    mu_raster *r = context;
    for (int32_t i = 0; i + 2 < r->vertex_count; i += 3)
        emit_triangle(r, &r->vertices[i]);
    r->vertex_count = 0;
}

static void texcoord(void *context, float s, float t)
{
    mu_raster *r = context;
    r->current_texcoord[0] = s;
    r->current_texcoord[1] = t;
}

static void color3(void *context, const float rgb[3])
{
    mu_raster *r = context;
    r->current_color[0] = rgb[0];
    r->current_color[1] = rgb[1];
    r->current_color[2] = rgb[2];
    r->current_color[3] = 1.0f;
}

static void color4(void *context, float red, float green, float blue, float alpha)
{
    mu_raster *r = context;
    r->current_color[0] = red;
    r->current_color[1] = green;
    r->current_color[2] = blue;
    r->current_color[3] = alpha;
}

static void vertex(void *context, const float xyz[3])
{
    mu_raster *r = context;
    if (r->vertex_count == r->vertex_capacity) {
        int32_t capacity = r->vertex_capacity ? r->vertex_capacity * 2 : 4096;
        mu_raster_vertex *grown = realloc(r->vertices, sizeof *grown * (size_t)capacity);
        if (!grown)
            return;
        r->vertices = grown;
        r->vertex_capacity = capacity;
    }
    mu_raster_vertex *v = &r->vertices[r->vertex_count++];
    memcpy(v->position, xyz, sizeof v->position);
    memcpy(v->texcoord, r->current_texcoord, sizeof v->texcoord);
    for (int k = 0; k < 4; ++k)
        v->color[k] = clamp01(r->current_color[k]);
}

void mu_raster_set(mu_raster *r, const mu_meshdraw_state *state, const mu_image *texture, int linear)
{
    r->state = *state;
    r->texture = texture;
    r->texture_slot = -1;   /* no per-slot filter/wrap: `linear` decides */
    r->linear = linear;
}

void mu_raster_begin_mode(mu_raster *r, int mode)
{
    r->primitive = mode;
    r->vertex_count = 0;
}

void mu_raster_end_mode(mu_raster *r)
{
    if (r->primitive == 6) {
        for (int32_t i = 1; i + 1 < r->vertex_count; ++i) {
            mu_raster_vertex t[3] = {r->vertices[0], r->vertices[i], r->vertices[i + 1]};
            emit_triangle(r, t);
        }
    } else if (r->primitive == 7) {
        for (int32_t i = 0; i + 3 < r->vertex_count; i += 4) {
            mu_raster_vertex a[3] = {r->vertices[i], r->vertices[i + 1], r->vertices[i + 2]};
            mu_raster_vertex b[3] = {r->vertices[i], r->vertices[i + 2], r->vertices[i + 3]};
            emit_triangle(r, a);
            emit_triangle(r, b);
        }
    } else {
        for (int32_t i = 0; i + 2 < r->vertex_count; i += 3)
            emit_triangle(r, &r->vertices[i]);
    }
    r->vertex_count = 0;
}

void mu_raster_backend(mu_raster *r, mu_render_backend *backend)
{
    memset(backend, 0, sizeof *backend);
    backend->context = r;
    backend->prepare = prepare;
    backend->begin = begin;
    backend->end = end;
    backend->sink.context = r;
    backend->sink.texcoord = texcoord;
    backend->sink.color3 = color3;
    backend->sink.color4 = color4;
    backend->sink.vertex = vertex;
}
