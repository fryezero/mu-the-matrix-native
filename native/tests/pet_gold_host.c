/* RENDER-EFFECTS-007: Rudolph's gold pieces 0x3fa (sub 0, no owner, key -1, scale 0, as the pet's visuals ask) in the
 * world particle module's effect pool: created, moved, drawn through the software rasterizer (orthographic, from
 * above). Prints a JSON line; writes a PPM when given a third argument. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../core/mu_particles.h"
#include "../core/mu_raster.h"

static mu_world_particles particles;

int main(int argc, char **argv)
{
    assert(argc >= 2);
    char error[256];
    assert(mu_world_particles_open(&particles, argv[1], NULL, 0, 0x1234u, 0, error, sizeof error) == 0);
    const float at[3] = {12000.0f, 12000.0f, 150.0f}, angle[3] = {0.0f, 0.0f, 0.0f}, light[3] = {1.0f, 1.0f, 1.0f};
    mu_sfx_info info;
    memset(&info, 0, sizeof info);
    info.key = 0xffff;
    int created = 0;
    for (int k = 0; k < 8; ++k)
        created += mu_world_particles_effect(&particles, 0x3fa, 0, at, angle, light, -1, 0.0f, &info);
    for (int s = 0; s < 6; ++s)
        mu_world_particles_step(&particles, 1000.0f + 40.0f * (float)s);
    const int32_t live = mu_world_particles_live_effects(&particles);
    mu_raster r;
    assert(mu_raster_init(&r, 200, 160) == 0);
    const uint8_t clear[4] = {0, 0, 0, 255};
    mu_raster_clear(&r, clear);
    memset(r.view, 0, sizeof r.view);
    r.view[0] = r.view[5] = r.view[10] = r.view[15] = 1.0f;
    r.view[12] = -at[0];
    r.view[13] = -at[1];
    r.view[14] = -at[2] - 1000.0f;
    memset(r.projection, 0, sizeof r.projection);
    r.projection[0] = 1.0f / 250.0f;
    r.projection[5] = 1.0f / 200.0f;
    r.projection[10] = -1.0f / 2000.0f;
    r.projection[15] = 1.0f;
    const int32_t drawn = mu_world_particles_draw_models_raster(&particles, &r);
    long lit = 0;
    for (int32_t i = 0; i < r.width * r.height; ++i)
        lit += r.color[4 * i] || r.color[4 * i + 1] || r.color[4 * i + 2];
    printf("{\"created\": %d, \"live\": %d, \"drawn\": %d, \"pixels\": %ld, \"unsupported\": %llu}\n", created, live,
           drawn, lit, (unsigned long long)particles.stats.effects_unsupported);
    if (argc > 2) {
        FILE *f = fopen(argv[2], "wb");
        assert(f);
        fprintf(f, "P6\n%d %d\n255\n", r.width, r.height);
        for (int32_t i = 0; i < r.width * r.height; ++i)
            fwrite(&r.color[4 * i], 1, 3, f);
        fclose(f);
    }
    mu_raster_free(&r);
    mu_world_particles_close(&particles);
    return 0;
}
