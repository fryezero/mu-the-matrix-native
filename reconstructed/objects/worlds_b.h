/* RENDER-WORLDS-B. Per-world branches, after MoveObject's generic tick. */
#ifndef MU_WORLDS_B_H
#define MU_WORLDS_B_H
#include "object_render.h"
void mu_devias_move(uint8_t *, int32_t, const mu_obj_move_inputs *, mu_obj_log *);
void mu_tarkan_move(uint8_t *, int32_t, const mu_obj_move_inputs *, mu_obj_log *);
void mu_elbeland_move(uint8_t *, int32_t, const mu_obj_move_inputs *, mu_obj_log *);
void mu_elbeland_pool(uint8_t *, const uint8_t *, mu_obj_rand_fn, void *);
void mu_raklion_move(uint8_t *, float);
void mu_raklion_create(uint8_t *, int32_t, mu_obj_log *);
/* Code-created placements of AccessModels 0x018392db. Capacity must be >= 3. */
int32_t mu_devias_records(mu_object_record *);
int32_t mu_raklion_records(int32_t world, mu_object_record *);
#endif
