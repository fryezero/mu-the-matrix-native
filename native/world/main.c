/* mu-world: the first native "walk around the world" build (NATIVE-WORLD-001),
 * made alive by NATIVE-WORLD-002 (docs/research/native-world-alive.md).
 *
 * One window (SDL2 + OpenGL 2.1) or a headless run (CGL/GLX offscreen, or the
 * deterministic software rasterizer) of one in-world session (core/mu_walk):
 * the world's real terrain, the hero assembled by the character module and
 * animated, the client camera following it, click-to-move through the client
 * terrain pick, the client's walk step and speed, and the client wheel zoom.
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
 *
 * Built twice: build/mu-world (SDL2 + OpenGL) and, with MU_WORLD_NO_GL,
 * build/mu-walk, the headless software-only tool of `make -C native` (no
 * SDL2 or GL needed; the portable tests use it).
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
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif
#endif

#include "../core/mu_character.h"
#include "../core/mu_combat.h"
#include "../core/mu_env.h"
#include "../core/mu_items.h"
#include "../core/mu_objects.h"
#include "../core/mu_particles.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_renderchar.h"
#include "../core/mu_scene.h"
#include "../core/mu_terrain.h"
#include "../core/mu_walk.h"
#include "../core/mu_wav.h"
#include "../core/mu_world_actors.h"
#include "../core/mu_world_audio.h"
#include "../core/mu_world_names.h"
#ifndef MU_WORLD_NO_GL
#include "../viewer/gl_backend.h"
#include "../viewer/gl_headless.h"
#include "../gfx/mu_gfx_layer.h"
#include "world_gfx.h"
#include "world_names_gfx.h"
#endif

#define MAX_WAYPOINTS 64
#define MAX_WHEELS 32
#define TERRAIN_RADIUS 34

typedef struct app {
    const char *root, *player, *out_dir, *backend;
    int32_t world, width, height, frames, every, pause, headless, quiet;
    int32_t tile[2];
    float angle, near_plane, seconds;
    uint8_t class_byte;
    int32_t waypoints[MAX_WAYPOINTS][2], waypoint_count;
    /* NATIVE-PATH-002: hero boots level (run counter) and a long-distance auto move */
    int32_t boots, auto_target[2], has_auto, auto_started;
    int32_t wheel_frame[MAX_WHEELS], wheel_delta[MAX_WHEELS], wheel_count;
    mu_world *map;
    mu_camera_info info;
    mu_character ch;
    int has_character;
    mu_walk walk;
#ifndef MU_WORLD_NO_GL
    /* GL objects */
    GLuint tiles[MU_WORLD_BITMAPS];
    mu_gl_backend items[MU_CHARACTER_ITEMS];
    int gl_ready;
#endif
    /* script state */
    int32_t next_waypoint, idle_frames, click_stage, click_x, click_y;
    /* stats */
    double walked;
    uint32_t moving_steps;
    /* NATIVE-WORLD-002 */
    const char *sound_table, *placement, *wav_path;
    int audio, legacy_box, audio_rate;
    mu_world_sound sound;
    int has_sound;
    mu_world_actors actors;
    int has_actors;
    /* NATIVE-OBJECTS-001: static objects from local decoded files (--objects-dir) */
    const char *objects_dir;
    mu_objects objects;
    int has_objects;
    long objects_drawn;
    mu_terrain_frustum frustum;
    mu_terrain_tile_stats tile_stats;
    /* NATIVE-ENV-001 */
    mu_world_env env;
    int has_env, no_env, env_tga;
    uint32_t env_seed;
    /* NATIVE-PARTICLE-001 */
    mu_world_particles particles;
    int has_particles, no_particles;
    uint32_t particle_seed;
    int32_t joint_demo;            /* NATIVE-JOINT-001: --joint-demo SUB (-1 off) */
    /* NATIVE-NAMES-001: hudPlayerName's game side (names, HP bars, chat bubbles); --no-names, --hero-name,
     * --chat-script "F:text ...", --monster-info 0|1 */
    mu_world_names *names;
    int no_names, no_monster_info;
    const char *hero_name, *chat_script_text;
    int32_t chat_frame[16], chat_count;
    char chat_text[16][64];
    uint32_t effects_visible;
    float *wav;
    size_t wav_frames, wav_capacity;
    uint64_t audio_frames;         /* stereo frames produced since start */
    uint32_t audio_start;          /* clock (ms) at which audio started */
#ifndef MU_WORLD_NO_GL
    mu_gl_backend object_gl[MU_OBJECT_TYPES];
    mu_gl_backend actor_gl[MU_WORLD_ACTORS_MAX];
    mu_gl_backend env_gl[MU_WORLD_ENV_MODELS + 1];   /* models, then the weather bitmaps */
    mu_gl_backend particle_gl;                       /* NATIVE-PARTICLE-001: the effect bitmaps */
    mu_gl_backend particle_model_gl[MU_WORLD_FX_MODELS]; /* NATIVE-JOINT-001: the world objects' effect models */
    const mu_image *fx_images[64];
    GLuint fx_names[64];
    int fx_count;
    SDL_AudioDeviceID audio_device;
    /* NATIVE-GFX-002: the GFx interface over the world (--gfx DIR) */
    const char *gfx_dir, *gfx_open;
    world_gfx *gfx;
    world_names_gfx names_gfx;     /* NATIVE-NAMES-001: hudPlayerName through the layer */
    GLuint names_tex;
#endif
    /* NATIVE-COMBAT-001 */
    int combat_on;
    mu_combat_config combat_config;
    mu_combat *combat;
    const char *combat_script_text;
    mu_combat_script combat_script;
    int32_t combat_next, combat_click_stage, combat_click_x, combat_click_y;
#ifndef MU_WORLD_NO_GL
    mu_gl_backend combat_gl[MU_COMBAT_MODELS];
    GLuint combat_tex[MU_COMBAT_BITMAPS];
#endif
    /* NATIVE-ITEMS-001 */
    int items_on, no_items;
    mu_world_items_config items_config;
    mu_world_items *ground;    /* NATIVE-ITEMS-001: dropped items (a->ground are the hero's GL item sets) */
    const char *item_script_text;
    mu_world_item_script item_script;
    int32_t item_next, item_click_stage, item_click_x, item_click_y, item_alt;
#ifndef MU_WORLD_NO_GL
    mu_gl_backend item_gl[MU_WORLD_ITEM_MODELS];
#endif
} app;

static const int draw_order[MU_CHARACTER_ITEMS] = {5, 4, 3, 2, 1, 0, 6, 7, 8};
static const uint8_t sky[4] = {0, 0, 0, 255};

/* ---- loading ---- */

static void on_step(void *context, mu_walk *w);
static void env_sound(void *context, int32_t id);

/* NATIVE-COMBAT-001: MoveHero's attack case runs before its walk and click code. */
static void combat_sound(void *context, int32_t id)
{
    app *a = context;
    mu_audio_host_play(a->sound.host, id, 0);   /* SND_Play(id, object, 0) */
}

static void combat_pre_step(void *context, mu_walk *w)
{
    (void)w;
    app *a = context;
    if (a->ground)   /* NATIVE-ITEMS-001: a click on the selected item starts the pick-up walk */
        mu_world_items_pre_step(a->ground);
    if (a->combat)
        mu_combat_pre_step(a->combat);
}

static int load(app *a)
{
    char error[1024];
    a->map = mu_world_load(a->root, a->world, 1, 1, error, sizeof error);
    if (!a->map) {
        fprintf(stderr, "world %d: %s\n", a->world, error);
        return 1;
    }
    if (mu_camera_info_load(a->root, a->map->report.folder, &a->info, error, sizeof error)) {
        fprintf(stderr, "camera record: %s\n", error);
        return 1;
    }
    char player[4096];
    if (a->player)
        snprintf(player, sizeof player, "%s", a->player);
    else
        snprintf(player, sizeof player, "%s/Data/Player/Player.bmd", a->root);
    mu_model_params params;
    mu_model_scene_params(&params);   /* light override 1 (NATIVE-LIGHT-001) */
    params.world = a->world;
    if (mu_character_init(&a->ch, player, &params, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    a->has_character = 1;
    for (int slot = 1; slot < MU_CHARACTER_PART_SLOTS; ++slot) {
        char path[4096];
        if (mu_character_part_path(a->root, slot, a->class_byte, path, sizeof path)) {
            FILE *f = fopen(path, "rb");
            if (!f)
                continue;
            fclose(f);
            if (mu_character_set_item(&a->ch, slot, path, 0, error, sizeof error)) {
                fprintf(stderr, "%s\n", error);
                return 1;
            }
        }
    }
    mu_walk_init(&a->walk, a->map, &a->info, (uint32_t)a->width, (uint32_t)a->height, a->tile[0], a->tile[1], a->angle,
                 a->class_byte, a->ch.player_bmd.action_count, a->near_plane);
    mu_hero *h = &a->walk.hero;
    if (a->boots) {   /* boots of that item level on the body part (SetPlayerWalk's run rule) */
        h->gear.boots_type = 0x0c00;
        h->gear.boots_level = (int8_t)a->boots;
    }
    mu_character_set_state(&a->ch, h->action, 0.0f, 0.0f, h->action);
    mu_walk_place(&a->walk, &a->ch);
    if (a->audio) {
        if (mu_world_sound_open(&a->sound, a->root, a->sound_table, (uint32_t)a->audio_rate, a->world, error,
                                sizeof error)) {
            fprintf(stderr, "sound: %s\n", error);
            return 1;
        }
        a->has_sound = 1;
    }
    if (a->placement) {
        if (mu_world_actors_load(&a->actors, a->root, a->map, a->placement, 0, error, sizeof error)) {
            fprintf(stderr, "placement: %s\n", error);
            return 1;
        }
        a->has_actors = 1;
    }
    if (a->objects_dir) {
        mu_objects_init(&a->objects, a->world);
        if (mu_objects_load_dir(&a->objects, a->objects_dir, error, sizeof error) == MU_OBJECTS_FILE_OK) {
            mu_objects_load_models(&a->objects, a->root, 0);
            mu_objects_start(&a->objects, a->root);   /* NATIVE-OBJECTS-002: CreateObject per record */
            a->has_objects = 1;
        } else {
            fprintf(stderr, "objects: %s (drawing none)\n", error);
        }
    }
    if (!a->no_env) {
        if (mu_world_env_open(&a->env, a->root, a->map, a->world, a->env_seed, 0, a->env_tga, error, sizeof error)) {
            fprintf(stderr, "environment: %s\n", error);
            return 1;
        }
        a->has_env = 1;
        if (a->has_sound) {
            a->env.sound = env_sound;
            a->env.sound_context = a;
        }
    }
    if (!a->no_particles) {   /* NATIVE-PARTICLE-001: CreateParticle, CreateSprite, RenderBodyShadow */
        if (mu_world_particles_open(&a->particles, a->root, a->map, a->world, a->particle_seed, 0, error,
                                    sizeof error)) {
            fprintf(stderr, "particles: %s\n", error);
            return 1;
        }
        a->has_particles = 1;
        mu_world_particles_attach(&a->particles, a->has_objects ? &a->objects : NULL, a->has_env ? &a->env : NULL);
    }
    a->walk.step_hook = on_step;
    a->walk.step_context = a;
    if (a->combat_on) {
        const char *file = mu_combat_weapon_file(a->combat_config.weapon);
        char path[4096];
        if (file) {
            snprintf(path, sizeof path, "%s/%s", a->root, file);
            FILE *f = fopen(path, "rb");
            if (f) {
                fclose(f);
                if (mu_character_set_item(&a->ch, MU_CHARACTER_WEAPON_ITEM(0), path, 0, error, sizeof error))
                    fprintf(stderr, "combat weapon: %s (continuing without it)\n", error);
            }
        }
        a->combat = calloc(1, sizeof *a->combat);
        if (!a->combat || mu_combat_init(a->combat, a->root, &a->walk, &a->ch, a->has_actors ? &a->actors : NULL,
                                         &a->combat_config, error, sizeof error)) {
            fprintf(stderr, "combat: %s\n", a->combat ? error : "out of memory");
            return 1;
        }
        a->walk.pre_step_hook = combat_pre_step;
        a->walk.pre_step_context = a;
        if (a->has_particles)   /* NATIVE-PARTICLE-001: the skills' sprites and their legacy particle kinds */
            a->combat->legacy_particles = &a->particles;
        if (a->has_sound) {   /* NATIVE-COMBAT-002: swings, skills, the hero's voice through SND_Play */
            a->combat->play_sound = combat_sound;
            a->combat->sound_context = a;
        }
    }
    if ((a->combat_on || a->items_on) && !a->no_items) {   /* NATIVE-ITEMS-001 */
        a->ground = calloc(1, sizeof *a->ground);
        if (!a->ground ||
            mu_world_items_open(a->ground, a->root, &a->walk, &a->items_config, error, sizeof error)) {
            fprintf(stderr, "items: %s (continuing without them)\n", a->ground ? error : "out of memory");
            if (a->ground)
                mu_world_items_close(a->ground);
            free(a->ground);
            a->ground = NULL;
        } else {
            if (a->has_particles)
                a->ground->particles = &a->particles;
            a->ground->frustum = &a->frustum;   /* RenderItems' TestFrustrum uses the frame's planes */
            if (a->has_sound) {
                a->ground->play_sound = env_sound;
                a->ground->sound_context = a;
            }
            a->walk.pre_step_hook = combat_pre_step;
            a->walk.pre_step_context = a;
        }
    }
    if (!a->no_names) {   /* NATIVE-NAMES-001: the join and viewport packets' addInfo */
        a->names = calloc(1, sizeof *a->names);
        mu_world_names_config nc = {a->hero_name, 0, NULL, NULL, !a->no_monster_info};
        if (a->names)
            mu_world_names_init(a->names, &nc, &a->walk, a->has_actors ? &a->actors : NULL, a->combat);
    }
    return 0;
}

/* SND_Play of the ambient creatures (aBird1/aBird2/aBat/the rat). */
static void env_sound(void *context, int32_t id)
{
    app *a = context;
    if (a->has_sound)
        mu_audio_host_play(a->sound.host, id, 0);
}

/* End of every logic step (mu_walk_step): the client's MoveCharacters runs
 * the hero's per-character routine (foot reset after its animation step,
 * footstep trigger in 0x013b23f8) and every other character. HeroTile was set
 * at the end of MoveHero, which mu_world_sound_hero_step does first. */
static void on_step(void *context, mu_walk *w)
{
    app *a = context;
    const mu_hero *h = &w->hero;
    if (a->has_sound) {
        mu_world_sound_hero hero = {{h->position[0], h->position[1]}, {h->tile[0], h->tile[1]}, h->action,
                                    h->frame, h->step_result, h->safe_zone, 0xa91};
        int32_t id = mu_world_sound_hero_step(&a->sound, &hero, a->map->layer1, a->map->attributes);
        (void)id;
    }
    if (a->has_actors)
        mu_world_actors_step(&a->actors);
    if (a->combat)
        mu_combat_step(a->combat);
    if (a->ground) {   /* NATIVE-ITEMS-001: the demo server's drops, MoveItems, the pick-up mode */
        mu_world_items_watch_combat(a->ground, a->combat);
        mu_world_items_step(a->ground);
    }
    if (a->names)   /* NATIVE-NAMES-001: HP packets, SetPlayerDie's removeInfo, respawns */
        mu_world_names_step(a->names);
    if (a->has_objects) {   /* MoveObjects in the client's in-world tick (NATIVE-OBJECTS-002) */
        const int32_t index = ((h->tile[1] & 0xff) << 8) + (h->tile[0] & 0xff);
        mu_objects_step_inputs in = {6, a->map->layer1[index], a->map->time,
                                     {h->position[0], h->position[1], h->position[2]}, a->frustum.x2d,
                                     a->frustum.y2d};
        mu_objects_step(&a->objects, &in);
    }
    if (a->has_env) {   /* MoveLeaves (guarded), MoveBoids, MoveFishs in the tick's order */
        mu_world_env_hero hero = {{h->position[0], h->position[1], h->position[2]}, {h->tile[0], h->tile[1]},
                                  h->action, h->safe_zone, mu_hero_tile(a->map->layer1, h->position[0],
                                                                        h->position[1])};
        mu_world_env_step(&a->env, &hero, w->frame.view.position, (float)w->frame.clock.frame_tick);
        if (a->has_sound)
            a->sound.rain = a->env.env.rain_level;   /* 0x0a3a9acc for the per-frame audio block */
    }
    if (a->has_particles && a->joint_demo >= 0 && w->steps % 20 == 1) {
        /* --joint-demo (a viewer test, not client behaviour): a Tormenta lightning joint 0x7f7d of the subtype
         * above the hero every 20 steps, through the world objects' joint pool */
        const float at[3] = {h->position[0], h->position[1], h->position[2] + 150.0f}, angle[3] = {0.0f, 0.0f, 0.0f};
        mu_world_particles_joint(&a->particles, MU_JT_TYPE_THUNDER_BOLT, at, at, angle, a->joint_demo, -1, 1.0f, 0xffff,
                                 0, 0, 0xffff, 0);
    }
    if (a->has_particles) {   /* MoveEffects, MoveJoints, MoveParticles after the other movers of the in-world tick */
        mu_world_particles_set_hero(&a->particles, h->position);
        mu_world_particles_step(&a->particles, a->map->time);
    }
}

/* Once per rendered frame after the frame cap: the per-frame audio block. */
static void sound_frame(app *a)
{
    if (!a->has_sound)
        return;
    const mu_hero *h = &a->walk.hero;
    mu_world_sound_hero hero = {{h->position[0], h->position[1]}, {h->tile[0], h->tile[1]}, h->action, h->frame,
                                h->step_result, h->safe_zone, 0xa91};
    uint16_t attribute = a->map->attributes[((h->tile[1] & 0xff) << 8) + (h->tile[0] & 0xff)];
    mu_world_sound_frame(&a->sound, &hero, attribute);
}

/* Mixes the audio due at clock `now` (ms since the audio start) into buffer
 * (headless WAV) or returns the frame count for the caller. */
static uint32_t audio_due(app *a, uint32_t now)
{
    uint64_t due = (uint64_t)(now - a->audio_start) * (uint64_t)mu_world_sound_rate(&a->sound) / 1000u;
    return due > a->audio_frames ? (uint32_t)(due - a->audio_frames) : 0;
}

static int wav_append(app *a, uint32_t frames)
{
    if (!frames)
        return 0;
    if (a->wav_frames + frames > a->wav_capacity) {
        size_t capacity = a->wav_capacity ? a->wav_capacity * 2 : 1u << 20;
        while (capacity < a->wav_frames + frames)
            capacity *= 2;
        float *grown = realloc(a->wav, capacity * 2 * sizeof *grown);
        if (!grown)
            return 1;
        a->wav = grown;
        a->wav_capacity = capacity;
    }
    mu_world_sound_mix(&a->sound, a->wav + a->wav_frames * 2, frames);
    a->wav_frames += frames;
    a->audio_frames += frames;
    return 0;
}

static void unload(app *a)
{
    mu_walk_free(&a->walk);
    if (a->has_character)
        mu_character_free(&a->ch);
    if (a->map)
        mu_world_free(a->map);
    if (a->has_actors)
        mu_world_actors_free(&a->actors);
    if (a->has_objects)
        mu_objects_free(&a->objects);
    if (a->has_env)
        mu_world_env_close(&a->env);
    if (a->has_particles)
        mu_world_particles_close(&a->particles);
    if (a->has_sound)
        mu_world_sound_close(&a->sound);
    if (a->combat) {
        mu_combat_free(a->combat);
        free(a->combat);
        a->combat = NULL;
    }
    if (a->ground) {
        mu_world_items_close(a->ground);
        free(a->ground);
        a->ground = NULL;
    }
    if (a->names) {
        mu_world_names_free(a->names);
        free(a->names);
        a->names = NULL;
    }
    free(a->wav);
}

/* ---- script ---- */

static uint32_t pack(int x, int y)
{
    return ((uint32_t)(uint16_t)y << 16) | (uint16_t)x;
}

/* NATIVE-COMBAT-001: scripted attacks, skills and clicks on monsters. */
static void combat_script(app *a, int32_t frame)
{
    mu_walk *w = &a->walk;
    if (!a->combat)
        return;
    if (a->combat_click_stage == 1) {
        mu_walk_message(w, MU_WM_LBUTTONDOWN, 1, pack(a->combat_click_x, a->combat_click_y));
        a->combat_click_stage = 2;
        return;
    }
    if (a->combat_click_stage == 2) {
        mu_walk_message(w, MU_WM_LBUTTONUP, 0, pack(a->combat_click_x, a->combat_click_y));
        a->combat_click_stage = 0;
        return;
    }
    while (a->combat_next < a->combat_script.count && a->combat_script.items[a->combat_next].frame <= frame) {
        const mu_combat_script_item *it = &a->combat_script.items[a->combat_next++];
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
            a->combat_click_x = (int)((int64_t)sx * a->width / 640);
            a->combat_click_y = (int)((int64_t)sy * a->height / 480);
            mu_walk_message(w, MU_WM_MOUSEMOVE, 0, pack(a->combat_click_x, a->combat_click_y));
            a->combat_click_stage = 1;
            if (!a->quiet)
                fprintf(stderr, "frame %d: click on actor %d at %d,%d\n", frame, actor, a->combat_click_x,
                        a->combat_click_y);
            return;
        }
    }
}

/* NATIVE-ITEMS-001: scripted drops, label toggles, hovers and clicks on items. */
static int32_t nth_live_item(const app *a, int32_t n)
{
    for (int32_t i = 0; i < MU_GI_ITEMS; ++i)
        if (a->ground->pool[i].object.live && n-- == 0)
            return i;
    return -1;
}

static void item_script(app *a, int32_t frame)
{
    mu_walk *w = &a->walk;
    if (!a->ground)
        return;
    if (a->item_click_stage == 1) {
        mu_walk_message(w, MU_WM_LBUTTONDOWN, 1, pack(a->item_click_x, a->item_click_y));
        a->item_click_stage = 2;
        return;
    }
    if (a->item_click_stage == 2) {
        mu_walk_message(w, MU_WM_LBUTTONUP, 0, pack(a->item_click_x, a->item_click_y));
        a->item_click_stage = 0;
        return;
    }
    while (a->item_next < a->item_script.count && a->item_script.items[a->item_next].frame <= frame) {
        const mu_world_item_script_entry *e = &a->item_script.items[a->item_next++];
        if (!strcmp(e->verb, "drop")) {
            const float *h = w->hero.position;
            float x = e->has_xy ? e->x * 100.0f + 50.0f : h[0] + 150.0f, y = e->has_xy ? e->y * 100.0f + 50.0f : h[1];
            mu_world_items_drop(a->ground, e->a, e->b < 0 ? 0 : e->b, 0, 0, e->a == MU_GI_CODE_ZEN ? 1234 : 0, x, y, 1);
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
            a->item_click_x = (int)((int64_t)sx * a->width / 640);
            a->item_click_y = (int)((int64_t)sy * a->height / 480);
            mu_walk_message(w, MU_WM_MOUSEMOVE, 0, pack(a->item_click_x, a->item_click_y));
            if (!strcmp(e->verb, "pick")) {
                a->item_click_stage = 1;
                if (!a->quiet)
                    fprintf(stderr, "frame %d: click on item %d at %d,%d\n", frame, slot, a->item_click_x,
                            a->item_click_y);
                return;
            }
        }
    }
}

static void script(app *a, int32_t frame)
{
    mu_walk *w = &a->walk;
    combat_script(a, frame);
    item_script(a, frame);
    for (int32_t i = 0; a->names && i < a->chat_count; ++i)   /* NATIVE-NAMES-001: the hero's chat, echoed */
        if (a->chat_frame[i] == frame)
            mu_world_names_chat(a->names, a->names->names.env.hero ? a->names->names.env.hero->name : "", a->chat_text[i]);
    for (int32_t i = 0; i < a->wheel_count; ++i)
        if (a->wheel_frame[i] == frame)
            mu_walk_message(w, MU_WM_MOUSEWHEEL, (uint32_t)(uint16_t)(a->wheel_delta[i] * 120) << 16, 0);
    if (a->click_stage == 1) {
        mu_walk_message(w, MU_WM_LBUTTONDOWN, 1, pack(a->click_x, a->click_y));
        a->click_stage = 2;
        return;
    }
    if (a->click_stage == 2) {
        mu_walk_message(w, MU_WM_LBUTTONUP, 0, pack(a->click_x, a->click_y));
        a->click_stage = 0;
        a->idle_frames = 0;
        return;
    }
    if (a->next_waypoint >= a->waypoint_count) {
        /* NATIVE-PATH-002: after the clicks, the long-distance auto move (once) */
        if (a->has_auto && !a->auto_started && !w->hero.movement && ++a->idle_frames >= a->pause) {
            a->auto_started = 1;
            int started = mu_walk_auto_move_to(w, a->auto_target[0], a->auto_target[1]);
            if (!a->quiet)
                fprintf(stderr, "frame %d: auto move toward tile %d,%d: %s\n", frame, a->auto_target[0],
                        a->auto_target[1], started ? "started" : "refused");
        }
        return;
    }
    if (w->hero.movement) {
        a->idle_frames = 0;
        return;
    }
    if (++a->idle_frames < a->pause)
        return;
    const int32_t *t = a->waypoints[a->next_waypoint++];
    float point[3] = {(float)t[0] * 100.0f + 50.0f, (float)t[1] * 100.0f + 50.0f, 0.0f};
    point[2] = mu_request_terrain_height(a->map->height, a->map->attributes, a->map->water_height, 6, point[0],
                                         point[1]);
    int32_t sx, sy;
    mu_view_projection(&w->frame.view, point, &sx, &sy);   /* 640x480 units, 0x0184a244 */
    if (sx < 0 || sy < 0 || sx > 639 || sy > 479) {
        if (!a->quiet)
            fprintf(stderr, "frame %d: tile %d,%d is off screen (%d,%d), skipped\n", frame, t[0], t[1], sx, sy);
        a->idle_frames = 0;
        return;
    }
    a->click_x = (int)((int64_t)sx * a->width / 640);
    a->click_y = (int)((int64_t)sy * a->height / 480);
    mu_walk_message(w, MU_WM_MOUSEMOVE, 0, pack(a->click_x, a->click_y));
    a->click_stage = 1;
    if (!a->quiet)
        fprintf(stderr, "frame %d: click toward tile %d,%d at %d,%d\n", frame, t[0], t[1], a->click_x, a->click_y);
}

/* ---- terrain frame (NATIVE-TERRAIN-002 in the client's frame order) ---- */

static void terrain_box(const app *a, int32_t box[4]);

/* RenderTerrain's view: CreateFrustrum 0x016cba24 from the GL modelview the
 * camera left (aspect = window width / 640, far [0x01cf1630] = the far plane
 * MoveMainCamera set, fov [0x01cf1634]) and CreateFrustrum2D 0x016d20d9 around
 * the hero in zoom mode 0, whose scale and distance come from the world
 * camera record (0x0098ac7c: width / 640 * Distance * Z_Distance * scale;
 * 0x0098ac45(2400) = 2400 * Distance * Z_Distance * scale). Then the
 * per-frame update 0x016ca4fa over the box: light copy, waves, and the
 * animated-layer counter; the water UV scroll follows the world time. */
static void terrain_frame(app *a, uint32_t now)
{
    const mu_client_view *v = &a->walk.frame.view;
    mu_terrain_frustum *f = &a->frustum;
    memset(f, 0, sizeof *f);
    if (a->legacy_box) {
        int32_t box[4];
        terrain_box(a, box);
        f->x_min = box[0];
        f->y_min = box[1];
        f->x_max = box[2];
        f->y_max = box[3];
        mu_world_frame(a->map, (float)now);
        return;
    }
    float rows[12];
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 4; ++j)
            rows[4 * i + j] = v->modelview[4 * j + i];   /* 0x0184a569: m[i][j] = gl[4j + i] */
    int32_t width = (int32_t)v->window_width;
    mu_terrain_frustum_create((float)width / 640.0f, v->view_far, v->fov, rows, v->position, f);
    const mu_camera_info *c = &a->info;
    float factor = c->distance * c->z_distance * 1.0f;   /* camera scale +0x10 = 1 */
    mu_terrain_frustum_2d_params params;
    const float hero[3] = {a->walk.hero.position[0], a->walk.hero.position[1], a->walk.hero.position[2]};
    if (mu_terrain_frustum_2d_params_for(a->map->world, 0, width, (float)width / 640.0f * factor, 2400.0f * factor,
                                         &params)) {
        const float angle[3] = {v->angle[0], v->angle[1], v->angle[2]};
        mu_terrain_frustum_2d(a->map->world, hero, angle, &params, 0, f->x2d, f->y2d);
    }
    mu_world_frame_box(a->map, (float)now, f->x_min, f->y_min, f->x_max, f->y_max);
    if (a->has_objects)   /* the object light sources of the last MoveObjects (AddTerrainLight) */
        mu_objects_apply_lights(&a->objects, a->map);
}

/* ---- frame logic shared by the front ends ---- */

static int32_t advance(app *a, uint32_t now)
{
    mu_walk *w = &a->walk;
    float before[2] = {w->hero.position[0], w->hero.position[1]};
    uint32_t steps_before = w->steps;
    int was_moving = w->hero.movement;
    int32_t steps = mu_walk_update(w, now, a->has_character ? &a->ch : NULL);
    if (was_moving || w->hero.movement) {
        double dx = (double)(w->hero.position[0] - before[0]), dy = (double)(w->hero.position[1] - before[1]);
        a->walked += sqrt(dx * dx + dy * dy);
        a->moving_steps += w->steps - steps_before;
    }
    if (a->has_character)
        mu_walk_place(w, &a->ch);
    mu_walk_begin_render(w, now);
    if (a->ground) {   /* SelectObjects: with Alt held items come first, else only without a monster under the cursor */
        int alt = a->item_alt || w->frame.sample.down[0x12];
        int no_character = !(a->combat && mu_combat_pick(a->combat) >= 0);
        mu_world_items_select(a->ground, alt, no_character);
    }
    terrain_frame(a, now);
    if (a->combat)
        mu_combat_terrain_lights(a->combat, a->map);   /* effect lights after the frame light copy */
    if (a->has_actors)
        mu_world_actors_frame(&a->actors, 0.1f);   /* effect node update per frame, dt [0x01cf103c] = 0.1 */
    if (a->names) {   /* NATIVE-NAMES-001: 0x009a1618 in the tick, the hudPlayerName handler's update */
#ifndef MU_WORLD_NO_GL
        if (a->gfx)
            world_names_gfx_frame(&a->names_gfx);
#endif
        a->names->hero_wing = a->has_character && a->ch.items[MU_CHARACTER_WING_ITEM].loaded;
        mu_world_names_frame(a->names, now);
    }
    return steps;
}

static void terrain_box(const app *a, int32_t box[4])
{
    int32_t cx = (int32_t)(a->walk.hero.position[0] / 100.0f), cy = (int32_t)(a->walk.hero.position[1] / 100.0f);
    int32_t x0 = cx - TERRAIN_RADIUS, y0 = cy - TERRAIN_RADIUS, x1 = cx + TERRAIN_RADIUS, y1 = cy + TERRAIN_RADIUS;
    box[0] = x0 < 0 ? 0 : x0 & ~3;
    box[1] = y0 < 0 ? 0 : y0 & ~3;
    box[2] = x1 > 254 ? 254 : x1;
    box[3] = y1 > 254 ? 254 : y1;
}

/* Camera of the EffectManager frustum 0x00a8d821: the camera position and
 * the view direction of the modelview (its third row, negated). */
static void effect_camera(const app *a, float eye[3], float target[3])
{
    const mu_client_view *v = &a->walk.frame.view;
    for (int k = 0; k < 3; ++k) {
        eye[k] = v->position[k];
        target[k] = v->position[k] - v->modelview[4 * k + 2] * 1000.0f;
    }
}

/* Viewer aid (not a client reading): a flat marker on the clicked point
 * while the hero walks there. The client draws a cursor effect instead. */
static void marker(const app *a, const mu_render_backend *b)
{
    const mu_walk *w = &a->walk;
    if (!w->hero.movement)
        return;
    mu_meshdraw_state state;
    mu_meshdraw_state_defaults(&state);   /* depth test and writes on, blend off (ONE, ZERO) */
    state.cull = 0;
    state.texture = 0;
    b->prepare(b->context, &state, -1);
    b->begin(b->context);
    const float red[3] = {0.95f, 0.2f, 0.1f};
    float c[3] = {(float)w->target[0] * 100.0f + 50.0f, (float)w->target[1] * 100.0f + 50.0f, 0.0f};
    c[2] = mu_request_terrain_height(a->map->height, a->map->attributes, a->map->water_height, 6, c[0], c[1]) + 3.0f;
    const float s = 28.0f;
    float p[4][3] = {{c[0], c[1] - s, c[2]}, {c[0] + s, c[1], c[2]}, {c[0], c[1] + s, c[2]}, {c[0] - s, c[1], c[2]}};
    const int tri[6] = {0, 1, 2, 0, 2, 3};
    for (int i = 0; i < 6; ++i) {
        b->sink.color3(b->sink.context, red);
        b->sink.vertex(b->sink.context, p[tri[i]]);
    }
    b->end(b->context);
}

#ifndef MU_WORLD_NO_GL
/* ---- OpenGL ---- */

static void g_state(void *c, int32_t state, int32_t argument)
{
    (void)c;
    mu_meshdraw_state s;
    mu_world_state(state, argument, &s);
    if (s.blend) {
        glEnable(GL_BLEND);
        glBlendFunc((GLenum)s.src, (GLenum)s.dst);   /* GL blend factors */
    } else {
        glDisable(GL_BLEND);
    }
    if (s.cull)
        glEnable(GL_CULL_FACE);
    else
        glDisable(GL_CULL_FACE);
    glDepthMask(s.depth_mask ? GL_TRUE : GL_FALSE);
    if (s.alpha_test)
        glEnable(GL_ALPHA_TEST);
    else
        glDisable(GL_ALPHA_TEST);
}

static void g_bind(void *c, int32_t texture)
{
    app *a = c;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? a->tiles[i] : 0;
    if (name) {
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, name);
    } else {
        glDisable(GL_TEXTURE_2D);
    }
}

static void g_begin(void *c, int32_t mode)
{
    (void)c;
    glBegin(mode == MU_TERRAIN_GL_QUADS ? GL_QUADS : GL_TRIANGLE_FAN);
}
static void g_end(void *c) { (void)c; glEnd(); }
static void g_tex(void *c, float s, float t) { (void)c; glTexCoord2f(s, t); }
static void g_c3(void *c, const float rgb[3]) { (void)c; glColor3fv(rgb); }
static void g_c4(void *c, float r, float g, float b, float al) { (void)c; glColor4f(r, g, b, al); }
static void g_v(void *c, const float xyz[3]) { (void)c; glVertex3fv(xyz); }

static void gl_setup(app *a)
{
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i) {
        const mu_image *image = &a->map->bitmaps[i];
        a->tiles[i] = 0;
        if (image->width <= 0)
            continue;
        GLuint name = 0;
        glGenTextures(1, &name);
        glBindTexture(GL_TEXTURE_2D, name);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        GLint filter = a->map->bitmap_linear[i] ? GL_LINEAR : GL_NEAREST;  /* loader argument 0x2601 / 0x2600 */
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, image->width, image->height, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                     image->rgba);
        a->tiles[i] = name;
    }
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
        memset(&a->items[i], 0, sizeof a->items[i]);
        const mu_character_item *item = &a->ch.items[i];
        if (a->has_character && item->loaded)
            mu_gl_upload(&a->items[i], &item->textures, 0);
    }
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t) {
        memset(&a->object_gl[t], 0, sizeof a->object_gl[t]);
        if (a->has_objects && a->objects.models[t] && a->objects.models[t]->loaded)
            mu_gl_upload(&a->object_gl[t], &a->objects.models[t]->textures, 0);
    }
    for (int32_t i = 0; i < MU_WORLD_ACTORS_MAX; ++i)
        memset(&a->actor_gl[i], 0, sizeof a->actor_gl[i]);
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i)
        mu_gl_upload(&a->actor_gl[i], &a->actors.list[i].actor.textures, 0);
    memset(a->env_gl, 0, sizeof a->env_gl);
    for (int32_t i = 0; a->has_env && i < a->env.model_count; ++i)
        if (a->env.models[i].loaded)
            mu_gl_upload(&a->env_gl[i], &a->env.models[i].textures, 0);
    if (a->has_env)
        mu_gl_upload(&a->env_gl[MU_WORLD_ENV_MODELS], &a->env.bitmaps, 0);
    memset(&a->particle_gl, 0, sizeof a->particle_gl);
    memset(a->particle_model_gl, 0, sizeof a->particle_model_gl);
    if (a->has_particles)
        mu_gl_upload(&a->particle_gl, &a->particles.bitmaps, 0);
    a->fx_count = 0;
    a->gl_ready = 1;
}

static void gl_teardown(app *a)
{
    if (!a->gl_ready)
        return;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        if (a->tiles[i]) {
            glDeleteTextures(1, &a->tiles[i]);
            a->tiles[i] = 0;
        }
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
        mu_gl_release(&a->items[i]);
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i)
        mu_gl_release(&a->actor_gl[i]);
    for (int32_t i = 0; i <= MU_WORLD_ENV_MODELS; ++i)
        if (a->env_gl[i].textures)
            mu_gl_release(&a->env_gl[i]);
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t)
        if (a->object_gl[t].textures)
            mu_gl_release(&a->object_gl[t]);
    if (a->particle_gl.textures)
        mu_gl_release(&a->particle_gl);
    for (int i = 0; i < MU_WORLD_FX_MODELS; ++i)
        if (a->particle_model_gl[i].textures)
            mu_gl_release(&a->particle_model_gl[i]);
    for (int i = 0; i < a->fx_count; ++i)
        glDeleteTextures(1, &a->fx_names[i]);
    a->fx_count = 0;
    for (int i = 0; i < MU_COMBAT_MODELS; ++i)
        if (a->combat_gl[i].textures)
            mu_gl_release(&a->combat_gl[i]);
    for (int i = 0; i < MU_COMBAT_BITMAPS; ++i)
        if (a->combat_tex[i]) {
            glDeleteTextures(1, &a->combat_tex[i]);
            a->combat_tex[i] = 0;
        }
    for (int i = 0; i < MU_WORLD_ITEM_MODELS; ++i)
        if (a->item_gl[i].textures)
            mu_gl_release(&a->item_gl[i]);
    a->gl_ready = 0;
}

/* Effect texture as the effect loader sets it up (0x00a90987 with the base
 * load's arguments): GL_LINEAR, GL_REPEAT, GL_MODULATE, no mipmaps. */
static GLuint fx_texture(app *a, const mu_image *image)
{
    for (int i = 0; i < a->fx_count; ++i)
        if (a->fx_images[i] == image)
            return a->fx_names[i];
    if (a->fx_count == (int)(sizeof a->fx_names / sizeof a->fx_names[0]) || image->width <= 0)
        return 0;
    GLuint name = 0;
    glGenTextures(1, &name);
    glBindTexture(GL_TEXTURE_2D, name);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, image->width, image->height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image->rgba);
    a->fx_images[a->fx_count] = image;
    a->fx_names[a->fx_count++] = name;
    return name;
}

/* One visible effect of the EffectManager render pass 0x00a7a30e: depth
 * writes and alpha test off (the pass saves and restores them), the depth
 * test as the preceding pass left it (on), GL_QUADS. */
static void g_effect(void *context, const mu_fx_vertex *vertices, uint32_t count, const mu_fx_draw_state *state,
                     const mu_image *texture, const float *matrix)
{
    app *a = context;
    if (!state->visible || !count)
        return;
    if (state->blend) {
        glEnable(GL_BLEND);
        glBlendFunc((GLenum)state->src, (GLenum)state->dst);
    } else {
        glDisable(GL_BLEND);
    }
    glDepthMask(GL_FALSE);
    glDisable(GL_ALPHA_TEST);
    glDisable(GL_CULL_FACE);
    GLuint name = state->texture && texture ? fx_texture(a, texture) : 0;
    if (name) {
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, name);
    } else {
        glDisable(GL_TEXTURE_2D);
    }
    if (matrix) {
        glMatrixMode(GL_MODELVIEW);
        glPushMatrix();
        glMultMatrixf(matrix);
    }
    glBegin(GL_QUADS);
    for (uint32_t i = 0; i + 3 < count; i += 4)
        for (uint32_t k = 0; k < 4; ++k) {
            const mu_fx_vertex *v = &vertices[i + k];
            glTexCoord2fv(v->texcoord);
            glColor4fv(v->color);
            glVertex3fv(v->position);
        }
    glEnd();
    if (matrix)
        glPopMatrix();
}

/* NATIVE-COMBAT-001: effect models through the scene draw, then the frame's
 * quads (effect bitmaps, RenderPoints) in immediate mode. */
static void combat_model_gl(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                            const mu_draw_options *draw_options)
{
    app *a = context;
    mu_gl_backend *gl = &a->combat_gl[slot];
    if (!gl->textures)
        mu_gl_upload(gl, textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_draw_options options = *draw_options;   /* RenderObject's RenderBody arguments (mu_combat) */
    options.textures = textures;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(model, &options, &backend, &ds);
}

/* NATIVE-ITEMS-001: RenderItems' RenderPartObject calls through the item render passes, then the labels as a
 * screen-space overlay (the hudPlayerName movie draws them over the 3D view). */
static void items_model_gl(void *context, const mu_world_item_draw *d)
{
    app *a = context;
    mu_gl_backend *gl = &a->item_gl[d->slot];
    if (!gl->textures)
        mu_gl_upload(gl, d->textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_renderchar_glow glow = {d->type, d->level, d->option1, d->ext, d->has_record, d->kind_a, d->kind_b,
                               d->item_kind};
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    env.time = a->map->time;
    env.quality = a->ground->config.quality;
    memcpy(env.glow_color, a->ground->config.glow_color, sizeof env.glow_color);
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = d->textures;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_renderchar_stats rs = {0, 0};
    mu_renderchar_draw_item(d->model, &glow, &env, d->light, d->alpha, &options, &backend, &ds, &rs);
}

static void items_labels_gl(app *a, int32_t width, int32_t height)
{
    static mu_world_item_label labels[MU_WORLD_ITEM_LABELS];
    int32_t n = mu_world_items_labels(a->ground, labels, MU_WORLD_ITEM_LABELS);
    if (!n)
        return;
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glLoadIdentity();
    glOrtho(0.0, (double)width, (double)height, 0.0, -1.0, 1.0);
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glLoadIdentity();
    glViewport(0, 0, width, height);
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_ALPHA_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    for (int32_t i = 0; i < n; ++i) {
        const mu_world_item_label *l = &labels[i];
        float x0 = l->anchor[0] + l->box.bg_x, y0 = l->anchor[1] + l->box.bg_y;
        glDisable(GL_TEXTURE_2D);
        glColor4f(0.0f, 0.0f, 0.0f, 0.5f);
        glBegin(GL_QUADS);
        glVertex2f(x0, y0);
        glVertex2f(x0 + l->box.bg_w, y0);
        glVertex2f(x0 + l->box.bg_w, y0 + l->box.bg_h);
        glVertex2f(x0, y0 + l->box.bg_h);
        glEnd();
        int32_t tw = l->text_width, th = l->text_height;
        if (tw <= 0 || th <= 0 || tw > 2048 || th > 256)
            continue;
        uint8_t *rgba = malloc((size_t)tw * (size_t)th * 4);
        if (!rgba || mu_world_items_label_bitmap(a->ground, l, rgba, tw, th)) {
            free(rgba);
            continue;
        }
        GLuint tex;
        glGenTextures(1, &tex);
        glBindTexture(GL_TEXTURE_2D, tex);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, tw, th, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
        free(rgba);
        glEnable(GL_TEXTURE_2D);
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
        glColor4f(l->rgb[0], l->rgb[1], l->rgb[2], 1.0f);
        float tx = l->anchor[0] + l->box.text_x + 3.0f, ty = l->anchor[1] + l->box.text_y + 2.0f;
        glBegin(GL_QUADS);
        glTexCoord2f(0.0f, 0.0f);
        glVertex2f(tx, ty);
        glTexCoord2f(1.0f, 0.0f);
        glVertex2f(tx + (float)tw, ty);
        glTexCoord2f(1.0f, 1.0f);
        glVertex2f(tx + (float)tw, ty + (float)th);
        glTexCoord2f(0.0f, 1.0f);
        glVertex2f(tx, ty + (float)th);
        glEnd();
        glDeleteTextures(1, &tex);
    }
    glBindTexture(GL_TEXTURE_2D, 0);
    glDisable(GL_TEXTURE_2D);
    glDisable(GL_BLEND);
    glEnable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
}

static void combat_draw_gl(app *a)
{
    mu_combat *c = a->combat;
    mu_combat_draw_models(c, combat_model_gl, a);
    static mu_combat_quad quads[1024];
    int32_t n = mu_combat_quads(c, quads, 1024);
    glDepthMask(GL_FALSE);
    glDisable(GL_ALPHA_TEST);
    glDisable(GL_CULL_FACE);
    glEnable(GL_BLEND);
    for (int32_t i = 0; i < n; ++i) {
        const mu_combat_quad *q = &quads[i];
        if (q->bitmap >= 0) {
            const mu_combat_bitmap *b = &c->bitmaps[q->bitmap];
            if (!a->combat_tex[q->bitmap]) {
                glGenTextures(1, &a->combat_tex[q->bitmap]);
                glBindTexture(GL_TEXTURE_2D, a->combat_tex[q->bitmap]);
                glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, b->image.width, b->image.height, 0, GL_RGBA,
                             GL_UNSIGNED_BYTE, b->image.rgba);
            }
            glEnable(GL_TEXTURE_2D);
            glBindTexture(GL_TEXTURE_2D, a->combat_tex[q->bitmap]);
            glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
        } else {
            glDisable(GL_TEXTURE_2D);
        }
        if (q->src || q->dst)
            glBlendFunc((GLenum)q->src, (GLenum)q->dst);   /* RenderJoints' render types (NATIVE-COMBAT-002) */
        else if (q->additive)
            glBlendFunc(GL_ONE, GL_ONE);
        else
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        if (q->depth_test)
            glEnable(GL_DEPTH_TEST);
        else
            glDisable(GL_DEPTH_TEST);
        if (q->eye_space) {   /* RenderSpriteUV draws eye-space corners with an identity modelview */
            glMatrixMode(GL_MODELVIEW);
            glPushMatrix();
            glLoadIdentity();
        }
        glBegin(GL_QUADS);
        for (int k = 0; k < 4; ++k) {
            glColor4fv(q->color[k]);
            glTexCoord2fv(q->texcoord[k]);
            glVertex3fv(q->position[k]);
        }
        glEnd();
        if (q->eye_space)
            glPopMatrix();
    }
    glBindTexture(GL_TEXTURE_2D, 0);
    glEnable(GL_DEPTH_TEST);
    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);
}

static int env_gl_backend(void *context, const mu_world_env *e, int32_t slot, mu_render_backend *out)
{
    app *a = context;
    (void)e;
    mu_gl_backend_bind(&a->env_gl[slot < 0 ? MU_WORLD_ENV_MODELS : slot], out);
    return 0;
}

static int particle_gl_backend(void *context, const mu_world_particles *p, mu_render_backend *out)
{
    app *a = context;
    (void)p;
    mu_gl_backend_bind(&a->particle_gl, out);
    return 0;
}

/* NATIVE-JOINT-001: the world objects' effect models (the Tormenta tornado) through the scene draw. */
static void particle_model_gl(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                              const mu_draw_options *draw_options)
{
    app *a = context;
    mu_gl_backend *gl = &a->particle_model_gl[slot];
    if (!gl->textures)
        mu_gl_upload(gl, textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(model, draw_options, &backend, &ds);
}

/* NATIVE-NAMES-001: the stand-in plates as one window-sized overlay texture (no movie running). */
static void names_gl(app *a, int32_t width, int32_t height)
{
    size_t bytes = (size_t)width * (size_t)height * 4;
    uint8_t *overlay = calloc(bytes, 1);
    if (!overlay)
        return;
    mu_world_names_draw(a->names, overlay, width, height);
    if (!a->names_tex)
        glGenTextures(1, &a->names_tex);
    glBindTexture(GL_TEXTURE_2D, a->names_tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, overlay);
    free(overlay);
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glLoadIdentity();
    glOrtho(0, width, height, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glLoadIdentity();
    glViewport(0, 0, width, height);
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_ALPHA_TEST);
    glDisable(GL_LIGHTING);
    glEnable(GL_TEXTURE_2D);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glColor4f(1, 1, 1, 1);
    glBegin(GL_QUADS);
    glTexCoord2f(0, 0); glVertex2f(0, 0);
    glTexCoord2f(1, 0); glVertex2f((float)width, 0);
    glTexCoord2f(1, 1); glVertex2f((float)width, (float)height);
    glTexCoord2f(0, 1); glVertex2f(0, (float)height);
    glEnd();
    glBindTexture(GL_TEXTURE_2D, 0);
    glDisable(GL_BLEND);
    glEnable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
}

static long draw_gl(app *a, int32_t width, int32_t height)
{
    const mu_client_view *v = &a->walk.frame.view;
    uint8_t clear[4] = {sky[0], sky[1], sky[2], sky[3]};
    if (a->has_env)
        mu_world_env_clear(&a->env, clear);   /* glClearColor of the render scene 0x0185916b */
    mu_gl_frame(width, height, clear, v->modelview, v->projection);
    glViewport(v->gl_viewport[0], v->gl_viewport[1], v->gl_viewport[2], v->gl_viewport[3]);
    glEnable(GL_DEPTH_TEST);
    glFrontFace(GL_CCW);
    mu_terrain_sink sink = {a, g_state, g_bind, g_begin, g_tex, g_c3, g_c4, g_v, g_end};
    mu_terrain_scene scene;
    mu_world_scene(a->map, &scene);
    mu_terrain_tile_stats stats;
    memset(&stats, 0, sizeof stats);
    if (a->legacy_box)
        mu_terrain_draw(&scene, a->frustum.x_min, a->frustum.y_min, a->frustum.x_max, a->frustum.y_max,
                        mu_terrain_alpha_layers(a->map->world), &sink, &stats);
    else   /* RenderTerrain with the client's block and tile tests, in-game scene state 6 */
        mu_terrain_render(&scene, &a->frustum, 6, 0, mu_terrain_alpha_layers(a->map->world), &sink, &stats);
    a->tile_stats = stats;
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    mu_draw_options options;
    mu_draw_default_options(&options);
    a->objects_drawn = 0;
    if (a->has_objects) {   /* RenderObjects: client sector/object visibility, RenderObject per entry */
        mu_objects_visibility(&a->objects, &a->frustum, 6);
        for (int32_t k = 0; k < a->objects.rt.draw_count; ++k) {
            mu_draw_options object_options;
            mu_object_model *m = mu_objects_prepare(&a->objects, k, a->map, 6, &object_options);
            if (!m)
                continue;
            mu_render_backend backend;
            mu_gl_backend_bind(&a->object_gl[m->type], &backend);
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &object_options, &backend, &ds))
                ++a->objects_drawn;
        }
        glDisable(GL_BLEND);
        glDepthMask(GL_TRUE);
    }
    if (a->has_character)
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
            const mu_character_item *item = &a->ch.items[draw_order[n]];
            if (!item->loaded)
                continue;
            mu_render_backend backend;
            mu_gl_backend_bind(&a->items[draw_order[n]], &backend);
            if (a->has_particles)   /* the part's shadow (item render 0x0176ce74, NATIVE-PARTICLE-001) */
                mu_world_particles_character_shadow(&a->particles, &item->model, &item->bmd, &backend);
            options.textures = &item->textures;   /* bitmap GL names and component counts */
            mu_draw_stats ds = {0, 0, 0, 0};
            mu_scene_draw_model(&item->model, &options, &backend, &ds);
        }
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i) {
        const mu_world_actor *actor = &a->actors.list[i];
        float alpha = a->combat ? mu_combat_actor_alpha(a->combat, i) : 1.0f;   /* o + 0xdc */
        if (alpha <= 0.0f)
            continue;   /* removed by the dead fade */
        mu_render_backend backend;
        mu_gl_backend_bind(&a->actor_gl[i], &backend);
        if (a->has_particles)
            mu_world_particles_character_shadow(&a->particles, &actor->actor.model, &actor->actor.bmd, &backend);
        options.textures = &actor->actor.textures;
        options.alpha = alpha;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_scene_draw_model(&actor->actor.model, &options, &backend, &ds);
    }
    options.alpha = 1.0f;
    if (a->ground) {   /* RenderItems after the characters (0x0185988d in the render scene) */
        mu_world_items_draw(a->ground, items_model_gl, a);
        glDisable(GL_BLEND);
        glDepthMask(GL_TRUE);
        glDisable(GL_ALPHA_TEST);
    }
    if (a->has_env) {
        mu_world_env_target target = {a, env_gl_backend};
        mu_world_env_draw(&a->env, v->modelview, a->legacy_box ? NULL : &a->frustum, &target);
        glDisable(GL_BLEND);
        glDepthMask(GL_TRUE);
        glDisable(GL_ALPHA_TEST);
    }
    mu_gl_backend plain;
    memset(&plain, 0, sizeof plain);
    mu_render_backend backend;
    mu_gl_backend_bind(&plain, &backend);
    marker(a, &backend);
    if (a->has_particles) {   /* effect models, RenderJoints(0), the sprite section (NATIVE-PARTICLE-001, -JOINT-001) */
        mu_world_particles_draw_models(&a->particles, particle_model_gl, a);
        mu_world_particles_target target = {a, particle_gl_backend};
        mu_world_particles_draw(&a->particles, v->modelview, &target);
        glBindTexture(GL_TEXTURE_2D, 0);
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
        glDisable(GL_ALPHA_TEST);
    }
    else if (a->has_objects) {   /* --no-particles: the NATIVE-OBJECTS-002 stand-in billboards of the object fires */
        static mu_fx_vertex quads[4 * MU_OBJECT_PARTICLES];
        float eye[3], target[3];
        effect_camera(a, eye, target);
        for (int32_t b = 0; b < 2; ++b) {
            mu_fx_draw_state state;
            uint32_t n = mu_objects_particle_quads(&a->objects, b, eye, target, quads, 4 * MU_OBJECT_PARTICLES, &state);
            if (n)
                g_effect(a, quads, n, &state, b == 0 ? &a->objects.rt.fire : &a->objects.rt.smoke, NULL);
        }
        glBindTexture(GL_TEXTURE_2D, 0);
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
    }
    if (a->has_actors && a->actors.has_effects && a->actors.effects.instance_count) {
        float eye[3], target[3];
        effect_camera(a, eye, target);
        glEnable(GL_DEPTH_TEST);
        a->effects_visible = mu_effect_scene_render_to(&a->actors.effects, eye, target, v->fov,
                                                       (float)width / (float)height, v->view_near,
                                                       v->view_far * 1.4f, g_effect, a);
        glBindTexture(GL_TEXTURE_2D, 0);   /* the pass ends with glBindTexture(GL_TEXTURE_2D, 0) */
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
    }
    if (a->combat)
        combat_draw_gl(a);
    if (a->ground)
        items_labels_gl(a, width, height);
    if (a->names && !world_names_gfx_active(&a->names_gfx))
        names_gl(a, width, height);
    return stats.faces;
}

#endif

/* ---- software ---- */

static void items_model_raster(void *context, const mu_world_item_draw *d)
{
    mu_raster *raster = ((void **)context)[0];
    const app *a = ((void **)context)[1];
    raster->textures = d->textures->slots;
    raster->texture_count = d->textures->count;
    raster->texture_filter = d->textures->filter;
    raster->texture_wrap = d->textures->wrap;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    mu_renderchar_glow glow = {d->type, d->level, d->option1, d->ext, d->has_record, d->kind_a, d->kind_b,
                               d->item_kind};
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    env.time = a->map->time;
    env.quality = a->ground->config.quality;
    memcpy(env.glow_color, a->ground->config.glow_color, sizeof env.glow_color);
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = d->textures;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_renderchar_stats rs = {0, 0};
    mu_renderchar_draw_item(d->model, &glow, &env, d->light, d->alpha, &options, &backend, &ds, &rs);
}

static long draw_soft(app *a, mu_raster *raster)
{
    const mu_client_view *v = &a->walk.frame.view;
    memcpy(raster->view, v->modelview, sizeof raster->view);
    memcpy(raster->projection, v->projection, sizeof raster->projection);
    uint8_t clear[4] = {sky[0], sky[1], sky[2], sky[3]};
    if (a->has_env)
        mu_world_env_clear(&a->env, clear);
    mu_raster_clear(raster, clear);
    mu_world_draw_stats stats;
    if (a->legacy_box)
        mu_world_draw_raster(a->map, raster, a->frustum.x_min, a->frustum.y_min, a->frustum.x_max, a->frustum.y_max,
                             &stats);
    else
        mu_world_draw_raster_view(a->map, raster, &a->frustum, 6, 0, &stats);
    a->tile_stats = stats.tiles;
    if (a->has_objects) {   /* RenderObjects with the client's visibility (NATIVE-OBJECTS-002) */
        float eye[3], target[3];
        effect_camera(a, eye, target);
        a->objects_drawn = mu_objects_render_raster(&a->objects, a->map, raster, &a->frustum, 6, eye, target);
    }
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    mu_draw_options options;
    mu_draw_default_options(&options);
    raster->linear = 1;
    raster->front_ccw = 1;
    if (a->has_character)
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
            const mu_character_item *item = &a->ch.items[draw_order[n]];
            if (!item->loaded)
                continue;
            raster->textures = item->textures.slots;
            raster->texture_count = item->textures.count;
            raster->texture_filter = item->textures.filter;
            raster->texture_wrap = item->textures.wrap;
            if (a->has_particles)
                mu_world_particles_character_shadow(&a->particles, &item->model, &item->bmd, &backend);
            options.textures = &item->textures;   /* bitmap GL names and component counts */
            mu_draw_stats ds = {0, 0, 0, 0};
            mu_scene_draw_model(&item->model, &options, &backend, &ds);
        }
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i) {
        const mu_world_actor *actor = &a->actors.list[i];
        float alpha = a->combat ? mu_combat_actor_alpha(a->combat, i) : 1.0f;   /* o + 0xdc */
        if (alpha <= 0.0f)
            continue;
        if (a->has_particles)
            mu_world_particles_character_shadow(&a->particles, &actor->actor.model, &actor->actor.bmd, &backend);
        options.alpha = alpha;
        raster->textures = actor->actor.textures.slots;
        raster->texture_count = actor->actor.textures.count;
        raster->texture_filter = actor->actor.textures.filter;
        raster->texture_wrap = actor->actor.textures.wrap;
        options.textures = &actor->actor.textures;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_scene_draw_model(&actor->actor.model, &options, &backend, &ds);
    }
    if (a->ground) {   /* RenderItems (NATIVE-ITEMS-001) */
        void *context[2] = {raster, a};
        mu_world_items_draw(a->ground, items_model_raster, context);
    }
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    if (a->has_env)
        mu_world_env_draw_raster(&a->env, raster, v->modelview, a->legacy_box ? NULL : &a->frustum);
    if (a->has_particles) {   /* effect models, RenderJoints(0), the sprite section (NATIVE-PARTICLE-001, -JOINT-001) */
        mu_world_particles_draw_models_raster(&a->particles, raster);
        mu_world_particles_draw_raster(&a->particles, raster, v->modelview);
    }
    marker(a, &backend);
    if (a->has_actors && a->actors.has_effects && a->actors.effects.instance_count) {
        float eye[3], target[3];
        effect_camera(a, eye, target);
        a->effects_visible = mu_effect_scene_render(&a->actors.effects, eye, target, v->fov,
                                                    (float)raster->width / (float)raster->height, v->view_near,
                                                    v->view_far * 1.4f, raster);
    }
    if (a->combat)
        mu_combat_draw_raster(a->combat, raster);
    if (a->ground) {   /* the labels over the frame (NATIVE-ITEMS-001) */
        static mu_world_item_label labels[MU_WORLD_ITEM_LABELS];
        int32_t n = mu_world_items_labels(a->ground, labels, MU_WORLD_ITEM_LABELS);
        for (int32_t i = 0; i < n; ++i)
            mu_world_items_label_blit(a->ground, &labels[i], raster->color, raster->width, raster->height);
    }
    if (a->names)   /* NATIVE-NAMES-001: the stand-in for the movie's plates (core/mu_label) */
        mu_world_names_draw(a->names, raster->color, raster->width, raster->height);
    return stats.tiles.faces;
}

/* ---- reports ---- */

static void report_frame(const app *a, int32_t frame, uint32_t now, const char *hash, const char *png)
{
    const mu_walk *w = &a->walk;
    const mu_hero *h = &w->hero;
    const mu_client_view *v = &w->frame.view;
    printf("{\"frame\": %d, \"tick\": %u, \"steps\": %u, \"hero\": [%.2f, %.2f, %.2f], \"tile\": [%d, %d],"
           " \"angle\": %.3f, \"action\": %u, \"frame_anim\": %.3f, \"run\": %u, \"safe\": %u, \"moving\": %u,"
           " \"path\": [%u, %u, %u], \"target\": [%d, %d], \"fov\": %.3f, \"pitch\": %.3f, \"far\": %.2f,"
           " \"eye\": [%.2f, %.2f, %.2f], \"hero_tile\": %d, \"footsteps\": %u, \"voices\": %d, \"music\": %d,"
           " \"tiles\": %ld, \"box\": [%d, %d, %d, %d], \"effects\": %u, \"env\": [%u, %u, %u, %u, %u],"
           " \"particles\": [%u, %u, %u, %u], \"joints\": [%u, %u, %u], \"sha256\": \"%s\", \"png\": \"%s\"}\n",
           frame, now, w->steps, (double)h->position[0], (double)h->position[1], (double)h->position[2], h->tile[0],
           h->tile[1], (double)h->angle[2], h->action, (double)h->frame, h->run, h->safe_zone, h->movement,
           h->path.current, h->path.current_float, h->path.count, w->target[0], w->target[1], (double)v->fov,
           (double)v->angle[0], (double)v->view_far, (double)v->position[0], (double)v->position[1],
           (double)v->position[2], a->has_sound ? a->sound.hero_tile : -1, a->has_sound ? a->sound.footsteps : 0,
           a->has_sound ? mu_world_sound_voices(&a->sound) : 0, a->has_sound ? a->sound.last_music : -1,
           a->tile_stats.faces, a->frustum.x_min, a->frustum.y_min, a->frustum.x_max, a->frustum.y_max,
           a->effects_visible, a->env.stats.live_boids, a->env.stats.live_fishs, a->env.stats.live_leaves,
           a->env.stats.drawn_objects, a->env.stats.drawn_leaves, a->particles.stats.live,
           a->particles.stats.drawn_particles, a->particles.stats.drawn_sprites, a->particles.stats.shadows,
           a->particles.stats.live_joints, a->particles.stats.drawn_joint_quads, a->particles.stats.live_effects,
           hash ? hash : "", png ? png : "");
    if (a->combat)
        mu_combat_report_frame(a->combat, stdout, frame);
    if (a->ground)
        mu_world_items_report_frame(a->ground, stdout, frame);
    if (a->names) {   /* NATIVE-NAMES-001: what the movie shows (key, type, x, y, clip visible, info visible, hp,
                       * hp bar, bubble) */
        printf("{\"names_frame\": %d, \"plates\": [", frame);
        for (int32_t i = 0; i < a->names->names.plate_count; ++i) {
            const mu_names_plate *p = &a->names->names.plates[i];
            printf("%s[%d, %d, %.2f, %.2f, %d, %d, %d, %d, \"%s\"]", i ? ", " : "", (int)p->key, (int)p->type,
                   (double)p->x, (double)p->y, p->mc_visible, p->info_visible, (int)p->hp, p->hp_show,
                   p->message[0] ? "msg" : "");
        }
        printf("], \"selected\": %d}\n", (int)a->names->names.window.selected);
    }
}

static void report_summary(const app *a, const char *renderer)
{
    const mu_walk *w = &a->walk;
    printf("{\"summary\": true, \"renderer\": \"%s\", \"world\": %d, \"folder\": %d, \"camera_key\": %d,"
           " \"world_fov\": %.3f, \"distance\": %.4f, \"z_distance\": %.4f, \"near\": %.2f, \"steps\": %u,"
           " \"moves\": %u, \"arrivals\": %u, \"path_refused\": %u, \"picks\": %d, \"hits\": %d, \"walked\": %.2f,"
           " \"moving_steps\": %u, \"position_steps\": %u, \"units_per_step\": %.4f}\n",
           renderer, a->world, a->map->report.folder, a->info.key, (double)a->info.fov, (double)a->info.distance,
           (double)a->info.z_distance, (double)a->walk.frame.view.view_near, w->steps, w->moves, w->arrivals,
           w->path_refused, w->frame.picks, w->frame.pick_hits, a->walked, a->moving_steps, w->position_steps,
           w->position_steps ? w->position_distance / w->position_steps : 0.0);
    if (a->boots || a->has_auto)
        printf("{\"run\": true, \"boots\": %d, \"run_counter\": %u, \"top_speed\": %.3f, \"auto_moves\": %u,"
               " \"auto_segments\": %u, \"auto_searches\": %u, \"auto_flag\": %d, \"tile\": [%d, %d]}\n", a->boots,
               w->hero.run, (double)w->top_speed, w->auto_moves, w->auto_segments, w->auto_searches,
               w->auto_path.flag, w->hero.tile[0], w->hero.tile[1]);
    if (a->has_sound) {
        const mu_world_sound *s = &a->sound;
        printf("{\"sound\": true, \"table\": %s, \"steps\": %u, \"frames\": %u, \"footsteps\": %u,"
               " \"soil\": %u, \"grass\": %u, \"snow\": %u, \"swim\": %u, \"bridge\": %u, \"foot_resets\": %u,"
               " \"ambient_plays\": %u, \"ambient_stops\": %u, \"music_plays\": %u, \"music_stops\": %u,"
               " \"delegates\": %u, \"last_music\": %d, \"wav_frames\": %zu, \"rate\": %u}\n",
               s->has_table ? "true" : "false", s->steps, s->frames, s->footsteps, s->footstep_ids[0],
               s->footstep_ids[1], s->footstep_ids[2], s->footstep_ids[3], s->bridge_steps, s->resets,
               s->ambient_plays, s->ambient_stops, s->music_plays, s->music_stops, s->delegates, s->last_music,
               a->wav_frames, mu_world_sound_rate(s));
        if (!a->quiet)
            for (int32_t i = 0; i < s->log_count; ++i)
                printf("{\"sound_log\": \"%s\"}\n", s->log[i]);
    }
    if (a->has_env) {
        const mu_world_env_stats *e = &a->env.stats;
        printf("{\"env\": true, \"world\": %d, \"models\": %d, \"leaf_bitmap\": %d, \"steps\": %u,"
               " \"leaf_steps\": %u, \"max_boids\": %u, \"max_fishs\": %u, \"max_leaves\": %u, \"sounds\": %u,"
               " \"bird\": %u, \"bat\": %u, \"rat\": %u, \"particles\": %u, \"inits\": %u, \"kills\": %u,"
               " \"rand_calls\": %llu, \"rain_level\": %d, \"tormenta_rain\": %.3f}\n",
               a->env.world, a->env.model_count, a->env.bitmap_present[0], e->steps, e->leaf_steps, e->max_boids,
               e->max_fishs, e->max_leaves, e->sounds, e->sound_bird, e->sound_bat, e->sound_rat, e->particles,
               e->inits, e->kills, (unsigned long long)a->env.env.rand_calls, a->env.env.rain_level,
               (double)a->env.env.tormenta.rain);
    }
    if (a->has_particles) {
        const mu_world_particles_stats *p = &a->particles.stats;
        printf("{\"particles\": true, \"created\": %llu, \"dropped\": %llu, \"unsupported\": %llu,"
               " \"overflow\": %llu, \"live\": %u, \"max_live\": %u, \"steps\": %u, \"sprites_created\": %llu,"
               " \"drawn_particles\": %u, \"drawn_sprites\": %u, \"shadows\": %u, \"shadow_vertices\": %u,"
               " \"visuals\": %u, \"joints\": %llu, \"effects\": %llu, \"rand_calls\": %llu, \"bitmaps\": [",
               (unsigned long long)p->created, (unsigned long long)p->dropped, (unsigned long long)p->unsupported,
               (unsigned long long)p->overflow, p->live, p->max_live, p->steps,
               (unsigned long long)p->sprites_created, p->drawn_particles, p->drawn_sprites, p->shadows,
               p->shadow_vertices, p->visuals, (unsigned long long)p->joints, (unsigned long long)p->effects,
               (unsigned long long)a->particles.rand_calls);
        for (int i = 0; i < MU_WORLD_PT_BITMAPS; ++i)
            printf("%s%d", i ? ", " : "", a->particles.bitmap_present[i]);
        printf("]}\n");
        /* NATIVE-JOINT-001: the world objects' joint and effect pools */
        printf("{\"joints\": true, \"created\": %llu, \"unsupported\": %llu, \"full\": %llu, \"live\": %u,"
               " \"max_live\": %u, \"quads\": %u, \"effects_created\": %llu, \"effects_unsupported\": %llu,"
               " \"effects_live\": %u, \"effect_models\": %u, \"sounds\": %llu}\n",
               (unsigned long long)p->joints_created, (unsigned long long)p->joints_unsupported,
               (unsigned long long)p->joints_full, p->live_joints, p->max_joints, p->drawn_joint_quads,
               (unsigned long long)p->effects_created, (unsigned long long)p->effects_unsupported, p->live_effects,
               p->drawn_effect_models, (unsigned long long)p->sounds);
    }
    if (a->has_objects)
        printf("{\"objects\": %d, \"object_models\": %d, \"object_models_missing\": %d, \"objects_drawn\": %ld,"
               " \"objects_created\": %d, \"objects_create_unsupported\": %d, \"object_steps\": %u,"
               " \"objects_moved\": %ld, \"object_ticks\": %ld, \"object_lights\": %ld, \"object_particles\": %ld,"
               " \"object_sounds\": %ld, \"object_draw_list\": %d, \"object_lights_last_step\": %d,"
               " \"objects_animated\": %d}\n",
               a->objects.count, a->objects.models_loaded, a->objects.models_missing, a->objects_drawn,
               a->objects.rt.created, a->objects.rt.create_unsupported, a->objects.rt.steps, a->objects.rt.moved,
               a->objects.rt.ticks, a->objects.rt.light_events, a->objects.rt.particle_events,
               a->objects.rt.sound_events, a->objects.rt.draw_count, a->objects.rt.light_count,
               mu_objects_animated(&a->objects));
    if (a->has_actors) {
        const mu_world_actors *s = &a->actors;
        printf("{\"actors\": %d, \"actor_steps\": %u, \"actor_moves\": %u, \"actor_arrivals\": %u,"
               " \"effect_instances\": %u}\n", s->count, s->steps, s->moves, s->arrivals, s->effect_instances);
        for (int32_t i = 0; i < s->count; ++i) {
            const mu_world_actor *x = &s->list[i];
            printf("{\"actor\": %d, \"class\": %d, \"label\": \"%s\", \"model\": %d, \"tile\": [%d, %d],"
                   " \"action\": %u, \"frame\": %.3f, \"speed\": %.4f, \"moves\": %u, \"arrivals\": %u,"
                   " \"effects\": %d, \"light\": [%.6g, %.6g, %.6g], \"light_override\": %d}\n", i, x->server_class,
                   x->label, x->actor.spec.model_index, x->tile[0], x->tile[1], mu_actor_action(&x->actor),
                   (double)mu_actor_frame(&x->actor), (double)x->actor.last_speed, x->moves, x->arrivals,
                   x->effect_count, (double)x->actor.model.params.color[0], (double)x->actor.model.params.color[1],
                   (double)x->actor.model.params.color[2], x->actor.model.params.light_override);
        }
    }
    if (a->combat)
        mu_combat_report_summary(a->combat, stdout, a->quiet);
    if (a->ground)
        mu_world_items_report_summary(a->ground, stdout);
    if (a->names) {   /* NATIVE-NAMES-001 */
        char line[512];
        mu_names_report(&a->names->names, line, sizeof line);
        printf("{%s}\n", line);
        if (!a->quiet)
            for (int32_t i = 0; i < a->names->names.plate_count; ++i) {
                const mu_names_plate *p = &a->names->names.plates[i];
                printf("{\"plate\": %d, \"type\": %d, \"x\": %.2f, \"y\": %.2f, \"visible\": %d, \"info\": %d,"
                       " \"hp\": %d, \"message\": %d}\n", (int)p->key, (int)p->type, (double)p->x, (double)p->y,
                       p->mc_visible, p->info_visible, (int)p->hp, p->message[0] != 0);
            }
    }
    if (!a->quiet)
        for (int32_t i = 0; i < w->log_count; ++i)
            printf("{\"log\": \"%s\"}\n", w->log[i]);
}

/* ---- headless ---- */

#ifndef MU_WORLD_NO_GL
/* NATIVE-NAMES-001: the chat input's lines come back as the server echo would (demo) and show as bubbles. */
static void names_chat_hook(void *user, const char *text)
{
    app *a = user;
    if (a->names && a->names->names.env.hero)
        mu_world_names_chat(a->names, a->names->names.env.hero->name, text);
}

static void names_gfx_attach(app *a, double scale)
{
    if (!a->names || !a->gfx)
        return;
    world_names_gfx_attach(&a->names_gfx, a->gfx, &a->names->names, scale);
    mu_gfx_layer_set_chat_hook(world_gfx_layer(a->gfx), names_chat_hook, a);
}
#endif

static int headless(app *a)
{
#ifndef MU_WORLD_NO_GL
    char error[256];
    int gl = a->backend && !strcmp(a->backend, "gl");
#else
    const int gl = 0;
    if (a->backend && strcmp(a->backend, "soft")) {
        fprintf(stderr, "mu-walk renders with the software rasterizer only (--backend soft)\n");
        return 2;
    }
#endif
    if (a->out_dir && mkdir(a->out_dir, 0755) && errno != EEXIST) {
        fprintf(stderr, "cannot create %s\n", a->out_dir);
        return 1;
    }
#ifndef MU_WORLD_NO_GL
    if (gl && mu_gl_headless_begin(a->width, a->height, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    if (gl)
        gl_setup(a);
    if (gl && a->gfx_dir) {
        a->gfx = world_gfx_open(a->gfx_dir, a->root, a->width, a->height, 1.0, 1, a->gfx_open, error, sizeof error);
        if (!a->gfx)
            fprintf(stderr, "gfx: %s (continuing without the interface)\n", error);
        else
            names_gfx_attach(a, 1.0);
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
    uint32_t now = 100000;
#ifndef MU_WORLD_NO_GL
    uint32_t gfx_clock = now;
#endif
    a->walk.frame.clock.frame_tick = now;
    a->audio_start = now;
    for (int32_t frame = 0; frame < a->frames; ++frame) {
        script(a, frame);
        advance(a, now);
#ifndef MU_WORLD_NO_GL
        int gfx_draw = a->gfx && a->out_dir && a->every > 0 && (frame % a->every == 0 || frame == a->frames - 1);
        if (a->gfx)
            world_gfx_set_location(a->gfx, a->world, a->walk.hero.position[0], a->walk.hero.position[1]);
        if (a->gfx && !gfx_draw)
            world_gfx_frame(a->gfx, (double)(now - gfx_clock), 0);
#endif
        int save = a->out_dir && a->every > 0 && (frame % a->every == 0 || frame == a->frames - 1);
        char hash[65] = "", path[4096] = "";
        if (save) {
            if (gl) {
#ifndef MU_WORLD_NO_GL
                draw_gl(a, a->width, a->height);
                if (a->gfx)
                    world_gfx_frame(a->gfx, (double)(now - gfx_clock), 1);
                glFinish();
                mu_gl_read(a->width, a->height, pixels);
#endif
            } else {
                draw_soft(a, &raster);
                memcpy(pixels, raster.color, bytes);
            }
            mu_sha256_hex(pixels, bytes, hash);
            snprintf(path, sizeof path, "%s/frame-%04d.png", a->out_dir, frame);
            if (mu_png_write(path, pixels, a->width, a->height)) {
                fprintf(stderr, "cannot write %s\n", path);
                return 1;
            }
        }
        if (!a->quiet && (save || frame == a->frames - 1))
            report_frame(a, frame, now, save ? hash : NULL, save ? path : NULL);
#ifndef MU_WORLD_NO_GL
        gfx_clock = now;
#endif
        now += 12;   /* virtual render time, then the client's cap */
        int32_t sleep = mu_walk_end_render(&a->walk);
        if (sleep > 0)
            now += (uint32_t)sleep;
        sound_frame(a);   /* after the cap, as 0x0185280c in the frame driver */
        if (a->has_sound && a->wav_path && wav_append(a, audio_due(a, now))) {
            fprintf(stderr, "audio buffer allocation failed\n");
            return 1;
        }
    }
    if (a->has_sound && a->wav_path) {
        if (mu_wav_write16(a->wav_path, a->wav, (uint32_t)a->wav_frames, 2, mu_world_sound_rate(&a->sound))) {
            fprintf(stderr, "cannot write %s\n", a->wav_path);
            return 1;
        }
    }
#ifndef MU_WORLD_NO_GL
    report_summary(a, gl ? mu_gl_renderer() : "software");
    if (a->gfx) {
        char line[512];
        world_gfx_report(a->gfx, line, sizeof line);
        printf("{%s}\n", line);
        world_gfx_close(a->gfx);
        a->gfx = NULL;
    }
    if (gl) {
        gl_teardown(a);
        mu_gl_headless_end();
    }
#else
    report_summary(a, "software");
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
static void audio_open(app *a)
{
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
    a->audio_device = SDL_OpenAudioDevice(NULL, 0, &want, &have, 0);
    if (!a->audio_device) {
        fprintf(stderr, "SDL audio: %s (continuing without sound output)\n", SDL_GetError());
        return;
    }
    SDL_PauseAudioDevice(a->audio_device, 0);
}

static void audio_pump(app *a, uint32_t now)
{
    if (!a->has_sound)
        return;
    const uint32_t lead = 120;   /* ms queued ahead of the clock */
    uint32_t frames = audio_due(a, now + lead);
    if (!frames)
        return;
    static float buffer[2 * 48000];
    uint32_t rate = mu_world_sound_rate(&a->sound);
    if (frames > rate)   /* after a stall, drop instead of queueing seconds of audio */
        frames = rate;
    mu_world_sound_mix(&a->sound, buffer, frames);
    a->audio_frames += frames;
    if (a->audio_device)
        SDL_QueueAudio(a->audio_device, buffer, frames * 2 * (uint32_t)sizeof(float));
}

static int windowed(app *a)
{
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
    a->walk.frame.view.window_width = (uint32_t)dw;
    a->walk.frame.view.window_height = (uint32_t)dh;
    a->walk.frame.mouse.scale_x = (float)dw / 640.0f;
    a->walk.frame.mouse.scale_y = (float)dh / 480.0f;
    int32_t script_width = a->width, script_height = a->height;
    a->width = dw;
    a->height = dh;
    gl_setup(a);
    if (a->gfx_dir) {
        char error[512];
        a->gfx = world_gfx_open(a->gfx_dir, a->root, dw, dh, scale, 1, a->gfx_open, error, sizeof error);
        if (a->gfx) {
            SDL_StartTextInput();
            names_gfx_attach(a, scale);
        }
        else
            fprintf(stderr, "gfx: %s (continuing without the interface)\n", error);
    }
    audio_open(a);
    a->walk.frame.clock.frame_tick = SDL_GetTicks();
    uint32_t start = SDL_GetTicks(), frames = 0;
    a->audio_start = start;
    int running = 1, escapes = 0;
    int32_t printed = 0;
    (void)script_width;
    (void)script_height;
    while (running) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (a->gfx && world_gfx_event(a->gfx, &e, scale))
                continue;   /* the interface took it */
            if (e.type == SDL_QUIT) {
                running = 0;
            } else if (e.type == SDL_MOUSEMOTION) {
                mu_walk_message(&a->walk, MU_WM_MOUSEMOVE, 0,
                                pack((int)(e.motion.x * scale), (int)(e.motion.y * scale)));
            } else if (e.type == SDL_MOUSEBUTTONDOWN || e.type == SDL_MOUSEBUTTONUP) {
                int down = e.type == SDL_MOUSEBUTTONDOWN;
                uint32_t message = e.button.button == SDL_BUTTON_LEFT ? (down ? 0x201u : 0x202u)
                                 : e.button.button == SDL_BUTTON_RIGHT ? (down ? 0x204u : 0x205u)
                                 : (down ? 0x207u : 0x208u);
                mu_walk_message(&a->walk, message, 0, pack((int)(e.button.x * scale), (int)(e.button.y * scale)));
            } else if (e.type == SDL_MOUSEWHEEL) {
                int delta = e.wheel.y * 120;
                mu_walk_message(&a->walk, MU_WM_MOUSEWHEEL, (uint32_t)(uint16_t)delta << 16, 0);
            } else if (e.type == SDL_KEYDOWN || e.type == SDL_KEYUP) {
                int vk = mu_vk_from_hid((int)e.key.keysym.scancode);
                int down = e.type == SDL_KEYDOWN;
                mu_walk_key(&a->walk, vk, down);
                mu_walk_message(&a->walk, down ? 0x100u : 0x101u, (uint32_t)vk, 0);
                if (down && !e.key.repeat && vk == 0x1b && ++escapes >= 2)
                    running = 0;
                else if (down && vk != 0x1b)
                    escapes = 0;
                if (down && !e.key.repeat && a->ground && vk == 0x12)   /* Alt: setItemView(!view) (0x00efc7d3) */
                    mu_world_items_alt(a->ground);
                if (down && !e.key.repeat && a->ground && vk == 0x20)   /* space: the nearest item (0x00efd9ab) */
                    mu_world_items_space(a->ground);
                if (down && !e.key.repeat && a->combat && vk >= 0x30 && vk <= 0x39) {
                    /* 1..6 (NATIVE-COMBAT-001), 7 Evil Spirit, 8 Hellfire, 9 Inferno, 0 Cyclone */
                    static const int32_t keys[10] = {22, 4, 17, 22, 41, 24, 26, 9, 10, 14};
                    mu_combat_cast(a->combat, keys[vk - 0x30], -1);
                }
                if (down && !e.key.repeat && vk == 0x4f) {   /* O: screenshot */
                    uint8_t *pixels = malloc((size_t)dw * (size_t)dh * 4);
                    if (pixels) {
                        mu_gl_read(dw, dh, pixels);
                        mu_png_write("mu-world-screenshot.png", pixels, dw, dh);
                        free(pixels);
                    }
                }
            }
        }
        script(a, (int32_t)frames);
        advance(a, SDL_GetTicks());
        draw_gl(a, dw, dh);
        if (a->gfx) {
            static uint32_t gfx_last;
            uint32_t t = SDL_GetTicks();
            world_gfx_set_location(a->gfx, a->world, a->walk.hero.position[0], a->walk.hero.position[1]);
            world_gfx_frame(a->gfx, gfx_last ? (double)(t - gfx_last) : 0.0, 1);
            gfx_last = t;
        }
        SDL_GL_SwapWindow(window);
        ++frames;
        int32_t sleep = mu_walk_end_render(&a->walk);
        if (sleep > 0)
            SDL_Delay((uint32_t)sleep);
        sound_frame(a);   /* after the cap, as 0x0185280c in the frame driver */
        audio_pump(a, SDL_GetTicks());
        if (frames % 25 == 0) {
            const mu_hero *h = &a->walk.hero;
            char title[160];
            snprintf(title, sizeof title, "mu-world  World%d  tile %d,%d  %s  FOV %.0f  %.1f fps",
                     a->map->report.folder, h->tile[0], h->tile[1], h->movement ? "walking" : "standing",
                     (double)a->walk.frame.view.fov,
                     (double)frames * 1000.0 / (double)(SDL_GetTicks() - start + 1));
            SDL_SetWindowTitle(window, title);
        }
        for (; printed < a->walk.log_count; ++printed)
            if (!a->quiet)
                printf("%s\n", a->walk.log[printed]);
        if (a->walk.log_count == MU_WALK_LOG) {
            a->walk.log_count = 0;
            printed = 0;
        }
        if (a->seconds > 0 && (SDL_GetTicks() - start) / 1000.0 >= a->seconds)
            running = 0;
    }
    double elapsed = (SDL_GetTicks() - start) / 1000.0;
    printf("{\"frames\": %u, \"seconds\": %.2f, \"fps\": %.2f, \"logic_steps\": %u, \"walked\": %.1f,"
           " \"arrivals\": %u, \"audio_device\": %s, \"audio_seconds\": %.2f}\n", frames, elapsed,
           elapsed > 0 ? frames / elapsed : 0.0, a->walk.steps, a->walked, a->walk.arrivals,
           a->audio_device ? "true" : "false",
           a->has_sound ? (double)a->audio_frames / (double)mu_world_sound_rate(&a->sound) : 0.0);
    report_summary(a, mu_gl_renderer());
    if (a->audio_device)
        SDL_CloseAudioDevice(a->audio_device);
    world_gfx_close(a->gfx);
    a->gfx = NULL;
    gl_teardown(a);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}

#endif

/* ---- options ---- */

static int parse_waypoints(app *a, const char *text)
{
    a->waypoint_count = 0;
    const char *p = text;
    while (*p && a->waypoint_count < MAX_WAYPOINTS) {
        int x, y, used = 0;
        if (sscanf(p, " %d,%d%n", &x, &y, &used) != 2)
            return 1;
        if (x < 0 || y < 0 || x > 255 || y > 255)
            return 1;
        a->waypoints[a->waypoint_count][0] = x;
        a->waypoints[a->waypoint_count++][1] = y;
        p += used;
        while (*p == ' ' || *p == ';')
            ++p;
    }
    return 0;
}

static int parse_wheels(app *a, const char *text)
{
    a->wheel_count = 0;
    const char *p = text;
    while (*p && a->wheel_count < MAX_WHEELS) {
        int frame, delta, used = 0;
        if (sscanf(p, " %d:%d%n", &frame, &delta, &used) != 2)
            return 1;
        a->wheel_frame[a->wheel_count] = frame;
        a->wheel_delta[a->wheel_count++] = delta;
        p += used;
        while (*p == ' ' || *p == ';')
            ++p;
    }
    return 0;
}

/* NATIVE-NAMES-001: "F:text;F:text" (the hero's chat lines on the given frames). */
static int parse_chat(app *a, const char *text)
{
    const char *p = text;
    while (*p && a->chat_count < 16) {
        char *end;
        long f = strtol(p, &end, 10);
        if (end == p || *end != ':')
            return 1;
        const char *t = end + 1, *e = strchr(t, ';');
        size_t len = e ? (size_t)(e - t) : strlen(t);
        if (len >= sizeof a->chat_text[0])
            len = sizeof a->chat_text[0] - 1;
        a->chat_frame[a->chat_count] = (int32_t)f;
        memcpy(a->chat_text[a->chat_count], t, len);
        a->chat_text[a->chat_count][len] = 0;
        a->chat_count++;
        p = e ? e + 1 : t + len;
    }
    return 0;
}

static int usage(void)
{
    fprintf(stderr, "usage: mu-world --game-root ROOT [--world N] [--class C] [--tile X,Y] [--angle D] [--near Z]\n"
                    "                [--width W --height H] [--seconds S] [--walk \"X,Y ...\"] [--wheel \"F:+1 ...\"]\n"
                    "                [--headless --frames N --out-dir DIR --backend gl|soft --every K --pause P]\n"
                    "                [--player Player.bmd] [--quiet]\n"
                    "                [--boots L] [--auto-move X,Y]   run gear; long-distance auto move (S+click)\n"
                    "                [--sound-table TSV] [--no-audio] [--wav OUT.wav] [--audio-rate HZ]\n"
                    "                [--placement DEMO.txt] [--legacy-box]\n"
                    "                [--objects-dir DIR]   local decoded EncTerrain<n>.plain files\n"
                    "                [--combat] [--combat-weapon none|sword|twohand|spear|bow|crossbow|staff]\n"
                    "                [--attack-speed N] [--combat-seed N] [--hero-hp N] [--combat-script \"F:attack:ACTOR F:skill:N:ACTOR ...\"]\n"
                    "                [--items] [--no-items] [--item-script \"F:drop:CODE[:LEVEL[:X,Y]] F:alt F:space F:hover:N F:pick:N\"]\n"
                    "                [--item-seed N] [--item-latency STEPS] [--item-despawn STEPS]\n"
                    "                [--no-env] [--env-tga-leaves] [--env-seed N] [--no-particles] [--particle-seed N]\n"
                    "                [--joint-demo SUB]   a lightning joint 0x7f7d SUB above the hero every 20 steps\n"
                    "                [--gfx DIR [--gfx-open inventory,character]]   GFx interface (converted movies)\n"
                    "                [--no-names] [--hero-name NAME] [--monster-info 0|1] [--chat-script \"F:text;F:text\"]\n");
    return 2;
}

int main(int argc, char **argv)
{
    static app a;
    memset(&a, 0, sizeof a);
    a.width = 1280;
    a.height = 800;
    a.frames = 300;
    a.every = 10;
    a.pause = 8;
    a.class_byte = 0x01;      /* Dark Knight */
    a.env_seed = 1;           /* rand() state at world entry: the CRT default (viewer choice) */
    a.particle_seed = 1;
    a.joint_demo = -1;
    a.tile[0] = 133;          /* Lorencia town square */
    a.tile[1] = 127;
    a.angle = 0.0f;
    a.near_plane = 20.0f;     /* CameraViewNear 0x01cf162c (static data, runtime data-section capture) */
    a.backend = "gl";
    a.audio = 1;
    a.audio_rate = 44100;
    mu_combat_default_config(&a.combat_config);
    mu_world_items_default_config(&a.items_config);
    for (int i = 1; i < argc; ++i) {
        const char *k = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(k, "--headless")) { a.headless = 1; continue; }
        if (!strcmp(k, "--quiet")) { a.quiet = 1; continue; }
        if (!strcmp(k, "--no-audio")) { a.audio = 0; continue; }
        if (!strcmp(k, "--legacy-box")) { a.legacy_box = 1; continue; }
        if (!strcmp(k, "--combat")) { a.combat_on = 1; continue; }
        if (!strcmp(k, "--no-env")) { a.no_env = 1; continue; }
        if (!strcmp(k, "--env-tga-leaves")) { a.env_tga = 1; continue; }
        if (!strcmp(k, "--no-particles")) { a.no_particles = 1; continue; }
        if (!strcmp(k, "--items")) { a.items_on = 1; continue; }
        if (!strcmp(k, "--no-items")) { a.no_items = 1; continue; }
        if (!strcmp(k, "--no-names")) { a.no_names = 1; continue; }
        if (!v)
            return usage();
        ++i;
        if (!strcmp(k, "--game-root")) a.root = v;
        else if (!strcmp(k, "--player")) a.player = v;
        else if (!strcmp(k, "--world")) a.world = atoi(v);
        else if (!strcmp(k, "--class")) a.class_byte = (uint8_t)strtol(v, NULL, 0);
        else if (!strcmp(k, "--tile")) { if (sscanf(v, "%d,%d", &a.tile[0], &a.tile[1]) != 2) return usage(); }
        else if (!strcmp(k, "--angle")) a.angle = strtof(v, NULL);
        else if (!strcmp(k, "--near")) a.near_plane = strtof(v, NULL);
        else if (!strcmp(k, "--width")) a.width = atoi(v);
        else if (!strcmp(k, "--height")) a.height = atoi(v);
        else if (!strcmp(k, "--seconds")) a.seconds = strtof(v, NULL);
        else if (!strcmp(k, "--frames")) a.frames = atoi(v);
        else if (!strcmp(k, "--every")) a.every = atoi(v);
        else if (!strcmp(k, "--pause")) a.pause = atoi(v);
        else if (!strcmp(k, "--out-dir")) a.out_dir = v;
        else if (!strcmp(k, "--backend")) a.backend = v;
        else if (!strcmp(k, "--walk")) { if (parse_waypoints(&a, v)) return usage(); }
        else if (!strcmp(k, "--boots")) a.boots = atoi(v);
        else if (!strcmp(k, "--auto-move")) {
            if (sscanf(v, "%d,%d", &a.auto_target[0], &a.auto_target[1]) != 2) return usage();
            a.has_auto = 1;
        }
        else if (!strcmp(k, "--wheel")) { if (parse_wheels(&a, v)) return usage(); }
        else if (!strcmp(k, "--sound-table")) a.sound_table = v;
        else if (!strcmp(k, "--wav")) a.wav_path = v;
        else if (!strcmp(k, "--audio-rate")) a.audio_rate = atoi(v);
        else if (!strcmp(k, "--placement")) a.placement = v;
        else if (!strcmp(k, "--objects-dir")) a.objects_dir = v;
        else if (!strcmp(k, "--combat-weapon")) {
            static const char *names[] = {"none", "sword", "twohand", "spear", "bow", "crossbow", "staff"};
            int found = -1;
            for (int n = 0; n < 7; ++n)
                if (!strcmp(v, names[n]))
                    found = n;
            if (found < 0)
                return usage();
            a.combat_config.weapon = found;
            a.combat_on = 1;
        }
        else if (!strcmp(k, "--attack-speed")) { a.combat_config.attack_speed = strtof(v, NULL); a.combat_on = 1; }
        else if (!strcmp(k, "--combat-seed")) { a.combat_config.seed = (uint32_t)strtoul(v, NULL, 0); a.combat_on = 1; }
        else if (!strcmp(k, "--hero-hp")) { a.combat_config.hero_hp = atoi(v); a.combat_on = 1; }
        else if (!strcmp(k, "--combat-script")) {
            if (mu_combat_script_parse(&a.combat_script, v))
                return usage();
            a.combat_on = 1;
        }
        else if (!strcmp(k, "--env-seed")) a.env_seed = (uint32_t)strtoul(v, NULL, 0);
        else if (!strcmp(k, "--item-script")) {
            if (mu_world_items_script_parse(&a.item_script, v))
                return usage();
            a.items_on = 1;
        }
        else if (!strcmp(k, "--item-seed")) a.items_config.seed = (uint32_t)strtoul(v, NULL, 0);
        else if (!strcmp(k, "--item-latency")) a.items_config.drop_latency = atoi(v);
        else if (!strcmp(k, "--item-despawn")) a.items_config.despawn_steps = atoi(v);
#ifndef MU_WORLD_NO_GL
        else if (!strcmp(k, "--gfx")) a.gfx_dir = v;
        else if (!strcmp(k, "--gfx-open")) a.gfx_open = v;
#endif
        else if (!strcmp(k, "--particle-seed")) a.particle_seed = (uint32_t)strtoul(v, NULL, 0);
        else if (!strcmp(k, "--joint-demo")) a.joint_demo = (int32_t)strtol(v, NULL, 0);
        else if (!strcmp(k, "--hero-name")) a.hero_name = v;
        else if (!strcmp(k, "--monster-info")) a.no_monster_info = !atoi(v);
        else if (!strcmp(k, "--chat-script")) { if (parse_chat(&a, v)) return usage(); }
        else return usage();
    }
    if (a.audio_rate < 8000 || a.audio_rate > 48000 || (a.wav_path && !a.audio))
        return usage();
    if (!a.root || a.width < 64 || a.height < 64 || a.width > 8192 || a.height > 8192 || a.frames < 1 ||
        a.tile[0] < 0 || a.tile[1] < 0 || a.tile[0] > 255 || a.tile[1] > 255)
        return usage();
    if (load(&a)) {
        unload(&a);
        return 1;
    }
#ifndef MU_WORLD_NO_GL
    int status = a.headless ? headless(&a) : windowed(&a);
#else
    int status = headless(&a);
#endif
    unload(&a);
    return status;
}
