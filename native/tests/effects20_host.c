/* RENDER-EFFECTS-020: the native routes of the item-owned particles (portable self-checks, no assets).
 *  - 0x810a/0x11 and 0x81cf/0 are admitted and have world particle slots;
 *  - an item OBJECT registered as owner gives an owner index; the particle's +0x54 follows the OBJECT's +0x158 each
 *    step (MoveParticles' common block) while its position stays where it was created;
 *  - 0x81cf/0 lives its 20 steps with an owner and ends at the first step without one (+0x50 NULL);
 *  - a slot is reused only after MU_WORLD_ITEM_OWNER_HOLD unrefreshed steps, with generation + 1; the old index then
 *    resolves to no OBJECT; with every slot held a new key gets -1. */
#include "mu_particles.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    assert(mu_pt_kind_supported(0x810a, 0x11) && mu_pt_kind_supported(0x81cf, 0));
    assert(!mu_pt_kind_supported(0x81cf, 2) && !mu_pt_kind_supported(0x810a, 0x10));
    assert(mu_world_particles_bitmap_slot(0x810a) >= 0 && mu_world_particles_bitmap_slot(0x81cf) >= 0);
    assert(mu_world_particles_bitmap_slot(MU_PT_BITMAP_RAIN_RING) == MU_WORLD_PT_BITMAPS - 1);
    mu_world_particles *p = calloc(1, sizeof *p);
    char error[128];
    if (!p || mu_world_particles_open(p, "", NULL, 0, 1, 1, error, sizeof error))
        return 1;
    const float at[3] = {12800.0f, 12900.0f, 150.0f}, moved[3] = {13000.0f, 12950.0f, 160.0f};
    const float angle[3] = {0.0f, 0.0f, 0.0f}, light[3] = {1.0f, 0.8f, 0.6f};
    const uint32_t key = (2u << 24) | 0x31u;   /* players: player 3, slot 1 */
    const int32_t owner = mu_world_particles_item_owner(p, key, at);
    assert(owner == MU_WORLD_FX_ITEM_BASE);
    assert(mu_world_particles_item_owner(p, key, at) == owner);   /* the same key keeps its slot */
    assert(mu_world_particles_create_owned(p, 0x81cf, at, angle, light, 0, 1.5f, owner));
    assert(mu_world_particles_create_owned(p, 0x81cf, at, angle, light, 0, 1.5f, MU_PT_NO_OWNER));
    assert(mu_world_particles_create_owned(p, 0x810a, at, angle, light, 0x11, 1.0f, owner));
    assert(p->list.count == 3 && p->stats.unsupported == 0);
    const mu_pt_particle *ring = &p->list.records[0];
    assert(ring->owner == owner && ring->owner_position[0] == at[0] && ring->owner_position[1] == at[1]);
    assert(ring->lifetime == 20 && ring->scale == 0.0f && ring->initial_scale == 1.5f && ring->alpha == 1.0f);
    assert(p->list.records[2].initial_lifetime == 30 && p->list.records[2].owner == owner);
    /* the OBJECT moves; the step copies its +0x158 into +0x54, the ring stays put and grows */
    mu_world_particles_item_owner_refresh(p, key, moved);
    mu_world_particles_step(p, 40.0f);
    assert(p->list.count == 3 && !p->list.records[1].live);   /* the unowned ring ends at its first step */
    ring = &p->list.records[0];
    assert(ring->owner_position[0] == moved[0] && ring->owner_position[1] == moved[1]);
    assert(ring->position[0] == at[0] && ring->position[1] == at[1] && ring->scale == 1.5f / 20.0f);
    /* nothing refreshes the OBJECT any more: the slot keeps its position, the ring lives its 20 steps */
    for (int i = 2; i <= 20; ++i)
        mu_world_particles_step(p, 40.0f * (float)i);
    assert(p->list.count == 2 && p->list.records[0].type == 0x81cf && p->list.records[0].lifetime == 0);
    assert(p->list.records[0].owner_position[0] == moved[0] && p->list.records[1].lifetime == 10);
    mu_world_particles_step(p, 840.0f);
    assert(p->list.count == 1 && p->list.records[0].type == 0x810a);
    /* every other slot held now: a new key gets -1; after the hold the stale slot is reused, generation + 1 */
    for (uint32_t k = 1; k < MU_WORLD_ITEM_OWNERS; ++k)
        assert(mu_world_particles_item_owner(p, (4u << 24) | k, at) >= 0);
    const uint32_t other = (4u << 24) | 0xfffu;
    assert(mu_world_particles_item_owner(p, other, at) == -1 && p->item_owners_full == 1);
    for (int i = 0; i < MU_WORLD_ITEM_OWNER_HOLD; ++i) {
        for (uint32_t k = 1; k < MU_WORLD_ITEM_OWNERS; ++k)
            mu_world_particles_item_owner_refresh(p, (4u << 24) | k, at);
        mu_world_particles_step(p, 1000.0f);
    }
    const int32_t reused = mu_world_particles_item_owner(p, other, moved);
    assert(reused == MU_WORLD_FX_ITEM_BASE + (1 << 8));
    assert(p->list.count == 0);   /* the spark lived its 30 steps */
    assert(mu_world_particles_create_owned(p, 0x81cf, at, angle, light, 0, 1.0f, owner));
    assert(p->list.records[0].owner == MU_PT_NO_OWNER);   /* the old index resolves to no OBJECT */
    assert(mu_world_particles_create_owned(p, 0x81cf, at, angle, light, 0, 1.0f, reused));
    assert(p->list.records[1].owner == reused && p->list.records[1].owner_position[0] == moved[0]);
    mu_world_particles_close(p);
    free(p);
    printf("item-owned particle kinds 0x810a/0x11, 0x81cf/0 and the item OBJECT owner slots through native routes: "
           "OK\n");
    return 0;
}
