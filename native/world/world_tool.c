#include "../data/manifest.h"
/* mu-world / mu-walk: the command line over the world runtime (WORLD-RT-001; world/mu_world_rt.h).
 *
 * The first native "walk around the world" build (NATIVE-WORLD-001), made alive by NATIVE-WORLD-002
 * (docs/research/native-world-alive.md).  One window (SDL2 + OpenGL 2.1) or a headless run (CGL/GLX offscreen,
 * or the deterministic software rasterizer) of one in-world session: the world's real terrain, the hero
 * assembled by the character module and animated, the client camera following it, click-to-move through the
 * client terrain pick, the client's walk step and speed, and the client wheel zoom.
 *
 *   mu-world --game-root ROOT [--world 0] [--class 0x01] [--tile X,Y] [--angle D]
 *            [--width W --height H] [--seconds S] [--walk "X,Y X,Y ..."] [--wheel "F:+1 F:-1"]
 *   mu-world --game-root ROOT --headless --frames N --out-dir DIR [--backend gl|soft] [--every K]
 *            [--walk ...] [--wheel ...] [--player FILE] [--quiet]
 *
 * --walk scripts clicks: whenever the hero stands (after --pause frames), the
 * next tile's centre is projected with the client projection 0x0184a244 and
 * a mouse move, left down and left up are sent there on three frames, so the
 * click goes through the same window-procedure, pick and path code as a
 * mouse (tiles off screen are skipped). --wheel sends WM_MOUSEWHEEL (+1 = zoom in) on the given frames.
 * In the window the mouse works as in the client: left click (or hold) moves,
 * Shift holds position, the wheel zooms. Esc twice quits, O saves a PNG.
 *
 * NATIVE-WORLD-002 adds, at the points of the client loop where they run:
 *   - sound (core/mu_world_audio): every logic step HeroTile, the foot-flag
 *     reset and the footstep trigger with PlayWalkSound; every rendered frame
 *     after the cap the per-frame ambient/music block; SDL2 audio in the
 *     window, a WAV file headless (--wav). --sound-table is the locally
 *     extracted table (scripts/extract_audio_tables.py --tsv);
 *   - the terrain as RenderTerrain draws it in the client: the CreateFrustrum
 *     box and 2D polygon from the camera (zoom mode 0 with the world camera
 *     record), the 4x4 block and tile tests, the per-frame light copy and
 *     waves over that box, and the time-driven water scroll and animated
 *     layer (--legacy-box draws the NATIVE-WORLD-001 square instead);
 *   - monsters and NPCs from a DEMO placement file (--placement; the server
 *     places them in the real game), animated with the client action tables,
 *     with the EffectManager effects their creation attaches.
 *
 * NATIVE-COMBAT-001 (--combat, core/mu_combat): a click on a monster attacks
 * it with the client's attack rules (range, facing, SetPlayerAttack action,
 * SetAttackSpeed PlaySpeed, AttackTime and the end-of-attack effects); keys
 * 1..6 cast Fire Ball, Energy Ball, Cyclone, Twisting Slash, Triple Shot and
 * Heal at the target; damage text, hit reactions, death, fade and removal run
 * the client routines. The server side (damage, death, respawn, counter-
 * attacks) is a labelled DEMO. --combat-script drives it headless.
 * NATIVE-ENV-001 adds the client's ambient life and weather (core/mu_env):
 * every logic step MoveLeaves (behind the tick's guard), MoveBoids and
 * MoveFishs; every frame the render routines' models and particles and the
 * world's clear colour (--no-env disables it, --env-tga-leaves loads the
 * leaf .tga the client unloads, a viewer option).
 *
 * NATIVE-ITEMS-001 (core/mu_items, on with --combat or --items): monsters that
 * die drop DEMO items (the server's item viewport message, made up here), which
 * fall, spin and land as CreateItem/MoveItems do, render through RenderItems'
 * plan with the item render passes and carry hudPlayerName-style labels (the
 * name builder's text and colour class); the mouse selects them (SelectItem),
 * a click walks there and picks up, the space bar takes the nearest, Alt toggles
 * the labels; --item-script drives it headless. Monsters play their hurt and
 * death sounds (the model's sound slots).
 * NATIVE-NPC-001 (--npc, --npc-demo FILE, core/mu_npc): a click on an NPC
 * runs the client's character pick, MoveHero's NPC branch (walk beside it
 * with the path finder, MoveCharacters' character bit on the tiles) and the
 * talk case at the end of the walk; the answer of the DEMO server (a local
 * table) goes through the client's talk-result dispatch, which opens
 * npcdialogue, NpcShop or StorageInven in the GFx layer (--gfx) and plays
 * SND_Play 25/28. --npc-script drives it headless (click/talk on actors,
 * buy/sell/take/put/option/next/close on the windows).
 *
 * Built twice: build/mu-world (SDL2 + OpenGL) and, with MU_WORLD_NO_GL,
 * build/mu-walk, the headless software-only tool of `make -C native` (no
 * SDL2 or GL needed; the portable tests use it).  The session is the world
 * runtime (world_rt.c and parts/, the same module mu-client and mu-shell open);
 * this file is the front end: its options, the --*-script drivers, the headless
 * frame loop with the virtual clock, and the window.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifndef MU_WORLD_NO_GL
#include <SDL.h>
#endif

#include "../core/mu_frame_time.h"
#include "../core/mu_frame.h"
#include "../core/mu_perf.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_skill.h"
#include "../core/mu_wav.h"
#ifndef MU_WORLD_NO_GL
#include "../gfx/mu_gfx_layer.h"
#include "../viewer/gl_backend.h"
#include "../viewer/gl_headless.h"
#include "world_gfx_options.h"
#include "input_sdl.h"
#endif
#include "world_rt_internal.h"
#include "time_series.h"

#define MAX_WAYPOINTS 64
#define MAX_WHEELS 32

typedef struct tool {
    mu_perf perf;
    uint32_t gfx_last;
    mu_world_rt_options o;         /* the runtime's options (the flags below that reach the world) */
    mu_world_rt *rt;
    const char *out_dir, *backend;
    int32_t frames, every, pause, headless;
    int32_t time_series_every;
    uint32_t time_series_start;
    float seconds;
    int32_t waypoints[MAX_WAYPOINTS][2], waypoint_count;
    /* NATIVE-PATH-002: a long-distance auto move */
    int32_t auto_target[2], has_auto, auto_started;
    int32_t wheel_frame[MAX_WHEELS], wheel_delta[MAX_WHEELS], wheel_count;
    int wheel_ui_hit;   /* RENDER-TIME-003 --wheel-ui-hit */
    mu_input_action input_script[MU_INPUT_SCRIPT_MAX];
    int input_count;
    /* script state */
    int32_t next_waypoint, idle_frames, click_stage, click_x, click_y;
    /* NATIVE-WORLD-002: the headless WAV and the window's audio clock */
    const char *wav_path;
    float *wav;
    size_t wav_frames, wav_capacity;
    uint64_t audio_frames;         /* stereo frames produced since start */
    uint32_t audio_start;          /* clock (ms) at which audio started */
    /* NATIVE-NAMES-001: --chat-script "F:text ..." */
    int32_t chat_frame[16], chat_count;
    char chat_text[16][64];
    /* NATIVE-PLAYERS-001 */
    const char *social_script;
    /* NATIVE-COMBAT-001 */
    mu_combat_script combat_script;
    int32_t combat_next, combat_click_stage, combat_click_x, combat_click_y;
    /* NATIVE-ITEMS-001 */
    mu_world_item_script item_script;
    int32_t item_next, item_click_stage, item_click_x, item_click_y;
    /* NATIVE-NPC-001 */
    mu_npc_script npc_script;
    int32_t npc_next, npc_click_stage, npc_click_x, npc_click_y;
    const char *perf_path;   /* NATIVE-PERF-001: --perf FILE [--perf-sync] */
    int perf_sync;
    float perf_fov;   /* offline camera stress override, 0 uses the client camera */
    /* NATIVE-SKILL-001: --skill-script "F:verb[:a[:b]] ..." (select, cast, open, close, drag, over, out, save,
     * cancel, page, tip); with --gfx a right click on a monster casts the bar's selected skill */
    struct { int32_t frame; char verb[12]; int a, b; } skill_items[48];
    int32_t skill_count, skill_next;
    /* NATIVE-MAP-001: --travel-script "F:move:KEY F:to:WORLD:X:Y F:respawn F:rows F:click:ROW F:sort:N F:tab
     * F:mwin" */
    struct map_travel_item { int32_t frame; char verb[8]; int32_t a, b, c; } travel_items[32];
    int32_t travel_count, travel_next;
    /* NATIVE-PROGRESS-001: --progress-script "F:kill:CLASS F:button:ROW F:add:STAT" */
    mu_progress_script progress_script;
    int32_t progress_next;
#ifndef MU_WORLD_NO_GL
    /* NATIVE-GFX-002: the GFx interface over the world (--gfx DIR) */
    const char *gfx_dir, *gfx_open;
    SDL_AudioDeviceID audio_device;
#endif
} tool;

/* ---- script ---- */

static uint32_t pack(int x, int y)
{
    return ((uint32_t)(uint16_t)y << 16) | (uint16_t)x;
}

/* NATIVE-COMBAT-001: scripted attacks, skills and clicks on monsters. */
/* RENDER-TIME-003 --wheel-ui-hit: the UI layer of the client the run reproduces holds its base movie and base.swf
 * hit-tests at the cursor, so the window procedure's route (client_wheel.c) gives it the wheel (no zoom). Native
 * has no base.swf hit test here; a live twin declares the recorded client's state (client-render-time.md). */
static int ui_no_dispatch(void *c, int32_t n, uint32_t m, uint32_t w, uint32_t p) { (void)c; (void)n; (void)m; (void)w; (void)p; return 0; }
static int ui_base_hit(void *c, float x, float y) { (void)c; (void)x; (void)y; return 1; }
static void ui_event(void *c, int32_t t, float x, float y, float l) { (void)c; (void)t; (void)x; (void)y; (void)l; }
static int ui_no_window(void *c, int32_t id) { (void)c; (void)id; return 0; }
static const mu_wheel_env ui_hit_layer = {.dispatch = ui_no_dispatch, .hit_test = ui_base_hit, .event = ui_event,
                                          .window_open = ui_no_window, .base_movie = 1, .gfx_input = 1};

static void combat_script(tool *t, int32_t frame)
{
    mu_world_rt *a = t->rt;
    mu_walk *w = &a->walk;
    if (!a->combat)
        return;
    if (t->combat_click_stage == 1) {
        mu_walk_message(w, MU_WM_LBUTTONDOWN, 1, pack(t->combat_click_x, t->combat_click_y));
        t->combat_click_stage = 2;
        return;
    }
    if (t->combat_click_stage == 2) {
        mu_walk_message(w, MU_WM_LBUTTONUP, 0, pack(t->combat_click_x, t->combat_click_y));
        t->combat_click_stage = 0;
        return;
    }
    while (t->combat_next < t->combat_script.count && t->combat_script.items[t->combat_next].frame <= frame) {
        const mu_combat_script_item *it = &t->combat_script.items[t->combat_next++];
        int32_t actor = mu_combat_find_actor(a->combat, it->actor);
        if (actor < 0 && it->actor[0] && strcmp(it->verb, "stop"))   /* was silent before the parser fix */
            fprintf(stderr, "frame %d: combat script: no actor \"%s\" (%s)\n", frame, it->actor, it->verb);
        if (!strcmp(it->verb, "stop")) {
            mu_combat_stop(a->combat);
        } else if (!strcmp(it->verb, "attack")) {
            mu_combat_attack(a->combat, actor);
        } else if (!strcmp(it->verb, "skill")) {
            mu_combat_cast(a->combat, it->skill, actor);
        } else if (!strcmp(it->verb, "click") && actor >= 0) {
            const mu_world_actor *x = &a->actors.list[actor];
            float point[3] = {x->position[0], x->position[1], x->position[2] + 90.0f * x->actor.spec.scale};
            int32_t sx, sy;
            mu_view_projection(&w->frame.view, point, &sx, &sy);   /* 640x480 units, 0x0184a244 */
            if (sx < 0 || sy < 0 || sx > 639 || sy > 479) {
                if (!a->quiet)
                    fprintf(stderr, "frame %d: actor %d is off screen (%d,%d), click skipped\n", frame, actor, sx, sy);
                continue;
            }
            t->combat_click_x = (int)((int64_t)sx * a->width / 640);
            t->combat_click_y = (int)((int64_t)sy * a->height / 480);
            mu_walk_message(w, MU_WM_MOUSEMOVE, 0, pack(t->combat_click_x, t->combat_click_y));
            t->combat_click_stage = 1;
            if (!a->quiet)
                fprintf(stderr, "frame %d: click on actor %d at %d,%d\n", frame, actor, t->combat_click_x,
                        t->combat_click_y);
            return;
        }
    }
}

/* NATIVE-ITEMS-001: scripted drops, label toggles, hovers and clicks on items. */
static int32_t nth_live_item(const mu_world_rt *a, int32_t n)
{
    for (int32_t i = 0; i < MU_GI_ITEMS; ++i)
        if (a->ground->pool[i].object.live && n-- == 0)
            return i;
    return -1;
}

static void item_script(tool *t, int32_t frame)
{
    mu_world_rt *a = t->rt;
    mu_walk *w = &a->walk;
    if (!a->ground)
        return;
    if (t->item_click_stage == 1) {
        mu_walk_message(w, MU_WM_LBUTTONDOWN, 1, pack(t->item_click_x, t->item_click_y));
        t->item_click_stage = 2;
        return;
    }
    if (t->item_click_stage == 2) {
        mu_walk_message(w, MU_WM_LBUTTONUP, 0, pack(t->item_click_x, t->item_click_y));
        t->item_click_stage = 0;
        return;
    }
    while (t->item_next < t->item_script.count && t->item_script.items[t->item_next].frame <= frame) {
        const mu_world_item_script_entry *e = &t->item_script.items[t->item_next++];
        if (!strcmp(e->verb, "drop")) {
            const float *h = w->hero.position;
            float x = e->has_xy ? e->x * 100.0f + 50.0f : h[0] + 150.0f, y = e->has_xy ? e->y * 100.0f + 50.0f : h[1];
            mu_world_items_drop(a->ground, e->a, e->b < 0 ? 0 : e->b, 0, (uint8_t)e->ancient, e->a == MU_GI_CODE_ZEN ? 1234 : 0, x, y, 1);
        } else if (!strcmp(e->verb, "alt")) {
            mu_world_items_alt(a->ground);
        } else if (!strcmp(e->verb, "space")) {
            mu_world_items_space(a->ground);
        } else if (!strcmp(e->verb, "hover") || !strcmp(e->verb, "pick")) {
            int32_t slot = nth_live_item(a, e->a < 0 ? 0 : e->a);
            if (slot < 0)
                continue;
            const mu_gi_object *o = &a->ground->pool[slot].object;
            float point[3] = {o->position[0], o->position[1], o->position[2] + 10.0f};
            int32_t sx, sy;
            mu_view_projection(&w->frame.view, point, &sx, &sy);   /* 640x480 units, 0x0184a244 */
            if (sx < 0 || sy < 0 || sx > 639 || sy > 479)
                continue;
            t->item_click_x = (int)((int64_t)sx * a->width / 640);
            t->item_click_y = (int)((int64_t)sy * a->height / 480);
            mu_walk_message(w, MU_WM_MOUSEMOVE, 0, pack(t->item_click_x, t->item_click_y));
            if (!strcmp(e->verb, "pick")) {
                t->item_click_stage = 1;
                if (!a->quiet)
                    fprintf(stderr, "frame %d: click on item %d at %d,%d\n", frame, slot, t->item_click_x,
                            t->item_click_y);
                return;
            }
        }
    }
}

/* NATIVE-NPC-001: scripted clicks and talks on NPCs and the window verbs. */
static void npc_script(tool *t, int32_t frame)
{
    mu_world_rt *a = t->rt;
    mu_walk *w = &a->walk;
    if (!a->npc)
        return;
    if (t->npc_click_stage == 1) {
        mu_walk_message(w, MU_WM_LBUTTONDOWN, 1, pack(t->npc_click_x, t->npc_click_y));
        t->npc_click_stage = 2;
        return;
    }
    if (t->npc_click_stage == 2) {
        mu_walk_message(w, MU_WM_LBUTTONUP, 0, pack(t->npc_click_x, t->npc_click_y));
        t->npc_click_stage = 0;
        return;
    }
    while (t->npc_next < t->npc_script.count && t->npc_script.items[t->npc_next].frame <= frame) {
        const mu_npc_script_item *it = &t->npc_script.items[t->npc_next++];
        if (!strcmp(it->verb, "click") || !strcmp(it->verb, "talk")) {
            int32_t actor = mu_npc_find_actor(a->npc, it->arg);
            if (actor < 0) {
                fprintf(stderr, "frame %d: npc script: no actor \"%s\"\n", frame, it->arg);
                continue;
            }
            if (!strcmp(it->verb, "talk")) {
                mu_npc_click(a->npc, actor);
                continue;
            }
            const mu_world_actor *x = &a->actors.list[actor];
            float point[3] = {x->position[0], x->position[1], x->position[2] + 90.0f * x->actor.spec.scale};
            int32_t sx, sy;
            mu_view_projection(&w->frame.view, point, &sx, &sy);   /* 640x480 units, 0x0184a244 */
            if (sx < 0 || sy < 0 || sx > 639 || sy > 479) {
                fprintf(stderr, "frame %d: actor %d is off screen (%d,%d), npc click skipped\n", frame, actor, sx, sy);
                continue;
            }
            t->npc_click_x = (int)((int64_t)sx * a->width / 640);
            t->npc_click_y = (int)((int64_t)sy * a->height / 480);
            mu_walk_message(w, MU_WM_MOUSEMOVE, 0, pack(t->npc_click_x, t->npc_click_y));
            t->npc_click_stage = 1;
            if (!a->quiet)
                fprintf(stderr, "frame %d: click on NPC %d at %d,%d\n", frame, actor, t->npc_click_x, t->npc_click_y);
            return;
        }
        int done = 0;
#ifndef MU_WORLD_NO_GL
        if (a->gfx)
            done = world_gfx_npc_action(a->gfx, it->verb, it->arg);
#endif
        if (!strcmp(it->verb, "close"))
            mu_npc_window_closed(a->npc);
        if (!a->quiet)
            printf("{\"npc_action\": \"%s\", \"arg\": \"%s\", \"frame\": %d, \"done\": %d, \"last\": \"%s\"}\n",
                   it->verb, it->arg, frame, done,
#ifndef MU_WORLD_NO_GL
                   a->gfx ? world_gfx_npc_last(a->gfx) : ""
#else
                   ""
#endif
            );
    }
#ifndef MU_WORLD_NO_GL
    if (a->gfx && a->npc->window_open && !world_gfx_npc_window(a->gfx))
        mu_npc_window_closed(a->npc);   /* the player closed the window */
#endif
}

#ifndef MU_WORLD_NO_GL
static int parse_skill_script(tool *t, const char *text)
{
    t->skill_count = 0;
    const char *p = text;
    while (*p) {
        while (*p == ' ' || *p == ',' || *p == ';')
            p++;
        if (!*p)
            break;
        if (t->skill_count >= (int32_t)(sizeof t->skill_items / sizeof t->skill_items[0]))
            return 1;
        int frame, used = 0;
        char verb[12] = "";
        if (sscanf(p, "%d:%11[a-z0-9]%n", &frame, verb, &used) != 2)
            return 1;
        p += used;
        int args[2] = {0, 0};
        for (int k = 0; k < 2 && *p == ':'; k++) {
            char *end;
            args[k] = (int)strtol(p + 1, &end, 0);
            p = end;
        }
        t->skill_items[t->skill_count].frame = frame;
        snprintf(t->skill_items[t->skill_count].verb, sizeof t->skill_items[0].verb, "%s", verb);
        t->skill_items[t->skill_count].a = args[0];
        t->skill_items[t->skill_count].b = args[1];
        t->skill_count++;
    }
    return 0;
}
#endif

static void skill_script(tool *t, int32_t frame)
{
    mu_world_rt *a = t->rt;
    while (t->skill_next < t->skill_count && t->skill_items[t->skill_next].frame <= frame) {
        const char *verb = t->skill_items[t->skill_next].verb;
        int x = t->skill_items[t->skill_next].a, y = t->skill_items[t->skill_next].b;
        t->skill_next++;
        int result = 0;
        int32_t skill = 0;
        const char *last = "";
#ifndef MU_WORLD_NO_GL
        if (!strcmp(verb,"learn") || !strcmp(verb,"forget")) {
            result=mu_world_rt_skill_demo_change(a,x,!strcmp(verb,"forget"));
        } else if (!a->gfx) continue;
        else if (!strcmp(verb, "select")) {          /* the bar's own key: 1..9, 0 -> onSelectSkill */
            int vk = x == 9 ? '0' : '1' + x;
            mu_world_rt_key(a, vk, 1);
            mu_world_rt_key(a, vk, 0);
            result = 1;
        } else if (!strcmp(verb, "cast")) {
            result = world_rt_skill_cast_at(a, x, &skill);
        } else {
            result = world_gfx_skill_action(a->gfx, verb, x, y);
        }
        last = mu_gfx_layer_skill_last(world_gfx_layer(a->gfx));
        const mu_skill_book *book = world_gfx_skills(a->gfx);
        if (!a->quiet)
            printf("{\"skill_action\": \"%s\", \"a\": %d, \"b\": %d, \"frame\": %d, \"result\": %d%s%s%s, "
                   "\"skill\": %d, \"selected\": %d, \"last\": \"%s\"}\n", verb, x, y, frame, result,
                   !strcmp(verb, "cast") ? ", \"cast\": \"" : "", !strcmp(verb, "cast") ? mu_skill_cast_name(result) : "",
                   !strcmp(verb, "cast") ? "\"" : "", (int)skill, (int)mu_skill_book_selected(book), last);
#else
        (void)a;
        (void)x;
        (void)y;
        (void)verb;
        (void)result;
        (void)skill;
        (void)last;
#endif
    }
}

static void social_script(tool *t, int32_t frame)
{
    mu_world_rt *a = t->rt;
    if (!a->social || !t->social_script) return;
    char *copy = strdup(t->social_script), *save = NULL;
    if (!copy) return;
    for (char *tok = strtok_r(copy, ";", &save); tok; tok = strtok_r(NULL, ";", &save)) {
        char *v = strchr(tok, ':'); if (!v) continue; *v++ = 0;
        if (atoi(tok) != frame) continue;
        char *arg = strchr(v, ':'); if (arg) *arg++ = 0; else arg = "";
        int ok;
#ifndef MU_WORLD_NO_GL
        if (a->gfxsocial) ok = world_gfx_social_action(a->gfxsocial, v, arg); else
#endif
        ok = mu_social_action(a->social, v, arg);
        fprintf(stderr, "social: %s %s: %s\n", v, arg, ok ? a->social->last : "refused");
    }
    free(copy);
}

/* NATIVE-PROGRESS-001: --progress-script "F:kill:CLASS F:button:ROW F:add:STAT" */
static void progress_script(tool *t, int32_t frame)
{
    mu_world_rt *a = t->rt;
    static const double ROWS[5] = {8.0, 13.0, 24.0, 29.0, 42.0};
    while (a->progress && t->progress_next < t->progress_script.count &&
           t->progress_script.items[t->progress_next].frame <= frame) {
        const mu_progress_script_item *it = &t->progress_script.items[t->progress_next++];
        if (!strcmp(it->verb, "kill"))
            mu_progress_kill(a->progress, it->a, 0x1000 + t->progress_next);
        else if (!strcmp(it->verb, "button"))
            mu_progress_button(a->progress, (double)it->a);
        else if (!strcmp(it->verb, "add") && it->a >= 0 && it->a < 5)
            mu_progress_button(a->progress, ROWS[it->a]);
#ifndef MU_WORLD_NO_GL
        else if (a->gfx && !strcmp(it->verb, "key")) {   /* a key of the layer (79 'O', 27 Esc) */
            mu_world_rt_key(a, it->a, 1);
            mu_world_rt_key(a, it->a, 0);
        } else if (a->gfx && !strcmp(it->verb, "click")) {   /* a left click at X * 10000 + Y (window pixels) */
            double x = it->a / 10000, y = it->a % 10000;
            mu_gfx_layer *l = world_gfx_layer(a->gfx);
            mu_gfx_layer_mouse(l, 0, 0, x, y);
            mu_gfx_layer_mouse(l, 1, 0, x, y);
            mu_gfx_layer_mouse(l, 2, 0, x, y);
        } else if (a->gfx && !strcmp(it->verb, "menu")) {   /* the system menu's buttons */
            static const char *EV[4] = {"onExit", "onCharSelectClick", "onServerSelectClick", "onClose"};
            char args[64];
            snprintf(args, sizeof args, "[\"%s\",null]", EV[it->a & 3]);
            wg_options_call(world_gfx_options(a->gfx), MU_GFX_SYSTEM_MENU, "channel", args);
        } else if (a->gfx && (!strcmp(it->verb, "volume") || !strcmp(it->verb, "monster"))) {
            /* the window's onChange with one value changed (the movie's _data object) */
            const mu_prg_options *o = wg_options_values(world_gfx_options(a->gfx));
            int vol = !strcmp(it->verb, "volume") ? it->a : o->volume;
            int mon = !strcmp(it->verb, "monster") ? it->a : o->monster_info;
            char args[512];
            snprintf(args, sizeof args,
                     "[\"onChange\",{\"isAutoAttack\":%s,\"isWhisperSound\":%s,\"isSlideHelp\":%s,"
                     "\"isPlayerInfo\":%s,\"isMonsterInfo\":%s,\"isMusicPlay\":%s,\"isSwitchMode\":%s,"
                     "\"switchModeTime\":%d,\"effectLimit\":%d,\"isMute\":%s,\"volum\":%d}]",
                     o->auto_attack ? "true" : "false", o->whisper_sound ? "true" : "false",
                     o->slide_help ? "true" : "false", o->player_info ? "true" : "false", mon ? "true" : "false",
                     o->music_play ? "true" : "false", o->switch_mode ? "true" : "false", (int)o->switch_time,
                     (int)o->effect + 1, o->mute ? "true" : "false", vol);
            wg_options_call(world_gfx_options(a->gfx), MU_GFX_OPTION, "channel", args);
        }
#endif
        if (!a->quiet)
            printf("{\"progress_script\": \"%s\", \"frame\": %d, \"arg\": %d, \"last\": \"%s\"}\n", it->verb, frame,
                   it->a, a->progress->last);
    }
}

/* NATIVE-MAP-001: scripted move-window rows, travel requests and the respawn answer. */
static void map_script(tool *t, int32_t frame)
{
    mu_world_rt *a = t->rt;
    while (a->mapsess && t->travel_next < t->travel_count && t->travel_items[t->travel_next].frame <= frame) {
        const struct map_travel_item *it = &t->travel_items[t->travel_next++];
        mu_map_session *s = a->mapsess;
        int r = 0;
        if (!strcmp(it->verb, "move"))
            r = mu_map_travel_move(s, it->a);
        else if (!strcmp(it->verb, "to"))
            r = mu_map_travel_to(s, it->a, it->b, it->c);
        else if (!strcmp(it->verb, "respawn"))   /* NATIVE-PROGRESS-001: the respawn answer without a death */
            r = world_rt_combat_respawned(a);
        else if (!strcmp(it->verb, "rows") || !strcmp(it->verb, "click") || !strcmp(it->verb, "sort")) {
            mu_move_row rows[MU_MAP_MOVES_MAX];
            if (!strcmp(it->verb, "sort"))
                mu_map_move_sort(s, it->a);
            int n = mu_map_move_rows(s, rows, MU_MAP_MOVES_MAX);
            if (!strcmp(it->verb, "click")) {
                mu_move_click_result cr;
                r = mu_map_move_click(s, it->a, &cr);
            } else if (!a->quiet) {
                for (int i = 0; i < n; i++)
                    printf("{\"move_row\": %d, \"map\": \"%s\", \"level\": \"%s\", \"zen\": \"%s\", \"strife\": %d,"
                           " \"disabled\": %d, \"key\": %d}\n", rows[i].order_idx, rows[i].map, rows[i].level,
                           rows[i].zen, rows[i].strife[0] != 0, rows[i].disabled, rows[i].map_idx);
            }
        }
#ifndef MU_WORLD_NO_GL
        else if (a->gfxmap && (!strcmp(it->verb, "tab") || !strcmp(it->verb, "mwin") || !strcmp(it->verb, "mclick"))) {
            r = world_gfx_map_action(a->gfxmap, !strcmp(it->verb, "tab") ? "tab" : !strcmp(it->verb, "mwin") ? "move"
                                                                                                             : "click",
                                     it->a);
        }
#endif
        if (!a->quiet)
            fprintf(stderr, "frame %d: map %s %d: %s\n", frame, it->verb, it->a, s->last);
        (void)r;
    }
}

static int parse_travel_script(tool *t, const char *text)
{
    const char *p = text;
    while (*p && t->travel_count < (int32_t)(sizeof t->travel_items / sizeof t->travel_items[0])) {
        while (*p == ' ')
            ++p;
        if (!*p)
            break;
        struct map_travel_item *it = &t->travel_items[t->travel_count];
        memset(it, 0, sizeof *it);
        char verb[16] = "";
        int n = 0;
        if (sscanf(p, "%d:%7[a-z]%n", &it->frame, verb, &n) < 2)
            return 1;
        snprintf(it->verb, sizeof it->verb, "%s", verb);
        p += n;
        int32_t *args[3] = {&it->a, &it->b, &it->c};
        for (int k = 0; k < 3 && *p == ':'; ++k) {
            char *end;
            *args[k] = (int32_t)strtol(p + 1, &end, 0);
            p = end;
        }
        t->travel_count++;
        while (*p && *p != ' ')
            ++p;
    }
    return 0;
}

static void script(tool *t, int32_t frame)
{
    for (int i = 0; i < t->input_count; ++i) {
        if (t->input_script[i].frame == frame) {
            int result = mu_world_rt_action(t->rt, t->input_script[i].what);
            if (!t->rt->quiet) fprintf(stderr, "frame %d: input result %d: %s\n", frame, result,
                                      t->input_script[i].what);
        }
    }

    mu_world_rt *a = t->rt;
    social_script(t, frame);
    mu_walk *w = &a->walk;
    progress_script(t, frame);
    map_script(t, frame);
    skill_script(t, frame);
    combat_script(t, frame);
    item_script(t, frame);
    for (int32_t i = 0; a->names && i < t->chat_count; ++i)   /* NATIVE-NAMES-001: the hero's chat, echoed */
        if (t->chat_frame[i] == frame)
            mu_world_names_chat(a->names, a->names->names.env.hero ? a->names->names.env.hero->name : "", t->chat_text[i]);
    npc_script(t, frame);
    for (int32_t i = 0; i < t->wheel_count; ++i)
        if (t->wheel_frame[i] == frame)
            mu_walk_message(w, MU_WM_MOUSEWHEEL, (uint32_t)(uint16_t)(t->wheel_delta[i] * 120) << 16, 0);
    if (t->click_stage == 1) {
        mu_walk_message(w, MU_WM_LBUTTONDOWN, 1, pack(t->click_x, t->click_y));
        t->click_stage = 2;
        return;
    }
    if (t->click_stage == 2) {
        mu_walk_message(w, MU_WM_LBUTTONUP, 0, pack(t->click_x, t->click_y));
        t->click_stage = 0;
        t->idle_frames = 0;
        return;
    }
    if (t->next_waypoint >= t->waypoint_count) {
        /* NATIVE-PATH-002: after the clicks, the long-distance auto move (once) */
        if (t->has_auto && !t->auto_started && !w->hero.movement && ++t->idle_frames >= t->pause) {
            t->auto_started = 1;
            int started = mu_walk_auto_move_to(w, t->auto_target[0], t->auto_target[1]);
            if (!a->quiet)
                fprintf(stderr, "frame %d: auto move toward tile %d,%d: %s\n", frame, t->auto_target[0],
                        t->auto_target[1], started ? "started" : "refused");
        }
        return;
    }
    if (w->hero.movement) {
        t->idle_frames = 0;
        return;
    }
    if (++t->idle_frames < t->pause)
        return;
    const int32_t *tile = t->waypoints[t->next_waypoint++];
    float point[3] = {(float)tile[0] * 100.0f + 50.0f, (float)tile[1] * 100.0f + 50.0f, 0.0f};
    point[2] = mu_request_terrain_height(a->map->height, a->map->attributes, a->map->water_height, 6, point[0],
                                         point[1]);
    int32_t sx, sy;
    mu_view_projection(&w->frame.view, point, &sx, &sy);   /* 640x480 units, 0x0184a244 */
    if (sx < 0 || sy < 0 || sx > 639 || sy > 479) {
        if (!a->quiet)
            fprintf(stderr, "frame %d: tile %d,%d is off screen (%d,%d), skipped\n", frame, tile[0], tile[1], sx, sy);
        t->idle_frames = 0;
        return;
    }
    t->click_x = (int)((int64_t)sx * a->width / 640);
    t->click_y = (int)((int64_t)sy * a->height / 480);
    mu_walk_message(w, MU_WM_MOUSEMOVE, 0, pack(t->click_x, t->click_y));
    t->click_stage = 1;
    if (!a->quiet)
        fprintf(stderr, "frame %d: click toward tile %d,%d at %d,%d\n", frame, tile[0], tile[1], t->click_x, t->click_y);
}

/* ---- sound output ---- */

/* Mixes the audio due at clock `now` (ms since the audio start) into buffer
 * (headless WAV) or returns the frame count for the caller. */
static uint32_t audio_due(const tool *t, uint32_t now)
{
    uint64_t due = (uint64_t)(now - t->audio_start) * (uint64_t)mu_world_sound_rate(&t->rt->sound) / 1000u;
    return due > t->audio_frames ? (uint32_t)(due - t->audio_frames) : 0;
}

static int wav_append(tool *t, uint32_t frames)
{
    if (!frames)
        return 0;
    if (t->wav_frames + frames > t->wav_capacity) {
        size_t capacity = t->wav_capacity ? t->wav_capacity * 2 : 1u << 20;
        while (capacity < t->wav_frames + frames)
            capacity *= 2;
        float *grown = realloc(t->wav, capacity * 2 * sizeof *grown);
        if (!grown)
            return 1;
        t->wav = grown;
        t->wav_capacity = capacity;
    }
    mu_world_sound_mix(&t->rt->sound, t->wav + t->wav_frames * 2, frames);
    t->wav_frames += frames;
    t->audio_frames += frames;
    t->rt->wav_frames = t->wav_frames;
    return 0;
}

/* ---- headless ---- */

static int headless(tool *t)
{
    mu_world_rt *a = t->rt;
#ifndef MU_WORLD_NO_GL
    char error[256];
    int gl = t->backend && !strcmp(t->backend, "gl");
#else
    const int gl = 0;
    if (t->backend && strcmp(t->backend, "soft")) {
        fprintf(stderr, "mu-walk renders with the software rasterizer only (--backend soft)\n");
        return 2;
    }
#endif
    if (t->out_dir && mkdir(t->out_dir, 0755) && errno != EEXIST) {
        fprintf(stderr, "cannot create %s\n", t->out_dir);
        return 1;
    }
#ifndef MU_WORLD_NO_GL
    if (gl && mu_gl_headless_begin(a->width, a->height, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    if (gl)
        mu_world_rt_gl_setup(a);
    if (gl && t->gfx_dir) {
        a->gfx = world_gfx_open(t->gfx_dir, a->root, a->width, a->height, 1.0, 1, t->gfx_open, mu_world_rt_skill_session(a), error, sizeof error);
        if (!a->gfx)
            fprintf(stderr, "gfx: %s (continuing without the interface)\n", error);
        else
            world_rt_names_gfx_attach(a, 1.0);
        if (a->gfx && a->npc_demo)
            world_gfx_npc_storage(a->gfx, a->npc_demo->storage, a->npc_demo->storage_count);
        if (a->gfx)   /* NATIVE-QUEST-001 */
            world_gfx_quest_setup(a->gfx, a->npc_demo ? a->npc_demo->quests : NULL);
    }
#endif
    mu_raster raster;
    memset(&raster, 0, sizeof raster);
    if (!gl && mu_raster_init(&raster, a->width, a->height)) {
        fprintf(stderr, "raster allocation failed\n");
        return 1;
    }
    size_t bytes = (size_t)a->width * (size_t)a->height * 4;
    uint8_t *pixels = malloc(bytes);
    if (!pixels)
        return 1;
    uint32_t now = t->time_series_start;
#ifndef MU_WORLD_NO_GL
    uint32_t gfx_clock = now;
#endif
    a->walk.frame.clock.frame_tick = now;
    if (t->wheel_ui_hit)
        a->walk.frame.wheel_ui = &ui_hit_layer;
    t->audio_start = now;
    if (t->perf_path && mu_perf_open(&t->perf, t->perf_path, t->perf_sync))
        fprintf(stderr, "cannot write %s\n", t->perf_path);
#ifndef MU_WORLD_NO_GL
    mu_perf_set_sync(&t->perf, glFinish);
#endif
    for (int32_t frame = 0; frame < t->frames; ++frame) {
        double perf = mu_perf_begin(&t->perf);
        script(t, frame);
        mu_world_rt_frame(a, now);
        mu_perf_end(&t->perf, MU_PERF_LOGIC, perf);
#ifndef MU_WORLD_NO_GL
        int gfx_draw = a->gfx && t->out_dir && t->every > 0 && (frame % t->every == 0 || frame == t->frames - 1);
        if (a->gfx)
            world_gfx_set_location(a->gfx, a->world, a->walk.hero.position[0], a->walk.hero.position[1]);
        perf = mu_perf_begin(&t->perf);
        if (a->gfx && !gfx_draw)
            world_gfx_frame(a->gfx, (double)(now - gfx_clock), 0);
        mu_perf_end(&t->perf, MU_PERF_GFX, perf);
        if (a->gfx) {   /* NATIVE-PROGRESS-001: the system menu's request */
            int menu = wg_options_take_request(world_gfx_options(a->gfx));
            if (menu >= 0 && !a->quiet)
                printf("{\"menu_request\": %d, \"frame\": %d}\n", menu, frame);
        }
#endif
        int sample = t->time_series_every > 0 && (frame % t->time_series_every == 0 || frame == t->frames - 1);
        int save = t->out_dir && t->every > 0 && (frame % t->every == 0 || frame == t->frames - 1);
        char hash[65] = "", path[4096] = "";
        if (!save && !sample && gl && (t->perf_path || t->time_series_every)) {   /* NATIVE-PERF-001: every frame drawn when profiling */
#ifndef MU_WORLD_NO_GL
            mu_world_rt_draw_gl(a, a->width, a->height);
            perf = mu_perf_begin(&t->perf);
            if (a->gfx)
                world_gfx_frame(a->gfx, 0.0, 1);
            glFlush();
            mu_perf_end(&t->perf, MU_PERF_GFX, perf);
#endif
        }
        if (!save && !sample && !gl && t->time_series_every)
            mu_world_rt_draw_soft(a, &raster);
        if (save || sample) {
            if (gl) {
#ifndef MU_WORLD_NO_GL
                mu_world_rt_draw_gl(a, a->width, a->height);
                if (a->gfx)
                    world_gfx_frame(a->gfx, (double)(now - gfx_clock), 1);
                glFinish();
                mu_gl_read(a->width, a->height, pixels);
#endif
            } else {
                mu_world_rt_draw_soft(a, &raster);
                memcpy(pixels, raster.color, bytes);
            }
            mu_sha256_hex(pixels, bytes, hash);
            /* Hash/readback and temporal sampling remain active without PNG output. */
            if (save && !getenv("MU_PERF_HASH_ONLY")) {
                snprintf(path, sizeof path, "%s/frame-%04d.png", t->out_dir, frame);
                if (mu_png_write(path, pixels, a->width, a->height)) {
                    fprintf(stderr, "cannot write %s\n", path);
                    return 1;
                }
            }
        }
        if (sample) time_series_sample(a, frame, pixels, hash);
        if (!a->quiet && (save || frame == t->frames - 1))
            world_rt_report_frame(a, frame, now, save ? hash : NULL, save ? path : NULL);
#ifndef MU_WORLD_NO_GL
        gfx_clock = now;
#endif
        now += 12;   /* virtual render time, then the client's cap */
        int32_t sleep = mu_walk_end_render(&a->walk);
        if (sleep > 0)
            now += (uint32_t)sleep;
        world_rt_sound_frame(a);   /* after the cap, as 0x0185280c in the frame driver */
        if (a->has_sound && t->wav_path && wav_append(t, audio_due(t, now))) {
            fprintf(stderr, "audio buffer allocation failed\n");
            return 1;
        }
        mu_perf_frame(&t->perf, 6);
    }
    mu_perf_close(&t->perf);
    if (a->has_sound && t->wav_path) {
        if (mu_wav_write16(t->wav_path, t->wav, (uint32_t)t->wav_frames, 2, mu_world_sound_rate(&a->sound))) {
            fprintf(stderr, "cannot write %s\n", t->wav_path);
            return 1;
        }
    }
#ifndef MU_WORLD_NO_GL
    world_rt_report_summary(a, gl ? mu_gl_renderer() : "software");
    if (a->gfx) {
        char line[2048];
        world_gfx_report(a->gfx, line, sizeof line);
        printf("{%s}\n", line);
        world_gfx_quest_report(a->gfx, stdout);
        world_gfx_social_close(a->gfxsocial); a->gfxsocial = NULL;
        world_gfx_map_close(a->gfxmap); a->gfxmap = NULL; a->gfxmap_owner = NULL;
        world_gfx_close(a->gfx);
        a->gfx = NULL;
    }
    if (gl) {
        mu_world_rt_gl_teardown(a);
        mu_gl_headless_end();
    }
#else
    world_rt_report_summary(a, "software");
#endif
    free(pixels);
    if (!gl)
        mu_raster_free(&raster);
    return 0;
}

#ifndef MU_WORLD_NO_GL
/* ---- window ---- */

/* SDL2 audio output: the engine's mix of the frames due at now + lead,
 * queued from the main thread after each frame (no audio callback, so the
 * engine is only touched by the thread that runs the game logic). */
static void audio_open(tool *t)
{
    mu_world_rt *a = t->rt;
    if (!a->has_sound)
        return;
    if (SDL_InitSubSystem(SDL_INIT_AUDIO) != 0) {
        fprintf(stderr, "SDL audio: %s (continuing without sound output)\n", SDL_GetError());
        return;
    }
    SDL_AudioSpec want, have;
    memset(&want, 0, sizeof want);
    want.freq = (int)mu_world_sound_rate(&a->sound);
    want.format = AUDIO_F32SYS;
    want.channels = 2;
    want.samples = 1024;
    t->audio_device = SDL_OpenAudioDevice(NULL, 0, &want, &have, 0);
    if (!t->audio_device) {
        fprintf(stderr, "SDL audio: %s (continuing without sound output)\n", SDL_GetError());
        return;
    }
    SDL_PauseAudioDevice(t->audio_device, 0);
}

static void audio_pump(tool *t, uint32_t now)
{
    mu_world_rt *a = t->rt;
    if (!a->has_sound)
        return;
    const uint32_t lead = 120;   /* ms queued ahead of the clock */
    uint32_t frames = audio_due(t, now + lead);
    if (!frames)
        return;
    float buffer[2 * 48000];
    uint32_t rate = mu_world_sound_rate(&a->sound);
    if (frames > rate)   /* after a stall, drop instead of queueing seconds of audio */
        frames = rate;
    mu_world_sound_mix(&a->sound, buffer, frames);
    t->audio_frames += frames;
    if (t->audio_device)
        SDL_QueueAudio(t->audio_device, buffer, frames * 2 * (uint32_t)sizeof(float));
}

static int windowed(tool *t)
{
    mu_world_rt *a = t->rt;
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_Window *window = SDL_CreateWindow("mu-world", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, a->width,
                                          a->height, SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI);
    SDL_GLContext context = window ? SDL_GL_CreateContext(window) : NULL;
    if (!context) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetSwapInterval(0);   /* the client caps with Sleep, not vsync */
    int dw, dh;
    SDL_GL_GetDrawableSize(window, &dw, &dh);
    double scale = (double)dw / (double)a->width;
    /* the session works in drawable pixels */
    mu_world_rt_resize(a, dw, dh);
    mu_world_rt_gl_setup(a);
    if (t->gfx_dir) {
        char error[512];
        a->gfx = world_gfx_open(t->gfx_dir, a->root, dw, dh, scale, 1, t->gfx_open, mu_world_rt_skill_session(a), error, sizeof error);
        if (a->gfx) {
            if (a->npc_demo)   /* NATIVE-NPC-001: the demo vault */
                world_gfx_npc_storage(a->gfx, a->npc_demo->storage, a->npc_demo->storage_count);
            world_gfx_quest_setup(a->gfx, a->npc_demo ? a->npc_demo->quests : NULL);   /* NATIVE-QUEST-001 */
            SDL_StartTextInput();
            world_rt_names_gfx_attach(a, scale);
        }
        else
            fprintf(stderr, "gfx: %s (continuing without the interface)\n", error);
    }
    audio_open(t);
    a->walk.frame.clock.frame_tick = SDL_GetTicks();
    uint32_t start = SDL_GetTicks(), frames = 0;
    t->audio_start = start;
    int running = 1, escapes = 0;
    int32_t printed = 0;
    if (t->perf_path && mu_perf_open(&t->perf, t->perf_path, t->perf_sync))
        fprintf(stderr, "cannot write %s\n", t->perf_path);
    mu_perf_set_sync(&t->perf, glFinish);
    uint32_t fps_start = start, fps_frames = 0;
    while (running) {
        mu_perf_pace_begin(&t->perf);
        double perf = mu_perf_begin(&t->perf);
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_KEYDOWN && mu_gfx_sdl_vk((int)e.key.keysym.scancode) != 0x1b)
                escapes = 0;
            if (mu_world_rt_sdl_event(a, &e, scale)) continue;
            if (e.type == SDL_QUIT) running = 0;
            else if (e.type == SDL_KEYDOWN && !e.key.repeat &&
                     mu_gfx_sdl_vk((int)e.key.keysym.scancode) == 0x1b && ++escapes >= 2)
                running = 0;   /* without GFx, two Escape presses retain standalone quit */

        }
        mu_perf_end(&t->perf, MU_PERF_EVENTS, perf);
        perf = mu_perf_begin(&t->perf);
        script(t, (int32_t)frames);
        const uint32_t frame_now = SDL_GetTicks();
        mu_frame_time_tick(frame_now);   /* the window loop only: [0x01cf103c] of 0x012aeb2b */
        mu_world_rt_frame(a, frame_now);
        mu_perf_end(&t->perf, MU_PERF_LOGIC, perf);
        mu_world_rt_draw_gl(a, dw, dh);
        perf = mu_perf_begin(&t->perf);
        if (a->gfx) {
            uint32_t *gfx_last = &t->gfx_last;
            uint32_t now = SDL_GetTicks();
            world_gfx_set_location(a->gfx, a->world, a->walk.hero.position[0], a->walk.hero.position[1]);
            world_gfx_frame(a->gfx, *gfx_last ? (double)(now - *gfx_last) : 0.0, 1);
            *gfx_last = now;
            int menu = wg_options_take_request(world_gfx_options(a->gfx));   /* NATIVE-PROGRESS-001 */
            if (menu == 0)
                running = 0;   /* Exit Game, after the countdown */
            else if (menu > 0 && !a->quiet)
                printf("{\"menu\": \"%s\"}\n", menu == 1 ? "switch character (mu-client)" : "select server (mu-client)");
        }
        mu_perf_end(&t->perf, MU_PERF_GFX, perf);
        perf = mu_perf_begin(&t->perf);
        SDL_GL_SwapWindow(window);
        mu_perf_end(&t->perf, MU_PERF_SWAP, perf);
        ++frames;
        perf = mu_perf_now();
        int32_t sleep = mu_walk_end_render(&a->walk);
        mu_perf_pace_end(&t->perf, sleep);
        world_rt_sound_frame(a);   /* after the cap, as 0x0185280c in the frame driver */
        audio_pump(t, SDL_GetTicks());
        if (mu_perf_enabled(&t->perf))
            mu_perf_add(&t->perf, MU_PERF_SLEEP, mu_perf_now() - perf);
        mu_perf_frame(&t->perf, 6);
        if (frames % 25 == 0) {
            const mu_hero *h = &a->walk.hero;
            char title[160];
            snprintf(title, sizeof title, "mu-world  World%d  tile %d,%d  %s  FOV %.0f  %.1f fps",
                     a->map->report.folder, h->tile[0], h->tile[1], h->movement ? "walking" : "standing",
                     (double)a->walk.frame.view.fov,   /* NATIVE-PERF-001: the last 25 frames */
                     (double)(frames - fps_frames) * 1000.0 / (double)(SDL_GetTicks() - fps_start + 1));
            fps_start = SDL_GetTicks();
            fps_frames = frames;
            SDL_SetWindowTitle(window, title);
        }
        for (; printed < a->walk.log_count; ++printed)
            if (!a->quiet)
                printf("%s\n", a->walk.log[printed]);
        if (a->walk.log_count == MU_WALK_LOG) {
            a->walk.log_count = 0;
            printed = 0;
        }
        if (t->seconds > 0 && (SDL_GetTicks() - start) / 1000.0 >= t->seconds)
            running = 0;
    }
    mu_perf_close(&t->perf);
    double elapsed = (SDL_GetTicks() - start) / 1000.0;
    printf("{\"frames\": %u, \"seconds\": %.2f, \"fps\": %.2f, \"logic_steps\": %u, \"walked\": %.1f,"
           " \"arrivals\": %u, \"audio_device\": %s, \"audio_seconds\": %.2f}\n", frames, elapsed,
           elapsed > 0 ? frames / elapsed : 0.0, a->walk.steps, a->walked, a->walk.arrivals,
           t->audio_device ? "true" : "false",
           a->has_sound ? (double)t->audio_frames / (double)mu_world_sound_rate(&a->sound) : 0.0);
    world_rt_report_summary(a, mu_gl_renderer());
    if (a->gfx) {   /* NATIVE-SKILL-001: the interface summary (skill book, casts) */
        char line[2048];
        world_gfx_report(a->gfx, line, sizeof line);
        printf("{%s}\n", line);
    }
    if (t->audio_device)
        SDL_CloseAudioDevice(t->audio_device);
    world_gfx_quest_report(a->gfx, stdout);
    world_gfx_social_close(a->gfxsocial); a->gfxsocial = NULL;
    world_gfx_map_close(a->gfxmap); a->gfxmap = NULL; a->gfxmap_owner = NULL;
        world_gfx_close(a->gfx);
    a->gfx = NULL;
    mu_world_rt_gl_teardown(a);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}

#endif

/* ---- options ---- */

static int parse_waypoints(tool *t, const char *text)
{
    t->waypoint_count = 0;
    const char *p = text;
    while (*p && t->waypoint_count < MAX_WAYPOINTS) {
        int x, y, used = 0;
        if (sscanf(p, " %d,%d%n", &x, &y, &used) != 2)
            return 1;
        if (x < 0 || y < 0 || x > 255 || y > 255)
            return 1;
        t->waypoints[t->waypoint_count][0] = x;
        t->waypoints[t->waypoint_count++][1] = y;
        p += used;
        while (*p == ' ' || *p == ';')
            ++p;
    }
    return 0;
}

static int parse_wheels(tool *t, const char *text)
{
    t->wheel_count = 0;
    const char *p = text;
    while (*p && t->wheel_count < MAX_WHEELS) {
        int frame, delta, used = 0;
        if (sscanf(p, " %d:%d%n", &frame, &delta, &used) != 2)
            return 1;
        t->wheel_frame[t->wheel_count] = frame;
        t->wheel_delta[t->wheel_count++] = delta;
        p += used;
        while (*p == ' ' || *p == ';')
            ++p;
    }
    return 0;
}

/* NATIVE-NAMES-001: "F:text;F:text" (the hero's chat lines on the given frames). */
static int parse_chat(tool *t, const char *text)
{
    const char *p = text;
    while (*p && t->chat_count < 16) {
        char *end;
        long f = strtol(p, &end, 10);
        if (end == p || *end != ':')
            return 1;
        const char *s = end + 1, *e = strchr(s, ';');
        size_t len = e ? (size_t)(e - s) : strlen(s);
        if (len >= sizeof t->chat_text[0])
            len = sizeof t->chat_text[0] - 1;
        t->chat_frame[t->chat_count] = (int32_t)f;
        memcpy(t->chat_text[t->chat_count], s, len);
        t->chat_text[t->chat_count][len] = 0;
        t->chat_count++;
        p = e ? e + 1 : s + len;
    }
    return 0;
}

static int usage(void)
{
    fprintf(stderr, "usage: mu-world --game-root ROOT [--world N] [--class C] [--tile X,Y] [--angle D] [--near Z]\n"
                    "                [--width W --height H] [--seconds S] [--walk \"X,Y ...\"] [--wheel \"F:+1 ...\"] [--wheel-ui-hit]\n"
                    "                [--headless --frames N --out-dir DIR --backend gl|soft --every K --pause P]\n"
                    "                [--player Player.bmd] [--quiet]\n"
                    "                [--boots L] [--auto-move X,Y]   run gear; long-distance auto move (S+click)\n"
                    "                [--sound-table TSV] [--no-audio] [--wav OUT.wav] [--audio-rate HZ]\n"
                    "                [--placement DEMO.txt] [--legacy-box]\n"
                    "                [--objects-dir DIR]   local decoded EncTerrain<n>.plain files\n"
                    "                [--time-series-every N] [--time-series-start-ms MS]   headless full draw, compact post-draw samples, max 10001 frames\n"
                    "                [--fidelity-dump PREFIX]   PREFIX-obj.bin / PREFIX-light.bin at the end (fidelity tour)\n"
                    "                [--combat] [--combat-weapon none|sword|twohand|spear|bow|crossbow|staff]\n"
                    "                [--attack-speed N] [--combat-seed N] [--hero-hp N] [--combat-script \"F:attack:ACTOR F:skill:N:ACTOR ...\"]\n"
                    "                [--progress] [--progress-class N] [--progress-level N] [--progress-points N] [--progress-rate N]\n"
                    "                [--progress-script \"F:kill:CLASS F:button:ROW F:add:STAT\"]   experience, levels, stat points (demo server)\n"
                    "                [--items] [--no-items] [--item-script \"F:drop:CODE[:LEVEL[:X,Y[:SET]]] F:alt F:space F:hover:N F:pick:N\"]\n"
                    "                [--item-seed N] [--item-latency STEPS] [--item-despawn STEPS]\n"
                    "                [--npc] [--npc-demo FILE] [--npc-script \"F:click:ACTOR F:buy:SLOT F:close ...\"]   NPC talk (demo server)\n"
                    "                [--input-script FILE | --script \"F:ACTION ...\"]   shared physical input\n"
                    "                [--skill-script \"F:select:SLOT F:cast:ACTOR F:open F:drag:FROM:TO F:over:SLOT F:save F:tip:SLOT\"]   skills (--gfx)\n"
                    "                [--no-env] [--env-tga-leaves] [--env-seed N] [--no-particles] [--particle-seed N]\n"
                    "                [--joint-demo SUB]   a lightning joint 0x7f7d SUB above the hero every 20 steps\n"
                    "                [--gfx DIR [--gfx-open inventory,character]]   GFx interface (converted movies)\n"
                    "                [--no-names] [--hero-name NAME] [--monster-info 0|1] [--chat-script \"F:text;F:text\"]\n"
                    "                [--perf FILE] [--perf-sync] [--perf-fov 20..90]   offline diagnostics\n"
                    "                [--players DEMO.txt] [--no-players] [--player-range TILES]\n"
                    "                [--social-script \"F:party:NAME;F:accept;F:trade:NAME;F:offer:CELL;F:zen:N;F:ok\"]   offline social demo\n"
                    "                [--helper angel|imp|uniria|dinorant|darkhorse|fenrir[-black|-blue|-gold]|CODE]\n"
                    "                [--helper-state N] [--no-helpers]\n"
                    "                [--no-map] [--travel-script \"F:move:KEY F:to:WORLD:X:Y F:respawn F:rows F:sort:N F:click:ROW F:tab F:mwin F:mclick:ROW\"]\n");
    return 2;
}

int main(int argc, char **argv)
{
    if (!mu_native_data_check_args(argc, argv)) return 1;
    tool t;
    memset(&t, 0, sizeof t);
    mu_world_rt_options *o = &t.o;
    mu_world_rt_default_options(o);
    t.time_series_start = 100000;
    t.frames = 300;
    t.every = 10;
    t.pause = 8;
    t.backend = "gl";
    for (int i = 1; i < argc; ++i) {
        const char *k = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(k, "--headless")) { t.headless = 1; continue; }
        if (!strcmp(k, "--quiet")) { o->quiet = 1; continue; }
        if (!strcmp(k, "--perf-sync")) { t.perf_sync = 1; continue; }   /* NATIVE-PERF-001 */
        if (!strcmp(k, "--no-audio")) { o->audio = 0; continue; }
        if (!strcmp(k, "--legacy-box")) { o->legacy_box = 1; continue; }
        if (!strcmp(k, "--combat")) { o->combat = 1; continue; }
        if (!strcmp(k, "--npc")) { o->npc = 1; continue; }
        if (!strcmp(k, "--no-env")) { o->no_env = 1; continue; }
        if (!strcmp(k, "--env-tga-leaves")) { o->env_tga = 1; continue; }
        if (!strcmp(k, "--no-particles")) { o->no_particles = 1; continue; }
        if (!strcmp(k, "--items")) { o->ground_items = 1; continue; }
        if (!strcmp(k, "--no-items")) { o->no_items = 1; continue; }
        if (!strcmp(k, "--no-names")) { o->no_names = 1; continue; }
        if (!strcmp(k, "--no-players")) { o->no_players = 1; continue; }
        if (!strcmp(k, "--no-helpers")) { o->no_helpers = 1; continue; }
        if (!strcmp(k, "--no-map")) { o->no_map = 1; continue; }
        if (!strcmp(k, "--wheel-ui-hit")) { t.wheel_ui_hit = 1; continue; }   /* RENDER-TIME-003 */
        if (!strcmp(k, "--progress")) { o->progress = 1; continue; }   /* NATIVE-PROGRESS-001 */
        if (!v)
            return usage();
        ++i;
        if (!strcmp(k, "--game-root")) o->root = v;
        else if (!strcmp(k, "--player")) o->player = v;
        else if (!strcmp(k, "--world")) o->world = atoi(v);
        else if (!strcmp(k, "--class")) o->class_byte = (uint8_t)strtol(v, NULL, 0);
        else if (!strcmp(k, "--tile")) { if (sscanf(v, "%d,%d", &o->tile[0], &o->tile[1]) != 2) return usage(); }
        else if (!strcmp(k, "--angle")) o->angle = strtof(v, NULL);
        else if (!strcmp(k, "--near")) o->near_plane = strtof(v, NULL);
        else if (!strcmp(k, "--width")) o->width = atoi(v);
        else if (!strcmp(k, "--height")) o->height = atoi(v);
        else if (!strcmp(k, "--seconds")) t.seconds = strtof(v, NULL);
        else if (!strcmp(k, "--perf-fov")) t.perf_fov = strtof(v, NULL);
        else if (!strcmp(k, "--perf")) t.perf_path = v;   /* NATIVE-PERF-001 */
        else if (!strcmp(k, "--frames")) t.frames = atoi(v);
        else if (!strcmp(k, "--every")) t.every = atoi(v);
        else if (!strcmp(k, "--pause")) t.pause = atoi(v);
        else if (!strcmp(k, "--out-dir")) t.out_dir = v;
        else if (!strcmp(k, "--backend")) t.backend = v;
        else if (!strcmp(k, "--walk")) { if (parse_waypoints(&t, v)) return usage(); }
        else if (!strcmp(k, "--boots")) o->boots = atoi(v);
        else if (!strcmp(k, "--auto-move")) {
            if (sscanf(v, "%d,%d", &t.auto_target[0], &t.auto_target[1]) != 2) return usage();
            t.has_auto = 1;
        }
        else if (!strcmp(k, "--wheel")) { if (parse_wheels(&t, v)) return usage(); }
        else if (!strcmp(k, "--sound-table")) o->sound_table = v;
        else if (!strcmp(k, "--wav")) t.wav_path = v;
        else if (!strcmp(k, "--audio-rate")) o->audio_rate = atoi(v);
        else if (!strcmp(k, "--placement")) o->placement = v;
        else if (!strcmp(k, "--social-script")) t.social_script = v;
        else if (!strcmp(k, "--players")) o->players = v;
        else if (!strcmp(k, "--helper")) o->helper = v;   /* NATIVE-HELPERS-001 (DEMO) */
        else if (!strcmp(k, "--helper-state")) o->helper_state = atoi(v);
        else if (!strcmp(k, "--player-range")) o->player_range = atoi(v);
        else if (!strcmp(k, "--objects-dir")) o->objects_dir = v;
        else if (!strcmp(k, "--time-series-start-ms")) {
            char *end; unsigned long n = strtoul(v, &end, 10);
            if (!*v || *end || *v == '-' || n < 1 || n > 2140000000UL) return usage();
            t.time_series_start = (uint32_t)n;
        }
        else if (!strcmp(k, "--time-series-every")) {
            char *end; long n = strtol(v, &end, 10);
            if (!*v || *end || n < 1 || n > 10000) return usage();
            t.time_series_every = (int32_t)n;
        }
        else if (!strcmp(k, "--fidelity-dump")) o->fidelity_dump = v;
        else if (!strcmp(k, "--combat-weapon")) {
            static const char *names[] = {"none", "sword", "twohand", "spear", "bow", "crossbow", "staff"};
            int found = -1;
            for (int n = 0; n < 7; ++n)
                if (!strcmp(v, names[n]))
                    found = n;
            if (found < 0)
                return usage();
            o->combat_config.weapon = found;
            o->combat = 1;
        }
        else if (!strcmp(k, "--attack-speed")) { o->combat_config.attack_speed = strtof(v, NULL); o->combat = 1; }
        else if (!strcmp(k, "--combat-seed")) { o->combat_config.seed = (uint32_t)strtoul(v, NULL, 0); o->combat = 1; }
        else if (!strcmp(k, "--hero-hp")) { o->combat_config.hero_hp = atoi(v); o->combat = 1; }
        else if (!strcmp(k, "--progress-class")) { o->progress_config.class_byte = (uint8_t)strtol(v, NULL, 0); o->progress = 1; }
        else if (!strcmp(k, "--progress-level")) { o->progress_config.level = atoi(v); o->progress = 1; }
        else if (!strcmp(k, "--progress-points")) { o->progress_config.points = atoi(v); o->progress = 1; }
        else if (!strcmp(k, "--progress-rate")) { o->progress_config.exp_rate = atoi(v); o->progress = 1; }
        else if (!strcmp(k, "--progress-script")) {
            if (mu_progress_script_parse(&t.progress_script, v) < 0)
                return usage();
            o->progress = 1;
        }
        else if (!strcmp(k, "--combat-script")) {
            if (mu_combat_script_parse(&t.combat_script, v))
                return usage();
            o->combat = 1;
        }
        else if (!strcmp(k, "--env-seed")) o->env_seed = (uint32_t)strtoul(v, NULL, 0);
        else if (!strcmp(k, "--item-script")) {
            if (mu_world_items_script_parse(&t.item_script, v))
                return usage();
            o->ground_items = 1;
        }
        else if (!strcmp(k, "--item-seed")) o->items_config.seed = (uint32_t)strtoul(v, NULL, 0);
        else if (!strcmp(k, "--item-latency")) o->items_config.drop_latency = atoi(v);
        else if (!strcmp(k, "--item-despawn")) o->items_config.despawn_steps = atoi(v);
        else if (!strcmp(k, "--npc-demo")) { o->npc_demo = v; o->npc = 1; }
        else if (!strcmp(k, "--npc-script")) {
            if (mu_npc_script_parse(&t.npc_script, v))
                return usage();
            o->npc = 1;
        }
#ifndef MU_WORLD_NO_GL
        else if (!strcmp(k, "--gfx")) t.gfx_dir = v;
        else if (!strcmp(k, "--gfx-open")) t.gfx_open = v;
        else if (!strcmp(k, "--skill-script")) { if (parse_skill_script(&t, v)) return usage(); }
#endif
        else if (!strcmp(k, "--travel-script")) { if (parse_travel_script(&t, v)) return usage(); }
        else if (!strcmp(k, "--particle-seed")) o->particle_seed = (uint32_t)strtoul(v, NULL, 0);
        else if (!strcmp(k, "--joint-demo")) o->joint_demo = (int32_t)strtol(v, NULL, 0);
        else if (!strcmp(k, "--hero-name")) o->hero_name = v;
        else if (!strcmp(k, "--monster-info")) o->no_monster_info = !atoi(v);
        else if (!strcmp(k, "--script")) {
            t.input_count = mu_input_script_parse(v, t.input_script);
            if (t.input_count < 0) return usage();
            for (int q = 0; q < t.input_count; ++q)
                if (mu_world_rt_action(NULL, t.input_script[q].what) == -2) return usage();
        }
        else if (!strcmp(k, "--input-script")) {
            char *text = mu_input_script_read(v);
            if (!text) { fprintf(stderr, "cannot read input script %s\n", v); return 2; }
            t.input_count = mu_input_script_parse(text, t.input_script); free(text);
            if (t.input_count < 0) return usage();
            for (int q = 0; q < t.input_count; ++q)
                if (mu_world_rt_action(NULL, t.input_script[q].what) == -2) return usage();
        }
        else if (!strcmp(k, "--chat-script")) { if (parse_chat(&t, v)) return usage(); }
        else return usage();
    }
    if (o->audio_rate < 8000 || o->audio_rate > 48000 || (t.wav_path && !o->audio))
        return usage();
    if (!o->root || o->width < 64 || o->height < 64 || o->width > 8192 || o->height > 8192 || t.frames < 1 ||
        o->tile[0] < 0 || o->tile[1] < 0 || o->tile[0] > 255 || o->tile[1] > 255)
        return usage();
    if (t.time_series_every && (!t.headless || t.frames > 10001)) return usage();
    char error[1024];
    o->perf = &t.perf;
    t.rt = mu_world_rt_open(o, error, sizeof error);   /* the loaders said why on stderr */
    if (!t.rt)
        return 1;
    if (t.perf_fov != 0.0f) {
        if (!(t.perf_fov >= 20.0f && t.perf_fov <= 90.0f)) {
            mu_world_rt_close(t.rt);
            return usage();
        }
        /* Synthetic wide camera without changing the reconstructed zoom limits. */
        mu_frame_world *f = &t.rt->walk.frame;
        f->camera.world_fov = t.perf_fov;
        f->camera.fov_from = f->camera.fov_to = f->view.fov = t.perf_fov;
    }
    t.rt->has_auto = t.has_auto;
#ifndef MU_WORLD_NO_GL
    int status = t.headless ? headless(&t) : windowed(&t);
#else
    int status = headless(&t);
#endif
    mu_world_rt_close(t.rt);
    t.rt = NULL;
    free(t.wav);
    return status;
}
