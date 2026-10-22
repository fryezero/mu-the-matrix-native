/* Gates and the teleport answer (NATIVE-MAP-001).  See map.h. */
#include "map.h"

#include <string.h>

/* Planted mistakes for scripts/validate_map.py --mutations (0: none). */
#ifndef MU_MAP_MUTATION
#define MU_MAP_MUTATION 0
#endif

int mu_gate_contains(const mu_gate *g, int32_t x, int32_t y)
{
    return g->x1 <= x && (MU_MAP_MUTATION == 10 ? x < g->x2 : x <= g->x2) && g->y1 <= y && y <= g->y2;
}

/* 0x016a4608 after its early exits: the gates in key order (the map's iterator). */
void mu_gate_check(const mu_gate *gates, int n, mu_gate_lookup_fn lookup, void *user, const mu_gate_hero *hero,
                   mu_gate_result *out)
{
    memset(out, 0, sizeof *out);
    out->gate = out->target = -1;
    out->loading_world = hero->loading_world;
    if (hero->busy || hero->loading_world != 0)
        return;
    if ((hero->world >= 0x62 && hero->world <= 0x63) || (hero->world >= 0x2d && hero->world <= 0x32))
        return;   /* the event worlds (Doppelganger, Imperial Guardian) keep their own gates */
    int throttle = hero->throttle;
    for (int i = 0; i < n; i++) {
        const mu_gate *g = &gates[i];
        if (g->flag != 1 || g->world != hero->world || !mu_gate_contains(g, hero->tile_x, hero->tile_y))
            continue;
        static const mu_gate none;
        const mu_gate *t = lookup ? lookup(user, g->target) : NULL;
        if (!t)
            t = &none;
        out->gate = g->index;
        out->target = g->target;
        if (hero->level < g->min_level) {
            out->refused = 1;
            out->loading_world = 50;
            return;
        }
        int32_t h = hero->helper_type;
        if (t->world == 10 || t->world == 0x84) {   /* Icarus: wings, a flying helper or the +0x3230 state */
            if (!hero->wings_kind6 && h != 0x1a02 && h != 0x1a03 && !hero->helper_flies && h != 0x1a25 &&
                hero->hero_3230 <= 0) {
                out->refused = 2;
                out->loading_world = 50;
                return;
            }
        } else if (t->world == 0x7a && t->index == 0x24e) {   /* a quest-gated gate (opens a window), static */
            out->refused = 3;
            out->loading_world = 50;
            return;
        } else if (t->world == 0x72) {
            out->loading_world = 50;   /* the party leader notice path, then the request (static) */
        }
        if (throttle)
            return;
        /* the request: C1 00 1C 00, gate (word), 0, 0; the builder XORs bytes 3..7 and sends it with the C3 flag */
        const uint8_t p[8] = {0xc1, 0, 0x1c, 0, (uint8_t)g->index, (uint8_t)(g->index >> 8), 0, 0};
        memcpy(out->packet, p, sizeof p);
        out->packet_length = 8;
        out->loading_world = 9999999;
        if (t->world == 0x1e || t->world == 0x1f || hero->world == 0x1e || hero->world == 0x1f)
            out->helper_stop = 1;
        throttle = 1;   /* the loop goes on; the 3 s throttle now stops a second request */
    }
}

int mu_teleport_parse(const uint8_t *p, size_t length, mu_teleport *out)
{
    memset(out, 0, sizeof *out);
    if (length < 11)
        return 0;
    out->number = (uint16_t)(p[4] | p[5] << 8);
    out->world = (uint16_t)(p[6] | p[7] << 8);
    out->x = p[8];
    out->y = p[9];
    out->dir = p[10];
    return 1;
}

void mu_teleport_position(const mu_teleport *t, float out[2])
{
    out[0] = ((float)t->x + (MU_MAP_MUTATION == 11 ? 0.0f : 0.5f)) * 100.0f;
    out[1] = ((float)t->y + 0.5f) * 100.0f;
}

float mu_teleport_angle(const mu_teleport *t)
{
    return ((float)t->dir - (MU_MAP_MUTATION == 12 ? 0.0f : 1.0f)) * 45.0f;
}

int mu_teleport_changes_world(const mu_teleport *t, int32_t current_world)
{
    return (MU_MAP_MUTATION == 13 || t->number != 0) && (int32_t)t->world != current_world;
}
