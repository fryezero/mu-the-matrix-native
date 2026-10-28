#define _POSIX_C_SOURCE 200809L
/* parts/map.c (WORLD-RT-001): maps and travel (NATIVE-MAP-001, core/mu_map with the demo server): LoadingWorld's
 * count-down and the gate entrance test (MoveHero) each step, hudMap's per-frame method over the GFx layer.  The
 * map session outlives world changes; the travel itself is the runtime's (world_rt_travel). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "../../session/mu_session_seed.h"
#include "../../fixture/mu_fixture.h"
#include "../../fixture/map_overlay_demo.h"

#include "../../core/mu_lang.h"
#include "../world_rt_internal.h"

typedef struct map_part {
    mu_session *session;
    mu_fixture *fixture;
    mu_transport *transport;
    uint32_t tick;
} map_part;

static void overlay_pump(map_part *p)
{
    ++p->tick;
    mu_transport_poll(p->transport, p->tick * 40);
    mu_session_pump(p->session, p->tick * 40);
}

static int map_open(struct mu_world_rt *a, void *self)
{
    map_part *p = self;
    if (!a->no_map) {   /* NATIVE-MAP-001: the session outlives world changes */
        if (!a->mapsess) {
            a->mapsess = calloc(1, sizeof *a->mapsess);
            if (a->mapsess)
                mu_map_session_init(a->mapsess, a->lang, a->world, a->tile[0], a->tile[1]);
        }
        if (a->mapsess) {
            mu_map_set_position(a->mapsess, a->world, a->walk.hero.tile[0], a->walk.hero.tile[1]);
            char path[] = "/tmp/mu-map-overlay-XXXXXX", error[512];
            int fd = mkstemp(path); if (fd < 0) return 1;
            FILE *f = fdopen(fd, "w"); if (!f) {close(fd);unlink(path);return 1;}
            fprintf(f, "endpoint game 127.0.0.1:55907\nuse map_overlay\n"); fclose(f);
            mu_fixture_options options = {path, NULL, 20261028};
            p->fixture = mu_fixture_open(&options, error, sizeof error); unlink(path);
            if (!p->fixture) return 1;
            p->transport = mu_fixture_transport(p->fixture);
            mu_session_config cfg = {0}; cfg.transport = p->transport;
            mu_fixture_endpoint(p->fixture, "game", &cfg.connect_server);
            mu_session_seed seed = {0}; seed.place.world = a->world;
            p->session = mu_session_open_seeded(&cfg, &seed, error, sizeof error);
            if (!p->session) return 1;
            void *demo = mu_fixture_behavior_state(p->fixture, "map_overlay");
            mu_map_overlay_demo_world(demo, a->lang, a->mapsess->gates, a->mapsess->ngates, a->world);
            for (int32_t i = 0; i < a->actors.count; i++) {
                const mu_world_actor *npc = &a->actors.list[i];
                if (npc->actor.spec.npc_index < 0)
                    continue;
                const char *name = a->mapsess->lang ? mu_lang_npc_name(a->mapsess->lang, npc->server_class) : NULL;
                mu_map_overlay_demo_npc(demo, i, name && name[0] ? name : npc->label, npc->tile[0], npc->tile[1]);
            }
            mu_map_bind_overlay(a->mapsess, p->session);
            /* Establish the in-process link, then deliver the fixture's initial records. */
            overlay_pump(p); overlay_pump(p);
        }
    }
    return 0;
}

/* NATIVE-MAP-001: LoadingWorld's count-down and the gate entrance test (MoveHero). */
static void map_tick(struct mu_world_rt *a, void *self)
{
    map_part *p = self;
    if (p->session) overlay_pump(p);
    const mu_walk *w = &a->walk;
    const mu_hero *h = &w->hero;
    if (a->mapsess) {
        mu_map_set_position(a->mapsess, a->world, h->tile[0], h->tile[1]);
        mu_map_step(a->mapsess);
        mu_gate_result gr;
        int sent = mu_map_gate_step(a->mapsess, w->frame.clock.frame_tick, &gr);
        if (!a->quiet && (sent || gr.refused))
            fprintf(stderr, "gate %d -> %d: %s%s\n", gr.gate, gr.target, sent ? a->mapsess->last : "refused: ",
                    sent ? "" : a->mapsess->notice);
    }
}

/* NATIVE-MAP-001: hudMap's per-frame method 0x00c6af22. */
static void map_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    (void)now;
#ifndef MU_WORLD_NO_GL
    const mu_walk *w = &a->walk;
    if (a->gfxmap && a->gfx == a->gfxmap_owner)
        world_gfx_map_frame(a->gfxmap, w->hero.position, w->hero.angle[2]);
#else
    (void)a;
#endif
}

static void map_close(mu_world_rt *a, void *self)
{
    map_part *p = self;
    if (a->mapsess) mu_map_bind_overlay(a->mapsess, NULL);
    mu_session_close(p->session); mu_transport_free(p->transport); mu_fixture_close(p->fixture);
    memset(p, 0, sizeof *p);
}

static void map_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    mu_map_overlay_view overlay = mu_session_map_overlay(a->mapsess ? a->mapsess->overlay : NULL);
    int npcs = 0;
    for (int i = 0; i < overlay.count; ++i) if (overlay.markers[i].type == 1) ++npcs;
    if (a->mapsess)   /* NATIVE-MAP-001 */
        printf("{\"map\": true, \"world\": %d, \"tile\": [%d, %d], \"travels\": %u, \"travel_failures\": %u,"
               " \"zen\": %lld, \"moves\": %d, \"gates\": %d, \"loading_world\": %d, \"map_shown\": %d,"
               " \"map_available\": %d, \"units\": %d, \"npc_units\": %d, \"move_open\": %d}\n", a->world, a->walk.hero.tile[0],
               a->walk.hero.tile[1], a->travels, a->travel_failures, (long long)a->mapsess->zen, a->mapsess->nentries,
               a->mapsess->ngates, a->mapsess->loading_world, a->mapsess->hud.shown, a->mapsess->hud.available,
               overlay.count, npcs, a->mapsess->move_open);
}

const mu_world_part_ops mu_part_map = {
    .name = "map",
    .state_size = sizeof(map_part),
    .close = map_close,
    .open = map_open,
    .tick = map_tick,
    .frame = map_frame,
    .report_summary = map_report_summary,
};
