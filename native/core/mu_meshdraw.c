/* Port of the client's mesh draw 0x012b8d1d, body 0x012bb35a and GL state
 * wrappers. See mu_meshdraw.h and docs/research/client-meshdraw-exec.md.
 * Comments give the client address of each block. */
#include "mu_meshdraw.h"

#include <math.h>
#include <string.h>

/* Client binary32 constants (second image section). */
static const float K_099 = 0.99f;      /* 0x01a82fe0 */
static const float K_0001 = 0.0001f;   /* 0x01a80214 */
static const float K_00025 = 0.00025f; /* 0x01a7fd94 */
static const float K_04 = 0.4f;        /* 0x01a7df0c */
static const float K_0001T = 0.001f;   /* 0x01a7e308 */
static const float K_0002T = 0.002f;   /* 0x01a7ed78 */
static const float K_1 = 1.0f;         /* 0x01a7dd48 */
static const float K_08 = 0.8f;        /* 0x01a7df18 */
static const float K_2 = 2.0f;         /* 0x01a7e474 */
static const float K_3 = 3.0f;         /* 0x01a7e864 */
static const float K_05 = 0.5f;        /* 0x01a7df14 */
static const float K_25 = 2.5f;        /* 0x01a7e9ec */
static const float K_5 = 5.0f;         /* 0x01a7e4cc */
static const float K_6E5 = 6e-05f;     /* 0x01aabda0 */
static const float K_02 = 0.2f;        /* 0x01a7df08 */
static const float K_256 = 256.0f;     /* 0x01a7fb20 */
static const float K_2000 = 2000.0f;   /* 0x01a802d8 */
static const float K_4000 = 4000.0f;   /* 0x01a9ff0c */
static const float K_0007 = 0.007f;    /* 0x01a80228 */
static const float K_28 = 28.0f;       /* 0x01a7fb18 */
static const float K_0 = 0.0f;         /* 0x01a7dd3c */

static int16_t s16(const uint8_t *p) { return (int16_t)(uint16_t)(p[0] | (p[1] << 8)); }

static uint32_t fbits(float f)
{
    uint32_t u;
    memcpy(&u, &f, 4);
    return u;
}

/* cvttss2si: out-of-range and NaN give 0x80000000. */
static int32_t cvtt(float f)
{
    if (!(f >= -2147483648.0f && f < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)f;
}

/* (int)t % d with C (x86 idiv) remainder sign, then cvtsi2ss. */
static float remainder_float(float t, int32_t d)
{
    int32_t i = cvtt(t);
    int32_t r = (i == INT32_MIN && d == -1) ? 0 : i % d;
    return (float)r;
}

static float client_sin(float x) { return (float)sin((double)x); }
static float client_cos(float x) { return (float)cos((double)x); }

/* ---- GL emission ---- */

static void gl(const mu_meshdraw_env *e, uint32_t op, uint32_t a, uint32_t b, uint32_t c, uint32_t d)
{
    const uint32_t words[4] = {a, b, c, d};
    e->sink->call(e->sink->context, op, words);
}
static void gl_enable(const mu_meshdraw_env *e, uint32_t cap) { gl(e, MU_GL_OP_ENABLE, cap, 0, 0, 0); }
static void gl_disable(const mu_meshdraw_env *e, uint32_t cap) { gl(e, MU_GL_OP_DISABLE, cap, 0, 0, 0); }
static void gl_color3fv(const mu_meshdraw_env *e, const float *c)
{
    gl(e, MU_GL_OP_COLOR3FV, fbits(c[0]), fbits(c[1]), fbits(c[2]), 0);
}
static void gl_color4f(const mu_meshdraw_env *e, float r, float g, float b, float a)
{
    gl(e, MU_GL_OP_COLOR4F, fbits(r), fbits(g), fbits(b), fbits(a));
}
static void gl_color3f(const mu_meshdraw_env *e, float r, float g, float b)
{
    gl(e, MU_GL_OP_COLOR3F, fbits(r), fbits(g), fbits(b), 0);
}
static void gl_texcoord(const mu_meshdraw_env *e, float s, float t)
{
    gl(e, MU_GL_OP_TEXCOORD2F, fbits(s), fbits(t), 0, 0);
}
static void gl_vertex(const mu_meshdraw_env *e, const float *v)
{
    gl(e, MU_GL_OP_VERTEX3FV, fbits(v[0]), fbits(v[1]), fbits(v[2]), 0);
}

/* alpha >= 0.99 (comiss/jb: NaN is unordered and takes glColor4f). */
static int opaque(float alpha) { return alpha >= K_099; }

static void colour(const mu_meshdraw_env *e, const float *c, float alpha)
{
    if (opaque(alpha))
        gl_color3fv(e, c);
    else
        gl_color4f(e, c[0], c[1], c[2], alpha);
}

/* ---- state wrappers 0x0184a6b7.. ---- */

/* 0x0184a6b7 (depth test on) is not called by the mesh draw. */
static void w_depth_off(const mu_meshdraw_env *e)  /* 0x0184a6da */
{
    if (e->cache->depth_test) { e->cache->depth_test = 0; gl_disable(e, MU_GL_DEPTH_TEST); }
}
static void w_cull_on(const mu_meshdraw_env *e)    /* 0x0184a6fd */
{
    if (!e->cache->cull) { e->cache->cull = 1; gl_enable(e, MU_GL_CULL_FACE); }
}
static void w_cull_off(const mu_meshdraw_env *e)   /* 0x0184a720 */
{
    if (e->cache->cull) { e->cache->cull = 0; gl_disable(e, MU_GL_CULL_FACE); }
}
static void w_mask_on(const mu_meshdraw_env *e)    /* 0x0184a743 */
{
    if (!e->cache->depth_mask) { e->cache->depth_mask = 1; gl(e, MU_GL_OP_DEPTH_MASK, 1, 0, 0, 0); }
}
static void w_mask_off(const mu_meshdraw_env *e)   /* 0x0184a763 */
{
    if (e->cache->depth_mask) { e->cache->depth_mask = 0; gl(e, MU_GL_OP_DEPTH_MASK, 0, 0, 0, 0); }
}
static void alpha_test_off(const mu_meshdraw_env *e)
{
    if (e->cache->alpha_test) { e->cache->alpha_test = 0; gl_disable(e, MU_GL_ALPHA_TEST); }
}
static void alpha_test_on(const mu_meshdraw_env *e)
{
    if (!e->cache->alpha_test) { e->cache->alpha_test = 1; gl_enable(e, MU_GL_ALPHA_TEST); }
}
static void texture_on(const mu_meshdraw_env *e)
{
    if (!e->cache->texture) { e->cache->texture = 1; gl_enable(e, MU_GL_TEXTURE_2D); }
}
static void w_alpha_mode(const mu_meshdraw_env *e, uint8_t on) /* 0x0184a783: untextured */
{
    w_mask_on(e);
    if (on == 1)
        alpha_test_on(e);
    else
        alpha_test_off(e);
    if (e->cache->texture) { e->cache->texture = 0; gl_disable(e, MU_GL_TEXTURE_2D); }
}
static void fog_enable(const mu_meshdraw_env *e)
{
    if (e->cache->fog)
        gl_enable(e, MU_GL_FOG);
}
static void w_blend_off(const mu_meshdraw_env *e)  /* 0x0184a7f3 */
{
    if (e->cache->blend != 0) { e->cache->blend = 0; gl_disable(e, MU_GL_BLEND); }
    w_cull_on(e);
    w_mask_on(e);
    alpha_test_off(e);
    texture_on(e);
    fog_enable(e);
}
static void blend(const mu_meshdraw_env *e, int32_t id, uint32_t src, uint32_t dst)
{
    if (e->cache->blend != id) {
        e->cache->blend = id;
        gl_enable(e, MU_GL_BLEND);
        gl(e, MU_GL_OP_BLEND_FUNC, src, dst, 0, 0);
    }
}
static void w_zero_src_color(const mu_meshdraw_env *e)  /* 0x0184a872 */
{
    blend(e, 1, MU_GL_ZERO, MU_GL_SRC_COLOR);
    w_cull_on(e); w_mask_on(e); alpha_test_off(e); texture_on(e); fog_enable(e);
}
static void w_zero_src_alpha(const mu_meshdraw_env *e)  /* 0x0184a901 */
{
    blend(e, 8, MU_GL_ZERO, MU_GL_SRC_ALPHA);
    w_cull_on(e); w_mask_on(e); alpha_test_off(e); texture_on(e); fog_enable(e);
}
static void w_alpha(const mu_meshdraw_env *e, uint8_t mask)  /* 0x0184a990 */
{
    blend(e, 2, MU_GL_SRC_ALPHA, MU_GL_ONE_MINUS_SRC_ALPHA);
    w_cull_off(e);
    if (mask)
        w_mask_on(e);
    alpha_test_on(e);
    texture_on(e);
    fog_enable(e);
}
static void w_one_one(const mu_meshdraw_env *e)  /* 0x0184aa2b */
{
    blend(e, 3, MU_GL_ONE, MU_GL_ONE);
    w_cull_off(e); w_mask_off(e); alpha_test_off(e); texture_on(e);
    if (e->cache->fog)
        gl_disable(e, MU_GL_FOG);
}
static void w_zero_one_minus_src_color(const mu_meshdraw_env *e)  /* 0x0184aab7 */
{
    blend(e, 4, MU_GL_ZERO, MU_GL_ONE_MINUS_SRC_COLOR);
    w_cull_off(e); w_mask_off(e); alpha_test_off(e); texture_on(e); fog_enable(e);
}
static void w_bind(const mu_meshdraw_env *e, int32_t index)  /* 0x0184acf6 */
{
    if (e->cache->bound == index)
        return;
    e->cache->bound = index;
    uint32_t name;
    if (index >= 0) {
        const mu_bitmap *b = e->bitmap(e->bitmap_context, index);
        name = b ? b->name : 0;
    } else {
        name = (uint32_t)(-index);
    }
    gl(e, MU_GL_OP_BIND_TEXTURE, MU_GL_TEXTURE_2D, name, 0, 0);
}

void mu_gl_cache_scene_defaults(mu_gl_cache *c)
{
    memset(c, 0, sizeof *c);
    c->depth_test = c->cull = c->depth_mask = c->texture = 1;
    c->alpha_test = 0;
    c->blend = 0;
    c->bound = -0x7fffffff;  /* nothing bound yet */
}

/* ---- index check (authored convention) ---- */

static int mesh_valid(const mu_meshdraw_mesh *m)
{
    if (m->normal_count > MU_MESHDRAW_MAX_ENTRIES)
        return 0;
    for (int32_t t = 0; t < m->triangle_count; ++t) {
        const uint8_t *tri = m->triangles + 0x24 * t;
        const int n = (int8_t)tri[0];
        if (n > 4)
            return 0;
        for (int j = 0; j < n || j < 3; ++j) {
            if (j >= 4)
                break;
            int32_t v = s16(tri + 2 + 2 * j), nn = s16(tri + 0xa + 2 * j), tt = s16(tri + 0x12 + 2 * j);
            if (v < 0 || v >= m->vertex_count)
                return 0;  /* corners 0..2 are also read by the 0x200000 cull */
            if (j < n && (nn < 0 || nn >= m->normal_count || tt < 0 || tt >= m->texcoord_count))
                return 0;
        }
    }
    return 1;
}

/* ---- mesh draw 0x012b8d1d ---- */

int mu_meshdraw_mesh_draw(const mu_meshdraw_env *e, int32_t i, const mu_meshdraw_args *a, long *corners)
{
    mu_meshdraw_model *M = e->model;
    uint32_t flags = a->flags;
    float alpha = a->alpha;  /* [ebp+0x1c], rewritten by mode 0x8000 */
    const float uoff = a->u_offset, voff = a->v_offset;
    if (corners)
        *corners = 0;

    /* 0x012b8d3f: 0 <= i < mesh_count */
    if (!(i < M->mesh_count) || !(i >= 0))
        return MU_MESHDRAW_RETURNED;
    const mu_meshdraw_mesh *mesh = &M->meshes[i];
    if (mesh->texture_slot < 0 || mesh->texture_slot >= M->texture_count || !mesh_valid(mesh))
        return MU_MESHDRAW_REFUSED;

    /* 0x012b8d56: pre-loop colour when lighting is off */
    if (M->lighting == 0)
        colour(e, M->color, alpha);
    /* 0x012b8dea: no triangles */
    if (mesh->triangle_count == 0)
        return MU_MESHDRAW_RETURNED;

    const float t6c = remainder_float(e->globals->time, 10000) * K_0001;  /* 0x012b8dfa */
    float saved[3] = {M->color[0], M->color[1], M->color[2]};            /* [ebp-0x44] */
    float saved_type[3] = {0, 0, 0};                                      /* [ebp-0x12c] */
    const int16_t slot = mesh->texture_slot;
    int32_t texture = M->texture_index[slot];                             /* [ebp-0x1c] */

    /* 0x012b8e78..0x012b946c: texture substitutions */
    switch (texture) {
    case 0x791a:
        return MU_MESHDRAW_RETURNED;
    case 0x7725: case 0x77c7: case 0x7818: case 0x7869: case 0x7776: case 0x78ba:
        if (M->flag_a5)
            return MU_MESHDRAW_RETURNED;
        texture = texture + M->skin_shift;
        if (M->alt_on_skin) {
            memcpy(saved, M->color, sizeof saved);
            memcpy(M->color, M->alt_color, sizeof M->color);
        }
        break;
    case 0x76f8:
        texture = e->globals->skin_base + 0x76f8;
        break;
    case 0x791c:
        if (M->flag_a5)
            return MU_MESHDRAW_RETURNED;
        break;
    default:
        break;
    }
    if (a->texture != -1 && !(flags & 0x8000))                            /* 0x012b9471 */
        texture = a->texture;
    if (M->flag_a6 && M->flag_a5)                                         /* 0x012b9487 */
        texture++;
    const int32_t type = M->texture_type[slot];                           /* 0x012b94aa */
    if (type == 1) {
        if (M->flag_a5 || M->hide_typed > 0)
            return MU_MESHDRAW_RETURNED;
        memcpy(saved_type, M->color, sizeof saved_type);
        memcpy(M->color, M->alt_color, sizeof M->color);
    } else if (type == 2) {
        if (M->hide_typed > 0)
            return MU_MESHDRAW_RETURNED;
    }
    if (texture == -1)                                                    /* 0x012b95bf */
        return MU_MESHDRAW_RETURNED;
    const mu_bitmap *bitmap = e->bitmap(e->bitmap_context, texture);      /* 0x012b95ca */
    const int8_t components = bitmap ? bitmap->components : 0;

    /* 0x012b95da: uv offset selector */
    uint8_t uvflag = 0;
    int32_t select2 = M->light_mesh;
    if (mesh->sub && mesh->sub[2])
        select2 = i;
    if ((i == a->select || i == select2) && (uoff != K_0 || voff != K_0))  /* NaN counts as nonzero */
        uvflag = 1;

    /* 0x012b964d: light byte and the per-normal colour pass */
    uint8_t light = M->lighting;
    float *T = e->scratch->light_colors;
    int32_t light_count = 0;
    if (i == M->light_mesh) {
        gl_color3fv(e, M->color);
        light = 0;
    } else if (light) {
        for (int32_t n = 0; n < mesh->normal_count; ++n) {
            if (M->secondary_light == 1) {
                const float s = mesh->secondary[n];
                const float p0 = s * M->color[0], p1 = s * M->color[1], p2 = s * M->color[2];
                T[3 * n] = p0 + K_02;
                T[3 * n + 1] = p1 + K_02;
                T[3 * n + 2] = p2 + K_02;
            } else {
                const float l = mesh->lights[n];
                T[3 * n] = l * M->color[0];
                T[3 * n + 1] = l * M->color[1];
                T[3 * n + 2] = l * M->color[2];
            }
        }
        light_count = mesh->normal_count;
    }

    /* 0x012b9971: draw mode and state */
    int32_t mode = (int32_t)flags;
    float *E = e->scratch->normal_texcoords;
    int32_t table_count = 0;
    if (flags & 1) {
        mode = 1;
        if (flags & 0x40)
            w_one_one(e);
        else if (flags & 0x80)
            w_zero_one_minus_src_color(e);
        else
            w_blend_off(e);
        if (flags & 0x2000)
            w_depth_off(e);
        w_alpha_mode(e, 0);
        if (opaque(alpha)) {
            gl_color3fv(e, M->color);
        } else {
            w_alpha(e, 1);
            gl_color4f(e, M->color[0], M->color[1], M->color[2], alpha);
        }
    } else if (flags & (4u | 0x200u | 0x800u | 0x1000u | 0x4000u | 0x10000u | 0x20000u | 0x80000u | 0x100000u | 8u |
                        0x8000u)) {
        /* 0x012b9abf: environment group */
        if (mesh->sub && mesh->sub[3])
            return MU_MESHDRAW_RETURNED;
        if (mesh->flag != 0)
            return MU_MESHDRAW_RETURNED;
        if (texture >= 0x7724 && texture <= 0x7909)
            return MU_MESHDRAW_RETURNED;
        mode = 4;
        if (flags & 0x1000) mode = 0x1000;
        if (flags & 0x80000) mode = 0x80000;
        if (flags & 0x8000) mode = 0x8000;
        const float time = e->globals->time;
        const float t48 = remainder_float(time, 4000) * K_00025 - K_04;   /* 0x012b9b3f */
        const float rot[3] = {client_cos(time * K_0001T), client_sin(time * K_0002T), K_1};  /* -0x5c, -0x58, -0x54 */
        const float *D = e->globals->env_vector;
        /* 0x012b9bb3: the normal-indexed texcoord table 0x072acfd8 */
        for (int32_t n = 0; n < mesh->normal_count && n <= MU_MESHDRAW_MAX_ENTRIES; ++n) {
            const float *nv = mesh->normals + 3 * n;
            float *u = E + 2 * n, *v = E + 2 * n + 1;
            if (flags & 0x200) {
                *u = (nv[2] + nv[0]) * K_08 + t48 * K_2;
                *v = (nv[1] + nv[0]) * K_1 + t48 * K_3;
            } else if (flags & 0x800) {
                float d = nv[0] * D[0];
                d = d + nv[1] * D[1];
                d = d + nv[2] * D[2];
                *u = d;
                float d2 = nv[0] * D[0];
                d2 = d2 + nv[1] * D[1];
                d2 = d2 + nv[2] * D[2];
                *v = K_1 - d2;
            } else if (flags & 0x1000 || flags & 0x4000) {
                const int chrome5 = !(flags & 0x1000);
                float d = nv[0] * rot[0] + nv[1] * rot[1];
                d = d + nv[2] * rot[2];
                *u = d;
                float d2 = nv[0] * rot[0] + nv[1] * rot[1];
                d2 = d2 + nv[2] * rot[2];
                *v = K_1 - d2;
                if (!chrome5) {
                    *v = *v - (nv[2] * K_05 + t6c * K_3);
                    *u = (nv[1] * K_05 + rot[1] * K_3) + *u;
                } else {
                    *v = *v - (nv[2] * K_25 + t6c * K_1);
                    *u = (nv[1] * K_3 + rot[1] * K_5) + *u;
                }
            } else if (flags & 0x10000) {
                *u = (nv[2] + nv[0]) * K_08 + t48 * K_2;
                *v = (nv[2] + nv[0]) * K_08 + t48 * K_2;
            } else if (flags & 0x20000) {
                *u = (nv[2] + nv[0]) * K_08 + time * K_6E5;
                *v = (nv[2] + nv[0]) * K_08 + time * K_6E5;
            } else if (flags & 0x100000) {
                *u = (nv[2] + nv[0]) * K_08 + t48 * K_2;
                *v = (nv[1] + nv[0]) * K_1 + t48 * K_3;
            } else if (flags & 0x80000) {
                memcpy(u, &nv[0], 4);
                memcpy(v, &nv[1], 4);
            } else if (flags & 4) {
                *u = nv[2] * K_05 + t6c;
                *v = nv[1] * K_05 + t6c * K_2;
            } else {
                *u = nv[2] * K_05 + K_02;
                *v = nv[1] * K_05 + K_05;
            }
            table_count = n + 1;
        }
        /* 0x012ba3ef: state */
        if (flags & (0x800u | 0x1000u | 0x4000u | 0x20000u | 0x80000u) || flags & 0x40) {
            if (K_099 > alpha)  /* comiss 0.99, alpha; jbe: NaN skips */
                for (int k = 0; k < 3; ++k)
                    M->color[k] = M->color[k] * alpha;
            w_one_one(e);
        } else if (flags & 0x80) {
            w_zero_one_minus_src_color(e);
        } else if (flags & 0x10) {
            w_zero_src_color(e);
        } else if (opaque(alpha)) {
            w_blend_off(e);
        } else {
            w_alpha(e, 1);
        }
        if (flags & 0x2000)
            w_depth_off(e);
        /* 0x012ba5c0: texture */
        const int none = a->texture == -1;
        if ((flags & 0x200) && none) w_bind(e, 0x7fcf);
        else if ((flags & 0x800) && none) w_bind(e, 0x7fcf);
        else if ((flags & 0x1000) && none) w_bind(e, 0x7fcf);
        else if ((flags & 0x80000) && none) w_bind(e, 0x800b);
        else if ((flags & 0x100000) && none) w_bind(e, 0x800c);
        else if ((flags & 0x10000) && none) w_bind(e, 0x8005);
        else if ((flags & 4) && none) w_bind(e, 0x7f1f);
        else if ((flags & 8) && none) w_bind(e, 0x7f66);
        else w_bind(e, texture);
    } else if (a->select <= -2 || mesh->texture_slot == a->select) {
        /* 0x012ba6d1: highlight pass */
        mode = 2;
        w_bind(e, texture);
        if (flags & 0x80)
            w_zero_one_minus_src_color(e);
        else
            w_one_one(e);
        if (flags & 0x2000)
            w_depth_off(e);
        const float s = a->color_scale;
        gl_color3f(e, M->color[0] * s, M->color[1] * s, M->color[2] * s);
        light = 0;
    } else if (flags & 2) {
        /* 0x012ba778: textured */
        mode = 2;
        w_bind(e, texture);
        if (flags & 0x40)
            w_one_one(e);
        else if (flags & 0x80)
            w_zero_one_minus_src_color(e);
        else if (flags & 0x400000) {
            if (components == 4)
                w_zero_src_alpha(e);
            else
                w_zero_src_color(e);
        } else if (K_099 > alpha || components == 4) {
            w_alpha(e, 1);
        } else {
            w_blend_off(e);
        }
        if (flags & 0x2000)
            w_depth_off(e);
    } else if (flags & 0x40) {
        /* 0x012ba812: untextured additive */
        if (components == 4 || mesh->texture_slot == a->select)
            return MU_MESHDRAW_RETURNED;
        mode = 0x40;
        w_one_one(e);
        w_alpha_mode(e, 0);
        w_mask_off(e);
        if (flags & 0x2000)
            w_depth_off(e);
    } else {
        mode = 2;  /* 0x012ba866: no state, no bind */
    }
    if ((flags & 0x40000) && components != 4) {                           /* 0x012ba86d */
        w_cull_on(e);
        w_mask_on(e);
    }
    if (e->scratch->tables)
        e->scratch->tables(e->scratch->context, i, light_count, T, table_count, E);

    /* 0x012ba891: glBegin(GL_TRIANGLES) and the corner loop */
    gl(e, MU_GL_OP_BEGIN, MU_GL_TRIANGLES, 0, 0, 0);
    long visited = 0;
    for (int32_t t = 0; t < mesh->triangle_count; ++t) {
        const uint8_t *tri = mesh->triangles + 0x24 * t;
        const int n = (int8_t)tri[0];
        for (int j = 0; j < n; ++j) {
            const int32_t vi = s16(tri + 2 + 2 * j), ni = s16(tri + 0xa + 2 * j), ti = s16(tri + 0x12 + 2 * j);
            visited++;
            switch (mode) {
            case 2: {
                const float *uv = mesh->texcoords + 2 * ti;
                if (uvflag)
                    gl_texcoord(e, uv[0] + uoff, uv[1] + voff);
                else
                    gl_texcoord(e, uv[0], uv[1]);
                if (light)
                    colour(e, T + 3 * ni, alpha);
                break;
            }
            case 4:
                colour(e, M->color, alpha);
                gl_texcoord(e, E[2 * ni], E[2 * ni + 1]);
                break;
            case 0x1000: case 0x80000:
                colour(e, M->color, alpha);
                gl_texcoord(e, E[2 * ni] + uoff, E[2 * ni + 1] + voff);
                break;
            case 0x8000: {
                /* 0x012bacf4: alpha from one texel of the override bitmap */
                const float *uv = mesh->texcoords + 2 * ti;
                const mu_bitmap *b = e->bitmap(e->bitmap_context, a->texture);
                if (!b)
                    break;
                float x = uv[0] * b->width;
                float y = uv[1] * b->height;
                y = y * (b->width - K_1);
                x = (x + y) * K_3;
                const int32_t at = cvtt(x);
                const uint8_t texel = (at >= 0 && (uint32_t)at < b->pixel_bytes) ? b->pixels[at] : 0;
                const float f = (float)texel / K_256;
                alpha = K_1 - (float)pow((double)f, (double)K_2);
                const float su = uv[0] + uoff, sv = uv[1] + voff;
                for (int k = 0; k < 3; ++k)
                    M->color[k] = M->color[k] * alpha;
                colour(e, M->color, alpha);
                gl_texcoord(e, su, sv);
                memcpy(M->color, saved, sizeof saved);
                break;
            }
            default:
                break;
            }
            const float *V = mesh->vertices + 3 * vi;
            if (flags & 0x20) {
                /* 0x012baee0: planar projection about the origin */
                float L0 = V[0] - M->origin[0], L1 = V[1] - M->origin[1], L2 = V[2] - M->origin[2];
                float q = (L0 + K_2000) * L2;
                q = q / (L2 - K_4000);
                L0 = q + L0;
                L2 = K_5;
                const float out[3] = {L0 + M->origin[0], L1 + M->origin[1], L2 + M->origin[2]};
                gl_vertex(e, out);
            } else if (flags & 0x400) {
                /* 0x012bb09f: wave along the normal */
                const int32_t base = cvtt(e->globals->time);
                const float w = client_sin((float)(int32_t)((uint32_t)base + (uint32_t)vi * 0x3a3u) * K_0007);
                const float *nn = mesh->normals + 3 * ni;
                float out[3];
                for (int k = 0; k < 3; ++k)
                    out[k] = nn[k] * w * K_28 + V[k];
                gl_vertex(e, out);
            } else if (flags & 0x200000) {
                /* 0x012bb18b: skip when voff > z of corners 0..2 */
                const float z0 = mesh->vertices[3 * s16(tri + 2) + 2];
                const float z1 = mesh->vertices[3 * s16(tri + 4) + 2];
                const float z2 = mesh->vertices[3 * s16(tri + 6) + 2];
                if (voff > z0 && voff > z1 && voff > z2)
                    continue;
                gl_vertex(e, V);
            } else {
                gl_vertex(e, V);
            }
        }
    }
    gl(e, MU_GL_OP_END, 0, 0, 0, 0);

    /* 0x012bb235: colour restores */
    if (type == 1)
        memcpy(M->color, saved_type, sizeof saved_type);
    const int32_t raw = M->texture_index[slot];
    if (raw == 0x7725 || raw == 0x77c7 || raw == 0x7818 || raw == 0x7869)
        memcpy(M->color, saved, sizeof saved);
    if (corners)
        *corners = visited;
    return MU_MESHDRAW_DRAWN;
}

/* ---- body 0x012bb35a ---- */

static void count(mu_meshdraw_counts *c, int status, long corners)
{
    if (!c)
        return;
    if (status == MU_MESHDRAW_DRAWN) c->drawn++;
    else if (status == MU_MESHDRAW_RETURNED) c->returned++;
    else c->refused++;
    c->corners += corners;
}

void mu_meshdraw_body(const mu_meshdraw_env *e, const mu_meshdraw_args *args, int32_t skip, mu_meshdraw_counts *c)
{
    const mu_meshdraw_model *M = e->model;
    if (M->mesh_count == 0)
        return;
    gl(e, MU_GL_OP_PUSH_MATRIX, 0, 0, 0, 0);  /* 0x012b7e53 */
    for (int32_t i = 0; i < M->mesh_count; ++i) {
        mu_meshdraw_args call = *args;
        const mu_meshdraw_mesh *mesh = &M->meshes[i];
        long corners = 0;
        if (mesh->sub) {
            if (mesh->sub[1] != 0 || i == skip)
                continue;
            if (mesh->sub[0])
                call.select = i;
            count(c, mu_meshdraw_mesh_draw(e, i, &call, &corners), corners);
            const uint8_t pass = mesh->sub[4];
            if (pass == 1 || pass == 2) {
                w_blend_off(e);
                if (opaque(args->alpha))
                    gl_color3f(e, 0, 0, 0);
                else
                    gl_color4f(e, 0, 0, 0, args->alpha);
                mu_meshdraw_args outline = call;
                outline.flags = pass == 1 ? 0x21 : 0x22;
                outline.texture = -1;
                count(c, mu_meshdraw_mesh_draw(e, i, &outline, &corners), corners);
                gl_color3f(e, K_1, K_1, K_1);
            }
        } else if (i != skip) {
            count(c, mu_meshdraw_mesh_draw(e, i, &call, &corners), corners);
        }
    }
    gl(e, MU_GL_OP_POP_MATRIX, 0, 0, 0, 0);   /* 0x012b7e65 */
}

/* ---- effective state for non-GL backends ---- */

void mu_meshdraw_state_defaults(mu_meshdraw_state *s)
{
    memset(s, 0, sizeof *s);
    s->depth_test = s->depth_mask = s->cull = s->texture = 1;
    s->src = MU_GL_ONE;
    s->dst = MU_GL_ZERO;
}

int mu_meshdraw_state_apply(mu_meshdraw_state *s, uint32_t op, const uint32_t w[4])
{
    switch (op) {
    case MU_GL_OP_ENABLE:
    case MU_GL_OP_DISABLE: {
        const uint8_t on = op == MU_GL_OP_ENABLE;
        switch (w[0]) {
        case MU_GL_BLEND: s->blend = on; break;
        case MU_GL_DEPTH_TEST: s->depth_test = on; break;
        case MU_GL_CULL_FACE: s->cull = on; break;
        case MU_GL_ALPHA_TEST: s->alpha_test = on; break;
        case MU_GL_TEXTURE_2D: s->texture = on; break;
        case MU_GL_FOG: s->fog = on; break;
        default: break;
        }
        return 1;
    }
    case MU_GL_OP_BLEND_FUNC: s->src = w[0]; s->dst = w[1]; return 1;
    case MU_GL_OP_DEPTH_MASK: s->depth_mask = w[0] != 0; return 1;
    case MU_GL_OP_BIND_TEXTURE: s->texture_name = w[1]; return 1;
    default: return 0;
    }
}
