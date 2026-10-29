/* RENDER-WORLDS-R2. Twisted Karutan (142), Kardamahal (143) and Swamp of Destruction (144) primary methods. */
#ifndef MU_WORLDS_R2_H
#define MU_WORLDS_R2_H
#include "object_render.h"
#include "login_world.h"
/* CreateEffect 0x013c0eaa(type, position, angle, light, sub, owner, -1, 0, word4, 0, 0.0, -1, 0, 0) with the
 * info word4 = (uint16_t)(int)scale: args type, position, angle, light, sub, owner (1 = the object), word4. */
#define MU_R2_EFFECT 0x00e68c23u
/* Kardamahal type 115: Animation(model, 0x06fce398, frame, prior frame, prior action, angle, head angle, 0, 1),
 * then for each name mu_kardamahal_bone_name(0..7) found by 0x0129f18a(name, 1) a zero-local TransformPosition
 * and AddTerrainLight at its x/y: args r, g, b, range. Logged only when the type has a model. */
#define MU_KARDAMAHAL_BONE_LIGHTS 0x00e0f0d9u
int mu_twisted_karutan_create(uint8_t *, int32_t world);
int mu_twisted_karutan_move(uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_obj_log *);
/* The object is written (types 115/118 HiddenMesh). Type 72 needs bones 11 and 7: without `bone` it requests
 * nothing and the host counts the refusal. */
int mu_twisted_karutan_visual(uint8_t *, int32_t index, int has_model, float time, mu_obj_rand_fn,
                              mu_login_bone_fn, void *, mu_obj_log *);
int mu_kardamahal_create(uint8_t *, int32_t world);
int mu_kardamahal_move(uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_obj_log *);
int mu_kardamahal_visual(const uint8_t *, int32_t index, int has_model, mu_obj_rand_fn, void *, mu_obj_log *);
const char *mu_kardamahal_bone_name(int32_t k);
int mu_swamp_create(uint8_t *, int32_t world);
int mu_swamp_move(uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_obj_log *);
/* The object's light (+0xec) is written before each joint. */
int mu_swamp_visual(uint8_t *, int32_t index, int has_model, mu_obj_rand_fn, void *, mu_obj_log *);
#endif
