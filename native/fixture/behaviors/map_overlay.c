/* Synthetic portal/NPC policy, transported through the recorded E7 routes. */
#include "../../core/mu_lang.h"
#include "../behavior.h"
#include "../map_overlay_demo.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MAX_MARKERS 128
typedef struct marker {
    uint8_t bytes[75];
    size_t length;
} marker;
typedef struct overlay_fixture {
    marker markers[MAX_MARKERS];
    int count, sent;
} overlay_fixture;
static void *open_overlay(mu_fixture_ctx *ctx, const char *args, char *error, size_t cap)
{
    (void)ctx;
    (void)args;
    (void)error;
    (void)cap;
    return calloc(1, sizeof(overlay_fixture));
}
static int add(overlay_fixture *s, int key, int type, int state, int action, int x, int y, const char *name)
{
    if (!s || s->count == MAX_MARKERS)
        return -1;
    marker *m = &s->markers[s->count++];
    uint8_t p[10] = {
        0xc1,       0,         0xe7, 3, (uint8_t)key, (uint8_t)type, (uint8_t)state, (uint8_t)action,
        (uint8_t)x, (uint8_t)y};
    memcpy(m->bytes, p, 10);
    size_t n = strlen(name);
    if (n > 63)
        n = 63;
    memcpy(m->bytes + 10, name, n);
    m->bytes[10 + n] = 0;
    m->length = 11 + n;
    m->bytes[1] = (uint8_t)m->length;
    return 0;
}
void mu_map_overlay_demo_world(void *self, const mu_lang *lang, const mu_gate *gates, int count, int world)
{
    overlay_fixture *s = self;
    int key = 0;
    for (int i = 0; i < count; ++i) {
        const mu_gate *g = &gates[i];
        if (g->flag != 1 || g->world != world)
            continue;
        const char *name = "";
        for (int j = 0; j < count; ++j)
            if (gates[j].index == g->target) {
                const char *n = lang ? mu_lang_map_name(lang, gates[j].world) : NULL;
                if (n)
                    name = n;
                break;
            }
        char text[64];
        snprintf(text, sizeof text, "%s%sEntrance", name, *name ? " " : "");
        add(s, key++, 0, 0, 0, (g->x1 + g->x2) / 2, (g->y1 + g->y2) / 2, text);
    }
}
void mu_map_overlay_demo_npc(void *self, int key, const char *name, int x, int y)
{
    add(self, key, 1, 0, 0, x, y, name ? name : "");
}
static void step(void *self, mu_fixture_ctx *ctx, uint32_t now)
{
    (void)now;
    overlay_fixture *s = self;
    while (s->sent < s->count) {
        marker *m = &s->markers[s->sent];
        mu_packet p;
        mu_packet_begin(&p, 0xc1, 0xe7);
        mu_packet_add(&p, m->bytes + 3, m->length - 3, 0);
        if (mu_fx_send(ctx, MU_CONN_GAME, &p, 0) != 0)
            return;
        ++s->sent;
    }
    /* Reuse bounded command storage after delivery. */
    s->sent = s->count = 0;
}
static int command(void *self, mu_fixture_ctx *ctx, const char *line, char *error, size_t cap)
{
    (void)ctx;
    int key, type, state, action, x, y, n = 0;
    if (sscanf(line, "marker %d %d %d %d %d %d %n", &key, &type, &state, &action, &x, &y, &n) == 6 && n)
        return add(self, key, type, state, action, x, y, line + n);
    snprintf(error, cap, "invalid overlay marker command");
    return -1;
}
const mu_fixture_behavior mu_fx_map_overlay = {
    .name = "map_overlay", .open = open_overlay, .on_step = step, .on_command = command, .close = free};
