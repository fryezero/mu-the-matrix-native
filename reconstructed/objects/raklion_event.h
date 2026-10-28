/* Raklion's inherited event timer. State offsets are the client's handler +0x14..+0x23. */
#ifndef MU_RAKLION_EVENT_H
#define MU_RAKLION_EVENT_H
#include "object_render.h"
void mu_raklion_event_arm(uint8_t state[0x28]); /* 0x00ea176f */
void mu_raklion_event_emit(const uint8_t state[0x28], const float hero[3], const float angle[3],
                           float *quake, mu_obj_rand_fn, void *, mu_obj_log *); /* 0x00ea186c */
void mu_raklion_event_step(uint8_t state[0x28], uint32_t now_ms, const float hero[3], const float angle[3],
                           float *quake, mu_obj_rand_fn, void *, mu_obj_log *); /* 0x00ea17c0 */
#endif
