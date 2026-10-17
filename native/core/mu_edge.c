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
    free(view->light_colors);
    free(view->normal_texcoords);
    free(view->vertices);
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

int mu_edge_mesh_view(const mu_meshdraw_mesh *in, mu_meshdraw_mesh *out, mu_edge_view *view)
{
    memset(view, 0, sizeof *view);
    *out = *in;
    /* Count redirected fields per array: vertex, normal, texcoord. */
    int32_t extra[3] = {0, 0, 0};
    const int32_t counts[3] = {in->vertex_count, in->normal_count, in->texcoord_count};
    for (int32_t t = 0; t < in->triangle_count; ++t) {
        const uint8_t *tri = in->triangles + 0x24 * t;
        int corners = (int8_t)tri[0];
        corners = corners < 0 ? 0 : corners > 4 ? 4 : corners;
        for (int a = 0; a < 3; ++a)
            for (int j = 0; j < corners; ++j) {
                int32_t index = s16(tri + 2 + 8 * a + 2 * j);
                if (index < 0 || index >= counts[a])
                    extra[a]++;
            }
    }
    if (!extra[0] && !extra[1] && !extra[2])
        return 0;
    size_t bytes = (size_t)(in->triangle_count > 0 ? in->triangle_count : 1) * 0x24;
    view->triangles = malloc(bytes);
    view->vertices = extend(in->vertices, in->vertex_count, extra[0], 3);
    view->light_colors = extend(in->light_colors, in->light_colors ? in->normal_count : 0, extra[1], 3);
    view->normal_texcoords = extend(in->normal_texcoords, in->normal_texcoords ? in->normal_count : 0, extra[1], 2);
    view->texcoords = extend(in->texcoords, in->texcoord_count, extra[2], 2);
    if (!view->triangles || !view->vertices || !view->light_colors || !view->normal_texcoords || !view->texcoords) {
        mu_edge_view_free(view);
        return -1;
    }
    memcpy(view->triangles, in->triangles, (size_t)in->triangle_count * 0x24);
    int32_t next[3] = {counts[0], counts[1], counts[2]};
    for (int32_t t = 0; t < in->triangle_count; ++t) {
        uint8_t *tri = view->triangles + 0x24 * t;
        int corners = (int8_t)tri[0];
        corners = corners < 0 ? 0 : corners > 4 ? 4 : corners;
        for (int a = 0; a < 3; ++a)
            for (int j = 0; j < corners; ++j) {
                uint8_t *field = tri + 2 + 8 * a + 2 * j;
                int32_t index = s16(field);
                if (index < 0 || index >= counts[a]) {
                    put16(field, next[a]++);
                    view->redirected++;
                }
            }
    }
    out->triangles = view->triangles;
    out->vertices = view->vertices;
    out->vertex_count = next[0];
    out->light_colors = view->light_colors;
    out->normal_texcoords = view->normal_texcoords;
    out->normal_count = next[1];
    out->texcoords = view->texcoords;
    out->texcoord_count = next[2];
    return 1;
}
