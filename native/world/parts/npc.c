/* parts/npc.c (WORLD-RT-001): NPC talk (NATIVE-NPC-001, core/mu_npc): a click on an NPC runs the client's
 * character pick, MoveHero's NPC branch (walk beside it with the path finder, MoveCharacters' character bit on
 * the tiles) and the talk case at the end of the walk; the answer of the DEMO server (a local table) goes
 * through the client's talk-result dispatch, which opens npcdialogue, NpcShop or StorageInven in the GFx layer
 * and plays SND_Play 25/28.  Two rows: npc_demo loads the demo table before the actors (its actor lines join
 * the placement), npc starts the talk session after the names. */
#include <stdio.h>
#include <stdlib.h>

#include "../world_rt_internal.h"

static int npc_demo_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (a->npc_on) {   /* NATIVE-NPC-001: the demo table first, its actor lines join the placement */
        a->npc_demo = calloc(1, sizeof *a->npc_demo);
        if (!a->npc_demo) {
            fprintf(stderr, "npc: out of memory\n");
            return 1;
        }
        if (a->npc_demo_path && mu_npc_demo_load(a->npc_demo, a->npc_demo_path, error, sizeof error)) {
            fprintf(stderr, "npc demo: %s\n", error);
            return 1;
        }
    }
    return 0;
}

static void npc_demo_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    free(a->npc_demo);
    a->npc_demo = NULL;
}

const mu_world_part_ops mu_part_npc_demo = {
    .name = "npc_demo",
    .open = npc_demo_open,
    .close = npc_demo_close,
};

/* NATIVE-NPC-001: the talk answer's window, its close-all and sounds. */
static void npc_window_open(void *context, const mu_npc_open *o)
{
    mu_world_rt *a = context;
    static const char *const KIND[] = {"none", "dialog", "shop", "storage", "other", "classic"};
    const char *kind = (unsigned)o->kind < sizeof KIND / sizeof KIND[0] ? KIND[o->kind] : "unknown";
    if (!a->quiet)
        printf("{\"npc_open\": \"%s\", \"actor\": %d, \"class\": %d, \"result\": %u, \"movie\": \"%s\","
               " \"slot\": %u, \"dialogue\": %d, \"mix_type\": %d, \"repair\": %d, \"tabs\": %d,"
               " \"close_all\": %d, \"step\": %d, \"dialog_packet\": %d}\n", kind, o->actor,
               o->server_class, o->result, o->window.movie ? o->window.movie : "", o->window.slot, o->window.dialogue,
               o->window.mix_type, o->repair, o->shop_tabs, o->close_all, a->npc ? a->npc->step : 0, o->dialog_packet);
#ifndef MU_WORLD_NO_GL
    if (a->gfx)
        world_gfx_npc_open(a->gfx, o, a->has_actors ? a->actors.list[o->actor].label : "");
#endif
}

static void npc_close_all(void *context)
{
#ifndef MU_WORLD_NO_GL
    mu_world_rt *a = context;
    if (a->gfx)
        world_gfx_npc_close_all(a->gfx);
#else
    (void)context;
#endif
}

static void npc_sound(void *context, int32_t id)
{
    mu_world_rt *a = context;
    if (a->has_sound)
        mu_audio_host_play(a->sound.host, id, 0);   /* SND_Play(id, 0, 0) */
}

static int npc_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->npc_on) {   /* NATIVE-NPC-001 */
        a->npc = calloc(1, sizeof *a->npc);
        if (!a->npc) {
            fprintf(stderr, "npc: out of memory\n");
            return 1;
        }
        mu_npc_init(a->npc, &a->walk, a->has_actors ? &a->actors : NULL, a->npc_demo);
        a->npc->open = npc_window_open;
        a->npc->close_all = npc_close_all;
        a->npc->sound = npc_sound;
        a->npc->context = a;
    }
    return 0;
}

static void npc_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    free(a->npc);
    a->npc = NULL;
}

/* The selection pass picks NPCs first (0x016b5157: mask 4, then 0x22, 1). */
static void npc_pre_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->npc)
        mu_npc_pre_step(a->npc);
}

/* MoveCharacters' character bit, the talk at the end of the walk, the demo answer. */
static void npc_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->npc)
        mu_npc_step(a->npc);
}

static void npc_report_frame(const struct mu_world_rt *a, const void *self, int32_t frame)
{
    (void)self;
    if (a->npc)
        mu_npc_report_frame(a->npc, stdout, frame);
}

static void npc_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->npc)
        mu_npc_report_summary(a->npc, stdout, a->quiet);
}

const mu_world_part_ops mu_part_npc = {
    .name = "npc",
    .open = npc_open,
    .close = npc_close,
    .pre_tick = npc_pre_tick,
    .tick = npc_tick,
    .report_frame = npc_report_frame,
    .report_summary = npc_report_summary,
};
