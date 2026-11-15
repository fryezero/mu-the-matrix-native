/* Native callback boundary controls. Including the module permits a synthetic
 * arrow/owner fixture without a session, app bundle or proprietary model. */
#include "../core/mu_combat.c"
#include <assert.h>

int main(void)
{
    mu_combat *c = calloc(1,sizeof *c);
    assert(c);
    mu_walk walk = {0}; c->walk = &walk; c->hero_key = 1234;
    init_env(c);
    mu_sfx_effect *arrow = &c->effects[0];
    arrow->live = 1; arrow->type = 0x43b; arrow->subtype = 2;
    arrow->position[0] = 100; arrow->position[1] = 200; arrow->position[2] = 50;
    arrow->angle[2] = 90;
    mu_sfx_call child = {0}; child.routine = MU_SFX_CALL_EFFECT;
    child.type = 0x46c; child.owner = -2; child.range = -1;
    memcpy(child.position,arrow->position,sizeof child.position);
    memcpy(child.angle,arrow->angle,sizeof child.angle);
    child.light[0] = child.light[1] = child.light[2] = 1;
    env_call(c,&child,arrow);
    mu_sfx_effect *e = &c->effects[1];
    assert(e->live && e->type == 0x46c && e->owner == MU_COMBAT_EFFECT_OBJECT(0));
    assert(e->key == 0xffff && e->scale == 1 && e->lifetime == 100);
    assert(c->stats.joints_created == 4 && c->stats.unsupported == 0);
    for (int n = 0; n < 4; ++n) {
        const mu_jt_joint *j = &c->joints[n];
        assert(j->live && j->type == 0x7f79 && j->subtype == n && j->lifetime == 30);
        assert(j->target == MU_COMBAT_EFFECT_OBJECT(1) && j->scale == 20);
        assert(j->jitter[0] == 18 && j->key == 0 && j->skill == 0);
    }
    e->heading = 11; e->heading_yz[0] = 22; e->heading_yz[1] = 33;
    e->impact[0] = 44; effect_object(c,e);
    const mu_sfx_object *o = &c->objects[MU_COMBAT_EFFECT_OBJECT(1)];
    assert(o->heading[0] == 11 && o->heading[1] == 22 && o->heading[2] == 33 && o->impact[0] == 44);
    c->env.model = NULL; /* synthetic action table, no asset needed */
    arrow->live = 0; effect_object(c,arrow);
    assert(mu_sfx_effect_move(e,&c->env) && !e->live);
    for (int n = 0; n < MU_SFX_EFFECTS; ++n) c->effects[n].live = 1;
    uint32_t full = c->stats.fx_created;
    env_call(c,&child,arrow);
    assert(c->stats.fx_created == full && c->stats.joints_created == 4);
    free(c);
    puts("{\"native_callbacks\":true,\"checks\":9}");
    return 0;
}
