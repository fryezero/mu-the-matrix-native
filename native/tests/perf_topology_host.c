#include "../core/mu_perf_mesh.h"
#include <stdlib.h>
#include <stdio.h>
int main(void)
{
    uint8_t tri[72] = {3, 0, 0, 0, 1, 0, 2};
    tri[18] = 0; tri[20] = 1; tri[22] = 2;
    mu_meshdraw_mesh m = {0};
    m.triangles = tri; m.triangle_count = 1;
    m.vertex_count = m.texcoord_count = 3; m.normal_count = 1;
    mu_perf_mesh_cache *c = mu_perf_mesh_new(1), *other = mu_perf_mesh_new(1);
#define CHECK(x) do { if (!(x)) return __LINE__; } while (0)
    CHECK(mu_perf_mesh_regular(c, 0, &m));
    CHECK(mu_perf_mesh_regular(c, 0, &m));
    tri[2] = 255; tri[3] = 255;
    CHECK(!mu_perf_mesh_regular(c, 0, &m));
    tri[2] = tri[3] = 0;
    CHECK(mu_perf_mesh_regular(c, 0, &m));
    m.vertex_count = 2;
    CHECK(!mu_perf_mesh_regular(c, 0, &m));
    m.vertex_count = 3; m.normal_count = 0;
    CHECK(!mu_perf_mesh_regular(c, 0, &m));
    m.normal_count = 1; m.texcoord_count = 2;
    CHECK(!mu_perf_mesh_regular(c, 0, &m));
    m.texcoord_count = 3; m.triangle_count = 2; tri[36] = 5;
    CHECK(!mu_perf_mesh_regular(c, 0, &m));
    m.triangle_count = 1;
    CHECK(mu_perf_mesh_regular(other, 0, &m));
    mu_perf_mesh_free(c);
    CHECK(mu_perf_mesh_regular(other, 0, &m));
    CHECK(!mu_perf_mesh_regular(other, 1, &m));
    CHECK(!mu_perf_mesh_regular(NULL, 0, &m));
    mu_perf_mesh_free(other);
    puts("12 topology and owner checks passed");
    return 0;
}
