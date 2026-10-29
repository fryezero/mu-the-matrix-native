/* RENDER-WORLDS-R. Scorched Canyon (131), Red Smoke Icarus (132), Temple of Arnil (133) and Gray Aida (134)
 * primary methods (create slot 0x2c, move 0x30, visual 0x34). */
#ifndef MU_WORLDS_R_H
#define MU_WORLDS_R_H
#include "object_render.h"
#include "world_visual.h"
/* Create: world = 0x01cf15fc; false for another world or a null object. */
int mu_scorched_canyon_create(uint8_t *, int32_t world, mu_obj_rand_fn, void *);
int mu_red_smoke_icarus_create(uint8_t *, int32_t world);
int mu_temple_arnil_create(uint8_t *, int32_t world);
int mu_gray_aida_create(uint8_t *, int32_t world);
/* Move: has_model = the type's model exists (0x00eaa8cf); 131..133 return false without one. */
int mu_scorched_canyon_move(uint8_t *, int32_t index, int32_t world, int has_model, mu_obj_rand_fn, void *,
                            mu_obj_log *);
int mu_red_smoke_icarus_move(const uint8_t *, int32_t world, int has_model);
int mu_temple_arnil_move(const uint8_t *, int32_t world, int has_model);
int mu_gray_aida_move(uint8_t *, int32_t index, int32_t world, mu_obj_rand_fn, void *, mu_obj_log *);
/* Visual: present = the slot's model argument; no world test. bone NULL: no current pose (the bone cases
 * then make no request; the host counts the refusal). */
int mu_scorched_canyon_visual(const uint8_t *, int present);
int mu_red_smoke_icarus_visual(uint8_t *, int32_t index, int present, mu_world_bone_fn bone, void *,
                               mu_obj_log *);
int mu_temple_arnil_visual(const uint8_t *, int present);
int mu_gray_aida_visual(uint8_t *, int32_t index, int present, float time, mu_obj_rand_fn, mu_world_bone_fn bone,
                        void *, mu_obj_log *);
/* Gray Aida requests without a native consumer. The model's StreamMesh byte +0x94 is 0 around the RenderMesh
 * 0x00966e4a of types 0x41/0x42/0x84/0x85/0x4d/0x4e and 0xff after it (one event each, value in args[0]).
 * Type 0x46's CreateEffect 0x199 passes (u16)(int)scale as the eighth argument (args: type, position, angle,
 * light, subtype, owner, that value). */
/* mu_obj_create defers the Scorched Canyon create (it draws from the RNG) to the host: MU_WR_CREATE (). */
#define MU_WR_CREATE 0x00e432d9u
#define MU_WR_STREAM 0x00d85c26u
#define MU_WR_EFFECT_SCALED 0x00d85e29u
#endif
