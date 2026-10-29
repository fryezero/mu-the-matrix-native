/* RENDER-WORLDS-Q. Primary methods of Acheron (91/92), Ferea (112), Swamp of Darkness (122) and
 * Kubera Mine (123..127): create (slot 0x2c), move (0x30) and, except Ferea, visual (0x34). */
#ifndef MU_WORLDS_Q_H
#define MU_WORLDS_Q_H
#include "object_render.h"
#include "world_visual.h"

/* Requests these methods make that have no native consumer; logged, refused and counted by the runtime. */
#define MU_Q_KEYED_EFFECT 0x013c0eabu   /* CreateEffect(type, position, angle, light, sub, object, -1, 0, key,
                                         * 0, 0.0, -1, 0, 0): args type, position, angle, light, sub, key */
#define MU_Q_STOP_SOUND 0x00a6ad76u     /* StopBuffer(id, 1): args id, 1 */

/* A type's model action table in client layout (0x00966cc4 -> 0x00eaa8cf: model +0x30, count model +0x26):
 * 16-byte records, +4 PlaySpeed (f32), +8 key count (i16), +0xa loop byte. Returns NULL when the type has
 * no model. */
typedef uint8_t *(*mu_q_actions_fn)(void *context, int32_t type, int32_t *count);

/* Handler members the methods read or write. */
typedef struct mu_q_handler {
    int32_t ferea_state;        /* Ferea +0x48: constructor 0, stepped by slot 0x28 0x00de5b82 (not ported) */
    uint8_t *ferea_object;      /* Ferea +0x50: the type-39 object */
    uint8_t swamp_variant;      /* Swamp of Darkness +0x78: constructor 1 */
    uint8_t *kubera_object;     /* Kubera +0x14: the type-158 object */
} mu_q_handler;

typedef struct mu_q_inputs {
    int32_t world;              /* 0x01cf15fc */
    float time;                 /* WorldTime 0x06fce370 */
    float frame_time;           /* 0x01cf103c */
    uint32_t now_ms;            /* timeGetTime */
    float hero[3];              /* hero +0x33ac */
    int32_t hero_tile[2];       /* hero +0x180, +0x184 */
    mu_q_actions_fn actions;
    mu_obj_rand_fn rand_fn;
    mu_world_bone_fn bone;      /* BMD::TransformPosition(bone matrix k, local, out) 0x012b6ef1 */
    void *context;
    mu_q_handler *handler;
    /* RENDER-WORLDS-Q2: the index of the posed model's bone named `name` (0x0129f18a's search), -1 when none. */
    int32_t (*bone_index)(void *context, const char *name);
} mu_q_inputs;

/* Acheron, worlds 91/92 (predicate 0x00d6a614): create 0x00d6a6d7, move 0x00d6a7aa, visual 0x00d6ae34. */
int mu_acheron_create(uint8_t *o, const mu_q_inputs *in);
int mu_acheron_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log);
int mu_acheron_visual(const uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log);
/* The highest bone the visual of `type` transforms (the model must be posed with more bones), -1 for none. */
int mu_acheron_visual_bones(int32_t type);
/* Ferea, world 112 (no world test): create 0x00de5cb0, move 0x00de5de2, visual 0x00de6405 (RENDER-WORLDS-Q2;
 * -1 when a bone it names is missing, where the client would fault). */
int mu_ferea_create(uint8_t *o, const mu_q_inputs *in);
int mu_ferea_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log);
int mu_ferea_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log);
/* The NULL-terminated bone names the Ferea visual of `type` looks up, NULL for none. */
const char *const *mu_ferea_visual_bones(int32_t type);
/* Swamp of Darkness, world 122 (0x00e543a1): create 0x00e54429, move 0x00e54646, visual 0x00e5540e. */
int mu_swamp_darkness_create(uint8_t *o, const mu_q_inputs *in);
int mu_swamp_darkness_move(uint8_t *o, const mu_q_inputs *in);
int mu_swamp_darkness_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log);
/* Kubera Mine, worlds 123..127 (0x00e1e4b6): create 0x00e19bb3, move 0x00e19ed0, visual 0x00e1b5fb. */
int mu_kubera_create(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log);
int mu_kubera_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log);
int mu_kubera_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log);

/* Dispatch by world: 1 when one of these classes owns `world`. The visual returns -1 for types it cannot run
 * (Acheron bone types without a bone callback, Ferea types whose bones are missing). */
int mu_worlds_q_owns(int32_t world);
int mu_worlds_q_create(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log);
int mu_worlds_q_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log);
int mu_worlds_q_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log);
#endif
