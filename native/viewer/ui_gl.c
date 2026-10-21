/* The 2D interface calls on OpenGL (NATIVE-PERF-001). See ui_gl.h. */
#include "ui_gl.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

#define UI_PROJECTION 0x1701u
#define UI_TRIANGLES 4u
#define UI_TRIANGLE_FAN 6u
#define UI_QUADS 7u
#define UI_TEXTURE_2D 0x0de1u
#define UI_BLEND 0x0be2u
#define UI_ALPHA_TEST 0x0bc0u
#define UI_CULL_FACE 0x0b44u
#define UI_REPEAT 0x2901u
#define UI_COLOR_BUFFER_BIT 0x4000u
#define UI_MAX_VERTICES 64
#define UI_MAX_TEXTURES 1024

typedef struct ui_texture {
    uint32_t name;          /* the client's texture name */
    GLuint gl;
    int32_t width, height;
    uint32_t min_filter, mag_filter, wrap_s, wrap_t;
    int has_pixels;         /* uploaded through this sink */
    int pulled;             /* taken from the raster */
    int params_dirty;
    int used;               /* drawn since its last upload */
    GLint filter_set;       /* the GL filter last applied (0 none) */
} ui_texture;

/* GL names a re-upload replaced while the GPU may still read them: re-specifying
 * a texture an earlier draw of this frame samples makes the driver wait for the
 * GPU (the client re-uploads its font texture for every string), so a new
 * upload goes to a fresh name and the old one is reused a few series later. */
#define UI_RETIRED 64
#define UI_RETIRE_SERIES 4
static uint32_t series;   /* mu_ui_gl_end calls */

typedef struct ui_vertex {
    double x, y, w;
    float u, v;
    float color[4];
} ui_vertex;

struct mu_ui_gl {
    const mu_ui_raster *raster;
    int32_t width, height;
    double projection[MU_UI_RASTER_STACK][16];
    double modelview[MU_UI_RASTER_STACK][16];
    int projection_depth, modelview_depth;
    uint32_t matrix_mode;
    int32_t viewport[4];
    uint8_t texture_2d, blend, alpha_test, cull_face;
    uint32_t blend_src, blend_dst;
    float clear_color[4];
    uint32_t bound;
    float color[4];
    float texcoord[2];
    uint32_t primitive;
    int in_begin;
    ui_vertex vertices[UI_MAX_VERTICES];
    int vertex_count;
    ui_texture textures[UI_MAX_TEXTURES];
    int texture_count;
    uint8_t *scratch;
    size_t scratch_cap;
    GLuint retired[UI_RETIRED];
    uint32_t retired_at[UI_RETIRED];
    int retired_count;
    mu_ui_gl_stats stats;
};

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

/* Column-major, out = a * b (as mu_ui_raster). */
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

static double *current_matrix(mu_ui_gl *g)
{
    if (g->matrix_mode == UI_PROJECTION)
        return g->projection[g->projection_depth];
    return g->modelview[g->modelview_depth];
}

static void reset(mu_ui_gl *g)
{
    identity(g->projection[0]);
    identity(g->modelview[0]);
    g->projection_depth = g->modelview_depth = 0;
    g->matrix_mode = 0x1700u;
    g->viewport[0] = g->viewport[1] = 0;
    g->viewport[2] = g->width;
    g->viewport[3] = g->height;
    g->texture_2d = 1;   /* mu_ui_raster_init: the state after the camera setup 0x0184adc7 */
    g->cull_face = 1;
    g->blend = 0;
    g->alpha_test = 0;
    g->blend_src = 1;
    g->blend_dst = 0;
    g->color[0] = g->color[1] = g->color[2] = g->color[3] = 1.0f;
    memset(g->clear_color, 0, sizeof g->clear_color);
    g->clear_color[3] = 1.0f;
}

mu_ui_gl *mu_ui_gl_new(const mu_ui_raster *raster, int32_t width, int32_t height)
{
    mu_ui_gl *g = calloc(1, sizeof *g);
    if (!g)
        return NULL;
    g->raster = raster;
    g->width = width;
    g->height = height;
    reset(g);
    if (raster) {   /* continue from the raster's state (its 2D layer may have run already) */
        memcpy(g->projection, raster->projection, sizeof g->projection);
        memcpy(g->modelview, raster->modelview, sizeof g->modelview);
        g->projection_depth = raster->projection_depth;
        g->modelview_depth = raster->modelview_depth;
        g->matrix_mode = raster->matrix_mode;
        memcpy(g->viewport, raster->viewport, sizeof g->viewport);
        g->texture_2d = raster->texture_2d;
        g->blend = raster->blend;
        g->alpha_test = raster->alpha_test;
        g->cull_face = raster->cull_face;
        g->blend_src = raster->blend_src;
        g->blend_dst = raster->blend_dst;
        memcpy(g->clear_color, raster->clear_color, sizeof g->clear_color);
        g->bound = raster->bound_texture;
        memcpy(g->color, raster->color, sizeof g->color);
        memcpy(g->texcoord, raster->texcoord, sizeof g->texcoord);
    }
    return g;
}

void mu_ui_gl_free(mu_ui_gl *g)
{
    if (!g)
        return;
    for (int i = 0; i < g->texture_count; ++i)
        if (g->textures[i].gl)
            glDeleteTextures(1, &g->textures[i].gl);
    if (g->retired_count)
        glDeleteTextures(g->retired_count, g->retired);
    free(g->scratch);
    free(g);
}

void mu_ui_gl_resize(mu_ui_gl *g, int32_t width, int32_t height)
{
    if (g) {
        g->width = width;
        g->height = height;
    }
}

mu_ui_sink mu_ui_gl_sink(mu_ui_gl *g)
{
    mu_ui_sink sink = {g, mu_ui_gl_call};
    return sink;
}

void mu_ui_gl_stats_get(const mu_ui_gl *g, mu_ui_gl_stats *out)
{
    memset(out, 0, sizeof *out);
    if (g)
        *out = g->stats;
}

static ui_texture *texture(mu_ui_gl *g, uint32_t name, int create)
{
    for (int i = 0; i < g->texture_count; ++i)
        if (g->textures[i].name == name)
            return &g->textures[i];
    if (!create || g->texture_count >= UI_MAX_TEXTURES)
        return NULL;
    ui_texture *t = &g->textures[g->texture_count++];
    memset(t, 0, sizeof *t);
    t->name = name;
    t->min_filter = 0x2702;   /* GL defaults, as the raster */
    t->mag_filter = 0x2601;
    t->wrap_s = t->wrap_t = UI_REPEAT;
    t->params_dirty = 1;
    if (g->raster)   /* parameters set while the raster was the sink */
        for (int i = 0; i < g->raster->texture_count; ++i)
            if (g->raster->textures[i].name == name) {
                const mu_ui_texture_object *r = &g->raster->textures[i];
                t->min_filter = r->min_filter;
                t->mag_filter = r->mag_filter;
                t->wrap_s = r->wrap_s;
                t->wrap_t = r->wrap_t;
            }
    return t;
}

/* The raster samples the base level for every filter: NEAREST and the
 * NEAREST/NEAREST_MIPMAP modes as nearest, everything else bilinear. */
static GLint filter(uint32_t f) { return f == 0x2600 || f == 0x2700 || f == 0x2702 ? GL_NEAREST : GL_LINEAR; }
static GLint wrap(uint32_t w) { return w == UI_REPEAT ? GL_REPEAT : GL_CLAMP_TO_EDGE; }

static GLuint fresh_name(mu_ui_gl *g)
{
    for (int i = 0; i < g->retired_count; ++i)
        if (series - g->retired_at[i] >= UI_RETIRE_SERIES) {
            GLuint name = g->retired[i];
            g->retired[i] = g->retired[--g->retired_count];
            g->retired_at[i] = g->retired_at[g->retired_count];
            return name;
        }
    GLuint name = 0;
    glGenTextures(1, &name);
    return name;
}

static void upload(mu_ui_gl *g, ui_texture *t, int32_t w, int32_t h, const uint8_t *rgba)
{
    if (t->gl && t->used) {   /* in flight: retire it */
        if (g->retired_count == UI_RETIRED) {
            glDeleteTextures(1, &g->retired[0]);
            g->retired[0] = g->retired[--g->retired_count];
            g->retired_at[0] = g->retired_at[g->retired_count];
        }
        g->retired[g->retired_count] = t->gl;
        g->retired_at[g->retired_count++] = series;
        t->gl = 0;
    }
    t->used = 0;
    if (!t->gl) {
        t->gl = fresh_name(g);
        glBindTexture(GL_TEXTURE_2D, t->gl);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);   /* complete without mipmaps */
    }
    glBindTexture(GL_TEXTURE_2D, t->gl);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
    t->width = w;
    t->height = h;
    t->params_dirty = 1;
    t->filter_set = 0;
    g->stats.uploads++;
}

/* The bound texture for a primitive, NULL when the raster would draw it
 * untextured (texturing off or no pixels). */
static ui_texture *ready_texture(mu_ui_gl *g)
{
    if (!g->texture_2d)
        return NULL;
    ui_texture *t = texture(g, g->bound, 0);
    if (!t)
        t = texture(g, g->bound, 1);
    if (!t)
        return NULL;
    if (!t->has_pixels && !t->pulled && g->raster) {
        t->pulled = 1;   /* loaded before this sink was attached */
        for (int i = 0; i < g->raster->texture_count; ++i) {
            const mu_ui_texture_object *r = &g->raster->textures[i];
            if (r->name == t->name && r->rgba && r->width > 0 && r->height > 0) {
                upload(g, t, r->width, r->height, r->rgba);
                t->has_pixels = 1;
            }
        }
    }
    if (!t->has_pixels)
        return NULL;
    glBindTexture(GL_TEXTURE_2D, t->gl);
    t->used = 1;
    if (t->params_dirty) {
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap(t->wrap_s));
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap(t->wrap_t));
        t->filter_set = 0;
        t->params_dirty = 0;
    }
    return t;
}

static void window_xy(const mu_ui_gl *g, const ui_vertex *v, double *x, double *y)
{
    *x = (double)g->viewport[0] + (v->x / v->w + 1.0) * (double)g->viewport[2] * 0.5;
    *y = (double)g->viewport[1] + (v->y / v->w + 1.0) * (double)g->viewport[3] * 0.5;
}

/* The raster picks the magnification or the minification filter once per triangle (texel extent against
 * pixel extent); GL decides per pixel, and at a 1:1 scale its choice flips with rounding.  Both GL filters
 * are set to the raster's choice for the primitive's first triangle (fans and quads: the same shape). */
static void choose_filter(mu_ui_gl *g, ui_texture *t, const ui_vertex *a, const ui_vertex *b, const ui_vertex *c)
{
    double x0, y0, x1, y1, x2, y2;
    window_xy(g, a, &x0, &y0);
    window_xy(g, b, &x1, &y1);
    window_xy(g, c, &x2, &y2);
    double du = fabs((double)(b->u - a->u) * t->width) + fabs((double)(c->u - a->u) * t->width);
    double dx = fabs(x1 - x0) + fabs(x2 - x0);
    double dv = fabs((double)(b->v - a->v) * t->height) + fabs((double)(c->v - a->v) * t->height);
    double dy = fabs(y1 - y0) + fabs(y2 - y0);
    int magnify = du <= dx + 1e-9 && dv <= dy + 1e-9;
    GLint f = filter(magnify ? t->mag_filter : t->min_filter);
    if (f != t->filter_set) {
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, f);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, f);
        t->filter_set = f;
    }
}

static void apply_state(mu_ui_gl *g, int textured)
{
    glViewport(g->viewport[0], g->viewport[1], g->viewport[2], g->viewport[3]);
    if (textured)
        glEnable(GL_TEXTURE_2D);
    else
        glDisable(GL_TEXTURE_2D);
    if (g->blend) {
        glEnable(GL_BLEND);
        glBlendFunc((GLenum)g->blend_src, (GLenum)g->blend_dst);
    } else {
        glDisable(GL_BLEND);
    }
    if (g->alpha_test)
        glEnable(GL_ALPHA_TEST);
    else
        glDisable(GL_ALPHA_TEST);
    if (g->cull_face)
        glEnable(GL_CULL_FACE);
    else
        glDisable(GL_CULL_FACE);
}

static void emit_vertex(const ui_vertex *v)
{
    glTexCoord2f(v->u, v->v);
    glColor4f(v->color[0], v->color[1], v->color[2], v->color[3]);
    glVertex4d(v->x, v->y, 0.0, v->w);
}

static void flush(mu_ui_gl *g)
{
    int n = g->vertex_count;
    g->vertex_count = 0;
    g->stats.primitives++;
    if (g->primitive != UI_TRIANGLE_FAN && g->primitive != UI_QUADS && g->primitive != UI_TRIANGLES) {
        g->stats.unsupported++;
        return;
    }
    if (n < 3)
        return;
    ui_texture *t = ready_texture(g);
    const ui_vertex *v = g->vertices;
    if (t)
        choose_filter(g, t, &v[0], &v[1], &v[2]);
    apply_state(g, t != NULL);
    glBegin(GL_TRIANGLES);
    if (g->primitive == UI_TRIANGLE_FAN) {
        for (int i = 1; i + 1 < n; ++i) {
            emit_vertex(&v[0]);
            emit_vertex(&v[i]);
            emit_vertex(&v[i + 1]);
            g->stats.triangles++;
        }
    } else if (g->primitive == UI_QUADS) {
        for (int i = 0; i + 3 < n; i += 4) {
            emit_vertex(&v[i]);
            emit_vertex(&v[i + 1]);
            emit_vertex(&v[i + 2]);
            emit_vertex(&v[i]);
            emit_vertex(&v[i + 2]);
            emit_vertex(&v[i + 3]);
            g->stats.triangles += 2;
        }
    } else {
        for (int i = 0; i + 2 < n; i += 3) {
            emit_vertex(&v[i]);
            emit_vertex(&v[i + 1]);
            emit_vertex(&v[i + 2]);
            g->stats.triangles++;
        }
    }
    glEnd();
}

static void vertex(mu_ui_gl *g, double x, double y)
{
    if (!g->in_begin || g->vertex_count >= UI_MAX_VERTICES) {
        g->stats.unsupported++;
        return;
    }
    const double *mv = g->modelview[g->modelview_depth], *pr = g->projection[g->projection_depth];
    double eye[4], clip[4];
    for (int k = 0; k < 4; ++k)
        eye[k] = mv[0 * 4 + k] * x + mv[1 * 4 + k] * y + mv[3 * 4 + k];
    for (int k = 0; k < 4; ++k)
        clip[k] = pr[0 * 4 + k] * eye[0] + pr[1 * 4 + k] * eye[1] + pr[2 * 4 + k] * eye[2] + pr[3 * 4 + k] * eye[3];
    ui_vertex *v = &g->vertices[g->vertex_count++];
    v->x = clip[0];
    v->y = clip[1];
    v->w = clip[3];
    v->u = g->texcoord[0];
    v->v = g->texcoord[1];
    memcpy(v->color, g->color, sizeof v->color);
}

static void set_cap(mu_ui_gl *g, uint32_t cap, uint8_t value)
{
    switch (cap) {
    case UI_TEXTURE_2D: g->texture_2d = value; break;
    case UI_BLEND: g->blend = value; break;
    case UI_ALPHA_TEST: g->alpha_test = value; break;
    case UI_CULL_FACE: g->cull_face = value; break;
    default: break;   /* depth test, fog: no effect on the 2D layer (as the raster) */
    }
}

static void teximage(mu_ui_gl *g, const uint32_t *w, const void *data, size_t bytes)
{
    ui_texture *t = texture(g, g->bound, 1);
    int32_t tw = (int32_t)w[3], th = (int32_t)w[4];
    if (!t || tw <= 0 || th <= 0)
        return;
    size_t components = w[6] == 0x1907 ? 3 : 4;
    size_t n = (size_t)tw * (size_t)th, need = n * 4;
    const uint8_t *src = data;
    const uint8_t *pixels = src;
    if (!(components == 4 && src && bytes >= need)) {   /* convert as the raster does */
        if (need > g->scratch_cap) {
            uint8_t *grown = realloc(g->scratch, need);
            if (!grown)
                return;
            g->scratch = grown;
            g->scratch_cap = need;
        }
        uint8_t *out = g->scratch;
        for (size_t i = 0; i < n; ++i) {
            if (src && (i + 1) * components <= bytes) {
                out[i * 4] = src[i * components];
                out[i * 4 + 1] = src[i * components + 1];
                out[i * 4 + 2] = src[i * components + 2];
                out[i * 4 + 3] = components == 4 ? src[i * components + 3] : 255;
            } else {
                memset(out + i * 4, 0, 4);
            }
        }
        pixels = out;
    }
    upload(g, t, tw, th, pixels);
    t->has_pixels = 1;
}

void mu_ui_gl_call(void *user, int op, const uint32_t *w, int count, const void *data, size_t bytes)
{
    mu_ui_gl *g = user;
    (void)count;
    switch (op) {
    case MU_GL_MATRIXMODE: g->matrix_mode = w[0]; break;
    case MU_GL_PUSHMATRIX:
        if (g->matrix_mode == UI_PROJECTION && g->projection_depth + 1 < MU_UI_RASTER_STACK) {
            memcpy(g->projection[g->projection_depth + 1], g->projection[g->projection_depth], 16 * sizeof(double));
            ++g->projection_depth;
        } else if (g->matrix_mode != UI_PROJECTION && g->modelview_depth + 1 < MU_UI_RASTER_STACK) {
            memcpy(g->modelview[g->modelview_depth + 1], g->modelview[g->modelview_depth], 16 * sizeof(double));
            ++g->modelview_depth;
        }
        break;
    case MU_GL_POPMATRIX:
        if (g->matrix_mode == UI_PROJECTION && g->projection_depth > 0)
            --g->projection_depth;
        else if (g->matrix_mode != UI_PROJECTION && g->modelview_depth > 0)
            --g->modelview_depth;
        break;
    case MU_GL_LOADIDENTITY: identity(current_matrix(g)); break;
    case MU_GL_VIEWPORT: memcpy(g->viewport, w, 4 * sizeof(int32_t)); break;
    case MU_GLU_ORTHO2D: {
        double left = word_double(w), right = word_double(w + 2), bottom = word_double(w + 4),
               top = word_double(w + 6), m[16];
        identity(m);
        m[0] = 2.0 / (right - left);
        m[5] = 2.0 / (top - bottom);
        m[10] = -1.0;
        m[12] = -(right + left) / (right - left);
        m[13] = -(top + bottom) / (top - bottom);
        multiply(current_matrix(g), m);
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
        multiply(current_matrix(g), m);
        break;
    }
    case MU_GL_BEGIN: g->primitive = w[0]; g->in_begin = 1; g->vertex_count = 0; break;
    case MU_GL_END: if (g->in_begin) flush(g); g->in_begin = 0; break;
    case MU_GL_VERTEX2F: vertex(g, word_float(w[0]), word_float(w[1])); break;
    case MU_GL_TEXCOORD2F: g->texcoord[0] = word_float(w[0]); g->texcoord[1] = word_float(w[1]); break;
    case MU_GL_COLOR4F:
        for (int k = 0; k < 4; ++k)
            g->color[k] = word_float(w[k]);
        break;
    case MU_GL_COLOR3F:
        for (int k = 0; k < 3; ++k)
            g->color[k] = word_float(w[k]);
        g->color[3] = 1.0f;
        break;
    case MU_GL_COLOR4UB:
        for (int k = 0; k < 4; ++k)
            g->color[k] = (float)(w[k] & 0xff) / 255.0f;
        break;
    case MU_GL_BINDTEXTURE: g->bound = w[1]; texture(g, w[1], 1); break;
    case MU_GL_ENABLE: set_cap(g, w[0], 1); break;
    case MU_GL_DISABLE: set_cap(g, w[0], 0); break;
    case MU_GL_BLENDFUNC: g->blend_src = w[0]; g->blend_dst = w[1]; break;
    case MU_GL_TEXIMAGE2D: teximage(g, w, data, bytes); break;
    case MU_GL_TEXPARAMETERI: {
        ui_texture *t = texture(g, g->bound, 1);
        if (!t)
            break;
        if (w[1] == 0x2801) t->min_filter = w[2];
        else if (w[1] == 0x2800) t->mag_filter = w[2];
        else if (w[1] == 0x2802) t->wrap_s = w[2];
        else if (w[1] == 0x2803) t->wrap_t = w[2];
        t->params_dirty = 1;
        break;
    }
    case MU_GL_CLEARCOLOR:
        for (int k = 0; k < 4; ++k)
            g->clear_color[k] = word_float(w[k]);
        break;
    case MU_GL_CLEAR:
        if (w[0] & UI_COLOR_BUFFER_BIT) {
            glClearColor(g->clear_color[0], g->clear_color[1], g->clear_color[2], g->clear_color[3]);
            glClear(GL_COLOR_BUFFER_BIT);
        }
        break;
    default:
        break;   /* GenTextures, TexEnvf (MODULATE only), GDI, sounds, events */
    }
}

void mu_ui_gl_begin(mu_ui_gl *g)
{
    (void)g;
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();   /* vertices arrive in clip coordinates */
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glDisable(GL_FOG);
    glDisable(GL_LIGHTING);
    glDisable(GL_SCISSOR_TEST);
    glShadeModel(GL_SMOOTH);
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
    glFrontFace(GL_CCW);
    glCullFace(GL_BACK);
    glAlphaFunc(GL_GREATER, 0.25f);
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
}

void mu_ui_gl_end(mu_ui_gl *g)
{
    (void)g;
    ++series;
    glBindTexture(GL_TEXTURE_2D, 0);
    glDisable(GL_TEXTURE_2D);
    glDisable(GL_BLEND);
    glDisable(GL_ALPHA_TEST);
    glDepthMask(GL_TRUE);
    glEnable(GL_DEPTH_TEST);
}
