/* RENDER-WORLDS-S2. Nars (110) and the Arca War class (92, 96, 101, 111) primary methods. */
#ifndef MU_WORLDS_S2_H
#define MU_WORLDS_S2_H
#include "object_render.h"
#include "world_visual.h"
#include "worlds_q.h"
/* Nars, worlds 110 and 111 (predicate 0x00e2602d), on the RENDER-WORLDS-Q inputs: create 0x00e260f0, move
 * 0x00e26668, visual 0x00e26ae7. No slot tests the object (or the visual its model) for null.
 * Create type 134 poses its model at creation (MU_NARS_POSE: model +0x78 = the position, +0x74 = the scale, then
 * Animation(bones, frame, prior frame, prior action, angle, head angle, 0, 1)) and stores bone 4 in +0x110; it
 * returns -1 without a bone callback. Move types 1/2 test their action record. The visual returns -1 for bone
 * types without a bone callback (mu_nars_visual_bones: the highest bone used). Its 0x413 effects use MU_R2_EFFECT
 * (owner 0, word4 = (uint16_t)(int)k) and type 26 writes the object light. */
#define MU_NARS_POSE 0x00e264a1u
int mu_nars_create(uint8_t *, int32_t index, const mu_q_inputs *, mu_obj_log *);
int mu_nars_move(uint8_t *, int32_t index, const mu_q_inputs *, mu_obj_log *);
int mu_nars_visual(uint8_t *, int32_t index, const mu_q_inputs *, mu_obj_log *);
int mu_nars_visual_bones(int32_t type);
/* Arca War class 0x01aa6154 (worlds 92, 96, 101, 111). The class list predicate 0x00d806b0; the base world
 * (handler +0x1c) is set on world entry by slot +0x20 0x00d7b65c through 0x00d7b225: world - 1 for a listed
 * world, else -1 (Acheron, Debenter, Uruk Mountain, Nars). Create 0x00d7bd7d, move 0x00d7be29 and visual
 * 0x00d7be80 forward to the base world's class slot (0x2c, 0x30, 0x34) through the class registry 0x00ea594b/
 * 0x00ea4679; mu_arca_forward_fn runs it and returns its AL (or -1 when the host refuses it). The world value
 * stays the Arca world, so each base class runs its own predicate on it.
 * The class's own types: 0x88a..0x88e (0x00d7b373 of the world-92 class: 1..5) and 0x59b. Create gives them
 * scale 0.85; the visual draws nothing for 0x88a..0x88e and, for 0x59b, CreateEffect 0x413 at bone 3 with the
 * light of stage `stage` (handler +0x30) and subtype 10 (stage < 4) or 11 (MU_OBJ_CALL_EFFECT: type, position,
 * angle, light, sub, 0, scale). The stage is server state (0x00d7ac66/0x00d7af0d, not ported): an input whose
 * initial value is 0 (constructor 0x00d7a185); the visual returns -1 for a stage outside 0..5 (the client's light
 * table has six entries) and for 0x59b without a bone callback. */
#define MU_ARCA_STAGES 6
#define MU_ARCA_CREATE_SLOT 0x2c
#define MU_ARCA_MOVE_SLOT 0x30
#define MU_ARCA_VISUAL_SLOT 0x34
typedef int (*mu_arca_forward_fn)(void *context, int32_t slot, int32_t base_world);
int mu_arca_world(int32_t world);
int32_t mu_arca_base_world(int32_t world);
int32_t mu_arca_type_index(int32_t type);
int mu_arca_create(uint8_t *, int32_t world, int32_t base_world, mu_arca_forward_fn, void *);
int mu_arca_move(int32_t world, int32_t base_world, mu_arca_forward_fn, void *);   /* reads no object field */
int mu_arca_visual(const uint8_t *, int32_t index, int32_t world, int32_t base_world, int32_t stage, mu_world_bone_fn,
                   void *bone_context, mu_arca_forward_fn, void *, mu_obj_log *);
/* 3 (bone 3) for type 0x59b, -1 otherwise: the base class's visual decides its own bones. */
int mu_arca_visual_bones(int32_t type);
#endif
