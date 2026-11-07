/* RENDER-WORLDS-SLOTS2 (world_slots2_visual.c): RenderObjectVisual's outer flicker draw for the class worlds, and
 * the custom (0x38) / after (0x3c) slots of the classes RENDER-WORLDS-SLOTS left. */
#ifndef MU_WORLD_VISUAL_SLOTS2_H
#define MU_WORLD_VISUAL_SLOTS2_H
#include <stdint.h>

/* RenderObjectVisual 0x017f9758 draws rand() % 30 (0x017f9797) for every object whose model it finds, before its
 * world switch (0x017f97e2), in every world: the inline cases (0..4, 6, 8..17, 0x34, 0x37) and the default branch
 * (hooks, then the class slot 0x34) all follow it. Answers 1 when the object runtime must draw it there: an object
 * with a model in any world but 4, 7 and 8, whose built-in visual (mu_builtin_visual) draws it as its first call
 * (RENDER-WORLDS-SLOTS2 for the class worlds; RENDER-WORLDS-SLOTS3 the worlds without a class and Tormenta 141,
 * whose particle visual now reads the drawn value instead of drawing). */
int mu_obj_visual_flicker(int32_t world, int has_model);
#endif
