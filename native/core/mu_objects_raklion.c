/* Raklion event host. The domain owning event state calls set_event; no fixture/live state is invented. */
#include "mu_objects.h"
#include "../../reconstructed/objects/raklion_event.h"
#include <string.h>

static float value(uint32_t b) { float f; memcpy(&f, &b, 4); return f; }
static int32_t random_value(void *c) { return mu_obj_msvc_rand(&((mu_objects *)c)->rt.seed); }

void mu_objects_raklion_set_event(mu_objects *o, uint8_t event)
{
    if (o->world != 57 && o->world != 58) return;
    o->rt.raklion_state[0x20] = event;
    mu_raklion_event_arm(o->rt.raklion_state);
}

void mu_objects_raklion_move(mu_objects *o, int32_t type, const float hero[3])
{
    if ((o->world != 57 && o->world != 58) || type == 0x16 || type == 0x46 || type == 0x50) return;
    mu_objects_runtime *rt = &o->rt;
    mu_obj_event events[30];
    mu_obj_log log = {0, 30, 0, events};
    mu_raklion_event_step(rt->raklion_state, rt->now_ms, hero, rt->raklion_hero_angle,
                          &rt->raklion_quake, random_value, o, &log);
    for (int k = 0; k < log.count; ++k) {
        const mu_obj_event *e = &events[k];
        float p[3], a[3], l[3];
        for (int q = 0; q < 3; ++q) {
            p[q] = value(e->args[1+q]); a[q] = value(e->args[4+q]); l[q] = value(e->args[7+q]);
        }
        if (e->call == MU_OBJ_CALL_CREATE_EFFECT) {
            if (rt->effect_scaled) rt->effect_scaled(rt->hook_context, (int32_t)e->args[0], (int32_t)e->args[10],
                                                     p, a, l, -1, value(e->args[11]));
            ++rt->effect_events;
        } else if (e->call == MU_OBJ_CALL_PARTICLE) {
            if (rt->particle) rt->particle(rt->hook_context, (int32_t)e->args[0], p, a, l,
                                           (int32_t)e->args[10], value(e->args[11]), -1);
            ++rt->particle_events;
        }
    }
}
