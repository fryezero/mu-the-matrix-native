/* RENDER-WORLDS-S. Aquila's Temple (145), Debenter (95), Boss Battle (139) and world 115 primary methods. */
#ifndef MU_WORLDS_S_H
#define MU_WORLDS_S_H
#include "object_render.h"
#include "worlds_q.h"
/* OBJECT +0x188 / +0x194: two f32[3] points the Aquila and Debenter slots write (bone positions) and read. */
#define MU_OBJF_POINT_A 0x188
#define MU_OBJF_POINT_B 0x194
/* Aquila's Temple: no world predicate in any of the three slots. Create returns false only for a null object. */
int mu_aquila_create(uint8_t *, int32_t world);
/* Move writes after-character (+0x0a) for every type and lights types 90 (at the object) and 136..140, 142 (at
 * +0x188, where the visual left bone 6). The original has no null test (native callers never pass null). */
int mu_aquila_move(uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_obj_log *);
/* Types 136..140 and 142 read 0x0129fd4f(6), bone 6 as a column-major 4x4: +0x188 x/y = matrix[12], matrix[13].
 * Without a matrix (no pose) the write is skipped; mu_aquila_bone_type tells the host to count that refusal. */
int mu_aquila_visual(uint8_t *, int has_model, const float *bone6);
int mu_aquila_bone_type(int32_t type);
/* Boss Battle (139) create/move/visual and world 115's create/move (the BaseMap defaults 0x00d5cb99/0x00d5cc16):
 * each returns false and requests nothing. */
int mu_boss_battle_create(const uint8_t *, int32_t world);
int mu_boss_battle_move(const uint8_t *, int32_t world);
int mu_boss_battle_visual(const uint8_t *, int32_t world);
int mu_world115_create(const uint8_t *, int32_t world);
int mu_world115_move(const uint8_t *, int32_t world);
/* Debenter (predicate 0x00dbd14d: worlds 95 and 96), on the RENDER-WORLDS-Q inputs. Create switches on OBJECT
 * +0x60 (not the type): 9 poses the type's model at creation (MU_DEBENTER_POSE: model +0x78 = the position, then
 * Animation(bones, frame, prior frame, prior action, angle, head angle, 0, 0)), stores bones 23 and 22 in +0x188
 * and +0x194 and creates joints 0x7fd6 subtypes 0x3c/0x3d (scale 40); 56..67 hide the object. Returns -1 for key 9
 * without a bone callback. Move returns -1 for types 9/11 without an action record (the original faults); the
 * visual returns -1 for bone types without a bone callback (mu_debenter_visual_bones: the highest bone used). */
#define MU_DEBENTER_POSE 0x00dbd399u
int mu_debenter_create(uint8_t *, int32_t index, const mu_q_inputs *, mu_obj_log *);
int mu_debenter_move(uint8_t *, int32_t index, const mu_q_inputs *, mu_obj_log *);
int mu_debenter_visual(uint8_t *, int32_t index, const mu_q_inputs *, mu_obj_log *);
int mu_debenter_visual_bones(int32_t type);
#endif
