/* mu-render world mode (NATIVE-RENDERCHAR-001): the client's in-world character
 * and object render passes (item level glow, excellent, ancient, back carry,
 * +15 attachments, monster weapons) drawn through the mesh-draw port.
 * See native/core/mu_renderchar.h and docs/research/client-renderchar.md. */
#include "mu_render_world.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "../core/mu_actor.h"
#include "../core/mu_character.h"
#include "../core/mu_gif.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_renderchar.h"
#include "../core/mu_particles.h"
#include "../../reconstructed/model-codec/character.h"

typedef struct world_options {
    int active;
    mu_renderchar_glow glow[MU_CHARACTER_ITEMS];
    int type_set[MU_CHARACTER_ITEMS];
    mu_renderchar_env env;
    float world_time;
    int safe_zone;
    const char *actor_weapons[2];
    int32_t actor_weapon_types[2];
    int32_t actor_weapon_levels[2];
    int attachments;          /* draw the +15 class15_* attachments for level-15 parts */
} world_options;

static world_options W;

static int slot_index(const char *name)
{
    static const char *names[] = {"head", "helm", "armor", "pants", "gloves", "boots", "weapon0", "weapon1", "wing"};
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
        if (!strcasecmp(name, names[i]))
            return i;
    char *end;
    long v = strtol(name, &end, 0);
    if (*end == 0 && v >= 0 && v < MU_CHARACTER_ITEMS)
        return (int)v;
    return -1;
}

/* SLOT=VALUE or "all"=VALUE */
static int slot_value(const char *arg, int *first, int *last, long *value)
{
    const char *eq = strchr(arg, '=');
    if (!eq)
        return 1;
    char name[32];
    size_t n = (size_t)(eq - arg) < sizeof name - 1 ? (size_t)(eq - arg) : sizeof name - 1;
    memcpy(name, arg, n);
    name[n] = 0;
    char *end;
    *value = strtol(eq + 1, &end, 0);
    if (*end)
        return 1;
    if (!strcasecmp(name, "all")) {
        *first = 1;
        *last = MU_CHARACTER_ITEMS - 1;
        return 0;
    }
    *first = *last = slot_index(name);
    return *first < 0;
}

int mu_render_world_args(int *argc, char **argv)
{
    memset(&W, 0, sizeof W);
    mu_renderchar_default_env(&W.env);
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
        W.glow[i].type = -1;
    W.actor_weapon_types[0] = W.actor_weapon_types[1] = -1;
    int out = 1;
    for (int i = 1; i < *argc; ++i) {
        const char *a = argv[i];
        const char *v = i + 1 < *argc ? argv[i + 1] : NULL;
        int first, last;
        long value;
        int consumed = 1;
        if (!strcmp(a, "--world-render")) {
            W.active = 1;
            consumed = 0;
        } else if (!strcmp(a, "--safe-zone")) {
            W.safe_zone = 1;
            consumed = 0;
        } else if (!strcmp(a, "--attachments")) {
            W.attachments = 1;
            consumed = 0;
        } else if (!v) {
            argv[out++] = argv[i];
            continue;
        } else if (!strcmp(a, "--item-level") || !strcmp(a, "--excellent") || !strcmp(a, "--ancient") ||
                   !strcmp(a, "--item-type") || !strcmp(a, "--kind-a") || !strcmp(a, "--kind-b") ||
                   !strcmp(a, "--item-kind")) {
            if (slot_value(v, &first, &last, &value)) {
                fprintf(stderr, "%s expects SLOT=VALUE\n", a);
                return 1;
            }
            for (int s = first; s <= last; ++s) {
                mu_renderchar_glow *g = &W.glow[s];
                if (!strcmp(a, "--item-level")) g->level = (int32_t)value;
                else if (!strcmp(a, "--excellent")) g->option1 = (int32_t)value;
                else if (!strcmp(a, "--ancient")) g->ext = (int32_t)value;
                else if (!strcmp(a, "--item-type")) { g->type = (int32_t)value; W.type_set[s] = 1; }
                else if (!strcmp(a, "--kind-a")) { g->kind_a = (uint8_t)value; g->has_record = 1; }
                else if (!strcmp(a, "--kind-b")) { g->kind_b = (uint8_t)value; g->has_record = 1; }
                else { g->item_kind = (uint8_t)value; g->has_record = 1; }
            }
            W.active = 1;
        } else if (!strcmp(a, "--glow-color")) {
            if (sscanf(v, "%f,%f,%f", &W.env.glow_color[0], &W.env.glow_color[1], &W.env.glow_color[2]) != 3) {
                fprintf(stderr, "--glow-color expects R,G,B\n");
                return 1;
            }
            W.env.glow_override = 1;   /* the parameter wins over the EnchantEffect table */
            W.active = 1;
        } else if (!strcmp(a, "--quality")) {
            W.env.quality = atoi(v);
            W.active = 1;
        } else if (!strcmp(a, "--world-time")) {
            W.world_time = (float)atof(v);
            W.active = 1;
        } else if (!strcmp(a, "--actor-weapon")) {
            if (slot_value(v, &first, &last, &value) == 0) {
                fprintf(stderr, "--actor-weapon expects N=PATH\n");
                return 1;
            }
            const char *eq = strchr(v, '=');
            int n = (eq && (v[0] == '0' || v[0] == '1') && eq == v + 1) ? v[0] - '0' : -1;
            if (n < 0) {
                fprintf(stderr, "--actor-weapon expects 0=PATH or 1=PATH\n");
                return 1;
            }
            W.actor_weapons[n] = eq + 1;
            W.active = 1;
        } else if (!strcmp(a, "--actor-weapon-level")) {
            const char *eq = strchr(v, '=');
            if (!eq || (v[0] != '0' && v[0] != '1')) {
                fprintf(stderr, "--actor-weapon-level expects N=LEVEL\n");
                return 1;
            }
            W.actor_weapon_levels[v[0] - '0'] = atoi(eq + 1);
        } else {
            argv[out++] = argv[i];
            continue;
        }
        if (consumed)
            ++i;
    }
    argv[out] = NULL;
    *argc = out;
    return 0;
}

int mu_render_world_active(void)
{
    return W.active;
}

static int write_frames(const mu_options *o, const uint8_t *frames)
{
    int status = 0;
    size_t frame_bytes = (size_t)o->width * (size_t)o->height * 4;
    if (o->output && mu_png_write(o->output, frames, o->width, o->height))
        status = 1;
    if (o->strip_path) {
        int32_t sw = o->width * o->frames;
        uint8_t *strip = malloc(frame_bytes * (size_t)o->frames);
        if (!strip)
            return 1;
        for (int32_t y = 0; y < o->height; ++y)
            for (int32_t n = 0; n < o->frames; ++n)
                memcpy(strip + ((size_t)y * (size_t)sw + (size_t)n * (size_t)o->width) * 4,
                       frames + frame_bytes * (size_t)n + (size_t)y * (size_t)o->width * 4, (size_t)o->width * 4);
        status |= mu_png_write(o->strip_path, strip, sw, o->height);
        free(strip);
    }
    if (o->gif_path)
        status |= mu_gif_write(o->gif_path, frames, o->width, o->height, o->frames, 4 * o->frame_steps);
    return status;
}

static void prepare_raster(mu_raster *raster, const mu_textures *t)
{
    raster->textures = t->slots;
    raster->texture_count = t->count;
    raster->texture_filter = t->filter;
    raster->texture_wrap = t->wrap;
}

/* +15 armour attachments (0x016d53a4): part slot -> {bone, model index, file}. */
static const struct { int slot; int bone; int32_t model; const char *file; } ATTACH[] = {
    {1, 20, 0xa9f, "class15_head"}, {2, 35, 0xa9b, "class15_bodyleft"}, {2, 26, 0xa9c, "class15_bodyright"},
    {3, 3, 0xaa0, "class15_pantleft"}, {3, 10, 0xaa1, "class15_pantright"}, {4, 36, 0xa99, "class15_armleft"},
    {4, 27, 0xa9a, "class15_armright"}, {5, 4, 0xa9d, "class15_bootleft"}, {5, 11, 0xa9e, "class15_bootright"},
};

int mu_render_world_character(const mu_options *o)
{
    static mu_character c;
    char error[1024];
    if (mu_options_character(o, &c, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        mu_character_free(&c);
        return 1;
    }
    c.params.world_items = 1;
    /* Armour item models in Data/Item use textures from Data/Player (the
     * client's OpenTexture directory for armour; viewer lookup rule). */
    if (o->game_root && !o->no_textures)
        for (int i = 0; i < MU_CHARACTER_PART_SLOTS; ++i) {
            mu_character_item *item = &c.items[i];
            if (!item->loaded || !item->textures.missing)
                continue;
            char directory[4096];
            snprintf(directory, sizeof directory, "%s/Data/Player", o->game_root);
            mu_textures retry;
            memset(&retry, 0, sizeof retry);
            mu_textures_load(&retry, &item->bmd, directory);
            if (retry.missing < item->textures.missing) {
                mu_textures_free(&item->textures);
                item->textures = retry;
            } else {
                mu_textures_free(&retry);
            }
        }
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
        if (!W.type_set[i] && c.items[i].loaded) {
            W.glow[i].type = mu_renderchar_type_from_path(c.items[i].path);
            /* class parts: the part type the client uses (0x01395473: base + skin) */
            if (W.glow[i].type < 0 && i >= MU_PART_HELM && i <= MU_PART_BOOTS && o->class_byte >= 0 && !o->part_paths[i])
                W.glow[i].type = (int32_t)mu_character_part_type(i, (uint8_t)o->class_byte);
        }
    /* BackCarry 0x0139db9a: in a safe zone plain weapons are drawn on the back. */
    int carried = 0;
    if (W.safe_zone) {
        for (int s = 0; s < MU_CHARACTER_WEAPON_SLOTS; ++s) {
            int item = MU_CHARACTER_WEAPON_ITEM(s);
            const mu_renderchar_glow *g = &W.glow[item];
            if (!c.items[item].loaded || g->type < 0)
                continue;
            uint32_t local[12];
            int right = s == 0;
            int mode = mu_renderchar_back_local(g->type, g->has_record ? g->kind_b : 0, right, local);
            if (mode) {
                c.items[item].action = 0;
                mu_character_set_carry(&c, item, mode, local, MU_CHARACTER_BACK_BONE, 0.0f);
                carried++;
            }
        }
    }
    if (mu_character_update(&c) != MU_MODEL_OK) {
        fprintf(stderr, "character update failed\n");
        mu_character_free(&c);
        return 1;
    }
    /* +15 attachments share the character's bone/root storage. */
    static mu_renderchar_attachment att[sizeof ATTACH / sizeof ATTACH[0]];
    mu_renderchar_host host = {c.shared_bones, c.shared_root, c.shared_quaternions};
    int attached = 0;
    if (W.attachments && o->game_root) {
        for (size_t k = 0; k < sizeof ATTACH / sizeof ATTACH[0]; ++k) {
            if (!c.items[ATTACH[k].slot].loaded || W.glow[ATTACH[k].slot].level != 15)
                continue;
            char path[4096];
            snprintf(path, sizeof path, "%s/Data/Item/%s.bmd", o->game_root, ATTACH[k].file);
            if (mu_renderchar_attach_load(&att[k], &host, path, ATTACH[k].bone, o->no_textures, error, sizeof error)) {
                fprintf(stderr, "%s\n", error);
                continue;
            }
            att[k].glow.type = ATTACH[k].model;
            attached++;
        }
    }
    mu_raster raster;
    if (mu_raster_init(&raster, o->width, o->height)) {
        fprintf(stderr, "bad image size\n");
        return 1;
    }
    raster.linear = o->linear;
    raster.front_ccw = !o->front_cw;
    mu_camera camera;
    mu_options_character_camera(o, &c, &camera);
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)o->width / (float)o->height, raster.projection);
    size_t frame_bytes = (size_t)o->width * (size_t)o->height * 4;
    uint8_t *frames = malloc(frame_bytes * (size_t)o->frames);
    float speed = mu_character_action_speed(&c, mu_model_action(&c.player));
    if (o->player_action < 0)
        speed = o->speed;
    mu_draw_stats stats = {0, 0, 0, 0};
    mu_renderchar_stats rstats = {0, 0};
    char hash[65] = "";
    mu_world_particles *particles = NULL;
    long link_sprites = 0;
    for (int k = 0; k < MU_CHARACTER_ITEMS; ++k) {
        if ((mu_rc_link_supported(W.glow[k].type) || W.glow[k].type == 0x389c || W.glow[k].type == 0x389d) &&
            c.items[k].loaded && !particles) {
            particles = calloc(1, sizeof *particles);
            char error[256];
            if (!particles || mu_world_particles_open(particles, o->game_root, NULL, 0, 1,
                                                       o->no_textures || !o->game_root, error, sizeof error)) {
                fprintf(stderr, "link sprite pool unavailable\n");
                free(particles);
                free(frames);
                mu_raster_free(&raster);
                mu_character_free(&c);
                return 1;
            }
        }
    }
    for (int32_t n = 0; n < o->frames && frames; ++n) {
        if (n) {
            for (int32_t step = 0; step < o->frame_steps; ++step)
                mu_character_tick(&c, speed, NULL);
            if (mu_character_update(&c) != MU_MODEL_OK)
                break;
        }
        mu_renderchar_env env = W.env;
        env.time = W.world_time + 40.0f * (float)(n * o->frame_steps);
        mu_raster_clear(&raster, o->background);
        mu_render_backend backend;
        mu_raster_backend(&raster, &backend);
        /* RenderCharacter order: body parts 5..0, +15 attachments, back carry, wing, hand weapons. */
        static const int parts[] = {5, 4, 3, 2, 1, 0};
        for (int k = 0; k < 6; ++k) {
            const mu_character_item *item = &c.items[parts[k]];
            if (!item->loaded)
                continue;
            prepare_raster(&raster, &item->textures);
            mu_draw_options draw = o->draw;
            draw.textures = o->no_textures ? NULL : &item->textures;
            mu_renderchar_draw_item(&item->model, &W.glow[parts[k]], &env, c.params.light, 1.0f, &draw, &backend,
                                    &stats, &rstats);
            if (W.glow[parts[k]].type == 0x389c || W.glow[parts[k]].type == 0x389d)
                link_sprites += mu_renderchar_link_effects(&item->model, c.player_bones, W.glow[parts[k]].type, particles);
        }
        for (size_t k = 0; k < sizeof ATTACH / sizeof ATTACH[0]; ++k) {
            if (!att[k].loaded)
                continue;
            /* each attachment poses into the shared buffers right before its draw */
            if (mu_renderchar_attach_update(&att[k], &c.player, c.player_bones, c.params.position, c.params.scale,
                                            c.params.light))
                continue;
            prepare_raster(&raster, &att[k].textures);
            mu_draw_options draw = o->draw;
            draw.textures = o->no_textures ? NULL : &att[k].textures;
            mu_renderchar_draw_item(&att[k].model, &att[k].glow, &env, c.params.light, 1.0f, &draw, &backend, &stats,
                                    &rstats);
        }
        static const int links[] = {6, 7, 8};
        for (int k = 0; k < 3; ++k) {
            const mu_character_item *item = &c.items[links[k]];
            if (!item->loaded)
                continue;
            prepare_raster(&raster, &item->textures);
            mu_draw_options draw = o->draw;
            draw.textures = o->no_textures ? NULL : &item->textures;
            mu_renderchar_draw_item(&item->model, &W.glow[links[k]], &env, c.params.light, 1.0f, &draw, &backend,
                                    &stats, &rstats);
            link_sprites += mu_renderchar_link_effects(&item->model, item->bones, W.glow[links[k]].type, particles);
        }
        if (particles)
            mu_world_particles_draw_raster(particles, &raster, raster.view);
        memcpy(frames + frame_bytes * (size_t)n, raster.color, frame_bytes);
        if (n == 0)
            mu_sha256_hex(raster.color, frame_bytes, hash);
    }
    int status = frames ? write_frames(o, frames) : 1;
    printf("{\"sha256\": \"%s\", \"width\": %d, \"height\": %d, \"meshes\": %ld, \"triangles\": %ld, \"passes\": %ld,"
           " \"special\": %ld, \"carried\": %d, \"attachments\": %d, \"quality\": %d, \"link_sprites\": %ld}\n",
           hash, o->width, o->height, stats.meshes, raster.triangles, rstats.passes, rstats.special, carried, attached,
           W.env.quality, link_sprites);
    if (particles) {
        mu_world_particles_close(particles);
        free(particles);
    }
    for (size_t k = 0; k < sizeof ATTACH / sizeof ATTACH[0]; ++k)
        mu_renderchar_attach_free(&att[k]);
    free(frames);
    mu_raster_free(&raster);
    mu_character_free(&c);
    return status;
}

int mu_render_world_actor(const mu_options *o)
{
    static mu_actor actor;
    char error[1024];
    const char *root = o->game_root ? o->game_root : o->model_path;
    mu_actor_spec spec;
    if (!o->actor_by || mu_actor_resolve(root, o->actor_by, o->actor_id, &spec, error, sizeof error)) {
        fprintf(stderr, "%s\n", o->actor_by ? error : "actor needs --type CLASS, --monster TYPE or --npc INDEX");
        return 1;
    }
    if (mu_actor_load(&actor, &spec, &o->params, o->no_textures, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    mu_actor_set_action(&actor, o->action);
    int32_t steps = (int32_t)(o->time / 0.04f + 0.5f);
    for (int32_t k = 0; k < steps; ++k)
        mu_actor_step(&actor, NULL);
    mu_renderchar_host host;
    if (mu_renderchar_host_init(&host, &actor.model)) {
        mu_actor_free(&actor);
        return 1;
    }
    if (mu_actor_update(&actor)) {
        fprintf(stderr, "actor update failed\n");
        mu_renderchar_host_free(&host);
        mu_actor_free(&actor);
        return 1;
    }
    /* Weapon link bones assigned by the character create 0x0137d8a1 for the model index. */
    int32_t bones[2] = {33, 42};
    int listed = mu_renderchar_link_bones(spec.model_index, &bones[0], &bones[1]);
    static mu_renderchar_attachment weapons[2];
    int loaded = 0;
    for (int s = 0; s < 2; ++s) {
        if (!W.actor_weapons[s])
            continue;
        if (mu_renderchar_attach_load(&weapons[s], &host, W.actor_weapons[s], bones[s], o->no_textures, error,
                                      sizeof error)) {
            fprintf(stderr, "%s\n", error);
            continue;
        }
        weapons[s].glow.type = mu_renderchar_type_from_path(W.actor_weapons[s]);
        weapons[s].glow.level = W.actor_weapon_levels[s];
        loaded++;
    }
    float position[3] = {o->params.origin[0], o->params.origin[1], o->params.origin[2]};
    float light[3] = {o->params.color[0], o->params.color[1], o->params.color[2]};
    mu_raster raster;
    if (mu_raster_init(&raster, o->width, o->height))
        return 1;
    raster.linear = o->linear;
    raster.front_ccw = !o->front_cw;
    mu_camera camera;
    mu_options_camera(o, &actor.model, &camera);
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)o->width / (float)o->height, raster.projection);
    size_t frame_bytes = (size_t)o->width * (size_t)o->height * 4;
    uint8_t *frames = malloc(frame_bytes * (size_t)o->frames);
    mu_draw_stats stats = {0, 0, 0, 0};
    mu_renderchar_stats rstats = {0, 0};
    char hash[65] = "";
    for (int32_t n = 0; n < o->frames && frames; ++n) {
        if (n) {
            for (int32_t step = 0; step < o->frame_steps; ++step)
                mu_actor_step(&actor, NULL);
            if (mu_actor_update(&actor))
                break;
        }
        mu_raster_clear(&raster, o->background);
        mu_render_backend backend;
        mu_raster_backend(&raster, &backend);
        prepare_raster(&raster, &actor.textures);
        mu_draw_options draw = o->draw;
        draw.textures = o->no_textures ? NULL : &actor.textures;
        mu_scene_draw_model(&actor.model, &draw, &backend, &stats);
        mu_renderchar_env env = W.env;
        env.time = W.world_time + 40.0f * (float)(n * o->frame_steps);
        for (int s = 0; s < 2; ++s) {
            if (!weapons[s].loaded)
                continue;
            if (mu_renderchar_attach_update(&weapons[s], &actor.model, NULL, position, spec.scale, light))
                continue;
            prepare_raster(&raster, &weapons[s].textures);
            mu_draw_options wd = o->draw;
            wd.textures = o->no_textures ? NULL : &weapons[s].textures;
            mu_renderchar_draw_item(&weapons[s].model, &weapons[s].glow, &env, light, 1.0f, &wd, &backend, &stats,
                                    &rstats);
        }
        memcpy(frames + frame_bytes * (size_t)n, raster.color, frame_bytes);
        if (n == 0)
            mu_sha256_hex(raster.color, frame_bytes, hash);
    }
    int status = frames ? write_frames(o, frames) : 1;
    printf("{\"sha256\": \"%s\", \"model_index\": %d, \"link_bones\": [%d, %d], \"listed\": %d, \"weapons\": %d,"
           " \"passes\": %ld, \"special\": %ld}\n",
           hash, spec.model_index, bones[0], bones[1], listed, loaded, rstats.passes, rstats.special);
    for (int s = 0; s < 2; ++s)
        mu_renderchar_attach_free(&weapons[s]);
    free(frames);
    mu_raster_free(&raster);
    mu_renderchar_host_free(&host);
    mu_actor_free(&actor);
    return status;
}
