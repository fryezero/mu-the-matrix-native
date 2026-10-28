/* WORLD-RT-001: the world runtime, one in-world session as a module (docs/design/native-port/plan.md, D).
 *
 * The walk-around session that mu-world, mu-walk, mu-client and mu-shell show: the world's terrain, the hero
 * (core/mu_walk), sound, actors, objects, environment, particles and the demo subsystems (combat, ground items,
 * NPC talk, players, helpers, names, social, maps, progression).  It replaces world/main.c's file-static `app`
 * and the textual embed (world_embed.c `#define main` + `#include "main.c"`): world_rt.c is the runtime,
 * parts/<part>.c hold each subsystem's hooks and presentation state, parts.def is the one list with the
 * client's tick and draw orders, and world_tool.c is the mu-world / mu-walk command line over this module.
 * NATIVE-SHELL-001's reason for the embed ("mu-client shows exactly what mu-world shows and follows mu-world's
 * changes without copies") holds through one module instead of one textual copy.
 *
 * Behaviour is world/main.c's: the same calls in the same order (native/tests/test_world_parts.py pins the
 * orders), so every headless hash and row of the four programs is unchanged.  Built twice: with OpenGL
 * (mu-world, mu-client) and with MU_WORLD_NO_GL (mu-walk, mu-shell, the test hosts; no GL entry points). */
#ifndef MU_WORLD_RT_H
#define MU_WORLD_RT_H

#include <stddef.h>
#include <stdio.h>
#include <stdint.h>

#include "../core/mu_character.h"
#include "../core/mu_combat.h"
#include "../core/mu_items.h"
#include "../core/mu_progress.h"
#include "../core/mu_raster.h"
#include "../core/mu_walk.h"

typedef struct mu_world_rt mu_world_rt;

/* The one options struct: what mu-world's command line, mu-client's command line (through mu_shell_config) and
 * the shell's join answer set, passed through unchanged.  mu_world_rt_default_options gives mu-world's
 * defaults; a memset of zero is the bare runtime (the test hosts).  Until the session exists the join
 * (world, class, tile, angle, equipment, name, level) and the demo feature switches live here too. */
typedef struct mu_world_rt_options {
    /* read-only inputs */
    const char *root;              /* game root (models, terrain, textures, WAVs) */
    const char *player;            /* Player.bmd (NULL: ROOT/Data/Player/Player.bmd) */
    const char *sound_table;       /* locally extracted audio table, may be NULL (silent) */
    const char *objects_dir;       /* local decoded EncTerrain<n>.plain files, may be NULL (terrain only) */
    /* the join: world, hero, equipment */
    int32_t world;                 /* client world index (0 Lorencia) */
    uint8_t class_byte;
    int32_t tile[2];
    float angle;
    int32_t boots;                 /* NATIVE-PATH-002: boots item level (run counter), 0 none */
    const char *hero_name;         /* NATIVE-NAMES-001: the hero's name plate (NULL: the demo name) */
    int32_t level;                 /* NATIVE-PROGRESS-001: the character's level (0: progress_config's) */
    int has_items;                 /* the front end's equipment (mu-client): applied after the class parts */
    const char *items[MU_CHARACTER_ITEMS];   /* index 1..5 body parts, 6/7 weapons, 8 wing; empty skipped */
    /* presentation */
    int32_t width, height;         /* drawable pixels */
    float near_plane;              /* CameraViewNear (the client's 20) */
    int legacy_box;                /* NATIVE-WORLD-001's square instead of the client frustum */
    const char *fidelity_dump;     /* NATIVE-FIDELITY-002: PREFIX-obj.bin / PREFIX-light.bin with the summary */
    int quiet;
    /* sound */
    int audio;                     /* open the sound session */
    int32_t audio_rate;            /* 0: 44100 */
    /* the demo data of the start world (placement, NPC table, players belong to demo_world) */
    int32_t demo_world;            /* -1: the world the runtime opens on */
    const char *placement;         /* demo actor placement, may be NULL */
    const char *npc_demo;          /* the NPC demo table (mu-world --npc-demo), may be NULL */
    const char *players;           /* NATIVE-PLAYERS-001: demo players file, may be NULL */
    /* feature switches (mu-world's flags; NATIVE-APP-001 passes them from mu-client) */
    int no_env, env_tga;
    uint32_t env_seed;
    int no_particles;
    uint32_t particle_seed;
    int32_t joint_demo;            /* NATIVE-JOINT-001: --joint-demo SUB (-1 off) */
    int no_names, no_monster_info;
    int no_players;
    int32_t player_range;
    const char *helper;            /* NATIVE-HELPERS-001: the hero's helper (DEMO), may be NULL */
    int32_t helper_state;          /* its ride state, -1: the name's */
    int no_helpers;
    int combat;                    /* NATIVE-COMBAT-001 */
    mu_combat_config combat_config;   /* with equipment (has_items) the weapon kind follows the weapons */
    int ground_items, no_items;    /* NATIVE-ITEMS-001: --items, --no-items (on with combat) */
    mu_world_items_config items_config;
    int npc;                       /* NATIVE-NPC-001 (on with npc_demo) */
    int no_map;                    /* NATIVE-MAP-001 */
    int progress;                  /* NATIVE-PROGRESS-001 */
    mu_progress_config progress_config;   /* class_byte 0xff: the hero's class */
} mu_world_rt_options;

void mu_world_rt_default_options(mu_world_rt_options *options);

/* Loads the world and the hero; NULL with `error` filled when it does not load (the loaders' messages went
 * to stderr).  The options are copied; their strings must outlive the runtime. */
mu_world_rt *mu_world_rt_open(const mu_world_rt_options *options, char *error, size_t error_size);
void mu_world_rt_close(mu_world_rt *rt);

/* INPUT-001: all front ends feed this router. Mouse coordinates are drawable pixels.
 * Text/preedit are UTF-8; cursor is a code-point index. Candidate keys go only to
 * an active text input. Return 1 = consumed, 0 = walk/unbound, -1 = unavailable. */
typedef enum mu_input_kind {
    MU_INPUT_KEY, MU_INPUT_MESSAGE, MU_INPUT_TEXT, MU_INPUT_COMPOSE, MU_INPUT_FOCUS
} mu_input_kind;
typedef struct mu_input_msg {
    mu_input_kind kind;
    int vk, down, mods, repeat, cursor;
    uint32_t message, wparam, lparam;
    const char *text;
} mu_input_msg;
int mu_world_rt_input(mu_world_rt *rt, const mu_input_msg *msg);
/* One ACTION of the documented FRAME:ACTION script. -2 = invalid action. */
int mu_world_rt_action(mu_world_rt *rt, const char *action);
/* Read a <=64 KiB script, strip whole-line or trailing # comments. Caller frees it. */
char *mu_input_script_read(const char *path);
#define MU_INPUT_SCRIPT_MAX 128
typedef struct mu_input_action { int32_t frame; char what[64]; } mu_input_action;
/* Parse schedule syntax only. Actions remain scene-specific. -1 rejects overflow or malformed frames. */
int mu_input_script_parse(const char *text, mu_input_action out[MU_INPUT_SCRIPT_MAX]);
void mu_world_rt_input_report(const mu_world_rt *rt, FILE *out);
/* Legacy adapters feed the same router, retained for existing hosts. */
void mu_world_rt_message(mu_world_rt *rt, uint32_t message, uint32_t wparam, uint32_t lparam);
void mu_world_rt_key(mu_world_rt *rt, int vk, int down);

/* Sets the drawable size and mouse scale (window front ends after creating the context). */
void mu_world_rt_resize(mu_world_rt *rt, int32_t width, int32_t height);
void mu_world_rt_set_clock(mu_world_rt *rt, uint32_t now);

/* Per rendered frame: a pending teleport answer (travel), the due 40 ms logic steps (pre_tick parts, the
 * walk, tick parts in parts.def order), hero placement, the render-pass camera and the frame parts. */
typedef struct mu_world_frame_info {
    int32_t steps;                 /* logic steps run this frame */
    int travelled;                 /* a travel ran this frame */
    int32_t world;
} mu_world_frame_info;
mu_world_frame_info mu_world_rt_frame(mu_world_rt *rt, uint32_t now);
/* After the frame: the client cap (milliseconds to sleep), then the per-frame sound block. */
int32_t mu_world_rt_end_frame(mu_world_rt *rt);

long mu_world_rt_draw_soft(mu_world_rt *rt, mu_raster *raster);
#ifndef MU_WORLD_NO_GL
/* The front end owns the GL context: textures are made and released around it (and again over a travel). */
void mu_world_rt_gl_setup(mu_world_rt *rt);
void mu_world_rt_gl_teardown(mu_world_rt *rt);
long mu_world_rt_draw_gl(mu_world_rt *rt, int32_t width, int32_t height);
/* NATIVE-NAMES-001 / NATIVE-QUEST-001: the front end's GFx interface over the world (NULL detaches). */
struct world_gfx;
void mu_world_rt_set_gfx(mu_world_rt *rt, struct world_gfx *gfx, double scale);
#endif

/* Sound: stereo float frames mixed from the world's engine (silence without sound). */
int mu_world_rt_has_sound(const mu_world_rt *rt);
uint32_t mu_world_rt_sound_rate(const mu_world_rt *rt);
void mu_world_rt_mix(mu_world_rt *rt, float *out, uint32_t frames);

struct mu_session;
struct mu_session *mu_world_rt_skill_session(mu_world_rt *rt);
int mu_world_rt_skill_demo_change(mu_world_rt *rt, int32_t skill, int forget);

/* State for reports and the shell. */
const mu_walk *mu_world_rt_walk(const mu_world_rt *rt);
int32_t mu_world_rt_folder(const mu_world_rt *rt);

#endif
