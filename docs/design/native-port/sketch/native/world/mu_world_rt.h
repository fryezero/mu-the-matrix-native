/* WORLD-RT-001 (sketch): the world runtime - the client's engine over a session.
 *
 * Replaces the textual embed (world_embed.c `#include "main.c"`, `#define main`, the
 * file-static `app`). world/main.c's load/advance/on_step/draw_gl/draw_soft/travel move here
 * as a real module; mu-world, mu-walk and mu-client become thin front ends over it, which
 * keeps "one world runtime, one copy" (NATIVE-SHELL-001's reason) without the mechanism.
 *
 * The runtime owns presentation and simulation only: the loaded terrain, objects,
 * environment, particles, effects, GL handles, the hero's motion (mu_walk), the GFx layer
 * and per-view caches. It owns no replicated state: the hero's stats, money, inventory,
 * quests, other characters and ground items are read from the session; the CharactersClient
 * and Items[] motion fields are advanced through the session's mu_sim lease.
 *
 * Which world is loaded is DERIVED: the runtime loads mu_session_place().world on open and
 * travels whenever it differs from the loaded one (join, teleport, respawn elsewhere). Travel
 * ends with mu_session_attach_world, which releases the session's barrier. Running travel
 * twice for the same world does nothing.
 */
#ifndef MU_WORLD_RT_H
#define MU_WORLD_RT_H

#include <stddef.h>
#include <stdint.h>

#include "../core/mu_raster.h"
#include "../session/mu_session.h"
#include "mu_input.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_world_rt mu_world_rt;
struct mu_lang;

/* Read-only inputs that are not game state. */
typedef struct mu_world_assets {
    const char *game_root;          /* models, terrain, textures, WAVs, .ozg (read-only install) */
    const char *objects_dir;        /* Native Data objects/ (NULL: terrain only) */
    const char *sound_table;        /* Native Data sound/audio-tables.tsv (NULL: silent) */
    const char *gfx_dir;            /* Native Data gfx/ (NULL: no GFx layer: mu-walk, mu-shell) */
    const struct mu_lang *lang;
} mu_world_assets;

/* Presentation options only. The feature switches (--combat --items --npc --players
 * --progress --helper) are gone from the product: the server decides what exists. `parts_off`
 * survives for development A/B runs (keeping old headless hashes comparable), and is the
 * only switch, carried by one struct from the front end to here. */
typedef struct mu_world_rt_options {
    int32_t width, height;          /* drawable pixels */
    float near_plane;               /* 0: the client's 20 */
    int gl;                         /* 0: software raster only */
    int audio;
    uint64_t parts_off;             /* bit per MU_PART_* (parts.def), development only */
    const char *fidelity_dump;      /* NATIVE-FIDELITY-002 dump prefix, may be NULL */
} mu_world_rt_options;

/* Opens the runtime on the session's current place (requires MU_PHASE_IN_WORLD) and attaches
 * its world port. */
mu_world_rt *mu_world_rt_open(mu_session *s, const mu_world_assets *assets, const mu_world_rt_options *options,
                              char *error, size_t error_size);
/* Detaches the port and frees everything the runtime owns. The session keeps its state, so a
 * return to character select and a new join rebuild the same inventory/quests/HUD. */
void mu_world_rt_close(mu_world_rt *rt);

/* THE input router (mu_input.h): GFx first refusal, the client's key scan and panel
 * bindings, hotkeys, then walk/attack. Produces intents through the session; returns 1 when
 * the message was consumed. Both mu-world (windowed) and mu-client call this, and nothing
 * else in either front end interprets world input. */
int mu_world_rt_input(mu_world_rt *rt, const mu_input_msg *msg);

/* Per rendered frame: travel if the place changed; the due 40 ms logic steps, each one
 *   sim = mu_session_sim_begin(s); pre_tick parts; mu_walk step; tick parts (parts.def order);
 *   mu_session_sim_end(s, &sim);
 * then hero placement, the render-pass camera, terrain frame, lights, and the frame parts
 * (which also consume their cues and re-read changed domains). */
typedef struct mu_world_frame_info {
    int32_t steps;                  /* logic steps run this frame */
    int travelled;                  /* a travel ran this frame */
    int32_t world;
} mu_world_frame_info;
mu_world_frame_info mu_world_rt_frame(mu_world_rt *rt, uint32_t now_ms);
/* The client cap (ms to sleep) and the per-frame sound block. */
int32_t mu_world_rt_end_frame(mu_world_rt *rt);

long mu_world_rt_draw_soft(mu_world_rt *rt, mu_raster *raster);
long mu_world_rt_draw_gl(mu_world_rt *rt, int32_t width, int32_t height);   /* 0 in a no-GL build */
void mu_world_rt_resize(mu_world_rt *rt, int32_t width, int32_t height);

/* verify-mu-native frame rows: per-part counters + the journal summary. */
void mu_world_rt_report(const mu_world_rt *rt, char *json, size_t cap);

#ifdef __cplusplus
}
#endif

#endif /* MU_WORLD_RT_H */
