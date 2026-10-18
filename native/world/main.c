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
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_scene.h"
#include "../core/mu_terrain.h"
#include "../core/mu_walk.h"
#include "../core/mu_wav.h"
#include "../core/mu_world_actors.h"
#include "../core/mu_world_audio.h"
#ifndef MU_WORLD_NO_GL
#include "../viewer/gl_backend.h"
#include "../viewer/gl_headless.h"
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
    mu_terrain_frustum frustum;
    mu_terrain_tile_stats tile_stats;
    uint32_t effects_visible;
    float *wav;
    size_t wav_frames, wav_capacity;
    uint64_t audio_frames;         /* stereo frames produced since start */
    uint32_t audio_start;          /* clock (ms) at which audio started */
#ifndef MU_WORLD_NO_GL
    mu_gl_backend actor_gl[MU_WORLD_ACTORS_MAX];
    const mu_image *fx_images[64];
    GLuint fx_names[64];
    int fx_count;
    SDL_AudioDeviceID audio_device;
#endif
} app;

static const int draw_order[MU_CHARACTER_ITEMS] = {5, 4, 3, 2, 1, 0, 6, 7, 8};
static const uint8_t sky[4] = {0, 0, 0, 255};

/* ---- loading ---- */

static void on_step(void *context, mu_walk *w);

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
    mu_model_default_params(&params);
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
    a->walk.step_hook = on_step;
    a->walk.step_context = a;
    return 0;
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
    if (a->has_sound)
        mu_world_sound_close(&a->sound);
    free(a->wav);
}

/* ---- script ---- */

static uint32_t pack(int x, int y)
{
    return ((uint32_t)(uint16_t)y << 16) | (uint16_t)x;
}

static void script(app *a, int32_t frame)
{
    mu_walk *w = &a->walk;
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
    if (a->next_waypoint >= a->waypoint_count)
        return;
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
    terrain_frame(a, now);
    if (a->has_actors)
        mu_world_actors_frame(&a->actors, 0.1f);   /* effect node update per frame, dt [0x01cf103c] = 0.1 */
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
    for (int32_t i = 0; i < MU_WORLD_ACTORS_MAX; ++i)
        memset(&a->actor_gl[i], 0, sizeof a->actor_gl[i]);
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i)
        mu_gl_upload(&a->actor_gl[i], &a->actors.list[i].actor.textures, 0);
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
    for (int i = 0; i < a->fx_count; ++i)
        glDeleteTextures(1, &a->fx_names[i]);
    a->fx_count = 0;
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

static long draw_gl(app *a, int32_t width, int32_t height)
{
    const mu_client_view *v = &a->walk.frame.view;
    mu_gl_frame(width, height, sky, v->modelview, v->projection);
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
    if (a->has_character)
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
            const mu_character_item *item = &a->ch.items[draw_order[n]];
            if (!item->loaded)
                continue;
            mu_render_backend backend;
            mu_gl_backend_bind(&a->items[draw_order[n]], &backend);
            options.textures = &item->textures;   /* bitmap GL names and component counts */
            mu_draw_stats ds = {0, 0, 0, 0};
            mu_scene_draw_model(&item->model, &options, &backend, &ds);
        }
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i) {
        const mu_world_actor *actor = &a->actors.list[i];
        mu_render_backend backend;
        mu_gl_backend_bind(&a->actor_gl[i], &backend);
        options.textures = &actor->actor.textures;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_scene_draw_model(&actor->actor.model, &options, &backend, &ds);
    }
    mu_gl_backend plain;
    memset(&plain, 0, sizeof plain);
    mu_render_backend backend;
    mu_gl_backend_bind(&plain, &backend);
    marker(a, &backend);
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
    return stats.faces;
}

#endif

/* ---- software ---- */

static long draw_soft(app *a, mu_raster *raster)
{
    const mu_client_view *v = &a->walk.frame.view;
    memcpy(raster->view, v->modelview, sizeof raster->view);
    memcpy(raster->projection, v->projection, sizeof raster->projection);
    mu_raster_clear(raster, sky);
    mu_world_draw_stats stats;
    if (a->legacy_box)
        mu_world_draw_raster(a->map, raster, a->frustum.x_min, a->frustum.y_min, a->frustum.x_max, a->frustum.y_max,
                             &stats);
    else
        mu_world_draw_raster_view(a->map, raster, &a->frustum, 6, 0, &stats);
    a->tile_stats = stats.tiles;
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
            options.textures = &item->textures;   /* bitmap GL names and component counts */
            mu_draw_stats ds = {0, 0, 0, 0};
            mu_scene_draw_model(&item->model, &options, &backend, &ds);
        }
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i) {
        const mu_world_actor *actor = &a->actors.list[i];
        raster->textures = actor->actor.textures.slots;
        raster->texture_count = actor->actor.textures.count;
        raster->texture_filter = actor->actor.textures.filter;
        raster->texture_wrap = actor->actor.textures.wrap;
        options.textures = &actor->actor.textures;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_scene_draw_model(&actor->actor.model, &options, &backend, &ds);
    }
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    marker(a, &backend);
    if (a->has_actors && a->actors.has_effects && a->actors.effects.instance_count) {
        float eye[3], target[3];
        effect_camera(a, eye, target);
        a->effects_visible = mu_effect_scene_render(&a->actors.effects, eye, target, v->fov,
                                                    (float)raster->width / (float)raster->height, v->view_near,
                                                    v->view_far * 1.4f, raster);
    }
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
           " \"tiles\": %ld, \"box\": [%d, %d, %d, %d], \"effects\": %u, \"sha256\": \"%s\", \"png\": \"%s\"}\n",
           frame, now, w->steps, (double)h->position[0], (double)h->position[1], (double)h->position[2], h->tile[0],
           h->tile[1], (double)h->angle[2], h->action, (double)h->frame, h->run, h->safe_zone, h->movement,
           h->path.current, h->path.current_float, h->path.count, w->target[0], w->target[1], (double)v->fov,
           (double)v->angle[0], (double)v->view_far, (double)v->position[0], (double)v->position[1],
           (double)v->position[2], a->has_sound ? a->sound.hero_tile : -1, a->has_sound ? a->sound.footsteps : 0,
           a->has_sound ? mu_world_sound_voices(&a->sound) : 0, a->has_sound ? a->sound.last_music : -1,
           a->tile_stats.faces, a->frustum.x_min, a->frustum.y_min, a->frustum.x_max, a->frustum.y_max,
           a->effects_visible, hash ? hash : "", png ? png : "");
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
    if (a->has_actors) {
        const mu_world_actors *s = &a->actors;
        printf("{\"actors\": %d, \"actor_steps\": %u, \"actor_moves\": %u, \"actor_arrivals\": %u,"
               " \"effect_instances\": %u}\n", s->count, s->steps, s->moves, s->arrivals, s->effect_instances);
        for (int32_t i = 0; i < s->count; ++i) {
            const mu_world_actor *x = &s->list[i];
            printf("{\"actor\": %d, \"class\": %d, \"label\": \"%s\", \"model\": %d, \"tile\": [%d, %d],"
                   " \"action\": %u, \"frame\": %.3f, \"speed\": %.4f, \"moves\": %u, \"arrivals\": %u,"
                   " \"effects\": %d}\n", i, x->server_class, x->label, x->actor.spec.model_index, x->tile[0],
                   x->tile[1], mu_actor_action(&x->actor), (double)mu_actor_frame(&x->actor),
                   (double)x->actor.last_speed, x->moves, x->arrivals, x->effect_count);
        }
    }
    if (!a->quiet)
        for (int32_t i = 0; i < w->log_count; ++i)
            printf("{\"log\": \"%s\"}\n", w->log[i]);
}

/* ---- headless ---- */

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
    a->walk.frame.clock.frame_tick = now;
    a->audio_start = now;
    for (int32_t frame = 0; frame < a->frames; ++frame) {
        script(a, frame);
        advance(a, now);
        int save = a->out_dir && a->every > 0 && (frame % a->every == 0 || frame == a->frames - 1);
        char hash[65] = "", path[4096] = "";
        if (save) {
            if (gl) {
#ifndef MU_WORLD_NO_GL
                draw_gl(a, a->width, a->height);
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

static int usage(void)
{
    fprintf(stderr, "usage: mu-world --game-root ROOT [--world N] [--class C] [--tile X,Y] [--angle D] [--near Z]\n"
                    "                [--width W --height H] [--seconds S] [--walk \"X,Y ...\"] [--wheel \"F:+1 ...\"]\n"
                    "                [--headless --frames N --out-dir DIR --backend gl|soft --every K --pause P]\n"
                    "                [--player Player.bmd] [--quiet]\n"
                    "                [--sound-table TSV] [--no-audio] [--wav OUT.wav] [--audio-rate HZ]\n"
                    "                [--placement DEMO.txt] [--legacy-box]\n");
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
    a.tile[0] = 133;          /* Lorencia town square */
    a.tile[1] = 127;
    a.angle = 0.0f;
    a.near_plane = 20.0f;     /* CameraViewNear 0x01cf162c (static data, runtime data-section capture) */
    a.backend = "gl";
    a.audio = 1;
    a.audio_rate = 44100;
    for (int i = 1; i < argc; ++i) {
        const char *k = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(k, "--headless")) { a.headless = 1; continue; }
        if (!strcmp(k, "--quiet")) { a.quiet = 1; continue; }
        if (!strcmp(k, "--no-audio")) { a.audio = 0; continue; }
        if (!strcmp(k, "--legacy-box")) { a.legacy_box = 1; continue; }
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
        else if (!strcmp(k, "--wheel")) { if (parse_wheels(&a, v)) return usage(); }
        else if (!strcmp(k, "--sound-table")) a.sound_table = v;
        else if (!strcmp(k, "--wav")) a.wav_path = v;
        else if (!strcmp(k, "--audio-rate")) a.audio_rate = atoi(v);
        else if (!strcmp(k, "--placement")) a.placement = v;
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
