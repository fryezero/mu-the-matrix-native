/* WORLD-RT-001: the world runtime (mu_world_rt.h).  world/main.c's load, unload, travel, advance, the two draw
 * functions, the GL lifetime and the reports, with each subsystem's code moved into its part (parts/<part>.c) and
 * called through parts.def's columns in world/main.c's order. */
#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_lang.h"
#include "../core/mu_perf.h"
#ifndef MU_WORLD_NO_GL
#include "../gfx/mu_gfx_layer.h"
#include "../viewer/gl_backend.h"
#include "world_gfx_options.h"
#endif
#include "world_rt_internal.h"

const int mu_world_draw_order[MU_CHARACTER_ITEMS] = {5, 4, 3, 2, 1, 0, 6, 7, 8};
static const uint8_t sky[4] = {0, 0, 0, 255};

/* ---- parts.def: the rows and the order of each column ---- */

enum { COL_PRE_TICK, COL_TICK, COL_FRAME, COL_DRAW_GL, COL_DRAW_SOFT, COL_REPORT, COLS };

typedef struct part_row {
    const mu_world_part_ops *ops;
    int16_t order[COLS];
} part_row;

static const part_row ROWS[MU_PART_COUNT] = {
#define MU_PART(id, ops, pre_tick, tick, frame, draw_gl, draw_soft, report) \
    {&ops, {pre_tick, tick, frame, draw_gl, draw_soft, report}},
#include "parts.def"
#undef MU_PART
};

static int has_hook(const mu_world_part_ops *o, int col)
{
    switch (col) {
    case COL_PRE_TICK: return o->pre_tick != NULL;
    case COL_TICK: return o->tick != NULL;
    case COL_FRAME: return o->frame != NULL;
    case COL_DRAW_GL: return o->draw_gl != NULL;
    case COL_DRAW_SOFT: return o->draw_soft != NULL;
    default: return o->report_frame != NULL || o->report_summary != NULL;
    }
}

/* Sorts each column once and checks the list: a hook exactly where the column has a number (draw_gl hooks are
 * absent from a MU_WORLD_NO_GL build), and no two rows with one number. */
static int seq_build(mu_world_rt *a, char *error, size_t error_size)
{
    static const char *const COLUMN[COLS] = {"pre_tick", "tick", "frame", "draw_gl", "draw_soft", "report"};
    for (int c = 0; c < COLS; ++c) {
        int n = 0;
        for (int i = 0; i < MU_PART_COUNT; ++i) {
            int order = ROWS[i].order[c], hook = has_hook(ROWS[i].ops, c);
#ifdef MU_WORLD_NO_GL
            if (c == COL_DRAW_GL)
                hook = order != 0;
#endif
            if ((order != 0) != hook) {
                snprintf(error, error_size, "parts.def: %s %s %s", ROWS[i].ops->name, COLUMN[c],
                         order ? "has a number but no hook" : "has a hook but no number");
                return 1;
            }
            if (!order)
                continue;
            int k = n++;
            for (; k > 0 && ROWS[a->seq[c][k - 1]].order[c] > order; --k)
                a->seq[c][k] = a->seq[c][k - 1];
            if (k > 0 && ROWS[a->seq[c][k - 1]].order[c] == order) {
                snprintf(error, error_size, "parts.def: %s and %s share %s order %d", ROWS[a->seq[c][k - 1]].ops->name,
                         ROWS[i].ops->name, COLUMN[c], order);
                return 1;
            }
            a->seq[c][k] = (int8_t)i;
        }
        a->seq[c][n] = -1;
    }
    return 0;
}

#define EACH(col, i) for (const int8_t *each_ = a->seq[col]; ((i) = *each_) >= 0; ++each_)

/* ---- the logic step hooks (mu_walk_step) ---- */

/* MoveHero's attack, pick-up and NPC cases run before its walk and click code (world/main.c combat_pre_step). */
static void pre_tick(void *context, mu_walk *w)
{
    (void)w;
    mu_world_rt *a = context;
    int i;
    EACH(COL_PRE_TICK, i)
        ROWS[i].ops->pre_tick(a, a->part[i]);
}

/* End of every logic step (mu_walk_step): the client's MoveCharacters runs the hero's per-character routine
 * and every other character, then the in-world tick's movers (world/main.c on_step). */
static void tick(void *context, mu_walk *w)
{
    (void)w;
    mu_world_rt *a = context;
    int i;
    EACH(COL_TICK, i)
        ROWS[i].ops->tick(a, a->part[i]);
}

/* ---- loading ---- */

int world_rt_load(mu_world_rt *a)
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
    a->walk.step_hook = tick;
    a->walk.step_context = a;
    a->walk.pre_step_hook = pre_tick;   /* the parts' pre_tick hooks each test their own subsystem */
    a->walk.pre_step_context = a;
    for (int i = 0; i < MU_PART_COUNT; ++i)
        if (ROWS[i].ops->open && ROWS[i].ops->open(a, a->part[i]))
            return 1;
#ifndef MU_WORLD_NO_GL
    if(a->gfx)world_gfx_rebind_skills(a->gfx,mu_world_rt_skill_session(a));
#endif
    return 0;
}

void world_rt_unload(mu_world_rt *a)
{
#ifndef MU_WORLD_NO_GL
    if(a->gfx)world_gfx_rebind_skills(a->gfx,NULL);
#endif
    for (int i = MU_PART_COUNT - 1; i >= 0; --i)
        if (ROWS[i].ops->close)
            ROWS[i].ops->close(a, a->part[i]);
    mu_walk_free(&a->walk);
    if (a->has_character)
        mu_character_free(&a->ch);
    if (a->map)
        mu_world_free(a->map);
}

/* The front end's equipment (the chosen character's items), after load() equipped the class parts: with combat
 * its weapons replace the stand-in weapon. */
int world_rt_apply_equipment(mu_world_rt *a, char *error, size_t error_size)
{
    if (!a->equip_set)
        return 0;
    int has_weapon = 0;
    for (int slot = 0; slot < MU_CHARACTER_WEAPON_SLOTS; ++slot)
        has_weapon |= a->equip[MU_CHARACTER_WEAPON_ITEM(slot)] && a->equip[MU_CHARACTER_WEAPON_ITEM(slot)][0];
    if (a->equip_combat && has_weapon)
        for (int slot = 0; slot < MU_CHARACTER_WEAPON_SLOTS; ++slot)
            mu_character_set_item(&a->ch, MU_CHARACTER_WEAPON_ITEM(slot), NULL, 0, error, error_size);
    for (int i = 1; i < MU_CHARACTER_ITEMS; ++i)
        if (a->equip[i] && a->equip[i][0] && mu_character_set_item(&a->ch, i, a->equip[i], 0, error, error_size))
            return 1;
    mu_walk_place(&a->walk, &a->ch);
    return 0;
}

/* ---- NATIVE-MAP-001: travel ---- */

/* The teleport answer (C3 1C, ReceiveTeleport 0x0128136d): a world change unloads the world and loads the
 * target with the existing loader (load()), the hero at the packet's tile and direction.  The client loads
 * synchronously inside the packet handler and shows no loading picture (live capture, 0.4 s frames); it sets
 * LoadingWorld = 30, which MoveHero counts down before the render.  The demo files (placement, NPC table,
 * players) belong to the start world and are left out elsewhere. */
int world_rt_travel(mu_world_rt *a, const mu_teleport *t)
{
    char error[512];
    float angle = mu_teleport_angle(t);
    int32_t world = (int32_t)t->world;
    if (!a->start_set) {
        a->start_set = 1;
        a->start_world = a->world;
        a->start_placement = a->placement;
        a->start_npc_demo = a->npc_demo_path;
        a->start_players = a->players_file;
    }
    if (!mu_teleport_changes_world(t, a->world)) {   /* same map: the hero is set on the tile (no reload) */
        mu_walk *w = &a->walk;
        mu_walk_stop(w);
        w->hero.tile[0] = t->x;
        w->hero.tile[1] = t->y;
        w->hero.position[0] = ((float)t->x + 0.5f) * 100.0f;
        w->hero.position[1] = ((float)t->y + 0.5f) * 100.0f;
        w->hero.angle[2] = angle;
#ifndef MU_WORLD_NO_GL
        world_gfx_quest_travel_complete(a->gfx, 1);
#endif
        a->travels++;
        return 0;
    }
#ifndef MU_WORLD_NO_GL
    int had_gl = a->gl_ready;
    if (had_gl)
        mu_world_rt_gl_teardown(a);
#endif
    int32_t old_world = a->world, old_tile[2] = {a->walk.hero.tile[0], a->walk.hero.tile[1]};
    float old_angle = a->walk.hero.angle[2];
    mu_auto_path armed_path = a->walk.auto_path;   /* ReceiveTeleport keeps the hero's armed quest PATH_t. */
    mu_frame_clock clock = a->walk.frame.clock;   /* the session's time goes on (no catch-up steps) */
    uint32_t steps = a->walk.steps;
    world_rt_unload(a);
    int home = world == a->start_world;
    a->placement = home ? a->start_placement : NULL;
    a->npc_demo_path = home ? a->start_npc_demo : NULL;
    a->players_file = home ? a->start_players : NULL;
    a->world = world;
    a->tile[0] = t->x;
    a->tile[1] = t->y;
    a->angle = angle;
    int failed = world_rt_load(a);
    if (failed) {   /* the target did not load: back where the hero was */
        fprintf(stderr, "travel: world %d did not load, staying in world %d\n", world, old_world);
        world_rt_unload(a);
        a->world = old_world;
        a->tile[0] = old_tile[0];
        a->tile[1] = old_tile[1];
        a->angle = old_angle;
        a->placement = old_world == a->start_world ? a->start_placement : NULL;
        a->npc_demo_path = old_world == a->start_world ? a->start_npc_demo : NULL;
        a->players_file = old_world == a->start_world ? a->start_players : NULL;
        if (world_rt_load(a))
            return 1;
        a->travel_failures++;
    }
    a->walk.frame.clock = clock;
    a->walk.steps = steps;
    if (!failed && armed_path.flag == 1)
        a->walk.auto_path = armed_path;
    world_rt_apply_equipment(a, error, sizeof error);
#ifndef MU_WORLD_NO_GL
    if (had_gl)
        mu_world_rt_gl_setup(a);
    if (a->gfx) {
        world_gfx_quest_travel_complete(a->gfx, !failed);
        world_rt_names_gfx_attach(a, a->gfx_scale > 0 ? a->gfx_scale : 1.0);
        if (a->npc_demo)
            world_gfx_npc_storage(a->gfx, a->npc_demo->storage, a->npc_demo->storage_count);
    }
#endif
    if (a->mapsess && a->mapsess->lang && !failed) {   /* sprintf("%s%s", map name, GlobalText[484]): the chat notice */
        const char *moved = mu_map_text(a->mapsess, MU_TELEPORT_TEXT_MOVED), *name = mu_map_world_name(a->mapsess, world);
        snprintf(a->mapsess->notice, sizeof a->mapsess->notice, "%s%s", name, moved);   /* "Noria - Welcome" */
#ifndef MU_WORLD_NO_GL
        if (a->gfx && a->mapsess->notice[0])
            mu_gfx_layer_chat(world_gfx_layer(a->gfx), 3, "", a->mapsess->notice);
#endif
    }
    a->travels++;
    if (!a->quiet)
        fprintf(stderr, "travel: world %d -> %d, tile %d,%d, angle %.0f\n", old_world, a->world, a->walk.hero.tile[0],
                a->walk.hero.tile[1], (double)angle);
    return failed;
}

/* ---- opening ---- */

void mu_world_rt_default_options(mu_world_rt_options *o)
{
    memset(o, 0, sizeof *o);
    o->width = 1280;
    o->height = 800;
    o->class_byte = 0x01;      /* Dark Knight */
    o->env_seed = 1;           /* rand() state at world entry: the CRT default (viewer choice) */
    o->particle_seed = 1;
    o->joint_demo = -1;
    o->helper_state = -1;      /* NATIVE-HELPERS-001: the helper name's ride state */
    o->tile[0] = 133;          /* Lorencia town square */
    o->tile[1] = 127;
    o->angle = 0.0f;
    o->near_plane = 20.0f;     /* CameraViewNear 0x01cf162c (static data, runtime data-section capture) */
    o->audio = 1;
    o->audio_rate = 44100;
    o->demo_world = -1;
    mu_combat_default_config(&o->combat_config);
    mu_world_items_default_config(&o->items_config);
    mu_progress_default_config(&o->progress_config);
    o->progress_config.class_byte = 0xff;   /* unset: the hero's class */
}

/* NATIVE-APP-001: the combat weapon kind of the equipped weapons (file names under Data/Item), sword when the
 * character carries none (mu-world's default). */
static int32_t equipment_weapon_kind(const mu_world_rt_options *o)
{
    static const struct { const char *stem; int32_t kind; } kinds[] = {
        {"crossbow", MU_COMBAT_WEAPON_CROSSBOW}, {"bow", MU_COMBAT_WEAPON_BOW}, {"staff", MU_COMBAT_WEAPON_STAFF},
        {"spear", MU_COMBAT_WEAPON_SPEAR}, {"sword", MU_COMBAT_WEAPON_SWORD}, {"axe", MU_COMBAT_WEAPON_SWORD},
        {"mace", MU_COMBAT_WEAPON_SWORD},
    };
    for (int slot = 0; slot < MU_CHARACTER_WEAPON_SLOTS; ++slot) {
        const char *path = o->items[MU_CHARACTER_WEAPON_ITEM(slot)];
        if (!path || !path[0])
            continue;
        const char *base = strrchr(path, '/');
        char name[64];
        size_t n = 0;
        for (const char *p = base ? base + 1 : path; *p && n + 1 < sizeof name; ++p)
            name[n++] = (char)(*p >= 'A' && *p <= 'Z' ? *p + 32 : *p);
        name[n] = 0;
        for (size_t k = 0; k < sizeof kinds / sizeof kinds[0]; ++k)
            if (!strncmp(name, kinds[k].stem, strlen(kinds[k].stem)))
                return kinds[k].kind;
    }
    return MU_COMBAT_WEAPON_SWORD;
}

static void free_runtime(mu_world_rt *a)
{
#ifndef MU_WORLD_NO_GL
    world_gfx_map_close(a->gfxmap);
#endif
    free(a->mapsess);
    mu_social_messages_destroy(a->social ? &a->social->messages : NULL);
    free(a->social);
    for (int i = 0; i < MU_PART_COUNT; ++i)
        free(a->part[i]);
    mu_lang_free(a->lang);
    free(a);
}

mu_world_rt *mu_world_rt_open(const mu_world_rt_options *o, char *error, size_t error_size)
{
    mu_world_rt *a = calloc(1, sizeof *a);
    if (!a) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    if (seq_build(a, error, error_size)) { free_runtime(a); return NULL; }
    a->perf = o->perf;
    a->lang = mu_lang_load_default();
    for (int i = 0; i < MU_PART_COUNT; ++i)
        if (ROWS[i].ops->state_size && !(a->part[i] = calloc(1, ROWS[i].ops->state_size))) {
            snprintf(error, error_size, "out of memory");
            free_runtime(a);
            return NULL;
        }
    a->root = o->root;
    a->player = o->player;
    a->world = o->world;
    a->class_byte = o->class_byte;
    a->tile[0] = o->tile[0];
    a->tile[1] = o->tile[1];
    a->angle = o->angle;
    a->width = o->width;
    a->height = o->height;
    a->near_plane = o->near_plane;
    a->boots = o->boots;
    a->quiet = o->quiet;
    a->sound_table = o->sound_table;
    a->audio = o->audio;
    a->audio_rate = o->audio_rate > 0 ? o->audio_rate : 44100;
    a->legacy_box = o->legacy_box;
    a->objects_dir = o->objects_dir;
    a->fidelity_dump = o->fidelity_dump;
    a->no_env = o->no_env;
    a->env_tga = o->env_tga;
    a->env_seed = o->env_seed;
    a->no_particles = o->no_particles;
    a->particle_seed = o->particle_seed;
    a->joint_demo = o->joint_demo;
    a->no_names = o->no_names;
    a->no_monster_info = o->no_monster_info;
    a->hero_name = o->hero_name;
    a->no_players = o->no_players;
    a->player_range = o->player_range;
    a->helper_arg = o->helper;   /* NATIVE-HELPERS-001 */
    a->helper_state = o->helper ? o->helper_state : -1;
    a->no_helpers = o->no_helpers;
    a->combat_on = o->combat;
    a->combat_config = o->combat_config;
    if (o->combat && o->has_items)   /* NATIVE-APP-001: the weapon kind follows the equipped weapon */
        a->combat_config.weapon = equipment_weapon_kind(o);
    a->items_on = o->ground_items;
    a->no_items = o->no_items;
    a->items_config = o->items_config;
    a->npc_on = o->npc || o->npc_demo;
    a->no_map = o->no_map;
    a->progress_on = o->progress;
    a->progress_config = o->progress_config;
    if (o->level > 0)   /* NATIVE-PROGRESS-001: the character's level */
        a->progress_config.level = o->level;
    /* the demo files belong to demo_world (mu-world: the start world) */
    a->start_set = 1;
    a->start_world = o->demo_world < 0 ? o->world : o->demo_world;
    a->start_placement = o->placement;
    a->start_npc_demo = o->npc_demo;
    a->start_players = o->players;
    int home = a->world == a->start_world;
    a->placement = home ? o->placement : NULL;
    a->npc_demo_path = home ? o->npc_demo : NULL;
    a->players_file = home ? o->players : NULL;
    if (world_rt_load(a)) {
        snprintf(error, error_size, "world %d did not load (see the messages above)", o->world);
        world_rt_unload(a);
        free_runtime(a);
        return NULL;
    }
    if (o->has_items) {
        /* the chosen character's equipment (mu-world itself shows the class parts only); with combat, its
         * weapons replace the stand-in weapon load() equipped.  NATIVE-MAP-001: kept, a world change applies it
         * again. */
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
            a->equip[i] = o->items[i];
        a->equip_combat = o->combat;
        a->equip_set = 1;
        if (world_rt_apply_equipment(a, error, error_size)) {
            world_rt_unload(a);
            free_runtime(a);
            return NULL;
        }
        mu_walk_place(&a->walk, &a->ch);
    }
    return a;
}

void mu_world_rt_close(mu_world_rt *a)
{
    if (!a)
        return;
    world_rt_unload(a);
    free_runtime(a);
}

/* ---- per frame ---- */

void mu_world_rt_resize(mu_world_rt *a, int32_t width, int32_t height)
{
    a->width = width;
    a->height = height;
    a->walk.frame.view.window_width = (uint32_t)width;
    a->walk.frame.view.window_height = (uint32_t)height;
    a->walk.frame.mouse.scale_x = (float)width / 640.0f;
    a->walk.frame.mouse.scale_y = (float)height / 480.0f;
}

void mu_world_rt_set_clock(mu_world_rt *a, uint32_t now)
{
    a->walk.frame.clock.frame_tick = now;
}

/* Once per rendered frame (world/main.c advance): the pending teleport answer, the due logic steps, the
 * character placement, the render-pass camera, then the frame parts (selection, terrain frame, lights, actor
 * effects, players, the GFx views, names). */
mu_world_frame_info mu_world_rt_frame(mu_world_rt *a, uint32_t now)
{
    mu_world_frame_info info = {0, 0, 0};
    mu_walk *w = &a->walk;
    float before[2] = {w->hero.position[0], w->hero.position[1]};
    uint32_t steps_before = w->steps;
    int was_moving = w->hero.movement;
    mu_teleport tp;
    if (a->mapsess && mu_map_take_teleport(a->mapsess, &tp)) {   /* NATIVE-MAP-001: the teleport answer */
        world_rt_travel(a, &tp);
        info.travelled = 1;
        w = &a->walk;
        before[0] = w->hero.position[0];
        before[1] = w->hero.position[1];
        steps_before = w->steps;
        was_moving = 0;
    }
    int32_t steps = mu_walk_update(w, now, a->has_character ? &a->ch : NULL);
    if (was_moving || w->hero.movement) {
        double dx = (double)(w->hero.position[0] - before[0]), dy = (double)(w->hero.position[1] - before[1]);
        a->walked += sqrt(dx * dx + dy * dy);
        a->moving_steps += w->steps - steps_before;
    }
    if (a->has_character)
        mu_walk_place(w, &a->ch);
    mu_walk_begin_render(w, now);
    int i;
    EACH(COL_FRAME, i)
        ROWS[i].ops->frame(a, a->part[i], now);
    info.steps = steps;
    info.world = a->world;
    return info;
}

int32_t mu_world_rt_end_frame(mu_world_rt *a)
{
    int32_t sleep = mu_walk_end_render(&a->walk);
    world_rt_sound_frame(a);   /* after the cap, as 0x0185280c in the frame driver */
    return sleep;
}

/* Camera of the EffectManager frustum 0x00a8d821: the camera position and the view direction of the modelview
 * (its third row, negated). */
void world_rt_effect_camera(const mu_world_rt *a, float eye[3], float target[3])
{
    const mu_client_view *v = &a->walk.frame.view;
    for (int k = 0; k < 3; ++k) {
        eye[k] = v->position[k];
        target[k] = v->position[k] - v->modelview[4 * k + 2] * 1000.0f;
    }
}

/* ---- software ---- */

long mu_world_rt_draw_soft(mu_world_rt *a, mu_raster *raster)
{
    const mu_client_view *v = &a->walk.frame.view;
    memcpy(raster->view, v->modelview, sizeof raster->view);
    memcpy(raster->projection, v->projection, sizeof raster->projection);
    uint8_t clear[4] = {sky[0], sky[1], sky[2], sky[3]};
    if (a->has_env)
        mu_world_env_clear(&a->env, clear);
    mu_raster_clear(raster, clear);
    mu_world_draw d = {raster->width, raster->height, 0.0, 0, raster};
    int i;
    EACH(COL_DRAW_SOFT, i)
        ROWS[i].ops->draw_soft(a, a->part[i], &d);
    return d.faces;
}

#ifndef MU_WORLD_NO_GL
/* ---- OpenGL ---- */

void mu_world_rt_gl_setup(mu_world_rt *a)
{
    a->batch = mu_perf_batching() ? mu_gl_batch_new() : NULL;
    for (int i = 0; i < MU_PART_COUNT; ++i)
        if (ROWS[i].ops->gl_setup)
            ROWS[i].ops->gl_setup(a, a->part[i]);
    a->fx_count = 0;
    a->gl_ready = 1;
}

void mu_world_rt_gl_teardown(mu_world_rt *a)
{
    if (!a->gl_ready)
        return;
    for (int i = 0; i < MU_PART_COUNT; ++i)
        if (ROWS[i].ops->gl_teardown)
            ROWS[i].ops->gl_teardown(a, a->part[i]);
    for (int i = 0; i < a->fx_count; ++i)
        glDeleteTextures(1, &a->fx_names[i]);
    a->fx_count = 0;
    mu_gl_perf_free(a->perf);
    mu_gl_batch_free(a->batch);
    a->batch = NULL;
    a->gl_ready = 0;
}

/* Effect texture as the effect loader sets it up (0x00a90987 with the base load's arguments): GL_LINEAR,
 * GL_REPEAT, GL_MODULATE, no mipmaps. */
static GLuint fx_texture(mu_world_rt *a, const mu_image *image)
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

/* One visible effect of the EffectManager render pass 0x00a7a30e: depth writes and alpha test off (the pass
 * saves and restores them), the depth test as the preceding pass left it (on), GL_QUADS. */
void world_rt_gl_effect(void *context, const mu_fx_vertex *vertices, uint32_t count, const mu_fx_draw_state *state,
                        const mu_image *texture, const float *matrix)
{
    mu_world_rt *a = context;
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

long mu_world_rt_draw_gl(mu_world_rt *a, int32_t width, int32_t height)
{
    mu_gl_perf_begin(a->perf);
    const mu_client_view *v = &a->walk.frame.view;
    uint8_t clear[4] = {sky[0], sky[1], sky[2], sky[3]};
    if (a->has_env)
        mu_world_env_clear(&a->env, clear);   /* glClearColor of the render scene 0x0185916b */
    mu_gl_frame(width, height, clear, v->modelview, v->projection);
    glViewport(v->gl_viewport[0], v->gl_viewport[1], v->gl_viewport[2], v->gl_viewport[3]);
    glEnable(GL_DEPTH_TEST);
    glFrontFace(GL_CCW);
    mu_world_draw d = {width, height, 0.0, 0, NULL};
    int i;
    EACH(COL_DRAW_GL, i)
        ROWS[i].ops->draw_gl(a, a->part[i], &d);
    mu_gl_perf_end(a->perf);
    return d.faces;
}

/* ---- the GFx interface (the front end's world_gfx) ---- */

/* NATIVE-NAMES-001: the chat input's lines come back as the server echo would (demo) and show as bubbles. */
static void names_chat_hook(void *user, const char *text)
{
    mu_world_rt *a = user;
    if (a->names && a->names->names.env.hero)
        mu_world_names_chat(a->names, a->names->names.env.hero->name, text);
}

/* NATIVE-PROGRESS-001: the options window's boundaries in mu-world */
static struct mu_audio_client *options_audio(void *user)
{
    mu_world_rt *a = user;
    return a->has_sound && a->sound.host ? mu_audio_host_client(a->sound.host) : NULL;
}

static void options_monster_info(void *user, int view)
{
    mu_world_rt *a = user;
    if (a->names)
        mu_names_set_monster_view(&a->names->names, view);   /* hudPlayerName +0x44 (0x00c83c86) */
}

static void options_chat(void *user, const char *text)
{
    mu_world_rt *a = user;
    if (a->gfx)
        mu_gfx_layer_chat(world_gfx_layer(a->gfx), 3, "", text);
}

void world_rt_names_gfx_attach(mu_world_rt *a, double scale)
{
    world_gfx_set_perf(a->gfx, a->perf);
    a->gfx_scale = scale;
    if (a->gfxsocial && a->gfxsocial_owner != a->gfx) { world_gfx_social_close(a->gfxsocial); a->gfxsocial = NULL; }
    if (!a->gfxsocial && a->gfx && a->social) {
        a->gfxsocial = world_gfx_social_open(world_gfx_layer(a->gfx), a->social); a->gfxsocial_owner = a->gfx;
    }
    world_gfx_quest_bind(a->gfx, &a->walk, a->mapsess);
    world_gfx_progress(a->gfx, a->progress);   /* NATIVE-PROGRESS-001 */
    {   /* NATIVE-PROGRESS-001: the options window's sound groups, hudPlayerName's monster info, the chat */
        wg_options_hooks oh = {a, options_audio, options_monster_info, options_chat};
        wg_options_set_hooks(world_gfx_options(a->gfx), &oh);
    }
    if (a->gfxmap && a->gfxmap_owner != a->gfx) {   /* NATIVE-MAP-001: the map host follows the front end's layer */
        world_gfx_map_close(a->gfxmap);
        a->gfxmap = NULL;
    }
    if (!a->gfxmap && a->gfx && a->mapsess) {
        a->gfxmap = world_gfx_map_open(world_gfx_layer(a->gfx), a->mapsess, a->root);
        a->gfxmap_owner = a->gfx;
    }
    if (!a->names || !a->gfx)
        return;
    world_names_gfx_attach(&a->names_gfx, a->gfx, &a->names->names, scale);
    mu_gfx_layer_set_chat_hook(world_gfx_layer(a->gfx), names_chat_hook, a);
}

void mu_world_rt_set_gfx(mu_world_rt *a, struct world_gfx *gfx, double scale)
{
    if (!gfx && a->gfxsocial) {
        world_gfx_social_close(a->gfxsocial);
        a->gfxsocial = NULL;
    }
    if (a->gfxmap && gfx != a->gfxmap_owner) {
        world_gfx_map_close(a->gfxmap); a->gfxmap = NULL; a->gfxmap_owner = NULL;
    }
    a->gfx = gfx;
    if (gfx) {
        world_gfx_set_perf(gfx, a->perf);
        world_rt_names_gfx_attach(a, scale);
        world_gfx_quest_setup(gfx, a->npc_demo ? a->npc_demo->quests : NULL);   /* NATIVE-QUEST-001 */
    } else if (a->names)
        mu_names_set_sink(&a->names->names, NULL);
}
#endif

/* ---- sound and state ---- */

int mu_world_rt_has_sound(const mu_world_rt *a)
{
    return a->has_sound;
}

uint32_t mu_world_rt_sound_rate(const mu_world_rt *a)
{
    return a->has_sound ? mu_world_sound_rate(&a->sound) : 44100u;
}

void mu_world_rt_mix(mu_world_rt *a, float *out, uint32_t frames)
{
    if (a->has_sound)
        mu_world_sound_mix(&a->sound, out, frames);
    else
        memset(out, 0, (size_t)frames * 2 * sizeof *out);
}

const mu_walk *mu_world_rt_walk(const mu_world_rt *a)
{
    return &a->walk;
}

int32_t mu_world_rt_folder(const mu_world_rt *a)
{
    return a->map ? a->map->report.folder : -1;
}

/* ---- reports ---- */

void world_rt_report_frame(const mu_world_rt *a, int32_t frame, uint32_t now, const char *hash, const char *png)
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
    int i;
    EACH(COL_REPORT, i)
        if (ROWS[i].ops->report_frame)
            ROWS[i].ops->report_frame(a, a->part[i], frame);
}

/* NATIVE-FIDELITY-002: the same layouts as live-readers/objread.c and lightread.c, so the tour compares the native
 * world with a live snapshot field by field. "address" is the object index; the sector is CreateObject's rule. */
static void write_fidelity_dump(const mu_world_rt *a)
{
    char path[4096];
    snprintf(path, sizeof path, "%s-obj.bin", a->fidelity_dump);
    FILE *f = fopen(path, "wb");
    if (!f) {
        fprintf(stderr, "%s: cannot write\n", path);
        return;
    }
    int32_t world = a->world, count = a->has_objects ? a->objects.count : 0;
    uint32_t n = a->has_objects && a->objects.rt.ready && a->objects.rt.images ? (uint32_t)count : 0;
    fwrite("MUOBJLV1", 1, 8, f);
    fwrite(&world, 4, 1, f);
    fwrite(&world, 4, 1, f);
    fwrite(&count, 4, 1, f);
    fwrite(&n, 4, 1, f);
    for (uint32_t i = 0; i < n; ++i) {
        const uint8_t *o = a->objects.rt.images + (size_t)i * MU_OBJ_SIZE;
        float x, y;
        memcpy(&x, o + 0x158, 4);
        memcpy(&y, o + 0x15c, 4);
        uint32_t sector = (uint32_t)((int32_t)(x / 1600.0f) * 16 + (int32_t)(y / 1600.0f));
        fwrite(&i, 4, 1, f);
        fwrite(&sector, 4, 1, f);
        fwrite(o, 1, MU_OBJ_SIZE, f);
    }
    fclose(f);
    snprintf(path, sizeof path, "%s-light.bin", a->fidelity_dump);
    f = fopen(path, "wb");
    if (!f) {
        fprintf(stderr, "%s: cannot write\n", path);
        return;
    }
    uint32_t grid = (uint32_t)(3 * MU_TERRAIN_CELLS * sizeof(float)), size = 2 * grid;
    fwrite("MULITLV1", 1, 8, f);
    fwrite("LITE", 1, 4, f);
    fwrite(&size, 4, 1, f);
    fwrite(a->map->primary, 1, grid, f);
    fwrite(a->map->light, 1, grid, f);
    fclose(f);
    printf("{\"fidelity_dump\": \"%s\", \"objects\": %u}\n", a->fidelity_dump, n);
}

void world_rt_report_summary(const mu_world_rt *a, const char *renderer)
{
#ifndef MU_WORLD_NO_GL
    if (a->batch) {
        long uploads, failures;
        mu_gl_batch_upload_stats(a->batch, &uploads, &failures);
        printf("{\"vbo_uploads\": %ld, \"vbo_failures\": %ld}\n", uploads, failures);
    }
#endif
    if (a->fidelity_dump)
        write_fidelity_dump(a);
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
    int i;
    EACH(COL_REPORT, i)
        if (ROWS[i].ops->report_summary)
            ROWS[i].ops->report_summary(a, a->part[i]);
    if (!a->quiet)
        for (int32_t k = 0; k < w->log_count; ++k)
            printf("{\"log\": \"%s\"}\n", w->log[k]);
}
