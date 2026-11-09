/* RENDER-EFFECTS-023: native bitmap routing and item point generations. Synthetic inputs only. */
#include "mu_particles.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static const int32_t bitmap[] = {0x7f7a,0x80ba,0x85bc,0x85fc,0x8315,0x8316,0x8317,0x7ffb,
                                 0x8549,0x82f2,0x810b,0x807e,0x807f,0x8080};
static const int32_t kinds[][2] = {{0x85bc,5},{0x83b8,8},{0x85fc,1},{0x8315,4},{0x8316,4},{0x8317,4},
                                  {0x7ffb,0},{0x83b3,19},{0x8109,14},{0x8549,1},{0x82f2,26},{0x810b,10},
                                  {0x85fc,2},{0x807e,24},{0x807f,24},{0x8080,24},{0x8081,9},{0x8082,9},{0x8083,9}};
int main(int argc, char **argv)
{
    mu_world_particles *p = calloc(1, sizeof *p);
    char error[128];
    assert(p && !mu_world_particles_open(p, argc > 1 ? argv[1] : "", NULL, 0, 1, argc < 2, error, sizeof error));
    for (int i = 0; i < 14; ++i) {
        int slot = mu_world_particles_bitmap_slot(bitmap[i]);
        assert(slot >= 0 && p->bitmaps.filter[slot] == 0x2601);
        assert(p->bitmaps.wrap[slot] == (i >= 11 ? 0x2901 : 0x2900));
        if (argc > 1) {
            assert(p->bitmap_present[slot]);
            const mu_image *image = &p->bitmaps.images[slot];
            assert(image->width == 32 && image->height == 32);
            /* Each fixture file has a unique flat grey. A wrong file mapping fails independently of the ID list. */
            assert(abs((int)image->rgba[0] - (12 + i * 16)) <= 2);
        }
    }
    assert(mu_world_particles_bitmap_slot(MU_PT_BITMAP_RAIN_RING) == MU_WORLD_PT_BITMAPS - 1);
    const float at[3] = {100,200,300}, zero[3] = {0,0,0}, light[3] = {1,0.5f,0.25f};
    const int32_t owner = mu_world_particles_item_owner(p, 1, at);
    for (int i = 0; i < 9; ++i) assert(mu_world_particles_item_point(p, owner, i, (float)(i * 10)));
    for (int i = 0; i < 19; ++i) {
        assert(mu_pt_kind_supported(kinds[i][0], kinds[i][1]));
        assert(mu_world_particles_create_args(p, kinds[i][0], at, zero, light, kinds[i][1], 0.5f, owner, i % 3));
    }
    const float view[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    mu_raster raster;
    assert(!mu_raster_init(&raster, 32, 32));
    mu_world_particles_draw_raster(p, &raster, view);
    if (argc > 1) assert(p->stats.drawn_particles == 19);
    for (int i = 0; i < 19; ++i) {
        if (kinds[i][0] != 0x85fc && kinds[i][0] != 0x7ffb) continue;
        for (int k = 0; k < 3; ++k) assert(p->list.records[i].position[k] == (float)((3 * (i % 3) + k) * 10));
    }
    assert(mu_world_particles_item_point(p, owner, 6, 900));
    mu_world_particles_draw_raster(p, &raster, view);
    assert(p->list.records[2].position[0] == 900); /* direct point, no birth-position offset */
    p->stats.steps += MU_WORLD_ITEM_OWNER_HOLD + 1;
    const int32_t replacement = mu_world_particles_item_owner(p, 2, at);
    assert(replacement != owner && !mu_world_particles_item_point(p, owner, 0, 999));
    mu_world_particles_draw_raster(p, &raster, view);
    for (int i = 0; i < 19; ++i)
        if (kinds[i][0] == 0x85fc || kinds[i][0] == 0x7ffb) assert(!p->list.records[i].live);
    assert(p->item_owners[0].points[0][0] == 0);
    mu_raster_free(&raster);
    mu_world_particles_close(p);
    free(p);
    printf("jpeg=%d\n", mu_image_have_jpeg());
    puts("mace consumers, bitmap files and point generations OK");
    return 0;
}
