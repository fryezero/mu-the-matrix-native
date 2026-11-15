#ifndef MU_WORLD_INNER4_VISUAL_H
#define MU_WORLD_INNER4_VISUAL_H
#include "world_inner_visual.h"
/* Fixed authored event byte, never an authoritative event feed. Outer RNG belongs to the caller. */
int mu_crywolf_inner(uint8_t *, int32_t, int32_t, int, float, uint8_t, mu_obj_rand_fn, void *, mu_obj_log *);
int mu_barracks_inner(uint8_t *, int32_t, int32_t, int, float, mu_obj_rand_fn, void *, mu_obj_log *);
#define MU_INNER4_CONTEXT_REFUSED 0x00def747u
int mu_kalima_inner(uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn, mu_world_named_bone_fn, void *, mu_obj_log *);
int mu_tower_inner(uint8_t *, int32_t, int32_t, float, uint8_t, mu_obj_rand_fn, mu_world_bone_fn, void *, mu_obj_log *);
#endif
