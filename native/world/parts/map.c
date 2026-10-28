/* parts/map.c (WORLD-RT-001): maps and travel (NATIVE-MAP-001, core/mu_map with the demo server): LoadingWorld's
 * count-down and the gate entrance test (MoveHero) each step, hudMap's per-frame method over the GFx layer.  The
 * map session outlives world changes; the travel itself is the runtime's (world_rt_travel). */
#include <stdio.h>
#include <stdlib.h>

#include "../../core/mu_lang.h"
#include "../world_rt_internal.h"

static int map_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (!a->no_map) {   /* NATIVE-MAP-001: the session outlives world changes */
        if (!a->mapsess) {
            a->mapsess = calloc(1, sizeof *a->mapsess);
            if (a->mapsess)
                mu_map_session_init(a->mapsess, a->lang, a->world, a->tile[0], a->tile[1]);
        }
        if (a->mapsess) {
            mu_map_set_position(a->mapsess, a->world, a->walk.hero.tile[0], a->walk.hero.tile[1]);
            mu_map_clear_npcs(a->mapsess);
            for (int32_t i = 0; i < a->actors.count; i++) {
                const mu_world_actor *npc = &a->actors.list[i];
                if (npc->actor.spec.npc_index < 0)
                    continue;
                const char *name = a->mapsess->lang ? mu_lang_npc_name(a->mapsess->lang, npc->server_class) : NULL;
                mu_map_add_npc(a->mapsess, i, name && name[0] ? name : npc->label, npc->tile[0], npc->tile[1]);
            }
        }
    }
    return 0;
}

/* NATIVE-MAP-001: LoadingWorld's count-down and the gate entrance test (MoveHero). */
static void map_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
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

static void map_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->mapsess)   /* NATIVE-MAP-001 */
        printf("{\"map\": true, \"world\": %d, \"tile\": [%d, %d], \"travels\": %u, \"travel_failures\": %u,"
               " \"zen\": %lld, \"moves\": %d, \"gates\": %d, \"loading_world\": %d, \"map_shown\": %d,"
               " \"map_available\": %d, \"units\": %d, \"npc_units\": %d, \"move_open\": %d}\n", a->world, a->walk.hero.tile[0],
               a->walk.hero.tile[1], a->travels, a->travel_failures, (long long)a->mapsess->zen, a->mapsess->nentries,
               a->mapsess->ngates, a->mapsess->loading_world, a->mapsess->hud.shown, a->mapsess->hud.available,
               a->mapsess->nunits, a->mapsess->nnpcs, a->mapsess->move_open);
}

const mu_world_part_ops mu_part_map = {
    .name = "map",
    .open = map_open,
    .tick = map_tick,
    .frame = map_frame,
    .report_summary = map_report_summary,
};
