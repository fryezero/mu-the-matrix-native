/* VIEWPORT-MONSTER-001: authored placement and wander policy, plaintext loopback only. */
#define _POSIX_C_SOURCE 200809L
#include "../behavior.h"
#include "../monsters_demo.h"
#include "../../../reconstructed/actors/effect_class_table.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct fx_monster {
    mu_monster_spec spec;
    int32_t tile[2], idle;
    uint8_t moving, paused;
} fx_monster;
typedef struct fx_monsters {
    fx_monster list[MU_WORLD_ACTORS_MAX];
    int32_t count;
    uint32_t rng;
    int sent;
    const mu_world *map;
} fx_monsters;
static uint32_t demo_rand(fx_monsters *s)
{
    s->rng = s->rng * 1103515245u + 12345u;
    return (s->rng >> 8) & 0xffffffu;
}
const mu_monster_spec *mu_monsters_demo_spec(void *state, int32_t index)
{
    fx_monsters *s = state;
    return s && index >= 0 && index < s->count ? &s->list[index].spec : NULL;
}
void mu_monsters_demo_observe(void *state, const mu_world_actors *view)
{
    fx_monsters *s = state;
    if (!s) return;
    s->map = view->map;
    for (int32_t i = 0; i < view->count; ++i) {
        const mu_world_actor *actor = &view->list[i];
        int32_t k = actor->session_key - 0x400;
        if (k < 0 || k >= s->count) continue;
        memcpy(s->list[k].tile, actor->tile, sizeof s->list[k].tile);
        s->list[k].moving = actor->moving;
        s->list[k].paused = actor->wander == 0 && s->list[k].spec.wander > 0;
    }
}
static int actor_command(fx_monsters *s, const char *line, char *error, size_t cap)
{
    mu_monster_spec specs[MU_WORLD_ACTORS_MAX]; int32_t count = 0;
    if (mu_monsters_parse(line, specs, &count, error, cap) || count != 1 || s->count == MU_WORLD_ACTORS_MAX) return -1;
    fx_monster *m = &s->list[s->count++];
    m->spec = specs[0]; m->tile[0] = m->spec.x; m->tile[1] = m->spec.y;
    m->idle = 20 + (int32_t)(demo_rand(s) % 60u);
    return 0;
}
static void *monsters_open(mu_fixture_ctx *ctx, const char *args, char *error, size_t cap)
{
    (void)ctx;
    fx_monsters *s = calloc(1, sizeof *s);
    if (!s) return NULL;
    s->rng = 0x5eed2026u;
    const char *file = strstr(args, "file=");
    if (file) {
        FILE *in = fopen(file + 5, "r");
        if (!in) { snprintf(error, cap, "placement: cannot open %s", file + 5); free(s); return NULL; }
        char line[512];
        while (fgets(line, sizeof line, in)) {
            char *p = line; while (isspace((unsigned char)*p)) ++p;
            if (!*p || *p == '#') continue;
            if (actor_command(s, p, error, cap)) { fclose(in); free(s); return NULL; }
        }
        fclose(in);
    }
    return s;
}
static void create(mu_fixture_ctx *ctx, fx_monster *m, int32_t index)
{
    mu_packet p; mu_packet_begin(&p, 0xc2, 0x13);
    uint8_t count = 1, b[28] = {0};
    uint16_t key = (uint16_t)(0x8400 + index);
    b[0] = (uint8_t)(key >> 8); b[1] = (uint8_t)key;
    b[2] = (uint8_t)(m->spec.server_class >> 8); b[3] = (uint8_t)m->spec.server_class;
    b[4] = b[6] = (uint8_t)m->spec.x; b[5] = b[7] = (uint8_t)m->spec.y;
    b[8] = (uint8_t)(((m->spec.direction & 7) + 1) << 4);
    mu_packet_add(&p, &count, 1, 0); mu_packet_add(&p, b, sizeof b, 0);
    mu_fx_send(ctx, MU_CONN_GAME, &p, 0);
}
static void monsters_step(void *self, mu_fixture_ctx *ctx, uint32_t now)
{
    (void)now; fx_monsters *s = self;
    if (!s->sent) {
        for (int32_t i = 0; i < s->count; ++i) create(ctx, &s->list[i], i);
        s->sent = 1; return;
    }
    for (int32_t i = 0; i < s->count; ++i) {
        fx_monster *m = &s->list[i];
        const mu_monster_class *row = mu_monster_class_find((uint32_t)m->spec.server_class);
        if (!row || row->kind != MU_CLASS_MONSTER || m->spec.wander <= 0 || m->moving || m->paused || --m->idle > 0) continue;
        int span = 2 * m->spec.wander + 1;
        int tx = m->spec.x - m->spec.wander + (int)(demo_rand(s) % (uint32_t)span);
        int ty = m->spec.y - m->spec.wander + (int)(demo_rand(s) % (uint32_t)span);
        /* The fixture stops its straight target before the same walls/safe tiles as the old demo. */
        int x = m->tile[0], y = m->tile[1];
        for (int k = 1; k < MU_PATH_CELLS && (x != tx || y != ty); ++k) {
            int nx = x + (tx > x) - (tx < x), ny = y + (ty > y) - (ty < y);
            if (s->map && (s->map->attributes[((ny & 255) << 8) + (nx & 255)] & 5)) break;
            x = nx; y = ny;
        }
        if (x != m->tile[0] || y != m->tile[1]) {
            mu_packet p; mu_packet_begin(&p, 0xc1, 0x3d);
            uint16_t key = (uint16_t)(0x400 + i);
            uint8_t b[] = {(uint8_t)(key >> 8), (uint8_t)key, (uint8_t)x, (uint8_t)y, 0x10};
            mu_packet_add(&p, b, sizeof b, 0); mu_fx_send(ctx, MU_CONN_GAME, &p, 0);
        }
        m->idle = 40 + (int32_t)(demo_rand(s) % 80u);
    }
}
static int monsters_command(void *self, mu_fixture_ctx *ctx, const char *line, char *error, size_t cap)
{
    fx_monsters *s = self;
    if (actor_command(s, line, error, cap)) return -1;
    create(ctx, &s->list[s->count - 1], s->count - 1); s->sent = 1;
    return 0;
}
const mu_fixture_behavior mu_fx_monsters = {
    .name = "monsters", .open = monsters_open, .on_step = monsters_step,
    .on_command = monsters_command, .close = free
};
