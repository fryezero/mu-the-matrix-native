/* RENDER-WORLDS-P. Old Kethotum (135), Burning Kethotum (136) and Bloody Tarkan (140) primary methods. */
#ifndef MU_WORLDS_P_H
#define MU_WORLDS_P_H
#include "object_render.h"
#include "world_visual.h"
/* The type's model: action count +0x26 and the action table +0x30 (16-byte entries: PlaySpeed +4,
 * key count +8). Create writes the speeds; move reads both. */
typedef struct mu_wp_model {
    int32_t action_count;
    float *speed;
    const int16_t *keys;
} mu_wp_model;
typedef struct mu_wp_move_inputs {
    int32_t world;             /* 0x01cf15fc */
    float hero[3];             /* hero +0x33ac */
    float frame_time;          /* 0x01cf103c */
    mu_wp_model *model;        /* NULL: no model of the type */
    mu_obj_rand_fn rand_fn;
    void *context;
    uint8_t has_effects;       /* 0x00d99e3f: the object's attached-effect container is not empty */
    uint8_t effects_valid;     /* bit k: the k-th effect-manager result is valid (136 type 0xb5) */
} mu_wp_move_inputs;
/* Create slot 0x2c; model NULL when the type has none (types that scale action 1 need a model). */
int mu_old_kethotum_create(uint8_t *, int32_t world, mu_wp_model *, mu_obj_rand_fn, void *);
int mu_burning_kethotum_create(uint8_t *, int32_t world, mu_wp_model *, mu_obj_rand_fn, void *);
int mu_bloody_tarkan_create(uint8_t *, int32_t world);
/* Move slot 0x30, run after the generic animation tick. */
int mu_old_kethotum_move(uint8_t *, int32_t index, const mu_wp_move_inputs *, mu_obj_log *);
int mu_burning_kethotum_move(uint8_t *, int32_t index, const mu_wp_move_inputs *, mu_obj_log *);
int mu_bloody_tarkan_move(uint8_t *, int32_t index, int32_t world, float time, mu_obj_rand_fn, void *, mu_obj_log *);
/* Visual slot 0x34; present = the slot's model argument. All three return false. bone NULL: no current pose. */
int mu_old_kethotum_visual(const uint8_t *, int32_t index, int present, float time, mu_obj_rand_fn,
                           mu_world_bone_fn bone, void *, mu_obj_log *);
int mu_burning_kethotum_visual(const uint8_t *, int32_t index, int present, mu_obj_rand_fn, void *, mu_obj_log *);
int mu_bloody_tarkan_visual(const uint8_t *, int present);
/* 0x016caeae: AddTerrainLight with every channel clamped to 0..1. */
void mu_bloody_tarkan_add_light_clamped(float x, float y, const float light[3], int32_t range, float *buffer);
/* Requests without a native consumer. Effect: CreateEffect 0x00a797a0(name k, (0,0,-20), (0,0,0),
 * life, 0, 0, 0, 0.0); attach 0x0129f9c6(effect k, 0x14, 1, 0, 0.0) when all four are valid. */
#define MU_WP_EIN_EFFECT 0x00a797a0u
#define MU_WP_EIN_ATTACH 0x0129f9c6u
#define MU_WP_CLAMPED_LIGHT 0x016caeaeu   /* (x, y, rgb, range) */
/* mu_obj_create/mu_obj_move defer worlds 135/136 to the host, which owns the model action table, the RNG,
 * the frame time and the order after the animation tick: create (world), move (). */
#define MU_WP_CREATE 0x00e3a4dcu
#define MU_WP_MOVE 0x00e3a719u
#endif
