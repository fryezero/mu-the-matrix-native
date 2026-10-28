#include "mu_perf_mesh.h"
#include <stdlib.h>
#include <string.h>

typedef struct topology {
    uint8_t *triangles;
    size_t bytes;
    int32_t vertices, normals, texcoords;
} topology;
struct mu_perf_mesh_cache {
    int32_t count;
    topology mesh[];
};

mu_perf_mesh_cache *mu_perf_mesh_new(int32_t meshes)
{
    if (meshes < 0 || meshes > 50) return NULL;
    mu_perf_mesh_cache *c = calloc(1, sizeof *c + (size_t)meshes * sizeof(topology));
    if (c) c->count = meshes;
    return c;
}

void mu_perf_mesh_free(mu_perf_mesh_cache *c)
{
    if (!c) return;
    for (int32_t i = 0; i < c->count; ++i) free(c->mesh[i].triangles);
    free(c);
}

int mu_perf_mesh_regular(mu_perf_mesh_cache *c, int32_t index, const mu_meshdraw_mesh *m)
{
    if (!c || index < 0 || index >= c->count || m->triangle_count <= 0) return 0;
    topology *t = &c->mesh[index];
    size_t bytes = (size_t)m->triangle_count * 0x24;
    if (t->triangles && t->bytes == bytes && t->vertices == m->vertex_count &&
        t->normals == m->normal_count && t->texcoords == m->texcoord_count &&
        memcmp(t->triangles, m->triangles, bytes) == 0) return 1;
    /* Invalid topology keeps the complete MODEL-EDGE path and is never marked
     * trusted, even if it matches a formerly valid snapshot. */
    if (!mu_meshdraw_mesh_valid(m)) return 0;
    uint8_t *copy = realloc(t->triangles, bytes);
    if (!copy) return 0;
    memcpy(copy, m->triangles, bytes);
    t->triangles = copy;
    t->bytes = bytes;
    t->vertices = m->vertex_count;
    t->normals = m->normal_count;
    t->texcoords = m->texcoord_count;
    return 1;
}
