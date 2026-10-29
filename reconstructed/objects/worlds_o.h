/* RENDER-WORLDS-O. Abyss of Atlans 1-3 (worlds 128-130) primary methods. */
#ifndef MU_WORLDS_O_H
#define MU_WORLDS_O_H
#include "object_render.h"
/* The three classes share one body; `cls` is the class's own world (128, 129
 * or 130), compared with the current world global as each original does. */
int mu_abyss_create(int32_t cls, uint8_t *, int32_t world);
int mu_abyss_move(int32_t cls, uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_obj_log *);
int mu_abyss_visual(int32_t cls, uint8_t *, int32_t world, int model_present);
#endif
