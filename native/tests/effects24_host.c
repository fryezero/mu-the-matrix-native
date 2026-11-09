/* RENDER-EFFECTS-024: real native loader and pool, synthetic textures. */
#include "../core/mu_particles.c"
#include <assert.h>

int main(int argc, char **argv)
{
    mu_world_particles *p = calloc(1, sizeof *p);
    char error[128];
    assert(p && !mu_world_particles_open(p, argc > 1 ? argv[1] : "", NULL, 0, 1, argc < 2,
                                         error, sizeof error));
    const int32_t ids[2] = {0x81ec, 0x854a};
    printf("{\"bitmaps\":[");
    for (int k = 0; k < 2; ++k) {
        const int slot = mu_world_particles_bitmap_slot(ids[k]);
        printf("%s{\"id\":%d,\"slot\":%d,\"filter\":%d,\"wrap\":%d,\"loaded\":%d,\"pixel\":%d}",
               k ? "," : "", ids[k], slot, slot < 0 ? -1 : p->bitmaps.filter[slot],
               slot < 0 ? -1 : p->bitmaps.wrap[slot], slot < 0 ? 0 : p->bitmap_present[slot],
               slot < 0 || !p->bitmap_present[slot] ? -1 : p->bitmaps.images[slot].rgba[0]);
    }
    const float at[3] = {0,0,0}, angle[3] = {0,0,0}, light[3] = {1,0.5f,0.25f};
    for (int k = 0; k < 2; ++k)
        mu_world_particles_sprite(p, ids[k], at, 1, light, -1, 0, 0, 4);
    mu_raster raster;
    assert(!mu_raster_init(&raster, 32, 32));
    const float view[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    mu_world_particles_draw_raster(p, &raster, view);
    printf("],\"sprites\":%u", p->stats.drawn_sprites);
    /* Each selected child is admitted even when no asset is available. */
    int children = mu_pt_kind_supported(0x8084, 3) + mu_pt_kind_supported(0x806e, 4) +
                   mu_pt_kind_supported(0x8085, 0);
    assert(mu_world_particles_effect(p, 0x413, 10, at, angle, light, -1, 1, NULL));
    mu_world_particles_step(p, 40);
    printf(",\"children\":%d,\"created\":%llu,\"unsupported\":%llu,\"effect_live\":%d,\"rain_last\":%d}\n",
           children, (unsigned long long)p->list.created, (unsigned long long)p->list.unsupported,
           p->effects[0].live,
           mu_world_particles_bitmap_slot(MU_PT_BITMAP_RAIN_RING) == MU_WORLD_PT_BITMAPS - 1);
    mu_raster_free(&raster);
    mu_world_particles_close(p);
    free(p);
    return 0;
}
