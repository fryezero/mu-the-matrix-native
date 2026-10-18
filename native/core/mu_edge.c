/* Client-memory corner view for out-of-range triangle indices. See mu_edge.h. */
#include "mu_edge.h"

#include <stdlib.h>
#include <string.h>

static int16_t s16(const uint8_t *p) { return (int16_t)(uint16_t)(p[0] | (p[1] << 8)); }

static void put16(uint8_t *p, int32_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)((uint32_t)value >> 8);
}

void mu_edge_view_free(mu_edge_view *view)
{
    if (!view)
        return;
    free(view->triangles);
    free(view->texcoords);
    free(view->vertices);
    free(view->normals);
    free(view->lights);
    free(view->secondary);
    memset(view, 0, sizeof *view);
}

/* Copy of count*width floats followed by extra zero entries. */
static float *extend(const float *source, int32_t count, int32_t extra, int width)
{
    size_t total = (size_t)(count + extra) * (size_t)width;
    float *out = calloc(total ? total : 1, sizeof *out);
    if (out && source && count > 0)
        memcpy(out, source, (size_t)count * (size_t)width * sizeof *out);
    return out;
}

/* Corner fields the port reads: a = 0 vertex (corners 0..max(n,3)-1, also read
 * by the 0x200000 cull), 1 normal and 2 texcoord (active corners 0..n-1). */
static int field_corners(int a, int corners)
{
    int n = corners < 0 ? 0 : corners > 4 ? 4 : corners;
    if (a == 0 && n < 3)
        n = 3;
    return n;
}

int mu_edge_mesh_view(const mu_meshdraw_mesh *in, mu_meshdraw_mesh *out, mu_edge_view *view)
{
    memset(view, 0, sizeof *view);
    *out = *in;
    int32_t extra[3] = {0, 0, 0};
    const int32_t counts[3] = {in->vertex_count, in->normal_count, in->texcoord_count};
    for (int32_t t = 0; t < in->triangle_count; ++t) {
        const uint8_t *tri = in->triangles + 0x24 * t;
        for (int a = 0; a < 3; ++a)
            for (int j = 0, n = field_corners(a, (int8_t)tri[0]); j < n; ++j) {
                int32_t index = s16(tri + 2 + 8 * a + 2 * j);
                if (index < 0 || index >= counts[a])
                    extra[a]++;
            }
    }
    if (!extra[0] && !extra[1] && !extra[2])
        return 0;
    const int32_t normals = counts[1] + extra[1];
    /* appended indices must fit the records' int16 fields */
    if (normals > MU_MESHDRAW_MAX_ENTRIES || counts[0] + extra[0] - 1 > INT16_MAX || counts[2] + extra[2] - 1 > INT16_MAX)
        return -1;
    size_t bytes = (size_t)(in->triangle_count > 0 ? in->triangle_count : 1) * 0x24;
    view->triangles = malloc(bytes);
    view->vertices = extend(in->vertices, counts[0], extra[0], 3);
    view->normals = extend(in->normals, in->normals ? counts[1] : 0, extra[1], 3);
    view->lights = extend(in->lights, in->lights ? counts[1] : 0, extra[1], 1);
    view->secondary = extend(in->secondary, in->secondary ? counts[1] : 0, extra[1], 1);
    view->texcoords = extend(in->texcoords, counts[2], extra[2], 2);
    if (!view->triangles || !view->vertices || !view->normals || !view->lights || !view->secondary ||
        !view->texcoords) {
        mu_edge_view_free(view);
        return -1;
    }
    memcpy(view->triangles, in->triangles, (size_t)in->triangle_count * 0x24);
    int32_t next[3] = {counts[0], counts[1], counts[2]};
    for (int32_t t = 0; t < in->triangle_count; ++t) {
        uint8_t *tri = view->triangles + 0x24 * t;
        for (int a = 0; a < 3; ++a)
            for (int j = 0, n = field_corners(a, (int8_t)tri[0]); j < n; ++j) {
                uint8_t *field = tri + 2 + 8 * a + 2 * j;
                int32_t index = s16(field);
                if (index < 0 || index >= counts[a]) {
                    put16(field, next[a]++);
                    view->redirected++;
                }
            }
    }
    view->normal_count = counts[1];
    view->extended_count = next[1];
    out->triangles = view->triangles;
    out->vertices = view->vertices;
    out->vertex_count = next[0];
    out->normals = view->normals;
    out->lights = view->lights;
    out->secondary = view->secondary;
    out->normal_count = (int16_t)next[1];
    out->texcoords = view->texcoords;
    out->texcoord_count = next[2];
    return 1;
}

void mu_edge_zero_tables(const mu_edge_view *view, float *light_colors, float *normal_texcoords)
{
    if (!view || view->extended_count <= view->normal_count)
        return;
    size_t extra = (size_t)(view->extended_count - view->normal_count);
    if (light_colors)
        memset(light_colors + 3 * (size_t)view->normal_count, 0, 3 * extra * sizeof *light_colors);
    if (normal_texcoords)
        memset(normal_texcoords + 2 * (size_t)view->normal_count, 0, 2 * extra * sizeof *normal_texcoords);
}
