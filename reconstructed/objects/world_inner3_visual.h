#ifndef MU_WORLD_INNER3_VISUAL_H
#define MU_WORLD_INNER3_VISUAL_H
#include "world_inner_visual.h"
/* Complete Aida inline leaf. Outer RNG belongs to RenderObjectVisual. clock is an authored offline tick. */
int mu_aida_inner(uint8_t *, uint8_t *, int32_t, int32_t, float, uint32_t, mu_obj_rand_fn,
                  mu_world_named_bone_fn, void *, mu_obj_log *);
int mu_kanturu_remain_inner(uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn,
                            mu_world_bone_fn, void *, mu_obj_log *);
int mu_trials_inner(uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn,
                     mu_world_bone_fn, void *, mu_obj_log *);
int mu_devil_square_inner(uint8_t *, int32_t, int32_t, mu_obj_rand_fn,
                          mu_world_named_bone_fn, void *, mu_obj_log *);
#endif
