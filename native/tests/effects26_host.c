/* RENDER-EFFECTS-026: bitmap mappings, real pool, owner points and raster. */
#include "../core/mu_particles.c"
#include "../core/mu_png.h"
#include <assert.h>

int main(int argc, char **argv)
{
    assert(argc >= 2);
    const int32_t kinds[5][2] = {{0x8500,2},{0x810b,8},{0x810a,12},{0x81cf,1},{0x8569,0}};
    const int grey[5] = {40,80,120,160,200};
    const float zero[3] = {0}, light[3] = {1,1,1};
    const float view[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    const uint8_t black[4] = {0,0,0,255};
    for (int k = 0; k < 5; ++k) {
        mu_world_particles *p = calloc(1, sizeof *p);
        char error[128], path[2048];
        assert(p && !mu_world_particles_open(p, argv[1], NULL, 0, 1, 0, error, sizeof error));
        const int slot = mu_world_particles_bitmap_slot(kinds[k][0]);
        assert(slot >= 0 && p->bitmap_present[slot]);
        assert(p->bitmaps.filter[slot] == 0x2601 && p->bitmaps.wrap[slot] == 0x2900);
        assert(abs((int)p->bitmaps.images[slot].rgba[0] - grey[k]) <= 2);
        const int32_t owner = mu_world_particles_item_owner(p, 1, zero);
        for (int n = 0; n < 9; ++n) assert(mu_world_particles_item_point(p, owner, n, 0));
        assert(mu_world_particles_create_args(p,kinds[k][0],zero,zero,light,kinds[k][1],1,owner,2));
        assert(p->list.created == 1 && p->list.unsupported == 0);
        mu_world_particles_step(p,40);
        assert(p->list.count == 1);
        mu_pt_particle *record = &p->list.records[0];
        const int32_t lifetime = record->lifetime;
        memcpy(record->position,zero,sizeof zero);
        mu_raster raster;
        assert(!mu_raster_init(&raster,64,64));
        mu_raster_clear(&raster,black);
        memcpy(raster.view,view,sizeof view); memcpy(raster.projection,view,sizeof view);
        if (argc > 2) {
            snprintf(path,sizeof path,"%s/%x-before.png",argv[2],(unsigned)kinds[k][0]);
            assert(!mu_png_write(path,raster.color,64,64));
        }
        mu_world_particles_draw_raster(p,&raster,view);
        assert(p->stats.drawn_particles == 1 && raster.fragments > 0);
        if (argc > 2) {
            snprintf(path,sizeof path,"%s/%x-after.png",argv[2],(unsigned)kinds[k][0]);
            assert(!mu_png_write(path,raster.color,64,64));
        }
        if (kinds[k][0] == 0x8569) {
            const float point[3] = {0.125f,-0.25f,0.5f};
            for (int n = 0; n < 3; ++n) assert(mu_world_particles_item_point(p,owner,6+n,point[n]));
            mu_world_particles_draw_raster(p,&raster,view);
            assert(!memcmp(record->position,point,sizeof point));
            assert(!mu_pt_item_later_follow(record,NULL) && !record->live);
        }
        printf("{\"kind\":%d,\"subtype\":%d,\"lifetime_after_step\":%d,\"fragments\":%ld}\n",
               kinds[k][0],kinds[k][1],lifetime,raster.fragments);
        for (int n = 0; n < 35; ++n) mu_world_particles_step(p,(uint32_t)(80+40*n));
        assert(!p->list.count);
        mu_raster_free(&raster); mu_world_particles_close(p); free(p);
    }
    return 0;
}
