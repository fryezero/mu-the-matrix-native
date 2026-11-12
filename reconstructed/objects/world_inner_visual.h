#ifndef MU_WORLD_INNER_VISUAL_H
#define MU_WORLD_INNER_VISUAL_H
#include "world_visual.h"
/* Classless RenderObjectVisual leaves. The caller supplies a fixed offline clock tick separately from WorldTime.
 * Bone callbacks are posed transforms; NULL leaves out requests which need them. Return 1 for a world owned by
 * the leaf, 0 otherwise. The outer rand is the caller's, not drawn here. */
#define MU_INNER_ALPHA_FUNC 0x01a7c6d0u
#define MU_INNER_PUSH_MATRIX 0x012b7e53u
#define MU_INNER_POP_MATRIX 0x012b7e65u
int mu_kanturu_inner(uint8_t *, uint8_t *, int32_t, int32_t, float, uint32_t, mu_obj_rand_fn,
                      mu_world_bone_fn, void *, mu_obj_log *);
int mu_blood_castle_inner(uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn,
                           mu_world_named_bone_fn, void *, mu_obj_log *);
/* Later classless leaves. stack_light defines Elbeland 0x3a's otherwise unwritten local only for authored
 * comparisons; NULL emits an explicit refusal marker. Outer rand remains the caller's. */
#define MU_INNER_UNWRITTEN_LIGHT 0x00e31358u
int mu_later_world_inner(uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn,
                          mu_world_bone_fn, void *, const float[3], mu_obj_log *);
#endif
