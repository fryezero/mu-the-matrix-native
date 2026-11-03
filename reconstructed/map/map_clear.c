/* What a numbered teleport clears (PLAY-FIX-001).  See map.h. */
#include "map.h"

/* Planted mistakes for scripts/validate_teleport_clear.py --mutations (0: none). */
#ifndef MU_MAP_CLEAR_MUTATION
#define MU_MAP_CLEAR_MUTATION 0
#endif

int32_t mu_teleport_clears(const mu_teleport *t, int32_t current_world, int32_t out[5])
{
    int32_t n = 0;
    if (t->number == 0)
        return 0;   /* 0x01281749: the same-map branch */
    out[n++] = MU_MAP_CLEAR_ITEMS;
    out[n++] = MU_MAP_CLEAR_CHARACTERS;
    if (MU_MAP_CLEAR_MUTATION != 1)
        out[n++] = MU_MAP_CLEAR_OTHERS;
    if ((int32_t)t->world != current_world) {   /* 0x012817b2 */
        out[n++] = MU_MAP_CLEAR_WORLD_MAP;
        out[n++] = MU_MAP_CLEAR_LOAD;
    }
    return n;
}

int mu_map_plates_hidden(int32_t world)
{
    return (world >= 0x12 && world <= (MU_MAP_CLEAR_MUTATION == 2 ? 0x16 : 0x17)) || world == 0x35 || world == 0x61;
}

static int32_t push(mu_map_clear_event *events, int32_t n, int32_t capacity, int32_t kind, int32_t slot, int32_t index)
{
    if (n < capacity) {
        events[n].kind = kind;
        events[n].slot = slot;
        events[n].index = index;
    }
    return n + 1;
}

int32_t mu_map_clear_characters(mu_map_clear_slot *slots, int32_t count, mu_map_owned *owned, int32_t owned_count,
                                int32_t key, int32_t scene, int32_t world, int32_t hero_key,
                                mu_map_clear_event *events, int32_t capacity)
{
    int32_t n = 0;
    for (int32_t i = 0; i < count; i++) {
        mu_map_clear_slot *c = &slots[i];
        if (c->live && (MU_MAP_CLEAR_MUTATION == 3 ? (int32_t)(uint16_t)c->key : (int32_t)c->key) != key) {
            c->live = 0;
            n = push(events, n, capacity, MU_MAP_CLEAR_KILL, i, 0);
            int hidden = mu_map_plates_hidden(world);
            if (scene == MU_MAP_SCENE_MAIN && !hidden)
                n = push(events, n, capacity, MU_MAP_CLEAR_REMOVE_INFO, i, 0);
            else if (hidden && (MU_MAP_CLEAR_MUTATION == 4 || c->key == (int16_t)hero_key))
                n = push(events, n, capacity, MU_MAP_CLEAR_REMOVE_INFO, i, 0);
            n = push(events, n, capacity, MU_MAP_CLEAR_RELEASE, i, 0);
            for (int32_t j = 0; j < owned_count; j++)
                if (owned[j].live && owned[j].owner == i) {
                    owned[j].live = 0;
                    n = push(events, n, capacity, MU_MAP_CLEAR_OWNED, i, j);
                }
            n = push(events, n, capacity, MU_MAP_CLEAR_DETACH, i, 0);
        }
        if (MU_MAP_CLEAR_MUTATION != 5 || c->live)
            n = push(events, n, capacity, MU_MAP_CLEAR_RESET, i, 0);
    }
    return n < capacity ? n : capacity;
}

int mu_map_clear_items(int handler, int list_a_empty, int list_b_empty, uint8_t *item_live, int32_t count)
{
    int invoked = handler && !(list_a_empty && (MU_MAP_CLEAR_MUTATION == 6 || list_b_empty));
    for (int32_t i = 0; i < count; i++)
        item_live[i] = 0;
    return invoked;
}
