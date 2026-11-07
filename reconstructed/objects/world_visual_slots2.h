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

/* RENDER-WORLDS-121 (world_test_area_visual.c, the SetAction in kanturu_underground.c) */
/* Pseudo call of a class custom render: every mesh's per-vertex light (MU_MODEL_LIGHTS 0x06fd0918, mesh stride
 * 0xea60, one float per normal) set to args[0] (float bits), written between Transform and the RenderBody that
 * follows it. The object runtime replays it after its pose (mu_objects_runtime.c slot_vertex_light). */
#define MU_OBJ_CALL_VERTEX_LIGHT 0x06fd0918u
/* SetAction 0x012affa4(o, action) with the object's model's action count: when action < count and differs from
 * the current action, the action and frame become the prior ones and the frame restarts at 0. */
void mu_obj_set_action(uint8_t *o, int32_t action_count, int32_t action);
/* RenderObjectVisual's Devias case 0x017f9bdc, type 0x67 (0x017f9d79), after the outer draw: when the model's
 * whole frame (+0xb4, Animation's (short)(int)frame) is the action's last key (keys - 1), one rand():
 * SetAction(o, rand() % 32 == 0 ? 1 : 0). Returns 1 when it drew. */
int mu_devias_action_pick(uint8_t *o, int16_t frame_whole, int16_t keys, int32_t action_count, int32_t (*rnd)(void *),
                          void *context);
/* (short)(int)frame as Animation 0x012b5128 stores it at model +0xb4 (cvttss2si, then the low 16 bits). */
int16_t mu_obj_frame_whole(float frame);
#endif
