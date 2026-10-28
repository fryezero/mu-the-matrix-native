#ifndef MU_ICARUS_H
#define MU_ICARUS_H
#include "object_render.h"
/* 0x018016b0. Returns the random object ordinal, or zero when none exists.
 * Host consumes light/effect/joint events. rand callback is MSVC rand, in call order. */
int32_t mu_icarus_sky(const float hero[3], int32_t object_count, mu_obj_rand_fn random, void *context, mu_obj_log *log);
/* World-10 branch of 0x0180249e. Count/ordinal are MoveObjects' two counters. */
void mu_icarus_object(const uint8_t *object, int32_t index, int32_t selected, int32_t *ordinal,
                      mu_obj_rand_fn random, void *context, mu_obj_log *log);
/* Sprite log args[9]: 2 denotes the hero OBJECT, not the emitting map object. */
#define MU_ICARUS_SPRITE_HERO 2u
#define MU_ICARUS_JOINT 0x0153b02cu
#define MU_ICARUS_SPRITE 0x01692eb7u
void mu_icarus_cover(uint8_t *object, int32_t index, mu_obj_log *log);
#endif
