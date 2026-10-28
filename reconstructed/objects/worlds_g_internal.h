#ifndef MU_WORLDS_G_INTERNAL_H
#define MU_WORLDS_G_INTERNAL_H
#include "worlds_g.h"
#include "worlds_b_internal.h"
#include "login_world.h"
#include "icarus.h"
#include <math.h>
/* Existing expanded sprite/particle/joint log formats. The omitted sprite
 * descriptor is always {1,1,1.0}; joint tail is always {-1,0,0,-1,0,-1,0}. */
static inline void wg_sprite(mu_obj_log *log, int32_t i, const uint8_t *o, float scale, const float light[3])
{
    float p[3];
    wb_get(o, MU_OBJF_POSITION, p);
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_SPRITE, i);
    wb_arg(e, 0x7ef7);
    wb_vec(e, p);
    wb_float(e, scale);
    wb_vec(e, light);
    wb_float(e, 0.0f);
    wb_arg(e, 1);
    wb_arg(e, 0);
    wb_arg(e, 4);
}
static inline void wg_particle(mu_obj_log *log, int32_t i, const uint8_t *o, uint32_t bitmap,
                               const float angle[3], const float light[3], uint32_t sub, uint32_t owner)
{
    float p[3];
    wb_get(o, MU_OBJF_POSITION, p);
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
    wb_arg(e, bitmap);
    wb_vec(e, p);
    wb_vec(e, angle);
    wb_vec(e, light);
    wb_arg(e, sub);
    wb_float(e, mu_obj_f32(o, MU_OBJF_SCALE));
    wb_arg(e, owner);
}
#endif
