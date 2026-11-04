#ifndef MU_ACTION_REGISTRY_H
#define MU_ACTION_REGISTRY_H

#include <stdint.h>

#include "object_render.h"

/* RENDER-WORLDS-AFTER5: the object action registry 0x01ec7d5c (docs/research/client-worlds-after5.md).
 *
 * The registry (getter 0x00ce3dad, constructor 0x00ce38a8) holds a std::map at +0x10 from the key
 * 0x0112bbba(type, action) = 1000 * action + type to a 0x20-byte entry, plus two handler vectors filled by its
 * constructor: SetAction handlers at +0x24 (0x00ce4f39) and tick handlers at +0x18 (0x00ce4d20). The entry's
 * +0xc picks the handler in both. The map is the current world's MapObjectAnimationInfo<world+1> table of
 * Data\Lang.mpr (loader 0x0112bc34, per-world table object 0x06fbc434, copied in at world load 0x00ea289c).
 *
 * The world manager's create tail 0x00ea2ad6 calls SetAction(object, 0) after the class create slot 0x2c; its
 * move tail 0x00ea2c2b calls the tick 0x00ce4b5b between the pre-move slot 0x74 and the move slot 0x30. Both run
 * only in worlds that have a factory class. */

typedef struct mu_anim_entry {
    int32_t type, action;     /* +0x0, +0x4 */
    float speed;              /* +0x8: OBJECT +0xbc */
    int32_t handler;          /* +0xc: index into both handler vectors */
    int32_t param;            /* +0x10: hero distance of the tick handlers 5 and 7 */
    int32_t extra_count;      /* +0x14 std::vector<int> */
    const int32_t *extra;
} mu_anim_entry;

/* GetModel 0x00966cc4 / 0x00eaa8cf: 0 when the type has no model. Otherwise *action_count is model +0x26 and,
 * when 0 <= action < *action_count, *keys and *lock are the action record's +8 (int16) and +0xa (byte). */
typedef int (*mu_anim_model_fn)(void *context, int32_t type, int32_t action, int32_t *action_count, int16_t *keys,
                                uint8_t *lock);

typedef struct mu_anim_inputs {
    const mu_anim_entry *entries;   /* the current world's table */
    int32_t count;
    mu_anim_model_fn model;
    mu_obj_rand_fn rand_fn;         /* the client's rand() 0x01989721 */
    void *context;
    float hero[2];                  /* [[0x0a39d754] + 0x33ac] x, y (0x00cfc922) */
} mu_anim_inputs;

enum {
    MU_ANIM_NONE = 0,         /* no model, action out of range, or no entry: only the action switch (if any) */
    MU_ANIM_APPLIED = 1,
    MU_ANIM_UNSUPPORTED = 2   /* tick handlers 4, 6 and 8 (hero box collision 0x018500bf), or malformed extras */
};

/* 1000 * action + type (0x0112bbba; the factor is (int)pow(10, digits of 300)). */
uint32_t mu_anim_key(int32_t type, int32_t action);
/* The entry for (type, action) by key, NULL when none. */
const mu_anim_entry *mu_anim_find(const mu_anim_inputs *in, int32_t type, int32_t action);

/* SetAction 0x00ce4a17 and its handlers 0x00ce1460..0x00ce15de. */
int mu_action_set(uint8_t *object, int32_t action, const mu_anim_inputs *in);
/* The tick 0x00ce4b5b and its handlers 0x00ce1646..0x00ce23ad; *found is the tick's return value (1 when the
 * current action has an entry and the type a model). */
int mu_action_tick(uint8_t *object, const mu_anim_inputs *in, int *found);

/* The worlds the factory 0x00ea488e registers a class for (the tails run only there). */
int mu_anim_class_world(int32_t world);

#endif
