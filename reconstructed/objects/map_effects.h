#ifndef MU_MAP_EFFECTS_H
#define MU_MAP_EFFECTS_H

#include <stdint.h>

#include "object_render.h"

/* The map-object effect table and its attach routine 0x0183067e (RENDER-EFFECTS-008,
 * docs/research/client-render-effects-008.md).
 *
 * The table is EnchantEffect's +0x5c std::map at 0x06fbb7b0: world -> record, the record's +0x3c a std::map from
 * the object's int32 +0x5c to a std::vector of 0x54-byte entries. The world loaders (0x00e21f75, 0x0182876e) call
 * 0x0183067e after the map objects exist. For the current world [0x01cf15fc], when the table holds it, it walks
 * the 256 sector lists (i, j = 0..15, sector i * 16 + j, objects through +0x354) and for every object:
 *   - clears its effect list +0x3d0 (0x009b0451);
 *   - looks its int32 +0x5c up in the world's type map; when found, for each entry in vector order asks the
 *     factory 0x00a797a0(path +4, position +0x1c, rotation +0x28, scale +0x34, template transform 0, the type
 *     word, tint +0x3d, actions +0x48 (a copy), start frame +0x44) and, when the effect is valid (0x00a78918),
 *     attaches it with 0x0129f9c6(effect, bone +0x38, follow +0x3c, timed 0, lifetime 0.0); the factory's
 *     shared pointer is released either way (0x00965b01). After the vector it runs 0x0129f4cb once (the
 *     attached effects' first update with dt 0).
 * A world the table does not hold returns at once: no list is cleared.
 *
 * The calls are the ops below, in the client's order; scripts/validate_map_effects.py compares them with the
 * client's instructions run in Unicorn. */

typedef struct mu_map_effect_entry {
    const char *path;                 /* +0x04 std::string, "Data\\Effect\\<name>.ein" */
    float position[3];                /* +0x1c */
    float rotation[3];                /* +0x28 */
    float scale;                      /* +0x34 */
    int32_t bone;                     /* +0x38 */
    uint8_t follow, tint;             /* +0x3c, +0x3d */
    uint32_t start_bits;              /* +0x44 binary32 start frame */
    const int32_t *actions;           /* +0x48 std::vector<int> */
    int32_t action_count;
} mu_map_effect_entry;

typedef struct mu_map_effect_type {
    int32_t type;                     /* the nested map's key: the object's int32 +0x5c */
    const mu_map_effect_entry *entries;
    int32_t count;
} mu_map_effect_type;

typedef struct mu_map_effect_world {
    int32_t world;                    /* the outer map's key */
    const mu_map_effect_type *types;  /* ascending by type */
    int32_t count;
} mu_map_effect_world;

typedef struct mu_map_effect_table {
    const mu_map_effect_world *worlds;  /* ascending by world */
    int32_t count;
} mu_map_effect_table;

typedef struct mu_map_effect_ops {
    void *context;
    void (*clear)(void *context, int32_t object);                       /* 0x009b0451 */
    /* 0x00a797a0 then 0x00a78918: a handle >= 0 when the factory's effect is valid, -1 for a null effect */
    int32_t (*create)(void *context, int32_t object, const mu_map_effect_entry *entry, uint16_t type_word);
    void (*attach)(void *context, int32_t object, int32_t handle, int32_t bone, int follow, int timed,
                   float lifetime);                                     /* 0x0129f9c6 */
    void (*release)(void *context, int32_t handle);                     /* 0x00965b01 (handle -1: null) */
    void (*prime)(void *context, int32_t object);                       /* 0x0129f4cb */
} mu_map_effect_ops;

const mu_map_effect_world *mu_map_effects_world(const mu_map_effect_table *table, int32_t world);
const mu_map_effect_type *mu_map_effects_type(const mu_map_effect_world *world, int32_t type);

/* 0x0183067e for world (the value of [0x01cf15fc]) over the sector lists of w. */
void mu_map_effects_attach(const mu_map_effect_table *table, int32_t world, const mu_obj_world *w,
                           const mu_map_effect_ops *ops);

/* RENDER-EFFECTS-019 (docs/research/client-render-effects-019.md §1): the per-frame update 0x0129f671 of a map
 * object's attached records (RenderObjects 0x016d51f5 / 0x016d536b, after RenderObjectVisual).
 *
 * 0x012a0d29: the OBJECT is "in a sector list" when +0x350 (previous) or +0x354 (next) is set. CreateObject appends
 * every map object to its sector's list, so the predicate fails exactly for an object alone in its sector (live: the
 * links are both 0 for 76 of 149,735 objects of the 32 DATA-ACQ-002 captures, each the only object of its sector). */
int mu_map_effects_in_sector(const mu_obj_world *w, int32_t object);

enum { MU_MAP_EFFECT_UNDEFINED = -1, MU_MAP_EFFECT_UNPOSED = 0, MU_MAP_EFFECT_OK = 1 };

/* The external matrix 0x0129f671 hands a record's node update (muun_effects.h's mu_object_effect_matrix) for a map
 * object: the OBJECT image's scale +0xa0, position +0x158 and angle +0x164; +0x318 is 0 for map objects, so every
 * bone comes from the shared pose buffer 0x06fce398, which RenderObject has just filled with this object's pose
 * (pose: 3x4 rows per bone, pose_bones of them). Following bone b >= 0 is 0x0129fd4f (the bone, placed by the
 * position and scale only outside a sector list); not following, bone b >= 0 is the scale's diagonal with
 * 0x012a0030's translation: the bone's, plus the position outside a sector list; bone -1 uses the OBJECT's world
 * matrix (following) or position (not following); not following, a bone below -1 has no translation.
 * MU_MAP_EFFECT_UNPOSED: a bone >= 0 without that pose (NULL or bone >= pose_bones: the client would read another
 * object's or a stale pose); MU_MAP_EFFECT_UNDEFINED: following a bone below -1 (left uninitialised). */
int mu_map_effect_matrix(float out[16], const uint8_t *object, int in_sector, const float *pose, int32_t pose_bones,
                         int32_t bone, int follow);

#endif
