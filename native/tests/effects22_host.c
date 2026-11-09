/* RENDER-EFFECTS-022: native argument 8, retained owner points and stale-owner handling, no assets. */
#include "mu_particles.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    mu_world_particles *p = calloc(1, sizeof *p);
    char error[128];
    assert(p && !mu_world_particles_open(p, "", NULL, 0, 1, 1, error, sizeof error));
    const float at[3] = {10, 20, 30}, zero[3] = {0, 0, 0}, light[3] = {1, 0.5f, 0.2f};
    const int32_t owner = mu_world_particles_item_owner(p, 1, at);
    for (int i = 0; i < 9; ++i) assert(mu_world_particles_item_point(p, owner, i, (float)(i * 10)));
    assert(!mu_world_particles_item_point(p, owner, -1, 1));
    assert(!mu_world_particles_item_point(p, owner, 9, 1));
    assert(!mu_world_particles_item_point(p, -1, 0, 1));
    for (int k = 0; k < 3; ++k) {
        assert(mu_world_particles_create_args(p, 0x810a, at, zero, light, 0x25, 0.6f, owner, k));
        assert(p->list.records[k].arg8 == k && p->list.records[k].owner == owner);
    }
    assert(mu_world_particles_create(p, 0x855d, at, zero, light, 1, 0.5f));
    assert(mu_world_particles_create(p, 0x84d1, at, zero, light, 1, 0.5f));
    assert(p->list.records[3].lifetime == 20 && p->list.records[3].moving);
    assert(p->list.records[4].lifetime == 50 && p->list.records[4].alpha == 0);
    assert(mu_world_particles_bitmap_slot(0x855d) >= 0 && mu_world_particles_bitmap_slot(0x84d1) >= 0);
    assert(mu_world_particles_bitmap_slot(MU_PT_BITMAP_RAIN_RING) == MU_WORLD_PT_BITMAPS - 1);
    const float view[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    mu_world_particles_target target = {0};
    mu_world_particles_draw(p, view, &target);
    for (int i = 0; i < 3; ++i)
        for (int k = 0; k < 3; ++k)
            assert(p->list.records[i].position[k] == at[k] + (float)((3*i+k)*10));
    /* Update only one anchor word, with no logic step. Render uses the current value, not the birth point. */
    assert(mu_world_particles_item_point(p, owner, 6, 900));
    mu_world_particles_draw(p, view, &target);
    assert(p->list.records[2].position[0] == 910);
    /* Generation reuse must never borrow another item's points. */
    p->stats.steps += MU_WORLD_ITEM_OWNER_HOLD + 1;
    const int32_t replacement = mu_world_particles_item_owner(p, 2, at);
    assert(replacement != owner && !mu_world_particles_item_point(p, owner, 0, 99));
    mu_world_particles_draw(p, view, &target);
    assert(!p->list.records[0].live && !p->list.records[1].live && !p->list.records[2].live);
    assert(p->item_owners[0].points[0][0] == 0);
    mu_world_particles_close(p);
    free(p);
    puts("mace argument, points and generations OK");
    return 0;
}
