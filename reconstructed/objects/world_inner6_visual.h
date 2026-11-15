#ifndef MU_WORLD_INNER6_VISUAL_H
#define MU_WORLD_INNER6_VISUAL_H
#include "world_inner_visual.h"
/* RENDER-WORLDS-PICK-001: chain hook 11 of RenderObjectVisual's common chain (0x017fcc58..0x017fcc77), the visual
 * slot +0x34 = 0x00db7656 of the singleton 0x01ec9118 (getter 0x00db747f, constructor 0x00db73f3, vtable
 * 0x01aa7a08). Its world test 0x0095fba9 accepts 45..50 and 98..99; these worlds have no factory class.
 * clock is the imported clock call of type 78 ([0x01a7c9a4]); the outer RNG belongs to the caller.
 * Returns the routine's AL: 1 for the eleven types it names, else 0. */
int mu_chain11_inner(uint8_t *object, int32_t index, int32_t world, int model, uint32_t clock, mu_obj_rand_fn rnd,
                     void *context, mu_obj_log *log);
/* 0x0095fba9: the worlds the hook takes. */
int mu_chain11_world(int32_t world);
#endif
