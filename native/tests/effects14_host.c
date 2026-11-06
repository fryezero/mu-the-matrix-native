/* RENDER-EFFECTS-014: the production combat routes of Flare/b (arrow write-back), Flare02/e (sprite and three
 * particles), 0x70c's rings and stones, and the volley script verb. */
#include "../core/mu_combat.c"
#include <assert.h>
#include <stdlib.h>

int main(void)
{
    mu_combat *c = calloc(1, sizeof *c);
    mu_world_particles *p = calloc(1, sizeof *p);
    assert(c && p);
    init_env(c);
    assert(mu_pt_system_init(&p->list, 16) == 0);
    p->sprites = calloc(1, sizeof *p->sprites);
    assert(p->sprites);
    c->legacy_particles = p;

    /* Flare/b: arrow 0x459 owns four joints; the skill-1 joint carries the arrow to its head */
    mu_sfx_effect *e = &c->effects[0];
    e->type = 0x459; e->live = 1; e->lifetime = 30;
    e->position[0] = 100; e->position[1] = 200; e->position[2] = 50;
    e->impact[0] = 1000; e->impact[1] = 2000; e->impact[2] = 300;
    mu_sfx_call call = {0};
    call.routine = MU_SFX_CALL_JOINT;
    call.type = 0x7f78; call.subtype = 0xb; call.owner = -2; call.scale = 50; call.arg7 = -1;
    memcpy(call.position, e->impact, sizeof call.position);
    memcpy(call.target, e->impact, sizeof call.target);
    call.arg8 = 0;
    env_call(c, &call, e);
    call.arg8 = 1;
    env_call(c, &call, e);
    assert(c->stats.joints_created == 2 && c->stats.unsupported == 0);
    const mu_jt_object *owner = mu_combat_object(c, c->joints[1].target);
    assert(owner && owner->impact[0] == 1000 && owner->impact[2] == 300);
    c->step = 7;
    c->jenv.ambient_clock = c->step;
    mu_jt_move_inputs in = {0}; in.time_step = 0.1f;
    in.index = 0;
    mu_jt_move(&c->joints[0], &c->jenv, &in);
    assert(e->position[0] == 100 && e->position[1] == 200);   /* skill 0: no write-back */
    in.index = 1;
    mu_jt_move(&c->joints[1], &c->jenv, &in);
    assert(e->position[0] == c->joints[1].position[0] && e->position[1] == c->joints[1].position[1] &&
           e->position[2] == c->joints[1].position[2]);
    assert(c->joints[1].lifetime == 29 && c->joints[0].live && c->joints[1].live);
    assert(p->sprites->created == 6);   /* Shiny02 and two flare01 per joint */
    e->live = 0; effect_object(c, e);
    mu_jt_move(&c->joints[0], &c->jenv, &in);
    assert(!c->joints[0].live && c->joints[0].lifetime == -2);

    /* Flare02/e: a Spark03 sprite, smoke01/0x22, /0x23 and Spark03/0xa per move while the arrow lives */
    memset(c->joints, 0, sizeof c->joints);
    c->stats.joints_created = 0;
    e->type = 0x45a; e->live = 1; e->lifetime = 30;
    call.type = 0x7f79; call.subtype = 0xe; call.arg7 = 40; call.arg8 = 0;
    env_call(c, &call, e);
    assert(c->stats.joints_created == 1 && c->joints[0].lifetime == 40);
    const uint64_t sprites = p->sprites->created;
    mu_jt_move(&c->joints[0], &c->jenv, &in);
    assert(c->stats.particles_created == 3 && p->stats.unsupported == 0 && c->stats.unsupported == 0);
    assert(p->sprites->created == sprites + 1);
    assert(c->joints[0].light[0] == 1.0f && c->joints[0].light[2] == 0.2f);

    /* 0x70c's rings and stones are created, not refused */
    const float at[3] = {0, 0, 0}, white[3] = {1, 1, 1};
    static const int32_t kinds[][2] = {{0x703, 0}, {0x704, 0}, {0x705, 0}, {0x705, 1}, {0x705, 3}, {0x706, 0},
                                       {0x419, 0x13}, {0x41a, 0x13}};
    for (size_t k = 0; k < sizeof kinds / sizeof kinds[0]; ++k)
        create_effect_scaled(c, kinds[k][0], kinds[k][1], at, at, white, -1, NULL, 0.25f);
    assert(c->stats.unsupported == 0);

    /* the ground-skill fixture: 0x70a is refused (counted), 0x7fd fires no arrows of its own */
    const uint32_t before = c->stats.unsupported;
    c->walk = calloc(1, sizeof *c->walk);
    assert(c->walk);
    ground_volley(c, 0x7fd);
    assert(c->stats.unsupported == before + 1 && c->stats.skills == 1);
    assert(c->unsupported_kinds[c->unsupported_kind_count - 1].type == 0x70a);
    free(c->walk);
    free(p->sprites);
    mu_pt_system_free(&p->list);
    free(p); free(c);
    puts("Flare/b write-back, Flare02/e particles, 0x70c rings and the ground-skill fixture through native routes: OK");
    return 0;
}
