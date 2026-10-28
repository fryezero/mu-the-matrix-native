/* Synthetic native link integration: saved pose, scale/origin, bounds and pool capacity. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_renderchar.h"
#include "../core/mu_particles.h"

int main(void)
{
    mu_world_particles *p = calloc(1, sizeof *p);
    char error[256];
    if (!p || mu_world_particles_open(p, NULL, NULL, 0, 1, 1, error, sizeof error)) return 2;
    mu_bmd bmd = {0};
    bmd.bone_count = 20;
    mu_model model = {0};
    model.bmd = &bmd;
    model.params.body_scale = 2;
    model.params.origin[0] = 100;
    model.params.origin[1] = 200;
    model.params.origin[2] = 300;
    float bones[20 * 12] = {0};
    for (int k = 0; k < 20; ++k) {
        bones[k * 12 + 3] = (float)k;
        bones[k * 12 + 7] = 10;
        bones[k * 12 + 11] = -5;
    }
    long n = mu_renderchar_link_effects(&model, bones, 0x12ec, p);
    if (n != 6 || p->rand_calls != 1 || p->sprites->created != 6) return 3;
    const mu_pt_sprite *s = &p->sprites->records[0];
    if (s->position[0] != 126 || s->position[1] != 220 || s->position[2] != 290 ||
        s->type != 0x7f67 || s->axes != 4 || s->blend != 0) return 4;
    /* No stale shared pose: explicitly changed saved matrices drive the second item. */
    bones[13 * 12 + 3] = 33;
    if (mu_renderchar_link_effects(&model, bones, 0x12ec, p) != 6 ||
        p->sprites->records[6].position[0] != 166) return 5;
    bmd.bone_count = 14;
    if (mu_renderchar_link_effects(&model, bones, 0x12ec, p) != 1) return 6;
    if (mu_renderchar_link_effects(&model, NULL, 0x12ec, p) != 0 ||
        mu_renderchar_link_effects(&model, bones, 0xae6, p) != 0 || p->rand_calls != 3) return 7;
    for (int i = 0; i < MU_PT_SPRITES; ++i) p->sprites->records[i].live = 1;
    if (mu_renderchar_link_effects(&model, bones, 0x12ec, p) != 0) return 8;
    if (mu_renderchar_type_from_path("Data/Item/Bow05.bmd") != 0x12ea ||
        mu_renderchar_type_from_path("Wing01.bmd") != 0x22e6 ||
        mu_renderchar_type_from_path("Spear513.bmd") != -1 ||
        mu_renderchar_type_from_path("HelmClass01.bmd") != 0x3700 ||
        mu_renderchar_type_from_path("Data/Player/BootClass81.bmd") != -1 ||
        mu_renderchar_type_from_path("BootClass00.bmd") != -1 ||
        mu_renderchar_type_from_path("bOoTcLaSs80.bmd") != 0x388f) return 9;
    printf("{\"created\":%llu,\"random_calls\":%llu,\"missing_bones_skipped\":5,\"full\":true}\n",
           (unsigned long long)p->sprites->created, (unsigned long long)p->rand_calls);
    mu_world_particles_discard_sprites(p);
    bmd.bone_count = 20;
    for (int k = 0; k < 20; ++k)
        bones[k * 12] = bones[k * 12 + 5] = bones[k * 12 + 10] = 1;
    p->rand_state = 1;
    p->rand_calls = 0;
    n = mu_renderchar_link_effects(&model, bones, 0x14f0, p);
    if (n < 10 || n > 20 || p->rand_calls != (uint64_t)n + 1) return 10;
    s = &p->sprites->records[0];
    if (s->position[0] != -260 || s->position[1] != 140 || s->position[2] != 290) return 11;
    mu_world_particles_discard_sprites(p);
    p->rand_state = 1;
    /* Spark03/11 now consumes both conditional requests. */
    if (mu_renderchar_link_effects(&model, bones, 0x12fb, p) != 7 ||
        p->stats.created != 2 || p->stats.unsupported != 0) return 15;
    mu_world_particles_discard_sprites(p);
    if (mu_renderchar_link_effects(&model, bones, 0x0ef4, p) != 5) return 16;
    mu_world_particles_discard_sprites(p);
    p->world_time = 700.25f;
    if (mu_renderchar_link_effects(&model, bones, 0x0afc, p) != 2) return 17;
    mu_world_particles_discard_sprites(p);
    uint64_t random_before = p->rand_calls;
    if (mu_renderchar_link_effects(&model, bones, 0x0afd, p) != 7 ||
        p->rand_calls != random_before + 3) return 18;
    mu_world_particles_discard_sprites(p);
    /* Skin sprites ignore body_scale, preserve the saved bone translation, then add origin. */
    if (mu_renderchar_link_effects(&model, bones, 0x389c, p) != 1 ||
        p->rand_calls != random_before + 3) return 19;
    s = &p->sprites->records[0];
    if (s->position[0] != 100 || s->position[1] != 210 || s->position[2] != 310 ||
        s->type != 0x7f26 || s->owner != MU_PT_NO_OWNER) return 20;
    mu_world_particles_discard_sprites(p);
    if (mu_renderchar_link_effects(&model, bones, 0x389d, p) != 1) return 21;
    s = &p->sprites->records[0];
    if (s->position[1] != 205 || s->position[2] != 280) return 22;
    bmd.bone_count = 0;
    if (mu_renderchar_link_effects(&model, bones, 0x389c, p) != 0) return 23;
    mu_world_particles_discard_sprites(p);
    for (int i = 0; i < MU_PT_SPRITES; ++i) p->sprites->records[i].live = 1;
    bmd.bone_count = 20;
    if (mu_renderchar_link_effects(&model, bones, 0x389c, p) != 0 ||
        mu_renderchar_link_effects(&model, bones, 0x0afd, p) != 0) return 24;
    mu_world_particles_discard_sprites(p);
    p->rand_state = 1;
    uint64_t before_chain = p->rand_calls;
    if (mu_renderchar_link_effects(&model, bones, 0x12f9, p) != 10 ||
        p->rand_calls != before_chain + 1) return 25;
    s = &p->sprites->records[9];
    if (s->position[0] != 110 || s->position[1] != 220 || s->position[2] != 310 ||
        s->light[0] != 1 || s->light[1] != 1 || s->light[2] != 1) return 26;
    mu_world_particles_discard_sprites(p);
    bmd.bone_count = 3;
    if (mu_renderchar_link_effects(&model, bones, 0x12f9, p) != 4) return 27;
    /* Ground/inventory skin entry point must not allocate weapon link sprites. */
    before_chain = p->rand_calls;
    if (mu_renderchar_skin_effects(&model, bones, 0x12f9, p) ||
        p->rand_calls != before_chain) return 28;
    mu_world_particles_discard_sprites(p);
    bmd.bone_count = 1;
    if (mu_renderchar_link_effects(&model, bones, 0x12fb, p) != 3) return 12;
    s = &p->sprites->records[0];
    if (s->position[0] != 140 || s->position[1] != 220 || s->type != 0x7ef7) return 13;
    for (int i = 0; i < MU_PT_SPRITES; ++i) p->sprites->records[i].live = 1;
    if (mu_renderchar_link_effects(&model, bones, 0x14f0, p) != 0) return 14;
    mu_world_particles_close(p);
    free(p);
    return 0;
}
