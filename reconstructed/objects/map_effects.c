/* The map-object effect table's attach routine 0x0183067e (RENDER-EFFECTS-008); see map_effects.h. */
#include "map_effects.h"

/* std::map::find on the ascending keys (0x010fa24c contains / 0x010fa28a at; 0x01849a27 find, signed compare
 * 0x0096ba31) */
const mu_map_effect_world *mu_map_effects_world(const mu_map_effect_table *table, int32_t world)
{
    int32_t lo = 0, hi = table ? table->count : 0;
    while (lo < hi) {
        const int32_t mid = lo + (hi - lo) / 2;
        if (table->worlds[mid].world < world)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo < (table ? table->count : 0) && table->worlds[lo].world == world ? &table->worlds[lo] : NULL;
}

const mu_map_effect_type *mu_map_effects_type(const mu_map_effect_world *world, int32_t type)
{
    int32_t lo = 0, hi = world->count;
    while (lo < hi) {
        const int32_t mid = lo + (hi - lo) / 2;
        if (world->types[mid].type < type)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo < world->count && world->types[lo].type == type ? &world->types[lo] : NULL;
}

void mu_map_effects_attach(const mu_map_effect_table *table, int32_t world, const mu_obj_world *w,
                           const mu_map_effect_ops *ops)
{
    const mu_map_effect_world *types = mu_map_effects_world(table, world);
    if (!types)
        return;
    for (int32_t i = 0; i < 16; ++i)
        for (int32_t j = 0; j < 16; ++j)
            for (int32_t k = w->head[i * 16 + j]; k >= 0; k = w->next[k]) {
                const uint8_t *o = w->objects[k];
                ops->clear(ops->context, k);
                const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
                const mu_map_effect_type *found = mu_map_effects_type(types, type);
                if (!found)
                    continue;
                for (int32_t e = 0; e < found->count; ++e) {
                    const mu_map_effect_entry *entry = &found->entries[e];
                    const int32_t handle = ops->create(ops->context, k, entry, (uint16_t)type);
                    if (handle >= 0)
                        ops->attach(ops->context, k, handle, entry->bone, entry->follow, 0, 0.0f);
                    ops->release(ops->context, handle);
                }
                ops->prime(ops->context, k);
            }
}
