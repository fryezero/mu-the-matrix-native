/* RENDER-WORLDS-H. Primary handler slots, raw OBJECT and expanded engine logs.
 * Return the original AL, including Duel Arena's false after emitting calls. */
#ifndef MU_WORLDS_H_H
#define MU_WORLDS_H_H
#include "object_render.h"
int mu_duel_create(uint8_t *);
int mu_duel_move(uint8_t *, int32_t, const mu_obj_move_inputs *, mu_obj_log *);
int mu_duel_visual(const uint8_t *, int32_t, int model_present, mu_obj_rand_fn, void *, mu_obj_log *);
int mu_world82_create(uint8_t *);
int mu_world82_move(uint8_t *, int32_t world);
/* world predicate is 82..90, although the factory registers this class at 82.
 * Type 48 requires trunc32(scale*60) != 0, as the original divides by it.
 * Invalid zero divisors are suppressed by the native host rather than trapping. */
int mu_world82_visual(uint8_t *, int32_t, int32_t world, int model_present, float time,
                      mu_obj_rand_fn, void *, mu_obj_log *);
#endif
