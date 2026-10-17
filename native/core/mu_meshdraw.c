/* Platform-neutral port of the mesh draw per-corner loop and colour pass.
 * See mu_meshdraw.h and mac-play/hotpatch/meshdraw-notes.md. */
#include "mu_meshdraw.h"

#include <string.h>

/* Client binary32 constants used by the loop (meshdraw-notes.md):
 * 0x01a82fe0 = 0.99, 0x01a802d8 = 2000, 0x01a9ff0c = 4000, 0x01a7e4cc = 5,
 * 0x01a7df08 = 0.2 (colour pass). */
static const float k_2000 = 2000.0f, k_4000 = 4000.0f, k_5 = 5.0f, k_light_bias = 0.2f;

static int16_t s16(const uint8_t *p) { return (int16_t)(uint16_t)(p[0] | (p[1] << 8)); }

static void colour(const mu_meshdraw_sink *sink, const float *c, int col3, float alpha)
{
    if (col3)
        sink->color3(sink->context, c);
    else
        sink->color4(sink->context, c[0], c[1], c[2], alpha);
}

int mu_meshdraw_corners(const mu_meshdraw_mesh *mesh, const mu_meshdraw_params *params,
                        const mu_meshdraw_sink *sink, long *corners)
{
    long visited = 0;
    if (corners)
        *corners = 0;
    const int32_t mode = params->mode;
    const uint32_t flags = params->flags;
    if (mode == 0x8000 || (flags & 0x420) == 0x400)
        return MU_MESHDRAW_CLIENT_CALLS;
    int kind; /* 0 none, 1 mode 2, 2 mode 4, 3 environment with uv offset */
    switch (mode) {
    case 2: kind = 1; break;
    case 4: kind = 2; break;
    case 0x1000: case 0x80000: case 0x100000: kind = 3; break;
    default: kind = 0; break;
    }
    const int vertex_kind = (flags & 0x20) ? 1 : (flags & 0x200000) ? 3 : 0;
    const float alpha = params->alpha, uoff = params->u_offset, voff = params->v_offset;
    const int col3 = alpha >= MU_MESHDRAW_ALPHA_THRESHOLD;
    const int uvflag = params->apply_uv_offset != 0, light = params->light_colors != 0;

    /* Index validation first, so a refused mesh emits nothing. */
    for (int32_t t = 0; t < mesh->triangle_count; ++t) {
        const uint8_t *tri = mesh->triangles + 0x24 * t;
        const int n = (int8_t)tri[0];
        for (int j = 0; j < n; ++j) {
            if (j >= 4)
                return MU_MESHDRAW_BAD_INDEX;
            int32_t v = s16(tri + 2 + 2 * j), nn = s16(tri + 0xa + 2 * j), tt = s16(tri + 0x12 + 2 * j);
            if (v < 0 || v >= mesh->vertex_count)
                return MU_MESHDRAW_BAD_INDEX;
            if (kind == 1 && (tt < 0 || tt >= mesh->texcoord_count))
                return MU_MESHDRAW_BAD_INDEX;
            if ((kind == 2 || kind == 3 || (kind == 1 && light)) && (nn < 0 || nn >= mesh->normal_count))
                return MU_MESHDRAW_BAD_INDEX;
        }
        if (vertex_kind == 3 && n > 0)
            for (int j = 0; j < 3; ++j) {
                int32_t v = s16(tri + 2 + 2 * j);
                if (v < 0 || v >= mesh->vertex_count)
                    return MU_MESHDRAW_BAD_INDEX;
            }
    }

    for (int32_t t = 0; t < mesh->triangle_count; ++t) {
        const uint8_t *tri = mesh->triangles + 0x24 * t;
        const int n = (int8_t)tri[0];
        for (int j = 0; j < n; ++j) {
            const int32_t vi = s16(tri + 2 + 2 * j), ni = s16(tri + 0xa + 2 * j), ti = s16(tri + 0x12 + 2 * j);
            visited++;
            switch (kind) {
            case 1: {
                const float *uv = mesh->texcoords + 2 * ti;
                if (uvflag) {
                    const float s = uv[0] + uoff, tv = uv[1] + voff;
                    sink->texcoord(sink->context, s, tv);
                } else {
                    sink->texcoord(sink->context, uv[0], uv[1]);
                }
                if (light)
                    colour(sink, mesh->light_colors + 3 * ni, col3, alpha);
                break;
            }
            case 2: {
                colour(sink, mesh->model_color, col3, alpha);
                const float *e = mesh->normal_texcoords + 2 * ni;
                sink->texcoord(sink->context, e[0], e[1]);
                break;
            }
            case 3: {
                colour(sink, mesh->model_color, col3, alpha);
                const float *e = mesh->normal_texcoords + 2 * ni;
                const float s = e[0] + uoff, tv = e[1] + voff;
                sink->texcoord(sink->context, s, tv);
                break;
            }
            default:
                break;
            }
            const float *v = mesh->vertices + 3 * vi;
            if (vertex_kind == 1) {
                const float *origin = mesh->origin;
                volatile float l0, l1, l2, a, b;
                l0 = v[0] - origin[0];
                l1 = v[1] - origin[1];
                l2 = v[2] - origin[2];
                a = l0 + k_2000;
                a = a * l2;
                b = l2 - k_4000;
                a = a / b;
                l0 = a + l0;
                l2 = k_5;
                float out[3];
                out[0] = l0 + origin[0];
                out[1] = l1 + origin[1];
                out[2] = l2 + origin[2];
                sink->vertex(sink->context, out);
            } else if (vertex_kind == 3) {
                const float z0 = mesh->vertices[3 * s16(tri + 2) + 2];
                const float z1 = mesh->vertices[3 * s16(tri + 4) + 2];
                const float z2 = mesh->vertices[3 * s16(tri + 6) + 2];
                if (voff > z0 && voff > z1 && voff > z2)
                    continue;
                sink->vertex(sink->context, v);
            } else {
                sink->vertex(sink->context, v);
            }
        }
    }
    if (corners)
        *corners = visited;
    return MU_MESHDRAW_OK;
}

void mu_meshdraw_light_colors(const float *light, const float *secondary, int32_t count, const float color[3],
                              uint8_t secondary_select, float *out)
{
    const float c0 = color[0], c1 = color[1], c2 = color[2];
    if (secondary_select == 1) {
        for (int32_t n = 0; n < count; ++n) {
            const float s = secondary[n];
            volatile float p;
            p = s * c0; out[3 * n] = p + k_light_bias;
            p = s * c1; out[3 * n + 1] = p + k_light_bias;
            p = s * c2; out[3 * n + 2] = p + k_light_bias;
        }
    } else {
        for (int32_t n = 0; n < count; ++n) {
            const float l = light[n];
            out[3 * n] = l * c0;
            out[3 * n + 1] = l * c1;
            out[3 * n + 2] = l * c2;
        }
    }
}

int mu_meshdraw_pre_color(uint8_t lighting, const float color[3], float alpha, const mu_meshdraw_sink *sink)
{
    if (lighting)
        return 0;
    colour(sink, color, alpha >= MU_MESHDRAW_ALPHA_THRESHOLD, alpha);
    return 1;
}

void mu_meshdraw_state_for(uint32_t flags, float alpha, mu_meshdraw_state *s)
{
    memset(s, 0, sizeof *s);
    s->depth_test = (flags & 0x2000) == 0;
    s->depth_mask = 1;
    s->texture = 1;
    const int translucent = !(alpha >= MU_MESHDRAW_ALPHA_THRESHOLD);
    if (flags & 0x40) {
        s->blend = 1; s->src = MU_BLEND_ONE; s->dst = MU_BLEND_ONE;
    } else if (flags & 0x80) {
        s->blend = 1; s->src = MU_BLEND_ZERO; s->dst = MU_BLEND_ONE_MINUS_SRC_COLOR;
    } else if (!(flags & 1) && (flags & 0x10)) {
        s->blend = 1; s->src = MU_BLEND_ZERO; s->dst = MU_BLEND_SRC_COLOR;
    } else if (!(flags & 1) && (flags & 0x400000)) {
        s->blend = 1; s->src = MU_BLEND_ZERO; s->dst = MU_BLEND_SRC_ALPHA;
    } else if (translucent) {
        s->blend = 1; s->src = MU_BLEND_SRC_ALPHA; s->dst = MU_BLEND_ONE_MINUS_SRC_ALPHA;
    } else {
        /* Blend-off wrapper 0x0184a7f3: blend off, cull and depth mask on, alpha test off, texture on. */
        s->cull = !(flags & 1);
    }
    if (flags & 0x40000) {
        s->cull = 1;
        s->depth_mask = 1;
    }
}
