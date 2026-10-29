#ifndef MU_WORLD_VISUAL_H
#define MU_WORLD_VISUAL_H
#include "login_world.h"
#include "object_render.h"
typedef void (*mu_world_bone_fn)(void *, int32_t, const float[3], float[3]);
/* Scoped world visual producers and after-character branches. See lane findings for limits. */
int mu_kanturu_flames(const uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn, mu_world_bone_fn, void *,
                      mu_obj_log *);
int mu_karutan_flames(const uint8_t *, int32_t, mu_obj_rand_fn, void *, mu_obj_log *);
/* Complete RENDER-WORLDS-J primary methods; legacy create/move Raklion in worlds_b.h. */
int mu_karutan_create(const uint8_t *);
int mu_karutan_move(uint8_t *, int32_t, const mu_obj_move_inputs *, mu_obj_log *);
int mu_karutan_visual(const uint8_t *, int32_t, int32_t, float, mu_obj_rand_fn,
                       mu_world_bone_fn, void *, mu_obj_log *);
int mu_raklion_visual(const uint8_t *, int32_t, int, mu_obj_rand_fn, void *, mu_obj_log *);
int mu_raklion_before(const uint8_t *, int32_t, mu_obj_log *);
int mu_world_defer(uint8_t *, int32_t);
int mu_world_after_enabled(int32_t);
int mu_world_after_special(const uint8_t *, int32_t);
int mu_world_after_pass(mu_obj_world *, const mu_obj_render_inputs *, int32_t *, mu_obj_log *);
/* RENDER-WORLDS-AFTER: the whole second pass 0x016d6949, its world test and per-object selector 0x017fe909. */
typedef struct mu_world_after_inputs {
    uint8_t class_flag;    /* current world handler byte +5 (slot 8 0x00d5cb7c); mu_world_class_after */
    int32_t tower_state;   /* world 0x27: 0x009a6ef3() + 0x78, field +4 (0x009a645f) */
    uint8_t master_class;  /* world 2 type 0x64: 0x0139d89f(hero +0x12) == 1 */
    int32_t level;         /* world 2 type 0x64: 0x00a00066(0x01d1df1c) */
} mu_world_after_inputs;
int mu_world_class_after(int32_t world);
int mu_world_after_gate(int32_t world, int class_flag);
int mu_world_after_native(int32_t world);
int mu_world_after_select(uint8_t *object, const mu_obj_render_inputs *in);
int mu_world_after_pass_ex(mu_obj_world *, const mu_obj_render_inputs *, const mu_world_after_inputs *, int32_t *,
                           mu_obj_log *);
/* Abyss of Atlans 1-3 (128..130) custom render slot 0x38 (0x00d5d2f6/0x00d5ef96/0x00d606da; returns handled,
 * logs RenderBody/RenderMesh) and after render slot 0x3c (0x00d5d5ad/0x00d5f23a/0x00d60991; returns drawn). */
int mu_abyss_custom(int32_t cls, uint8_t *object, int32_t index, int32_t world, float time, mu_obj_rand_fn rand_fn,
                    void *context, mu_obj_log *log);
int mu_abyss_after(int32_t cls, const uint8_t *object, int32_t index, int32_t world, mu_obj_log *log);
/* RENDER-WORLDS-AFTER2: the custom render slot 0x38 (returns handled) and after render slot 0x3c of the classes
 * mu_class_slots names (world_slots_visual.c). b: the model fields (+0x54 colour, +0x94 StreamMesh byte, +0xa8
 * action, +0xac frame); time: WorldTime. */
typedef struct mu_slot_model {
    int32_t mesh_count;        /* model +0x24 */
    const int16_t *sub_flag;   /* per mesh: -1 no texture sub record (+0x1c), else its first byte */
} mu_slot_model;
int mu_class_slots(int32_t world);
int mu_class_custom(int32_t cls, uint8_t *object, uint8_t *b, int32_t index, int32_t world, float time,
                    const mu_slot_model *model, mu_obj_log *log);
void mu_class_after(int32_t cls, uint8_t *object, uint8_t *b, int32_t index, int32_t world, float time,
                    const mu_slot_model *model, mu_obj_log *log);
/* The pre-move slot 0x74 of classes 69..72, 79, 80/81 and 122 (returns 0 for the others); state: the world-69
 * handler's +0x14 (Imperial Guardian). */
int mu_class_premove(int32_t cls, const uint8_t *object, int32_t index, int32_t world, int32_t state,
                     mu_obj_rand_fn rand_fn, void *context, mu_obj_log *log);
/* LoadBitmap registration (path under Data\, filter, wrap) of a bitmap the slots of `world` bind to a model mesh,
 * and the bitmaps the slots name for objects of `type` (at most 4). */
int mu_world_slot_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap);
int32_t mu_world_slot_bitmaps(int32_t world, int32_t type, int32_t out[4]);
int mu_world_chain_predicate(uint32_t address, int32_t world);
int mu_world_after_render(uint8_t *, int32_t, int32_t, float, mu_obj_log *, mu_world_bone_fn, void *);
typedef void (*mu_world_named_bone_fn)(void *, const char *, const float[3], float[3]);
int mu_builtin_visual(uint8_t *, int32_t, int32_t, int, float, mu_obj_rand_fn,
                      mu_world_named_bone_fn, void *, mu_obj_log *);
void mu_icarus_bone_flare(const uint8_t *, int32_t, mu_world_named_bone_fn, void *, mu_obj_log *);
void mu_losttower_push(uint8_t *, int32_t, const float[3], uint16_t, mu_obj_log *);
/* RENDER-WORLDS-Q2: the class slot 0x10 of worlds 134..145, the draw-first answer of 0x017fcd18 for them
 * (world_first_visual.c). mu_class_first_owned: the worlds whose answer it is. */
int mu_class_first_owned(int32_t world);
int mu_class_first(uint8_t *o, int32_t world, const float x2d[4], const float y2d[4], int32_t scene_state);
#endif
