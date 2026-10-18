/* Monsters and NPCs placed in the walk-around world. See mu_world_actors.h. */
#define _POSIX_C_SOURCE 200809L
#include "mu_world_actors.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/actors/effect_class_table.h"

#define MONSTER_IDLE 0     /* docs/research/client-actors.md section 2 (inference) */
#define MONSTER_WALK 2
#define CHARACTER_MOVE_SPEED 10   /* character create 0x0137dbb2: MoveSpeed word = 10 */

static void log_line(mu_world_actors *s, const char *text)
{
    if (s->log_count < (int32_t)(sizeof s->log / sizeof s->log[0]))
        snprintf(s->log[s->log_count++], sizeof s->log[0], "%s", text);
}

/* Demo wander only (stands in for the server's move decisions). */
static uint32_t demo_rand(mu_world_actors *s)
{
    s->rng = s->rng * 1103515245u + 12345u;
    return (s->rng >> 8) & 0xffffffu;
}

static const mu_effect_class *effect_class(int32_t server_class)
{
    for (uint32_t i = 0; i < MU_EFFECT_CLASS_ROWS; ++i)
        if ((int32_t)mu_effect_classes[i].server_class == server_class)
            return &mu_effect_classes[i];
    return NULL;
}

static uint16_t attribute_at(const mu_world *map, int32_t x, int32_t y)
{
    return map->attributes[((y & 0xff) << 8) + (x & 0xff)];
}

static float ground(const mu_world *map, float x, float y)
{
    return mu_request_terrain_height(map->height, map->attributes, map->water_height, 6, x, y);
}

static int is_monster(const mu_world_actor *a)
{
    return a->actor.spec.monster_type >= 0;
}

static void place_model(mu_world_actor *a)
{
    mu_model_params p = a->actor.model.params;
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = a->position[k];
        p.angles[k] = a->angle[k];
    }
    mu_model_apply_params(&a->actor.model, &p);
}

static int load_actor(mu_world_actors *s, mu_world_actor *a, const char *root, int32_t server_class, int32_t x,
                      int32_t y, int32_t direction, int32_t wander, const char *label, int no_textures, char *error,
                      size_t error_size)
{
    memset(a, 0, sizeof *a);
    a->server_class = server_class;
    snprintf(a->label, sizeof a->label, "%s", label ? label : "");
    mu_actor_spec spec;
    char message[512];
    const mu_effect_class *fx = effect_class(server_class);
    if (fx) {
        if (mu_actor_resolve(root, MU_ACTOR_BY_NPC, fx->npc_index, &spec, message, sizeof message))
            goto fail;
        spec.scale = fx->scale;
        spec.server_class = server_class;
    } else if (mu_actor_resolve(root, MU_ACTOR_BY_CLASS, server_class, &spec, message, sizeof message)) {
        goto fail;
    }
    mu_model_params params;
    mu_model_default_params(&params);
    params.world = s->map->world;
    if (mu_actor_load(&a->actor, &spec, &params, no_textures, message, sizeof message))
        goto fail;
    a->tile[0] = a->home[0] = x;
    a->tile[1] = a->home[1] = y;
    a->wander = wander;
    a->position[0] = (float)x * 100.0f + 50.0f;
    a->position[1] = (float)y * 100.0f + 50.0f;
    a->position[2] = ground(s->map, a->position[0], a->position[1]);
    a->angle[2] = (float)(direction & 7) * 45.0f;   /* demo: server direction byte times 45 degrees */
    a->idle_steps = 20 + (int32_t)(demo_rand(s) % 60u);
    mu_actor_set_action(&a->actor, MONSTER_IDLE);
    place_model(a);
    if (fx && s->has_effects) {
        for (uint32_t i = 0; i < fx->count && a->effect_count < MU_WORLD_ACTOR_EFFECTS; ++i) {
            const mu_effect_class_attach *e = &mu_effect_class_attaches[fx->first + i];
            int index = mu_effect_scene_create(&s->effects, e->path, e->position, e->rotation, e->scale,
                                               e->template_transform, e->tint, NULL, 0, e->start_frame, message,
                                               sizeof message);
            if (index < 0)
                goto fail;
            a->effects[a->effect_count] = index;
            a->effect_bone[a->effect_count++] = e->follow_bone ? e->bone : -1;
            ++s->effect_instances;
        }
    }
    return 0;
fail:
    snprintf(error, error_size, "class %d at %d,%d: %s", server_class, x, y, message);
    return 1;
}

int mu_world_actors_load_text(mu_world_actors *s, const char *root, const mu_world *map, const char *text,
                              int no_textures, char *error, size_t error_size)
{
    memset(s, 0, sizeof *s);
    s->map = map;
    s->rng = 0x5eed2026u;
    s->list = calloc(MU_WORLD_ACTORS_MAX, sizeof *s->list);
    if (!s->list) {
        snprintf(error, error_size, "out of memory");
        return 1;
    }
    if (mu_effect_scene_init(&s->effects, root, 0x2026u) == MU_EFFECT_OK) {
        s->has_effects = 1;
        mu_effect_scene_set_world(&s->effects, map);
    }
    int number = 0;
    const char *p = text;
    while (*p) {
        const char *end = strchr(p, '\n');
        size_t n = end ? (size_t)(end - p) : strlen(p);
        char line[512];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, p, n);
        line[n] = 0;
        p += n + (end ? 1 : 0);
        ++number;
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        char *q = line;
        while (isspace((unsigned char)*q))
            ++q;
        if (!*q)
            continue;
        int32_t server_class, x, y, direction, wander = 0;
        int used = 0;
        if (sscanf(q, "actor %d %d %d %d%n", &server_class, &x, &y, &direction, &used) != 4 || x < 0 || y < 0 ||
            x > 255 || y > 255) {
            snprintf(error, error_size, "placement line %d: expected \"actor CLASS X Y DIRECTION ...\"", number);
            mu_world_actors_free(s);
            return 1;
        }
        q += used;
        char label[48] = "";
        while (*q) {
            while (isspace((unsigned char)*q))
                ++q;
            if (!strncmp(q, "wander", 6)) {
                if (sscanf(q + 6, "%d%n", &wander, &used) != 1) {
                    snprintf(error, error_size, "placement line %d: wander needs a radius", number);
                    mu_world_actors_free(s);
                    return 1;
                }
                q += 6 + used;
            } else if (!strncmp(q, "label", 5)) {
                q += 5;
                while (isspace((unsigned char)*q))
                    ++q;
                snprintf(label, sizeof label, "%s", q);
                size_t len = strlen(label);
                while (len && isspace((unsigned char)label[len - 1]))
                    label[--len] = 0;
                break;
            } else if (*q) {
                snprintf(error, error_size, "placement line %d: unknown field \"%s\"", number, q);
                mu_world_actors_free(s);
                return 1;
            }
        }
        if (s->count == MU_WORLD_ACTORS_MAX) {
            snprintf(error, error_size, "placement: more than %d actors", MU_WORLD_ACTORS_MAX);
            mu_world_actors_free(s);
            return 1;
        }
        if (load_actor(s, &s->list[s->count], root, server_class, x, y, direction, wander < 0 ? 0 : wander, label,
                       no_textures, error, error_size)) {
            mu_world_actors_free(s);
            return 1;
        }
        const mu_world_actor *a = &s->list[s->count];
        char text[96];
        snprintf(text, sizeof text, "class %d (%s) model %#x at %d,%d, %d effect(s)", server_class,
                 a->label[0] ? a->label : "-", a->actor.spec.model_index, x, y, a->effect_count);
        log_line(s, text);
        ++s->count;
    }
    return 0;
}

int mu_world_actors_load(mu_world_actors *s, const char *root, const mu_world *map, const char *placement,
                         int no_textures, char *error, size_t error_size)
{
    FILE *f = fopen(placement, "rb");
    if (!f) {
        memset(s, 0, sizeof *s);
        snprintf(error, error_size, "cannot open placement file %s", placement);
        return 1;
    }
    char *text = calloc(1, 1 << 16);
    size_t n = text ? fread(text, 1, (1 << 16) - 1, f) : 0;
    fclose(f);
    if (!text) {
        memset(s, 0, sizeof *s);
        snprintf(error, error_size, "out of memory");
        return 1;
    }
    text[n] = 0;
    int status = mu_world_actors_load_text(s, root, map, text, no_textures, error, error_size);
    free(text);
    return status;
}

void mu_world_actors_free(mu_world_actors *s)
{
    if (s->list)
        for (int32_t i = 0; i < s->count; ++i)
            mu_actor_free(&s->list[i].actor);
    free(s->list);
    if (s->has_effects)
        mu_effect_scene_free(&s->effects);
    memset(s, 0, sizeof *s);
}

/* Demo stand-in for the server's move packet: a straight run of cells from
 * the actor's tile toward the target, stopping before walls (attribute 4)
 * and safe-zone cells (attribute 1), at most MU_PATH_CELLS cells. */
static int demo_path(const mu_world *map, const mu_world_actor *a, int32_t tx, int32_t ty, mu_path *path)
{
    memset(path, 0, sizeof *path);
    int32_t x = a->tile[0], y = a->tile[1];
    path->x[0] = (uint8_t)x;
    path->y[0] = (uint8_t)y;
    int n = 1;
    while (n < MU_PATH_CELLS && (x != tx || y != ty)) {
        int32_t nx = x + (tx > x) - (tx < x), ny = y + (ty > y) - (ty < y);
        if (attribute_at(map, nx, ny) & 0x5)
            break;
        x = nx;
        y = ny;
        path->x[n] = (uint8_t)x;
        path->y[n] = (uint8_t)y;
        ++n;
    }
    path->count = (uint8_t)n;
    return n >= 2;
}

static void actor_step(mu_world_actors *s, mu_world_actor *a)
{
    if (is_monster(a) && a->wander > 0) {
        if (!a->moving && --a->idle_steps <= 0) {
            int32_t span = 2 * a->wander + 1;
            int32_t tx = a->home[0] - a->wander + (int32_t)(demo_rand(s) % (uint32_t)span);
            int32_t ty = a->home[1] - a->wander + (int32_t)(demo_rand(s) % (uint32_t)span);
            mu_path path;
            if (demo_path(s->map, a, tx, ty, &path)) {
                a->path = path;
                a->moving = 1;
                ++a->moves;
                ++s->moves;
            }
            a->idle_steps = 40 + (int32_t)(demo_rand(s) % 80u);
        }
        if (a->moving) {
            mu_actor_set_action(&a->actor, MONSTER_WALK);
            /* MovePath 0x012b0846(c, 1), then MoveCharacterPosition 0x0137b351 */
            if (mu_move_path(&a->path, a->tile, a->position, a->angle, 1)) {
                a->moving = 0;
                ++a->arrivals;
                ++s->arrivals;
                mu_actor_set_action(&a->actor, MONSTER_IDLE);
            } else {
                mu_move_speed_input in;
                memset(&in, 0, sizeof in);
                in.move_speed = CHARACTER_MOVE_SPEED;
                in.object_type = a->actor.spec.model_index;
                in.object_kind = 2;
                in.helper_type = 0xffff;
                in.mount_type = 0xffff;
                in.wing_type = -1;
                mu_position_input pos;
                memset(&pos, 0, sizeof pos);
                pos.speed = mu_character_move_speed(&in, &a->run);
                pos.world = s->map->world;
                pos.helper_type = 0xffff;
                pos.object_type = a->actor.spec.model_index;
                pos.height = s->map->height;
                pos.wall = s->map->attributes;
                pos.special_height = s->map->water_height;
                pos.scene_state = 6;
                mu_move_character_position(&pos, a->position, a->angle, &a->timer);
            }
        }
    }
    mu_actor_step(&a->actor, &a->step_result);
}

void mu_world_actors_step(mu_world_actors *s)
{
    for (int32_t i = 0; i < s->count; ++i)
        actor_step(s, &s->list[i]);
    ++s->steps;
}

void mu_world_actors_frame(mu_world_actors *s, float effect_dt)
{
    for (int32_t i = 0; i < s->count; ++i) {
        mu_world_actor *a = &s->list[i];
        place_model(a);
        mu_actor_update(&a->actor);
        for (int32_t k = 0; k < a->effect_count; ++k) {
            float at[3] = {a->position[0], a->position[1], a->position[2]};
            int32_t bone = a->effect_bone[k];
            if (bone >= 0 && bone < a->actor.bmd.bone_count && a->actor.model.posed) {
                /* the bone's point as the transform 0x012b5bde places a vertex
                 * at the bone: M[b] * 0 = its translation, times the body scale,
                 * plus the origin */
                const float *m = mu_model_bone_matrices(&a->actor.model) + 12 * bone;
                for (int c = 0; c < 3; ++c)
                    at[c] += m[4 * c + 3] * a->actor.spec.scale;
            }
            float matrix[16];
            mu_effect_object_matrix(matrix, at, a->actor.spec.scale);
            mu_effect_scene_attach(&s->effects, (uint32_t)a->effects[k], matrix);
        }
    }
    if (s->has_effects && s->effects.instance_count)
        mu_effect_scene_update(&s->effects, effect_dt);
}
