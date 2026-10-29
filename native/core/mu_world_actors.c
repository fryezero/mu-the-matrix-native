/* Monsters and NPCs placed in the walk-around world. See mu_world_actors.h. */
#define _POSIX_C_SOURCE 200809L
#include "mu_world_actors.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/actors/effect_class_table.h"
#include "../../reconstructed/objects/object_render.h"
#include "mu_data.h"
#include "mu_item_textures.h"

#define MONSTER_IDLE 0     /* docs/research/client-actors.md section 2 (inference) */
#define MONSTER_WALK 2
#define CHARACTER_MOVE_SPEED 10   /* character create 0x0137dbb2: MoveSpeed word = 10 */

static const mu_effect_class *effect_class(int32_t server_class)
{
    for (uint32_t i = 0; i < MU_EFFECT_CLASS_ROWS; ++i)
        if ((int32_t)mu_effect_classes[i].server_class == server_class)
            return &mu_effect_classes[i];
    return NULL;
}

static float ground(const mu_world *map, float x, float y)
{
    return mu_request_terrain_height(map->height, map->attributes, map->water_height, 6, x, y);
}

/* RenderCharacter draws a monster or NPC body with RenderObject(o, translate 1, ...) (0x01364163; the translate
 * byte [ebp-0x3c] is set to 1 at 0x013632fe): Animation without translate, Transform(..., translate 1, 0, 0.4,
 * +0xe4, +0xe8) (0x017edd08) and the body light 0x017ec3d8. The character objects of a running client carry
 * +5/+6/+7 = 1, +0xe4/+0xe8 = 0.8/0.2 and the object light +0xec = 0.2, and the model colour equals the frame
 * light at the position plus 0.2 (live read, NATIVE-LIGHT-001). The light vector is the client's (light override
 * 1, MU_CLIENT_HIGH_LIGHT, set at load by mu_model_scene_params). */
#define ACTOR_OBJECT_LIGHT 0.2f
static void place_model(const mu_world_actors *s, mu_world_actor *a)
{
    mu_model_params p = a->actor.model.params;
    float light[3] = {1.0f, 1.0f, 1.0f};
    if (s->map) {
        mu_obj_terrain_light(s->map->light, 6, 1, a->position[0], a->position[1], light);   /* scene 6: the world */
        for (int k = 0; k < 3; ++k)
            light[k] = light[k] + ACTOR_OBJECT_LIGHT;
    }
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = a->position[k];
        p.angles[k] = a->angle[k];
        p.color[k] = light[k];
    }
    p.lighting = 1;
    p.pose_translate = 0;
    p.transform_translate = 1;
    p.vertex_scale = 0.0f;
    p.light_ambient = 0.4f;
    p.light_scale = 0.8f;
    p.light_minimum = 0.2f;
    mu_model_apply_params(&a->actor.model, &p);
}

static int load_player_npc(mu_world_actor *a, const char *root, const mu_monster_class *row,
                            const mu_model_params *params, int no_textures, char *error, size_t cap)
{
    a->player = calloc(1, sizeof *a->player);
    if (!a->player) {
        snprintf(error, cap, "out of memory");
        return 1;
    }
    char path[4096];
    snprintf(path, sizeof path, "%s/Data/Player/Player.bmd", root);
    if (mu_character_init(a->player, path, params, error, cap))
        return 1;
    mu_character_apply_player_speeds(a->player);
    mu_actor_spec *spec = &a->actor.spec;
    spec->by = MU_ACTOR_BY_CLASS;
    spec->id = spec->server_class = row->server_class;
    spec->monster_type = -1;
    spec->npc_index = spec->model_index = row->model;
    spec->scale = 0.9f;
    if (row->scale_bits)
        memcpy(&spec->scale, &row->scale_bits, 4);
    a->player->params.scale = a->player->params.wing_scale = spec->scale;
    a->player->params.world_items = 1;
    int32_t action = mu_player_unarmed_stop_action(row->class_byte, params->world, NULL, NULL);
    mu_character_set_state(a->player, (uint16_t)action, 0.0f, 0.0f, (uint16_t)action);
    mu_data_table table = {0};
    snprintf(path, sizeof path, "%s/Data/Local/Item.bmd", root);
    if (mu_data_load(path, NULL, &table) || table.result.status) {
        mu_data_free(&table);
        snprintf(path, sizeof path, "%s/Data/Local/item.bmd", root);
        if (mu_data_load(path, NULL, &table) || table.result.status) {
            mu_data_free(&table);
            snprintf(error, cap, "Player-model NPC needs Item.bmd");
            return 1;
        }
    }
    for (int k = 1; k < MU_CHARACTER_ITEMS; k++) {
        int32_t type = row->slots[k].type;
        if (type < 0xae6 || type == 0xffff)
            continue;
        mu_item item;
        if (mu_item_model(&table, type, &item) != 1) {
            snprintf(error, cap, "NPC %d: no item model for %#x", row->server_class, type);
            mu_data_free(&table);
            return 1;
        }
        snprintf(path, sizeof path, "%s/%s%s", root, item.folder, item.file);
        for (char *p = path; *p; p++)
            if (*p == '\\')
                *p = '/';
        if (mu_character_set_item(a->player, k, path, no_textures, error, cap)) {
            mu_data_free(&table);
            return 1;
        }
        /* RENDER-ITEMS-TEX-002: the client's item texture rule for the slot's type; parts take the NPC's skin */
        if (!no_textures)
            mu_item_textures_character(a->player, k, &table, root, type, row->class_byte);
        mu_character_item *part = &a->player->items[k];
        if (!no_textures && k <= 5 && part->textures.missing) {
            char player[4096], directory[4096];
            snprintf(player, sizeof player, "%s/Data/Player", root);
            mu_path_directory(path, directory, sizeof directory);
            mu_textures_free(&part->textures);
            mu_textures_load_with_effects(&part->textures, &part->bmd, player, directory);
        }
        a->player_glow[k] = (mu_renderchar_glow){.type = type, .level = row->slots[k].level, .has_record = 1,
                                                .kind_a = item.attributes.kind_a, .kind_b = item.attributes.kind_b,
                                                .item_kind = item.attributes.type};
    }
    mu_data_free(&table);
    return 0;
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
    const mu_monster_class *row = server_class >= 0 ? mu_monster_class_find((uint32_t)server_class) : NULL;
    int player = row && row->kind == MU_CLASS_PLAYER_MODEL && (server_class == 257 || server_class == 229);
    if (player) {
        memset(&spec, 0, sizeof spec);
    } else if (fx) {
        if (mu_actor_resolve(root, MU_ACTOR_BY_NPC, fx->npc_index, &spec, message, sizeof message))
            goto fail;
        spec.scale = fx->scale;
        spec.server_class = server_class;
    } else if (mu_actor_resolve(root, MU_ACTOR_BY_CLASS, server_class, &spec, message, sizeof message)) {
        goto fail;
    }
    mu_model_params params;
    mu_model_scene_params(&params);   /* light override 1 (NATIVE-LIGHT-001) */
    params.world = s->map->world;
    if (player ? load_player_npc(a, root, row, &params, no_textures, message, sizeof message)
               : mu_actor_load(&a->actor, &spec, &params, no_textures, message, sizeof message))
        goto fail;
    a->tile[0] = a->home[0] = x;
    a->tile[1] = a->home[1] = y;
    a->wander = wander;
    a->position[0] = (float)x * 100.0f + 50.0f;
    a->position[1] = (float)y * 100.0f + 50.0f;
    a->position[2] = ground(s->map, a->position[0], a->position[1]);
    a->angle[2] = (float)(direction & 7) * 45.0f;   /* demo: server direction byte times 45 degrees */

    if (!a->player) {
        mu_actor_set_action(&a->actor, MONSTER_IDLE);
        place_model(s, a);
    }
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
    if (a->player) {
        mu_character_free(a->player);
        free(a->player);
        a->player = NULL;
    }
    mu_actor_free(&a->actor);
    snprintf(error, error_size, "class %d at %d,%d: %s", server_class, x, y, message);
    return 1;
}

int mu_world_actors_init_records(mu_world_actors *s, const char *root, const mu_world *map,
    const mu_characters_view *v, char *error, size_t cap)
{
    memset(s, 0, sizeof *s); s->map = map;
    s->list = calloc(MU_WORLD_ACTORS_MAX, sizeof *s->list);
    if (!s->list) { snprintf(error, cap, "out of memory"); return 1; }
    if (mu_effect_scene_init(&s->effects, root, 0x2026u) == MU_EFFECT_OK) {
        s->has_effects = 1; mu_effect_scene_set_world(&s->effects, map);
    }
    for (int i = 0; i < v->capacity && s->count < MU_WORLD_ACTORS_MAX; ++i) {
        if (!v->used[i] || v->records[i].kind != 2) continue;
        const mu_rp_character *c = &v->records[i];
        mu_world_actor *a = &s->list[s->count];
        if (load_actor(s, a, root, c->class_word, c->tile[0], c->tile[1], 0, 0, c->name, 0, error, cap)) {
            mu_world_actors_free(s); return 1;
        }
        a->session_slot = i; a->session_key = c->key;
        memcpy(a->angle, c->angle, sizeof a->angle);
        ++s->count;
    }
    return 0;
}

void mu_world_actors_free(mu_world_actors *s)
{
    if (s->list)
        for (int32_t i = 0; i < s->count; ++i) {
            mu_actor_free(&s->list[i].actor);
            if (s->list[i].player) {
                mu_character_free(s->list[i].player);
                free(s->list[i].player);
            }
        }
    free(s->list);
    if (s->has_effects)
        mu_effect_scene_free(&s->effects);
    memset(s, 0, sizeof *s);
}

static void actor_step(mu_world_actors *s, mu_world_actor *a)
{
    if (a->player) {
        uint16_t action = mu_model_action(&a->player->player);
        mu_character_tick(a->player, mu_character_action_speed(a->player, action), &a->step_result);
        return;
    }
    {
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

void mu_world_actors_step_one(mu_world_actors *s, int32_t index, mu_rp_character *c)
{
    mu_world_actor *a = &s->list[index];
    if (!c->live) return;
    if (!a->moving && c->movement) { ++a->moves; ++s->moves; }
    a->moving = c->movement;
    memcpy(a->tile, c->tile, sizeof a->tile);
    memcpy(a->position, c->position, sizeof a->position);
    memcpy(a->angle, c->angle, sizeof a->angle);
    a->path.current = c->path.current; a->path.current_float = c->path.current_float; a->path.count = c->path.count;
    memcpy(a->path.x, c->path.x, sizeof a->path.x); memcpy(a->path.y, c->path.y, sizeof a->path.y);
    actor_step(s, a);
    c->movement = a->moving;
    memcpy(c->tile, a->tile, sizeof c->tile); memcpy(c->position, a->position, sizeof c->position);
    memcpy(c->angle, a->angle, sizeof c->angle);
    c->path.current = a->path.current; c->path.current_float = a->path.current_float;
    c->action = a->player ? mu_model_action(&a->player->player) : mu_actor_action(&a->actor);
}

void mu_world_actors_frame(mu_world_actors *s, float effect_dt)
{
    for (int32_t i = 0; i < s->count; ++i) {
        mu_world_actor *a = &s->list[i];
        if (a->player) {
            mu_character *p = a->player;
            memcpy(p->params.position, a->position, sizeof a->position);
            memcpy(p->params.angles, a->angle, sizeof a->angle);
            mu_obj_terrain_light(s->map->light, 6, 1, a->position[0], a->position[1], p->params.light);
            for (int k = 0; k < 3; k++)
                p->params.light[k] += ACTOR_OBJECT_LIGHT;
            p->params.lighting = 1;
            mu_character_update(p);
            continue;
        }
        place_model(s, a);
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
