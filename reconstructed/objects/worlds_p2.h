/* RENDER-WORLDS-P2. Kanturu Underground (137) and Ignis Volcano (138) primary methods. */
#ifndef MU_WORLDS_P2_H
#define MU_WORLDS_P2_H
#include "object_render.h"
#include "login_world.h"
/* Action table of the object's model (0x00966cc4 -> 0x00eaa8cf). Returns 0 when the type has no model;
 * otherwise the action count (model +0x26), and the key count (+8) and PlaySpeed (+4) of `action`. */
typedef int (*mu_kanturu_ug_action_fn)(void *context, int32_t type, int32_t action, int32_t *count,
                                       int16_t *keys, float *speed);
/* PlaySpeed event argument 1: every action of the type's model (create's loop over model +0x26). */
#define MU_OBJ_PLAY_SPEED_ALL 0xffffffffu
/* Deferred action-machine step of types 125-127 (move without an action table): args none. The host runs
 * mu_kanturu_ug_move again with the table after the generic animation tick, which the client runs first. */
#define MU_KANTURU_UG_ACTION_STEP 0xe0913cu
int mu_kanturu_ug_create(uint8_t *, int32_t index, int32_t world, mu_obj_rand_fn, void *, mu_obj_log *);
int mu_kanturu_ug_move(uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_kanturu_ug_action_fn,
                       float frame_time, mu_obj_log *);
int mu_kanturu_ug_visual(const uint8_t *, int32_t index, int has_model, float time, mu_obj_rand_fn,
                         mu_login_bone_fn, void *, mu_obj_log *);
/* model_actions: the model's action count, < 0 without a model. Types 79 and 148 log the model's
 * StreamMesh byte (+0x94) = 0 as MU_OBJ_CALL_MODEL_STREAM. */
int mu_ignis_create(uint8_t *, int32_t index, int32_t world, int32_t model_actions, mu_obj_log *);
int mu_ignis_move(uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_obj_log *);
/* 0x00e07081: returns false and requests nothing. */
int mu_ignis_visual(const uint8_t *, int32_t index);
#endif
