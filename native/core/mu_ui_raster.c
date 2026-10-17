/* Software OpenGL subset for the 2D interface layer.  See mu_ui_raster.h. */
#include "mu_ui_raster.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#define GL_PROJECTION 0x1701u
#define GL_MODELVIEW 0x1700u
#define GL_TRIANGLES 4u
#define GL_TRIANGLE_FAN 6u
#define GL_QUADS 7u
#define GL_TEXTURE_2D 0x0de1u
#define GL_BLEND 0x0be2u
#define GL_ALPHA_TEST 0x0bc0u
#define GL_CULL_FACE 0x0b44u
#define GL_NEAREST 0x2600u
#define GL_REPEAT 0x2901u
#define GL_COLOR_BUFFER_BIT 0x4000u

static float word_float(uint32_t word)
{
    float value;
    memcpy(&value, &word, 4);
    return value;
}

static double word_double(const uint32_t *words)
{
    double value;
    memcpy(&value, words, 8);
    return value;
}

static void identity(double *m)
{
    memset(m, 0, 16 * sizeof *m);
    m[0] = m[5] = m[10] = m[15] = 1.0;
}

/* Column-major like GL: m[col*4 + row]. out = a * b. */
static void multiply(double *a, const double *b)
{
    double out[16];
    for (int c = 0; c < 4; ++c)
        for (int r = 0; r < 4; ++r) {
            double sum = 0.0;
            for (int k = 0; k < 4; ++k)
                sum += a[k * 4 + r] * b[c * 4 + k];
            out[c * 4 + r] = sum;
        }
    memcpy(a, out, sizeof out);
}

static double *current_matrix(mu_ui_raster *r)
{
    if (r->matrix_mode == GL_PROJECTION)
        return r->projection[r->projection_depth];
    return r->modelview[r->modelview_depth];
}

size_t mu_ui_raster_sizeof(void)
{
    return sizeof(mu_ui_raster);
}

int mu_ui_raster_init(mu_ui_raster *r, int32_t width, int32_t height)
{
    memset(r, 0, sizeof *r);
    r->width = width;
    r->height = height;
    r->rgba = calloc((size_t)width * (size_t)height, 4);
    if (!r->rgba)
        return -1;
    for (size_t i = 0; i < (size_t)width * (size_t)height; ++i)
        r->rgba[i * 4 + 3] = 255;
    identity(r->projection[0]);
    identity(r->modelview[0]);
    r->matrix_mode = GL_MODELVIEW;
    r->viewport[2] = width;
    r->viewport[3] = height;
    /* State after the client's camera setup 0x0184adc7 (alpha test disabled
     * but configured GL_GREATER 0.25, texture enabled, cull face enabled). */
    r->texture_2d = 1;
    r->cull_face = 1;
    r->alpha_func = 0x0204;
    r->alpha_ref = 0.25f;
    r->blend_src = 1;
    r->blend_dst = 0;
    r->color[0] = r->color[1] = r->color[2] = r->color[3] = 1.0f;
    r->clear_color[3] = 1.0f;
    return 0;
}

void mu_ui_raster_free(mu_ui_raster *r)
{
    for (int i = 0; i < r->texture_count; ++i)
        free(r->textures[i].rgba);
    free(r->rgba);
    memset(r, 0, sizeof *r);
}

mu_ui_sink mu_ui_raster_sink(mu_ui_raster *raster)
{
    mu_ui_sink sink = {raster, mu_ui_raster_call};
    return sink;
}

void mu_ui_raster_read_top_down(const mu_ui_raster *r, uint8_t *out)
{
    size_t row = (size_t)r->width * 4;
    for (int32_t y = 0; y < r->height; ++y)
        memcpy(out + (size_t)y * row, r->rgba + (size_t)(r->height - 1 - y) * row, row);
}

static mu_ui_texture_object *texture(mu_ui_raster *r, uint32_t name, int create)
{
    for (int i = 0; i < r->texture_count; ++i)
        if (r->textures[i].name == name)
            return &r->textures[i];
    if (!create || r->texture_count >= MU_UI_RASTER_MAX_TEXTURES)
        return NULL;
    mu_ui_texture_object *t = &r->textures[r->texture_count++];
    memset(t, 0, sizeof *t);
    t->name = name;
    t->min_filter = 0x2702;      /* GL defaults: NEAREST_MIPMAP_LINEAR, LINEAR, REPEAT */
    t->mag_filter = 0x2601;
    t->wrap_s = t->wrap_t = GL_REPEAT;
    return t;
}

static int wrap_index(int i, int n, uint32_t mode)
{
    if (mode == GL_REPEAT) {
        i %= n;
        return i < 0 ? i + n : i;
    }
    return i < 0 ? 0 : (i >= n ? n - 1 : i);
}

static void fetch(const mu_ui_texture_object *t, int x, int y, float out[4])
{
    const uint8_t *p = t->rgba + ((size_t)y * (size_t)t->width + (size_t)x) * 4;
    for (int k = 0; k < 4; ++k)
        out[k] = (float)p[k] / 255.0f;
}

static void sample(const mu_ui_texture_object *t, float u, float v, int magnify, float out[4])
{
    uint32_t filter = magnify ? t->mag_filter : t->min_filter;
    if (t->wrap_s != GL_REPEAT)
        u = u < 0.0f ? 0.0f : (u > 1.0f ? 1.0f : u);
    if (t->wrap_t != GL_REPEAT)
        v = v < 0.0f ? 0.0f : (v > 1.0f ? 1.0f : v);
    if (filter == GL_NEAREST || filter == 0x2700 || filter == 0x2702) {
        /* NEAREST and the mipmap modes (no mipmaps are uploaded) sample the base level */
        int x = wrap_index((int)floorf(u * (float)t->width), t->width, t->wrap_s);
        int y = wrap_index((int)floorf(v * (float)t->height), t->height, t->wrap_t);
        fetch(t, x, y, out);
        return;
    }
    float fx = u * (float)t->width - 0.5f, fy = v * (float)t->height - 0.5f;
    int x0 = (int)floorf(fx), y0 = (int)floorf(fy);
    float ax = fx - (float)x0, ay = fy - (float)y0;
    int xa = wrap_index(x0, t->width, t->wrap_s), xb = wrap_index(x0 + 1, t->width, t->wrap_s);
    int ya = wrap_index(y0, t->height, t->wrap_t), yb = wrap_index(y0 + 1, t->height, t->wrap_t);
    float c00[4], c10[4], c01[4], c11[4];
    fetch(t, xa, ya, c00);
    fetch(t, xb, ya, c10);
    fetch(t, xa, yb, c01);
    fetch(t, xb, yb, c11);
    for (int k = 0; k < 4; ++k)
        out[k] = (c00[k] * (1 - ax) + c10[k] * ax) * (1 - ay) + (c01[k] * (1 - ax) + c11[k] * ax) * ay;
}

static float factor(uint32_t f, const float src[4], const float dst[4], int k)
{
    switch (f) {
    case 0: return 0.0f;
    case 1: return 1.0f;
    case 0x300: return src[k];
    case 0x301: return 1.0f - src[k];
    case 0x302: return src[3];
    case 0x303: return 1.0f - src[3];
    case 0x304: return dst[3];
    case 0x305: return 1.0f - dst[3];
    case 0x306: return dst[k];
    case 0x307: return 1.0f - dst[k];
    default: return 1.0f;
    }
}

static uint8_t to_byte(float v)
{
    if (!(v > 0.0f))
        return 0;
    if (v >= 1.0f)
        return 255;
    return (uint8_t)(v * 255.0f + 0.5f);
}

static void window_position(const mu_ui_raster *r, const mu_ui_vertex *v, double *x, double *y)
{
    double nx = v->x / v->w, ny = v->y / v->w;
    *x = (double)r->viewport[0] + (nx + 1.0) * (double)r->viewport[2] * 0.5;
    *y = (double)r->viewport[1] + (ny + 1.0) * (double)r->viewport[3] * 0.5;
}

static int top_left(double ax, double ay, double bx, double by)
{
    /* Counter-clockwise triangle in a y-up window: a left edge goes down,
     * a top edge is horizontal and goes left. */
    return (ay == by && bx < ax) || (by < ay);
}

static void triangle(mu_ui_raster *r, const mu_ui_vertex *a, const mu_ui_vertex *b, const mu_ui_vertex *c)
{
    double x[3], y[3];
    const mu_ui_vertex *v[3] = {a, b, c};
    for (int i = 0; i < 3; ++i)
        window_position(r, v[i], &x[i], &y[i]);
    double area = (x[1] - x[0]) * (y[2] - y[0]) - (x[2] - x[0]) * (y[1] - y[0]);
    if (area == 0.0)
        return;
    if (area < 0.0) {
        if (r->cull_face)
            return;                      /* back face (default CCW front, cull BACK) */
        const mu_ui_vertex *t = v[1];
        v[1] = v[2];
        v[2] = t;
        double tx = x[1], ty = y[1];
        x[1] = x[2]; y[1] = y[2];
        x[2] = tx; y[2] = ty;
        area = -area;
    }
    ++r->triangles;
    const mu_ui_texture_object *tex = r->texture_2d ? texture(r, r->bound_texture, 0) : NULL;
    if (tex && !tex->rgba)
        tex = NULL;
    double minx = fmin(x[0], fmin(x[1], x[2])), maxx = fmax(x[0], fmax(x[1], x[2]));
    double miny = fmin(y[0], fmin(y[1], y[2])), maxy = fmax(y[0], fmax(y[1], y[2]));
    int x0 = (int)floor(minx), x1 = (int)ceil(maxx), y0 = (int)floor(miny), y1 = (int)ceil(maxy);
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > r->width) x1 = r->width;
    if (y1 > r->height) y1 = r->height;
    /* texel footprint for the magnification decision */
    int magnify = 1;
    if (tex) {
        double du = fabs((double)(v[1]->u - v[0]->u) * tex->width) + fabs((double)(v[2]->u - v[0]->u) * tex->width);
        double dx = fabs(x[1] - x[0]) + fabs(x[2] - x[0]);
        double dv = fabs((double)(v[1]->v - v[0]->v) * tex->height) + fabs((double)(v[2]->v - v[0]->v) * tex->height);
        double dy = fabs(y[1] - y[0]) + fabs(y[2] - y[0]);
        magnify = du <= dx + 1e-9 && dv <= dy + 1e-9;
    }
    int tl0 = top_left(x[1], y[1], x[2], y[2]), tl1 = top_left(x[2], y[2], x[0], y[0]),
        tl2 = top_left(x[0], y[0], x[1], y[1]);
    for (int py = y0; py < y1; ++py) {
        double cy = py + 0.5;
        for (int px = x0; px < x1; ++px) {
            double cx = px + 0.5;
            double w0 = (x[2] - x[1]) * (cy - y[1]) - (y[2] - y[1]) * (cx - x[1]);
            double w1 = (x[0] - x[2]) * (cy - y[2]) - (y[0] - y[2]) * (cx - x[2]);
            double w2 = (x[1] - x[0]) * (cy - y[0]) - (y[1] - y[0]) * (cx - x[0]);
            if (w0 < 0 || w1 < 0 || w2 < 0)
                continue;
            if ((w0 == 0 && !tl0) || (w1 == 0 && !tl1) || (w2 == 0 && !tl2))
                continue;
            double l0 = w0 / area, l1 = w1 / area, l2 = w2 / area;
            float frag[4];
            for (int k = 0; k < 4; ++k)
                frag[k] = (float)(l0 * v[0]->color[k] + l1 * v[1]->color[k] + l2 * v[2]->color[k]);
            if (tex) {
                float texel[4];
                float u = (float)(l0 * v[0]->u + l1 * v[1]->u + l2 * v[2]->u);
                float t = (float)(l0 * v[0]->v + l1 * v[1]->v + l2 * v[2]->v);
                sample(tex, u, t, magnify, texel);
                for (int k = 0; k < 4; ++k)
                    frag[k] *= texel[k];               /* GL_MODULATE */
            }
            if (r->alpha_test && r->alpha_func == 0x0204 && !(frag[3] > r->alpha_ref))
                continue;
            uint8_t *dst = r->rgba + ((size_t)py * (size_t)r->width + (size_t)px) * 4;
            if (r->blend) {
                float d[4], out[4];
                for (int k = 0; k < 4; ++k)
                    d[k] = (float)dst[k] / 255.0f;
                for (int k = 0; k < 4; ++k)
                    out[k] = frag[k] * factor(r->blend_src, frag, d, k) + d[k] * factor(r->blend_dst, frag, d, k);
                for (int k = 0; k < 4; ++k)
                    dst[k] = to_byte(out[k]);
            } else {
                for (int k = 0; k < 4; ++k)
                    dst[k] = to_byte(frag[k]);
            }
            ++r->fragments;
        }
    }
}

static void flush(mu_ui_raster *r)
{
    int n = r->vertex_count;
    ++r->primitives;
    if (r->primitive == GL_TRIANGLE_FAN) {
        for (int i = 1; i + 1 < n; ++i)
            triangle(r, &r->vertices[0], &r->vertices[i], &r->vertices[i + 1]);
    } else if (r->primitive == GL_QUADS) {
        for (int i = 0; i + 3 < n; i += 4) {
            triangle(r, &r->vertices[i], &r->vertices[i + 1], &r->vertices[i + 2]);
            triangle(r, &r->vertices[i], &r->vertices[i + 2], &r->vertices[i + 3]);
        }
    } else if (r->primitive == GL_TRIANGLES) {
        for (int i = 0; i + 2 < n; i += 3)
            triangle(r, &r->vertices[i], &r->vertices[i + 1], &r->vertices[i + 2]);
    } else {
        ++r->unsupported;
    }
    r->vertex_count = 0;
}

static void vertex(mu_ui_raster *r, double x, double y)
{
    if (!r->in_begin || r->vertex_count >= MU_UI_RASTER_MAX_VERTICES) {
        ++r->unsupported;
        return;
    }
    const double *mv = r->modelview[r->modelview_depth], *pr = r->projection[r->projection_depth];
    double eye[4], clip[4];
    for (int k = 0; k < 4; ++k)
        eye[k] = mv[0 * 4 + k] * x + mv[1 * 4 + k] * y + mv[3 * 4 + k];
    for (int k = 0; k < 4; ++k)
        clip[k] = pr[0 * 4 + k] * eye[0] + pr[1 * 4 + k] * eye[1] + pr[2 * 4 + k] * eye[2] + pr[3 * 4 + k] * eye[3];
    mu_ui_vertex *v = &r->vertices[r->vertex_count++];
    v->x = clip[0];
    v->y = clip[1];
    v->z = clip[2];
    v->w = clip[3];
    v->u = r->texcoord[0];
    v->v = r->texcoord[1];
    memcpy(v->color, r->color, sizeof v->color);
}

static void set_cap(mu_ui_raster *r, uint32_t cap, uint8_t value)
{
    switch (cap) {
    case GL_TEXTURE_2D: r->texture_2d = value; break;
    case GL_BLEND: r->blend = value; break;
    case GL_ALPHA_TEST: r->alpha_test = value; break;
    case GL_CULL_FACE: r->cull_face = value; break;
    default: break;                      /* depth test, fog: no effect on 2D output */
    }
}

void mu_ui_raster_call(void *user, int op, const uint32_t *w, int count, const void *data, size_t bytes)
{
    mu_ui_raster *r = user;
    (void)count;
    switch (op) {
    case MU_GL_MATRIXMODE: r->matrix_mode = w[0]; break;
    case MU_GL_PUSHMATRIX:
        if (r->matrix_mode == GL_PROJECTION && r->projection_depth + 1 < MU_UI_RASTER_STACK) {
            memcpy(r->projection[r->projection_depth + 1], r->projection[r->projection_depth], 16 * sizeof(double));
            ++r->projection_depth;
        } else if (r->matrix_mode != GL_PROJECTION && r->modelview_depth + 1 < MU_UI_RASTER_STACK) {
            memcpy(r->modelview[r->modelview_depth + 1], r->modelview[r->modelview_depth], 16 * sizeof(double));
            ++r->modelview_depth;
        }
        break;
    case MU_GL_POPMATRIX:
        if (r->matrix_mode == GL_PROJECTION && r->projection_depth > 0)
            --r->projection_depth;
        else if (r->matrix_mode != GL_PROJECTION && r->modelview_depth > 0)
            --r->modelview_depth;
        break;
    case MU_GL_LOADIDENTITY: identity(current_matrix(r)); break;
    case MU_GL_VIEWPORT: memcpy(r->viewport, w, 4 * sizeof(int32_t)); break;
    case MU_GLU_ORTHO2D: {
        double left = word_double(w), right = word_double(w + 2), bottom = word_double(w + 4),
               top = word_double(w + 6), m[16];
        identity(m);
        m[0] = 2.0 / (right - left);
        m[5] = 2.0 / (top - bottom);
        m[10] = -1.0;
        m[12] = -(right + left) / (right - left);
        m[13] = -(top + bottom) / (top - bottom);
        multiply(current_matrix(r), m);
        break;
    }
    case MU_GLU_PERSPECTIVE: {
        double fovy = word_double(w), aspect = word_double(w + 2), znear = word_double(w + 4),
               zfar = word_double(w + 6), m[16];
        double f = 1.0 / tan(fovy * 3.14159265358979323846 / 360.0);
        memset(m, 0, sizeof m);
        m[0] = f / aspect;
        m[5] = f;
        m[10] = (zfar + znear) / (znear - zfar);
        m[11] = -1.0;
        m[14] = 2.0 * zfar * znear / (znear - zfar);
        multiply(current_matrix(r), m);
        break;
    }
    case MU_GL_BEGIN: r->primitive = w[0]; r->in_begin = 1; r->vertex_count = 0; break;
    case MU_GL_END: if (r->in_begin) flush(r); r->in_begin = 0; break;
    case MU_GL_VERTEX2F: vertex(r, word_float(w[0]), word_float(w[1])); break;
    case MU_GL_TEXCOORD2F: r->texcoord[0] = word_float(w[0]); r->texcoord[1] = word_float(w[1]); break;
    case MU_GL_COLOR4F:
        for (int k = 0; k < 4; ++k)
            r->color[k] = word_float(w[k]);
        break;
    case MU_GL_COLOR3F:
        for (int k = 0; k < 3; ++k)
            r->color[k] = word_float(w[k]);
        r->color[3] = 1.0f;
        break;
    case MU_GL_COLOR4UB:
        for (int k = 0; k < 4; ++k)
            r->color[k] = (float)(w[k] & 0xff) / 255.0f;
        break;
    case MU_GL_BINDTEXTURE: r->bound_texture = w[1]; texture(r, w[1], 1); break;
    case MU_GL_ENABLE: set_cap(r, w[0], 1); break;
    case MU_GL_DISABLE: set_cap(r, w[0], 0); break;
    case MU_GL_BLENDFUNC: r->blend_src = w[0]; r->blend_dst = w[1]; break;
    case MU_GL_TEXIMAGE2D: {
        mu_ui_texture_object *t = texture(r, r->bound_texture, 1);
        int32_t tw = (int32_t)w[3], th = (int32_t)w[4];
        uint32_t format = w[6];
        size_t components = format == 0x1907 ? 3 : 4;
        if (!t || tw <= 0 || th <= 0)
            break;
        uint8_t *pixels = realloc(t->rgba, (size_t)tw * (size_t)th * 4);
        if (!pixels)
            break;
        t->rgba = pixels;
        t->width = tw;
        t->height = th;
        const uint8_t *src = data;
        for (size_t i = 0; i < (size_t)tw * (size_t)th; ++i) {
            if (src && (i + 1) * components <= bytes) {
                pixels[i * 4] = src[i * components];
                pixels[i * 4 + 1] = src[i * components + 1];
                pixels[i * 4 + 2] = src[i * components + 2];
                pixels[i * 4 + 3] = components == 4 ? src[i * components + 3] : 255;
            } else {
                memset(pixels + i * 4, 0, 4);
            }
        }
        break;
    }
    case MU_GL_TEXPARAMETERI: {
        mu_ui_texture_object *t = texture(r, r->bound_texture, 1);
        if (!t)
            break;
        if (w[1] == 0x2801) t->min_filter = w[2];
        else if (w[1] == 0x2800) t->mag_filter = w[2];
        else if (w[1] == 0x2802) t->wrap_s = w[2];
        else if (w[1] == 0x2803) t->wrap_t = w[2];
        break;
    }
    case MU_GL_CLEARCOLOR:
        for (int k = 0; k < 4; ++k)
            r->clear_color[k] = word_float(w[k]);
        break;
    case MU_GL_CLEAR:
        if (w[0] & GL_COLOR_BUFFER_BIT) {
            uint8_t c[4];
            for (int k = 0; k < 4; ++k)
                c[k] = to_byte(r->clear_color[k]);
            for (size_t i = 0; i < (size_t)r->width * (size_t)r->height; ++i)
                memcpy(r->rgba + i * 4, c, 4);
        }
        break;
    default:
        break;   /* GenTextures, TexEnvf (MODULATE is the only mode used), GDI */
    }
}
