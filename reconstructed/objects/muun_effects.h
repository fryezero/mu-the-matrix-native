#ifndef MU_MUUN_EFFECTS_H
#define MU_MUUN_EFFECTS_H

#include <stdint.h>

/* The Muun (pet) effect table and its consumers (RENDER-EFFECTS-018,
 * docs/research/client-render-effects-018.md).
 *
 * MuunEffectInfo (0x06fbb46c) keeps at +0x38 a std::multimap from a Muun's render-info id to an entry laid out like
 * the map-object table's (RENDER-EFFECTS-008): node +0x10 the key, +0x14 the path std::string, +0x2c position,
 * +0x38 rotation, +0x44 scale, +0x48 bone, +0x4c follow byte (offsets below are from the value, node +0x10).
 *
 * A Muun slot (MainMuun/SubMuun/HeroMuun, NATIVE-HELPERS-002) holds +0x04 its owning CHARACTER, +0x08 the Muun
 * OBJECT, +0x0c its render-info record (the key is the record's first int32), +0x10 a byte and +0x1c a key the
 * owner must match. 0x009af699 (called by the slot's setup 0x009a9992 and the manager's refresh 0x009ba824, after
 * the clear 0x009af6f6) attaches the table's entries for the key to the OBJECT with 0x0114203d; 0x009af6f6 clears
 * the OBJECT's effect list +0x3d0 (0x009b0451). The OBJECT's per-frame update 0x0129f671 then moves each attached
 * record with the OBJECT: timed records expire, every effect takes template scale x OBJECT scale, and an external
 * matrix from the record's bone and follow flag.
 *
 * The calls are the ops below, in the client's order; scripts/validate_render_effects18.py compares them with the
 * client's instructions run in Unicorn. */

typedef struct mu_muun_effect_entry {
    int32_t code;                     /* the multimap key (node +0x10) */
    const char *path;                 /* +0x04 std::string, "Data\\Effect\\<name>.ein" */
    float position[3];                /* +0x1c */
    float rotation[3];                /* +0x28 */
    float scale;                      /* +0x34 */
    int32_t bone;                     /* +0x38 */
    uint8_t follow;                   /* +0x3c */
} mu_muun_effect_entry;

/* The multimap in order: ascending code (signed), equal codes in insertion order. */
typedef struct mu_muun_effect_table {
    const mu_muun_effect_entry *entries;
    int32_t count;
} mu_muun_effect_table;

typedef struct mu_muun_effect_ops {
    void *context;
    /* 0x00a797a0(path, position, rotation, scale, template transform 0, &type word 0, tint 0, no actions, start
     * frame 0.0) then 0x00a78918: a handle >= 0 when the factory's effect is valid, -1 for a null effect */
    int32_t (*create)(void *context, int32_t object, const mu_muun_effect_entry *entry);
    void (*attach)(void *context, int32_t object, int32_t handle, int32_t bone, int follow, int timed,
                   float lifetime);                                     /* 0x0129f9c6 */
    void (*release)(void *context, int32_t handle);                     /* 0x00965b01 (handle -1: null) */
    void (*clear)(void *context, int32_t object);                       /* 0x009b0451 */
} mu_muun_effect_ops;

/* 0x0114203d(object, &code) on MuunEffectInfo: equal_range(code) (0x00aed702), each entry in order. Returns the
 * number of entries it asked the factory for. */
int32_t mu_muun_effects_attach(const mu_muun_effect_table *table, int32_t object, int32_t code,
                               const mu_muun_effect_ops *ops);

typedef struct mu_muun_slot {
    int32_t has_owner;                /* +0x04 != 0 */
    int32_t owner_key;                /* the owner's +0x3244 (0x009a1b49) */
    int32_t object;                   /* +0x08: the OBJECT, -1 for null */
    int32_t has_info;                 /* +0x0c != 0 */
    int32_t code;                     /* [+0x0c]: the render-info id */
    uint8_t active;                   /* +0x10 */
    int32_t key;                      /* +0x1c */
} mu_muun_slot;

/* 0x009af699: with an OBJECT, an owner and a record, the byte +0x10 set and +0x1c equal to the owner's +0x3244,
 * 0x0114203d(OBJECT, the record's id). Returns 1 when it attached. */
int mu_muun_slot_attach(const mu_muun_slot *slot, const mu_muun_effect_table *table, const mu_muun_effect_ops *ops);
/* 0x009af6f6: with an OBJECT and an owner, 0x009b0451(OBJECT). Returns 1 when it cleared. */
int mu_muun_slot_clear(const mu_muun_slot *slot, const mu_muun_effect_ops *ops);

/* One record of an OBJECT's effect list +0x3d0 (0x0129f9c6). */
typedef struct mu_object_effect_record {
    int32_t handle;                   /* +0x00 the effect */
    float template_scale;             /* +0x08 the effect's scale at attach */
    int32_t bone;                     /* +0x0c */
    uint8_t follow, timed;            /* +0x10, +0x11 */
    float lifetime;                   /* +0x14 */
} mu_object_effect_record;

/* The OBJECT state 0x0129f671 and its bone helpers read. */
typedef struct mu_effect_object {
    float position[3];                /* +0x158 */
    float angle[3];                   /* +0x164 (bone -1's world matrix 0x0129faee) */
    float scale;                      /* +0xa0 */
    int32_t in_sector;                /* 0x012a0d29: +0x350 or +0x354 not 0 (a map object in a sector list) */
    const float *bones;               /* +0x318: the OBJECT's own 3x4 bone transforms, NULL when 0 */
    int32_t model_bones;              /* the model's bone count (int16 +0x22 of GetModel(+0x5c)); -1: no model */
    const float *shared;              /* 0x06fce398: the shared pose buffer, 3x4 per bone */
} mu_effect_object;

typedef struct mu_object_effect_ops {
    void *context;
    void (*expire)(void *context, int32_t handle);                       /* 0x012a1417 erases the record */
    void (*scale)(void *context, int32_t handle, float scale);           /* 0x012a0d5c: effect +0x50 */
    void (*update)(void *context, int32_t handle, float dt, const float matrix[16]);   /* 0x00a75708 */
} mu_object_effect_ops;

/* 0x0129fd4f(bone): the bone's 3x4 transposed into a column-major 4x4; outside a sector list it is placed by
 * 0x00cf2679(position, (0, 0, 0), scale) x bone (0x00cf0db8). */
void mu_object_bone_matrix(float out[16], const mu_effect_object *o, int32_t bone);
/* 0x012a0030(bone): the bone's translation, plus the position outside a sector list. */
void mu_object_bone_position(float out[3], const mu_effect_object *o, int32_t bone);
/* The external matrix 0x0129f671 hands a record's node update. Returns 0 for a following record with a bone
 * below -1: the client leaves its matrix uninitialised (0x00a7497a constructs nothing). */
int mu_object_effect_matrix(float out[16], const mu_object_effect_record *record, const mu_effect_object *o);
/* 0x0129f671(dt) over the list in order; expired records leave it (the rest keep their order). Returns the new
 * count. A following record with a bone below -1 is skipped after its scale (undefined in the client). */
int32_t mu_object_effects_update(mu_object_effect_record *records, int32_t count, const mu_effect_object *o, float dt,
                                 const mu_object_effect_ops *ops);

#endif
