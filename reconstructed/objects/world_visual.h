#ifndef MU_WORLD_VISUAL_H
#define MU_WORLD_VISUAL_H
#include "login_world.h"
#include "object_render.h"
typedef void (*mu_world_bone_fn)(void *, int32_t, const float[3], float[3]);
/* Scoped world visual producers and after-character branches. See lane findings for limits. */
int mu_kanturu_flames(const uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn, mu_world_bone_fn, void *,
                      mu_obj_log *);
int mu_karutan_flames(const uint8_t *, int32_t, mu_obj_rand_fn, void *, mu_obj_log *);
/* Complete RENDER-WORLDS-J primary methods; legacy create/move Raklion in worlds_b.h. */
int mu_karutan_create(const uint8_t *);
int mu_karutan_move(uint8_t *, int32_t, const mu_obj_move_inputs *, mu_obj_log *);
int mu_karutan_visual(const uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn,
                       mu_world_bone_fn, void *, mu_obj_log *);
int mu_raklion_visual(const uint8_t *, int32_t, int, mu_obj_rand_fn, void *, mu_obj_log *);
int mu_raklion_before(const uint8_t *, int32_t, mu_obj_log *);
int mu_world_defer(uint8_t *, int32_t);
int mu_world_after_enabled(int32_t);
int mu_world_after_special(const uint8_t *, int32_t);
int mu_world_after_pass(mu_obj_world *, const mu_obj_render_inputs *, int32_t *, mu_obj_log *);
int mu_world_after_render(uint8_t *, int32_t, int32_t, float, mu_obj_log *, mu_world_bone_fn, void *);
typedef void (*mu_world_named_bone_fn)(void *, const char *, const float[3], float[3]);
int mu_builtin_visual(uint8_t *, int32_t, int32_t, int, float, mu_obj_rand_fn,
                      mu_world_named_bone_fn, void *, mu_obj_log *);
void mu_icarus_bone_flare(const uint8_t *, int32_t, mu_world_named_bone_fn, void *, mu_obj_log *);
void mu_losttower_push(uint8_t *, int32_t, const float[3], uint16_t, mu_obj_log *);
#endif
