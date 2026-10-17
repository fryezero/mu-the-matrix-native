#define _POSIX_C_SOURCE 200809L /* opendir with -std=c11 on glibc */
#include "mu_actor.h"

#include <ctype.h>
#include <dirent.h>
#include <stdio.h>
#include <string.h>

#define SPEED_SENTINEL 0x7fc0deadu

static void put16(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) { for (int k = 0; k < 4; ++k) p[k] = (uint8_t)(v >> (8 * k)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
static uint32_t float_bits(float f) { uint32_t b; memcpy(&b, &f, 4); return b; }
static float bits_float(uint32_t b) { float f; memcpy(&f, &b, 4); return f; }

/* Case-insensitive lookup of one path component inside directory. */
static int find_component(const char *directory, const char *name, char *out, size_t size)
{
    DIR *dir = opendir(directory);
    if (!dir)
        return 0;
    struct dirent *entry;
    int found = 0;
    while (!found && (entry = readdir(dir)) != NULL) {
        const char *a = entry->d_name, *b = name;
        while (*a && *b && tolower((unsigned char)*a) == tolower((unsigned char)*b))
            ++a, ++b;
        if (!*a && !*b) {
            snprintf(out, size, "%s/%s", directory, entry->d_name);
            found = 1;
        }
    }
    closedir(dir);
    return found;
}

/* game_root + a client path with backslashes, each component matched without case. */
static int find_client_file(const char *game_root, const char *client_path, char *out, size_t size)
{
    char current[4096], next[4096], component[512];
    snprintf(current, sizeof current, "%s", game_root);
    const char *p = client_path;
    while (*p) {
        size_t n = 0;
        while (*p && *p != '\\' && *p != '/' && n + 1 < sizeof component)
            component[n++] = *p++;
        component[n] = 0;
        while (*p == '\\' || *p == '/')
            ++p;
        if (!n)
            continue;
        if (!find_component(current, component, next, sizeof next))
            return 0;
        memcpy(current, next, sizeof current);
    }
    snprintf(out, size, "%s", current);
    return 1;
}

int mu_actor_resolve(const char *game_root, int by, int32_t id, mu_actor_spec *spec, char *error, size_t error_size)
{
    memset(spec, 0, sizeof *spec);
    spec->by = by;
    spec->id = id;
    spec->monster_type = spec->npc_index = spec->server_class = -1;
    spec->scale = 0.9f;   /* character create 0x0137d8a1 default (static reading) */
    char client_path[512];
    if (by == MU_ACTOR_BY_CLASS) {
        const mu_monster_class *row = id >= 0 ? mu_monster_class_find((uint32_t)id) : NULL;
        if (!row) {
            snprintf(error, error_size, "server class %d is not in the extracted class table", id);
            return 1;
        }
        spec->server_class = id;
        spec->scale = mu_monster_class_scale(row);
        if (row->kind == MU_CLASS_MONSTER || row->kind == MU_CLASS_DEFAULT) {
            by = MU_ACTOR_BY_MONSTER;
            id = row->opened;
        } else if (row->kind == MU_CLASS_NPC) {
            by = MU_ACTOR_BY_NPC;
            id = row->opened;
        } else {
            snprintf(error, error_size, "server class %d uses model %#x (%s); not an actor model", spec->server_class,
                     row->model, row->kind == MU_CLASS_PLAYER_MODEL ? "Player model with parts" : "no opener");
            return 1;
        }
    }
    if (by == MU_ACTOR_BY_MONSTER) {
        if (!mu_monster_model_file(id, client_path, sizeof client_path)) {
            snprintf(error, error_size, "monster type %d outside 0..%u", id, MU_MONSTER_TYPE_COUNT - 1);
            return 1;
        }
        spec->monster_type = id;
        spec->model_index = id + (int32_t)MU_MONSTER_MODEL_BASE;
    } else if (by == MU_ACTOR_BY_NPC) {
        const mu_npc_model *npc = id >= 0 ? mu_npc_find((uint32_t)id) : NULL;
        if (!npc || !mu_access_model_file(npc->directory, npc->name, npc->number, client_path, sizeof client_path)) {
            snprintf(error, error_size, "NPC model index %#x is not in the extracted NPC table", id);
            return 1;
        }
        spec->npc_index = id;
        spec->model_index = id;
    } else {
        snprintf(error, error_size, "unknown actor kind");
        return 1;
    }
    if (!game_root || !find_client_file(game_root, client_path, spec->path, sizeof spec->path)) {
        snprintf(error, error_size, "%s not found under %s", client_path, game_root ? game_root : "(no game root)");
        return 1;
    }
    return 0;
}

/* ------------------------------------------------------------------ */

static uint8_t *host(const mu_actor *a, uint32_t address, uint32_t length)
{
    for (uint32_t i = 0; i < a->memory.count; ++i) {
        const mu_client_image *r = &a->memory.regions[i];
        if (address >= r->base && address - r->base <= r->size && length <= r->size - (address - r->base))
            return r->bytes + (address - r->base);
    }
    return NULL;
}

static uint32_t model_at(void *context, uint32_t index)
{
    mu_actor *a = context;
    return (int32_t)index == a->spec.model_index ? a->model.model : MU_ACTOR_SCRATCH_MODEL;
}

static void access_model(void *context, uint32_t index, const char *directory, const char *name, int32_t number)
{
    (void)directory, (void)name, (void)number;
    mu_actor *a = context;
    if ((int32_t)index != a->spec.model_index)
        return;
    /* The model is already laid out: restore the counts hidden before the opener ran. */
    uint8_t *counts = host(a, a->model.model + 0x24, 4);
    put16(counts, (uint32_t)(uint16_t)a->bmd.mesh_count);
    put16(counts + 2, (uint32_t)(uint16_t)a->bmd.action_count);
}

static uint8_t no_buff(void *context, uint32_t buffs, uint32_t buff) { (void)context, (void)buffs, (void)buff; return 0; }
static uint8_t no_weapon(void *context, uint32_t character) { (void)context, (void)character; return 0; }
static void no_stop(void *context, uint32_t character) { (void)context, (void)character; }

static void set_speed(mu_actor *a, int32_t action, uint32_t bits)
{
    if (action >= 0 && action < a->bmd.action_count)
        put32(host(a, a->model.actions + 16u * (uint32_t)action + 4, 4), bits);
}

static void build_memory(mu_actor *a)
{
    uint32_t n = 0;
    for (uint32_t i = 0; i < a->model.memory.count && n < MU_ACTOR_REGIONS - 3; ++i)
        a->regions[n++] = a->model.memory.regions[i];
    a->regions[n++] = (mu_client_image){a->object, MU_ACTOR_OBJECT, sizeof a->object};
    a->regions[n++] = (mu_client_image){a->character, MU_ACTOR_CHARACTER, sizeof a->character};
    a->regions[n++] = (mu_client_image){a->scratch, MU_ACTOR_SCRATCH_MODEL, sizeof a->scratch};
    a->memory.regions = a->regions;
    a->memory.count = n;
    /* Scratch model: one mesh, 32 actions. */
    put16(a->scratch + 0x24, 1);
    put16(a->scratch + 0x26, 32);
    put32(a->scratch + 0x30, MU_ACTOR_SCRATCH_MODEL + 0x100);
}

int mu_actor_load(mu_actor *a, const mu_actor_spec *spec, const mu_model_params *params, int no_textures,
                  char *error, size_t error_size)
{
    memset(a, 0, sizeof *a);
    a->spec = *spec;
    if (mu_bmd_load_file(spec->path, &a->bmd, error, error_size) != MU_BMD_OK)
        return 1;
    mu_model_params p;
    if (params)
        p = *params;
    else
        mu_model_default_params(&p);
    p.body_scale = spec->scale;
    if (mu_model_init(&a->model, &a->bmd, &p, error, error_size) != MU_MODEL_OK) {
        mu_bmd_free(&a->bmd);
        return 1;
    }
    a->loaded = 1;
    if (!no_textures) {
        char directory[4096];
        mu_path_directory(spec->path, directory, sizeof directory);
        mu_textures_load(&a->textures, &a->bmd, directory);
    }
    build_memory(a);
    put32(a->object + 0x5c, (uint32_t)spec->model_index);

    for (int32_t action = 0; action < a->bmd.action_count; ++action)
        set_speed(a, action, SPEED_SENTINEL);
    if (spec->monster_type >= 0) {
        uint8_t *counts = host(a, a->model.model + 0x24, 4);
        put32(counts, 0);   /* the opener returns at once for a model that already has meshes or actions */
        mu_monster_services services = {a, model_at, access_model, NULL};
        a->open_status = mu_monster_open(&a->memory, spec->monster_type, p.world, &services);
        access_model(a, (uint32_t)spec->model_index, "", "", 0);
    } else if (spec->npc_index >= 0) {
        const mu_npc_model *npc = mu_npc_find((uint32_t)spec->npc_index);
        /* OpenNpc sets every action to 0.25 (loop at 0x0180a9de), then its per-index speeds. */
        for (int32_t action = 0; action < a->bmd.action_count; ++action)
            set_speed(a, action, float_bits(0.25f));
        for (int32_t action = 0; npc && action < 16; ++action)
            if (npc->speed_bits[action])
                set_speed(a, action, npc->speed_bits[action]);
    }
    if (spec->server_class >= 0) {
        uint32_t count;
        const mu_monster_class_speed *rows = mu_monster_class_speeds_for((uint32_t)spec->server_class, &count);
        for (uint32_t i = 0; rows && i < count; ++i) {
            if (rows[i].model != (uint32_t)spec->model_index)
                continue;
            if (rows[i].speed_bits != SPEED_SENTINEL)
                set_speed(a, rows[i].action, rows[i].speed_bits);
            if (rows[i].loop && rows[i].action < a->bmd.action_count)
                *host(a, a->model.actions + 16u * rows[i].action, 1) = rows[i].loop;
        }
    }
    for (int32_t action = 0; action < a->bmd.action_count; ++action) {
        uint8_t *slot = host(a, a->model.actions + 16u * (uint32_t)action + 4, 4);
        if (get32(slot) == SPEED_SENTINEL) {
            put32(slot, float_bits(MU_ACTOR_UNSET_SPEED));
            a->unset_actions++;
        }
    }
    return 0;
}

void mu_actor_free(mu_actor *a)
{
    if (!a->loaded)
        return;
    mu_textures_free(&a->textures);
    mu_model_free(&a->model);
    mu_bmd_free(&a->bmd);
    a->loaded = 0;
}

float mu_actor_action_speed(const mu_actor *a, int32_t action)
{
    if (action < 0 || action >= a->bmd.action_count)
        return 0.0f;
    return bits_float(get32(host(a, a->model.actions + 16u * (uint32_t)action + 4, 4)));
}

int mu_actor_action_loop(const mu_actor *a, int32_t action)
{
    if (action < 0 || action >= a->bmd.action_count)
        return 0;
    return *host(a, a->model.actions + 16u * (uint32_t)action, 1);
}

int32_t mu_actor_action_count(const mu_actor *a) { return a->bmd.action_count; }
uint16_t mu_actor_action(const mu_actor *a) { return (uint16_t)(a->object[0x2a] | (a->object[0x2b] << 8)); }
float mu_actor_frame(const mu_actor *a) { return bits_float(get32(a->object + 0xd0)); }

static void sync_model(mu_actor *a)
{
    mu_model_set_state(&a->model, mu_actor_action(a), mu_actor_frame(a), bits_float(get32(a->object + 0xd4)),
                       (uint16_t)(a->object[0x2c] | (a->object[0x2d] << 8)));
}

int mu_actor_set_action(mu_actor *a, int32_t action)
{
    int status = mu_set_action(&a->memory, MU_ACTOR_OBJECT, action, model_at, a);
    sync_model(a);
    return status;
}

int mu_actor_step(mu_actor *a, uint8_t *loop)
{
    /* The callers set the model's current action from the object before animating it. */
    put16(host(a, a->model.model + 0xa8, 2), mu_actor_action(a));
    mu_character_services services = {a, model_at, no_buff, no_weapon, no_stop};
    mu_tick_globals globals = {MU_TICK_SCENE_STATE, MU_SKIN_WORLD};
    uint8_t result = 0;
    float speed = 0.0f;
    int status = mu_character_animation_step(&a->memory, MU_ACTOR_CHARACTER, MU_ACTOR_OBJECT, &services, &globals,
                                             &result, &speed);
    a->last_speed = speed;
    if (loop)
        *loop = result;
    sync_model(a);
    return status;
}

int mu_actor_update(mu_actor *a)
{
    if (mu_model_pose(&a->model) != MU_MODEL_OK)
        return 1;
    return mu_model_transform_all(&a->model) == MU_MODEL_OK ? 0 : 1;
}
