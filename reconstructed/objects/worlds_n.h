/* RENDER-WORLDS-N. Nixies Lake (113) and Deep Dungeon 1-5 (116-120) primary methods. */
#ifndef MU_WORLDS_N_H
#define MU_WORLDS_N_H
#include "object_render.h"
int mu_nixies_create(uint8_t *, int32_t world);
int mu_nixies_move(uint8_t *, const mu_obj_move_inputs *);
/* One template for the five Deep Dungeon classes; only create's range list differs by world. */
int mu_deep_dungeon_create(uint8_t *, int32_t index, int32_t world, mu_obj_log *);
int mu_deep_dungeon_move(uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_obj_log *);
/* Shared visual slot 0x00d5cc9b of worlds 113, 115 and 116-120: returns false, no request. */
int mu_worlds_n_visual(const uint8_t *, int32_t index);
/* CreateEffect(0x43a, ...) with key (u16)(int)scale. No native keyed-effect consumer yet: args type,
 * position, angle, light, subtype 0, owner 0, key. The host counts it as refused. */
#define MU_DEEP_DUNGEON_KEYED_EFFECT 0xe3e8f8u
#endif
