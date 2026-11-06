/* RENDER-WORLDS-S3. Imperial Guardian (69..72), Event square (114) and Test Area (121) primary methods. */
#ifndef MU_WORLDS_S3_H
#define MU_WORLDS_S3_H
#include "object_render.h"
#include "login_world.h"
#include "worlds_q.h"

/* Imperial Guardian (Varka), four classes with one body each (cls 69, 70, 71 or 72 selects the class's variant;
 * world is [0x01cf15fc], which each slot's predicate compares with cls).
 * Create (no predicate, no null test): types 0x73/0x75 set +0x60 = 100; 0x81..0x84 reduce angle z modulo 360 and
 * copy the angle to the head angle and the position to +0x17c; class 72 also gives type 10 +0x60 = rand() % 50.
 * Returns 1 for those types, 0 otherwise. */
#define MU_OBJF_POSITION_COPY 0x17c
int mu_imperial_create(uint8_t *, int32_t cls, mu_obj_rand_fn, void *);
/* Move: the world test, a second alpha step 0x012af883, the alpha and model gates, then the animation tick
 * 0x012b4dd3 with +0xbc scaled per type (logged as MU_OBJ_CALL_TICK; class 72 type 10 first counts +0x60 down and
 * rewinds frame and prior frame), then the post-tick cases. mu_imperial_move_tick is the part up to the tick (1:
 * continue with mu_imperial_move_cases once the tick is applied, 0: the slot returns false); mu_imperial_move is
 * both. frame_lock is the class's static (0x01ec9164 + 4 * (cls - 69), zero at load) that type 20 shares. */
int mu_imperial_move_tick(uint8_t *, int32_t index, int32_t cls, int32_t world, int has_model, mu_obj_log *);
int mu_imperial_move_cases(uint8_t *, int32_t cls, float *frame_lock);
int mu_imperial_move(uint8_t *, int32_t index, int32_t cls, int32_t world, int has_model, float *frame_lock,
                     mu_obj_log *);
/* Visual (predicate world == cls; no null test of object or model). Uses in->world, time, rand_fn, bone and
 * context. Returns -1 for a bone type (mu_imperial_visual_bones: the highest bone it transforms) without a bone
 * callback, else the slot's AL. Joints are MU_ICARUS_JOINT (0x7fd5 subtype 5), the word4 effect MU_R2_EFFECT. */
int mu_imperial_visual(const uint8_t *, int32_t index, int32_t cls, const mu_q_inputs *, mu_obj_log *);
int mu_imperial_visual_bones(int32_t cls, int32_t type);

/* Event square, world 114: create 0x00e1e989 is mu_market_create (byte-identical); move 0x00e1ea5c and visual
 * 0x00e1ef15 are Loren Market's bodies behind the predicate world == 114 (0x00e20416). */
int mu_event_square_move(uint8_t *, int32_t index, const mu_obj_move_inputs *, mu_obj_log *);
int mu_event_square_visual(const uint8_t *, int32_t index, int32_t world, float time, mu_obj_rand_fn,
                           mu_login_bone_fn, void *, mu_obj_log *);

/* Test Area, world 121 (no predicate, no null test of the object). Create: type 0x1a8 true; type 0x1ab three
 * CreateEffect 0x1ab/0x1ac/0x1ad (subtype 1, no owner) at the position + (0, -40/-36/-20, 520), logged as
 * MU_OBJ_CALL_CREATE_EFFECT with the angle/light offsets (object_render.c's create layout). Move: type 22 blend
 * light = sin(time * 0.001) + 1, types 70/80 HiddenMesh -2. Visual: false without a model; types 70/80 one of
 * three particles by rand() % 3, then 0x8086. */
int mu_test_area_create(const uint8_t *, int32_t index, mu_obj_log *);
int mu_test_area_move(uint8_t *, float time);
int mu_test_area_visual(const uint8_t *, int32_t index, int has_model, mu_obj_rand_fn, void *, mu_obj_log *);
#endif
