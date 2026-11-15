#ifndef MU_WORLD_INNER5_VISUAL_H
#define MU_WORLD_INNER5_VISUAL_H
#include "world_inner4_visual.h"
/* Offline authored context. A missing water manager returns zero in 0x00deeb4e.
 * A present manager's sampler is an explicit input boundary, not a recovered water simulation. */
typedef float (*mu_inner_water_fn)(void *, float, float);
typedef struct mu_kalima_fixture {
    uint16_t hero_action;
    float hero[3];
    mu_inner_water_fn water;
} mu_kalima_fixture;
int mu_kalima_helpers(uint8_t *, int32_t, int32_t, float, const mu_kalima_fixture *,
                      mu_world_named_bone_fn, void *, mu_obj_log *);
/* Exact scalar state read/written by tower type 0 and 0x00e8d888.
 * Timer answers are fixed authored inputs. No event controller or timer is inferred. */
typedef struct mu_tower_fixture {
    int32_t mode, stage, phase, burst, sequence;
    uint8_t active, rising, emit, timer0, timer1, timer2;
    float shake, hero[3];
} mu_tower_fixture;
int mu_tower_zero(uint8_t *, int32_t, int32_t, mu_tower_fixture *, mu_obj_rand_fn,
                   mu_world_bone_fn, void *, mu_obj_log *);
#endif
