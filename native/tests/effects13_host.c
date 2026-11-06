/* Exercise the production arrow owner adapter and joint -> legacy-particle route. */
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
    c->legacy_particles = p;
    mu_sfx_effect *e = &c->effects[0];
    e->type = 0x60d; e->live = 1; e->lifetime = 7;
    mu_sfx_call call = {0};
    call.routine = MU_SFX_CALL_JOINT;
    call.type = 0x80e3; call.subtype = 5; call.owner = -2; call.scale = 20;
    call.light[0] = 0.25f; call.light[1] = 0.5f; call.light[2] = 1;
    env_call(c, &call, e);
    assert(c->stats.joints_created == 1 && c->stats.unsupported == 0);
    const mu_jt_object *owner = mu_combat_object(c, c->joints[0].target);
    assert(owner && owner->lifetime == 7 && owner->live == 1);
    mu_jt_move_inputs in = {0}; in.time_step = 0.1f;
    mu_jt_move(&c->joints[0], &c->jenv, &in);
    assert(c->joints[0].live && c->joints[0].lifetime == 19);
    e->lifetime = 0; effect_object(c, e);
    mu_jt_move(&c->joints[0], &c->jenv, &in);
    assert(!c->joints[0].live && c->joints[0].lifetime == -1);
    e->type = 0x45b; e->lifetime = 20;
    call.type = 0x7f79; call.subtype = 15; call.arg7 = 80;
    env_call(c, &call, e);
    mu_jt_move(&c->joints[0], &c->jenv, &in);
    assert(c->stats.particles_created == 2 && c->stats.unsupported == 0);
    assert(p->stats.created == 2 && p->stats.unsupported == 0);
    e->live = 0; effect_object(c, e);
    mu_jt_move(&c->joints[0], &c->jenv, &in);
    assert(c->stats.particles_created == 2);
    mu_pt_system_free(&p->list);
    free(p); free(c);
    puts("owner lifetime and two Shiny01/3 particles through native route: OK");
    return 0;
}
