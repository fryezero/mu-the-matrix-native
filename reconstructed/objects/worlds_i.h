/* RENDER-WORLDS-I. World 79 and world 100 primary methods. */
#ifndef MU_WORLDS_I_H
#define MU_WORLDS_I_H
#include "object_render.h"
#include "login_world.h"
/* Deferred Animation/TransformPosition/AddTerrainLight service. args: bone,
 * RGB, range. The host poses the current object after its preceding tick. */
#define MU_MARKET_BONE_LIGHT 0xe6c29du
int mu_market_create(uint8_t *, int32_t, mu_obj_log *);
int mu_market_move(uint8_t *, int32_t, const mu_obj_move_inputs *, mu_obj_log *);
int mu_market_visual(const uint8_t *, int32_t, int32_t world, float time,
                     mu_obj_rand_fn, mu_login_bone_fn, void *, mu_obj_log *);
int mu_uruk_create(uint8_t *, int32_t world);
int mu_uruk_move(uint8_t *, int32_t, const mu_obj_move_inputs *, mu_obj_log *);
/* Requests whose additional original arguments have no native consumer yet.
 * They remain explicit rejected commands rather than losing key/color fields. */
#define MU_URUK_KEYED_EFFECT 0xe701e5u
#define MU_URUK_COLORED_JOINT 0xe70274u
int mu_uruk_visual(uint8_t *, int32_t, int32_t world, int32_t weather, float time,
                   mu_obj_rand_fn, void *, mu_obj_log *);
#endif
