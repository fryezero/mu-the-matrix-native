/* RENDER-EFFECTS-034: the new consumer pairs through the native pools: admission, bitmap routing, the item-owner
 * point of the follow pair, raster output and retirement. argv[1] = game root (fixture), argv[2] = image dir. */
#include "../core/mu_particles.c"
#include "../core/mu_png.h"
#include <assert.h>

static void raster_begin(mu_raster *raster, int size, float zoom)
{
    const float view[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    const uint8_t background[4] = {128,128,128,255};
    assert(!mu_raster_init(raster, size, size));
    mu_raster_clear(raster, background);
    memcpy(raster->view, view, sizeof view);
    memcpy(raster->projection, view, sizeof view);
    raster->projection[0] = raster->projection[5] = raster->projection[10] = zoom;
}

int main(int argc, char **argv)
{
    assert(argc >= 2);
    /* type, subtype, drawn bitmap, draws a sprite, follows an item-owner point */
    const int32_t kinds[][5] = {
        {0x8016,5,0x8016,1,0}, {0x7ef7,11,0x7ef7,1,0}, {0x7f5a,43,0x7ffd,1,0}, {0x7f5a,47,0x7f84,1,0},
        {0x7f54,1,0x7f54,1,0}, {0x7efa,3,0x7efa,0,0},
        {0x8616,0,0x8616,1,0}, {0x7fe0,10,0x7fe0,1,0}, {0x84d1,2,0x84d1,1,0}, {0x850b,5,0x850b,1,0},
        {0x807e,14,0x807e,1,0}, {0x807f,14,0x807f,1,0}, {0x8080,14,0x8080,1,0}, {0x855d,2,0x855d,1,1},
        {0x8081,1,0x8081,1,0}, {0x8082,1,0x8082,1,0}, {0x7ef7,19,0x7ef7,1,0}};
    const float zero[3] = {0}, light[3] = {1,1,1};
    const float view[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    char error[128], path[2048];
    for (unsigned k = 0; k < sizeof kinds / sizeof kinds[0]; ++k) {
        mu_world_particles *p = calloc(1, sizeof *p);
        assert(p && !mu_world_particles_open(p, argv[1], NULL, 0, 1, 0, error, sizeof error));
        const int32_t type = kinds[k][0], subtype = kinds[k][1];
        const int slot = mu_world_particles_bitmap_slot(kinds[k][2]);
        if (kinds[k][3]) assert(slot >= 0 && p->bitmap_present[slot]);
        int32_t owner = MU_PT_NO_OWNER;
        if (kinds[k][4]) {
            /* a NULL owner leaves a dead record; a retained item owner supplies the three points */
            assert(mu_world_particles_create(p, type, zero, zero, light, subtype, 1));
            assert(p->list.count == 1 && !p->list.records[0].live);
            mu_world_particles_step(p, 40);
            assert(!p->list.count);
            owner = mu_world_particles_item_owner(p, 1, zero);
            for (int i = 0; i < 9; ++i) assert(mu_world_particles_item_point(p, owner, i, (float)(i == 3 ? 0.25 : 0)));
        }
        const uint64_t created = p->list.created;
        assert(mu_world_particles_create_args(p, type, zero, zero, light, subtype, 1, owner, kinds[k][4] ? 1 : 0));
        assert(p->list.created == created + 1 && !p->list.unsupported && !p->refused_kind_count);
        mu_pt_particle *record = &p->list.records[0];
        assert(record->tex_type == kinds[k][2]);
        memcpy(record->position, zero, sizeof zero);   /* recentre for a camera-space raster control */
        memcpy(record->start, zero, sizeof zero);
        mu_world_particles_step(p, 40);
        assert(p->list.count == 1);
        memcpy(record->position, zero, sizeof zero);
        mu_raster raster;
        raster_begin(&raster, 64, 1.0f);
        mu_world_particles_draw_raster(p, &raster, view);
        if (kinds[k][4])   /* the draw moved the record to the owner's second point */
            assert(record->position[0] == 0.25f && record->position[1] == 0 && record->position[2] == 0);
        assert(p->stats.drawn_particles == (uint32_t)kinds[k][3]);   /* 0x7efa/3 sets its blend state only */
        assert(kinds[k][3] ? raster.fragments > 0 : raster.fragments == 0);
        if (argc > 2 && kinds[k][3]) {
            snprintf(path, sizeof path, "%s/%x-%d.png", argv[2], (unsigned)type, subtype);
            assert(!mu_png_write(path, raster.color, 64, 64));
        }
        printf("{\"kind\":%d,\"subtype\":%d,\"slot\":%d,\"fragments\":%ld,\"equal\":true}\n", type, subtype, slot,
               raster.fragments);
        for (int n = 0; n < 200; ++n) mu_world_particles_step(p, (float)(80 + 40 * n));
        assert(!p->list.count);
        mu_raster_free(&raster); mu_world_particles_close(p); free(p);
    }
    const int32_t joints[][2] = {{0x7f7c,8},{0x7f7c,19},{0x7fd5,4},{0x7f7d,11}};
    const float zooms[] = {0.02f, 0.0005f, 0.004f, 0.0008f};
    for (unsigned k = 0; k < sizeof joints / sizeof joints[0]; ++k) {
        mu_world_particles *p = calloc(1, sizeof *p);
        assert(p && !mu_world_particles_open(p, argv[1], NULL, 0, 1, 0, error, sizeof error));
        const float target[3] = {300, 200, 0};
        const int32_t index = mu_world_particles_joint(p, joints[k][0], zero, target, zero, joints[k][1], -1, 60,
                                                       0xffff, 0, 0, 0xffff, 0, NULL);
        assert(index >= 0 && p->stats.joints_created == 1 && !p->stats.joints_unsupported && !p->refused_kind_count);
        mu_world_particles_step(p, 40);
        if (joints[k][0] != 0x7f7c || joints[k][1] != 19) mu_world_particles_step(p, 80);
        mu_raster raster;
        raster_begin(&raster, 128, zooms[k]);
        mu_world_particles_draw_raster(p, &raster, view);
        fprintf(stderr, "joint %x/%d quads %u fragments %ld\n", (unsigned)joints[k][0], joints[k][1],
                p->stats.drawn_joint_quads, raster.fragments);
        assert(p->stats.drawn_joint_quads > 0 && raster.fragments > 0);
        if (argc > 2) {
            snprintf(path, sizeof path, "%s/j%x-%d.png", argv[2], (unsigned)joints[k][0], joints[k][1]);
            assert(!mu_png_write(path, raster.color, 128, 128));
        }
        printf("{\"joint\":true,\"kind\":%d,\"subtype\":%d,\"fragments\":%ld,\"equal\":true}\n", joints[k][0],
               joints[k][1], raster.fragments);
        for (int n = 0; n < 80; ++n) mu_world_particles_step(p, (float)(120 + 40 * n));
        assert(!mu_world_particles_live_joints(p));
        mu_raster_free(&raster); mu_world_particles_close(p); free(p);
    }
    const int32_t sprites[] = {0x810d, 0x8003, 0x8616, 0x850b};
    for (unsigned k = 0; k < sizeof sprites / sizeof sprites[0]; ++k) {
        mu_world_particles *p = calloc(1, sizeof *p);
        assert(p && !mu_world_particles_open(p, argv[1], NULL, 0, 1, 0, error, sizeof error));
        const int slot = mu_world_particles_bitmap_slot(sprites[k]);
        assert(slot >= 0 && p->bitmap_present[slot]);
        assert(p->bitmaps.filter[slot] == 0x2601 && p->bitmaps.wrap[slot] == 0x2900);
        assert(mu_world_particles_bitmap_slot(MU_PT_BITMAP_RAIN_RING) == MU_WORLD_PT_BITMAPS - 1);
        assert(mu_world_particles_sprite(p, sprites[k], zero, 1, light, -1, 0, 0, 4) >= 0);
        mu_raster raster;
        raster_begin(&raster, 64, 1.0f);
        mu_world_particles_draw_raster(p, &raster, view);
        assert(p->stats.drawn_sprites == 1 && raster.fragments > 0);
        if (argc > 2) {
            snprintf(path, sizeof path, "%s/s%x.png", argv[2], (unsigned)sprites[k]);
            assert(!mu_png_write(path, raster.color, 64, 64));
        }
        printf("{\"sprite\":true,\"kind\":%d,\"slot\":%d,\"grey\":%d,\"fragments\":%ld,\"equal\":true}\n", sprites[k], slot,
               (int)p->bitmaps.images[slot].rgba[0], raster.fragments);
        mu_raster_free(&raster); mu_world_particles_close(p); free(p);
    }
    {
        /* the refusal ledger: one row per refused pair, counted per request, in first-refusal order */
        mu_world_particles *p = calloc(1, sizeof *p);
        assert(p && !mu_world_particles_open(p, argv[1], NULL, 0, 1, 0, error, sizeof error));
        assert(!mu_world_particles_create(p, 0x7f5a, zero, zero, light, 9999, 1));
        assert(!mu_world_particles_create(p, 0x7f5a, zero, zero, light, 9999, 1));
        assert(mu_world_particles_joint(p, 0x7f7c, zero, zero, zero, 9999, -1, 60, 0xffff, 0, 0, 0xffff, 0, NULL) < 0);
        assert(!mu_world_particles_effect(p, 0x12345, 7, zero, zero, light, -1, 1, NULL));
        assert(mu_world_particles_create(p, 0x8016, zero, zero, light, 5, 1));
        const int equal = p->refused_kind_count == 3 && !p->refused_kinds_lost &&
            p->refused_kinds[0].routine == 'p' && p->refused_kinds[0].type == 0x7f5a &&
            p->refused_kinds[0].subtype == 9999 && p->refused_kinds[0].count == 2 &&
            p->refused_kinds[1].routine == 'j' && p->refused_kinds[1].type == 0x7f7c &&
            p->refused_kinds[1].subtype == 9999 && p->refused_kinds[1].count == 1 &&
            p->refused_kinds[2].routine == 'e' && p->refused_kinds[2].type == 0x12345 &&
            p->refused_kinds[2].subtype == 7 && p->refused_kinds[2].count == 1 &&
            p->stats.unsupported == 2 && p->stats.joints_unsupported == 1 && p->stats.effects_unsupported == 1;
        printf("{\"ledger\":true,\"rows\":%d,\"equal\":%s}\n", p->refused_kind_count, equal ? "true" : "false");
        mu_world_particles_close(p); free(p);
    }
    return 0;
}
