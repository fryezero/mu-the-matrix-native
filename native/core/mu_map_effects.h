#ifndef MU_MAP_EFFECTS_NATIVE_H
#define MU_MAP_EFFECTS_NATIVE_H

#include <stdint.h>

#include "../../reconstructed/objects/map_effects.h"

struct mu_objects;
struct mu_world_particles;

/* RENDER-EFFECTS-008: the map-object effect table (EnchantEffect +0x5c, 0x06fbb7b0) and its attach 0x0183067e
 * in the native world (docs/research/client-render-effects-008.md).
 *
 * The table is the client's decoded game data: scripts/live_effect_table_to_plain.py writes it from a langread
 * snapshot as mapeffects.tsv in the local lang directory (MU_LANG_DIR); it is never committed. Without the file
 * the native world attaches nothing, as before. */

typedef struct mu_map_effects {
    mu_map_effect_table table;
    mu_map_effect_world *worlds;
    mu_map_effect_type *types;
    mu_map_effect_entry *entries;
    int32_t *actions;
    char *paths;
    int32_t world_count, type_count, entry_count;
} mu_map_effects;

typedef struct mu_map_effects_stats {
    long cleared, requested, invalid, attached, primed;
} mu_map_effects_stats;

/* <dir>/mapeffects.tsv. NULL when the directory is NULL or holds no readable table. */
mu_map_effects *mu_map_effects_load(const char *dir);
/* The directory named by MU_LANG_DIR. */
mu_map_effects *mu_map_effects_load_default(void);
void mu_map_effects_free(mu_map_effects *table);

/* 0x0183067e for the objects of world (the world loaders run it after the map objects exist): the objects'
 * effect lists are cleared and the table's entries created through the particle module's EffectManager scene
 * and attached (the RENDER-EFFECTS-006 records, updated each frame after RenderObjectVisual). 0x0129f4cb's
 * first update (dt 0) is left to that first per-frame update, which runs before the first draw. */
void mu_map_effects_attach_world(const mu_map_effects *table, int32_t world, struct mu_objects *objects,
                                 struct mu_world_particles *particles, mu_map_effects_stats *stats);

#endif
