/* RENDER-WORLDS-G: Santa Village (62) and Vulcanus (63) class methods.
 * Return the client's AL handled flag. Raw OBJECT bytes and bounded engine logs
 * follow object_render.h; model_present is the slot +34 model pointer gate. */
#ifndef MU_WORLDS_G_H
#define MU_WORLDS_G_H
#include "object_render.h"
int mu_santa_create(uint8_t *);
int mu_santa_move(uint8_t *, int32_t world);
int mu_vulcanus_create(uint8_t *, int32_t world);
int mu_vulcanus_move(uint8_t *, int32_t world);
int mu_santa_visual(const uint8_t *, int32_t index, int model_present, float time, mu_obj_log *);
int mu_vulcanus_visual(uint8_t *, int32_t index, int32_t world, int model_present, float time,
                       mu_obj_rand_fn, void *, mu_obj_log *);
#endif
