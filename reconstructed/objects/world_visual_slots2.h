/* RENDER-WORLDS-SLOTS2 (world_slots2_visual.c): RenderObjectVisual's outer flicker draw for the class worlds, and
 * the custom (0x38) / after (0x3c) slots of the classes RENDER-WORLDS-SLOTS left. */
#ifndef MU_WORLD_VISUAL_SLOTS2_H
#define MU_WORLD_VISUAL_SLOTS2_H
#include <stdint.h>

/* RenderObjectVisual 0x017f9758 draws rand() % 30 (0x017f9797) for every object whose model it finds, before its
 * world switch; the class worlds then reach their slot 0x34 through the default branch (0x017fcb5c). Answers 1
 * when the native class visual of `world` must draw it: a world with a class registration (57 of them; Tormenta
 * 141 excepted, whose slot the particle visual runs after its own draw) and a model. */
int mu_obj_visual_flicker(int32_t world, int has_model);
#endif
