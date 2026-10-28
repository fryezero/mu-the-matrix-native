#include "mu_social.h"
/* Other players in the walk-around world (NATIVE-PLAYERS-001); see mu_world_players.h. */
#define _POSIX_C_SOURCE 200809L
#include "mu_world_players.h"
#include "../fixture/characters_demo.h"
#include "../session/mu_session.h"

#include <ctype.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/actors/actors.h"
#include "../../reconstructed/movement/client_movement.h"
#include "../../reconstructed/model-codec/character.h"
#include "../../reconstructed/objects/object_render.h"
#include "mu_combat.h"
#include "mu_lang.h"
#include "mu_names.h"
#include "mu_world_names.h"

#define PLAYER_OBJECT_LIGHT 0.2f   /* the object light of a character object (NATIVE-LIGHT-001 live read) */

static void log_line(mu_world_players *p, const char *text)
{
    if (p->log_count < (int32_t)(sizeof p->log / sizeof p->log[0]))
        snprintf(p->log[p->log_count++], sizeof p->log[0], "%s", text);
}

/* ---------------------------------------------------------------- models */

static int is_armour(int32_t type)
{
    return type >= 0x18e6 && type < 0x22e6;
}

static int item_file(mu_world_players *p, int32_t type, char *path, size_t cap)
{
    if (type >= 0x3700 && type < 0x3700 + 5 * 0x50) {   /* a class part */
        char name[64];
        if (!mu_character_part_file((uint32_t)type, name, sizeof name))
            return 1;
        snprintf(path, cap, "%s/Data/Player/%s", p->root, name);
        return 0;
    }
    if (!p->has_table)
        return 1;
    mu_item item;
    if (mu_item_model(&p->item_table, type, &item) != 1)
        return 1;
    snprintf(path, cap, "%s/%s%s", p->root, item.folder, item.file);
    for (char *c = path; *c; ++c)
        if (*c == '\\')
            *c = '/';
    return 0;
}

static int32_t weapon_kind(mu_world_players *p, int32_t type)
{
    if (type < 0xae6)
        return MU_WEAPON_NONE;
    int32_t group = (type - 0xae6) / 512, index = (type - 0xae6) % 512;
    int two_handed = 0, kind = 0;
    if (p->has_table) {
        mu_item item;
        if (mu_item_find(&p->item_table, (uint32_t)(type - 0xae6), &item) == 0) {
            two_handed = item.attributes.two_handed != 0;
            kind = item.attributes.kind_b;
        }
    }
    switch (group) {
    case 0: case 1: case 2: return two_handed ? MU_WEAPON_TWO_HAND : MU_WEAPON_ONE_HAND;
    case 3: return MU_WEAPON_SPEAR;
    case 4: return (kind == 9 || (!p->has_table && index >= 8 && index <= 14)) ? MU_WEAPON_CROSSBOW : MU_WEAPON_BOW;
    case 5: return two_handed ? MU_WEAPON_TWO_HAND_STAFF : MU_WEAPON_STAFF;
    default: return MU_WEAPON_NONE;
    }
}

/* Loads the part / weapon / wing models that ChangeCharacterExt's slots name. */
static void load_parts(mu_world_players *p, mu_world_player *q)
{
    char path[2048], error[512];
    static const int item_of[9] = {-1, 1, 2, 3, 4, 5, MU_CHARACTER_WEAPON_ITEM(0), MU_CHARACTER_WEAPON_ITEM(1),
                                   MU_CHARACTER_WING_ITEM};
    char missing[112] = "";
    for (int k = 1; k < 9; ++k) {
        int32_t type = q->c.slots[k].type;
        int item = item_of[k];
        if (type < 0 || item_file(p, type, path, sizeof path)) {
            mu_character_set_item(&q->model, item, NULL, 1, error, sizeof error);
            continue;
        }
        FILE *f = fopen(path, "rb");
        if (!f) {
            size_t n = strlen(missing);
            snprintf(missing + n, sizeof missing - n, "%s%s", n ? " " : "", strrchr(path, '/') + 1);
            mu_character_set_item(&q->model, item, NULL, 1, error, sizeof error);
            continue;
        }
        fclose(f);
        if (mu_character_set_item(&q->model, item, path, p->no_textures, error, sizeof error)) {
            log_line(p, error);
            continue;
        }
        mu_character_item *it = &q->model.items[item];
        if (!p->no_textures && is_armour(type) && it->textures.missing) {
            /* Armour bitmaps live in Data/Player; NULL keeps glow maps in ../Effect.
             * The model directory Data/Item is not the effect directory. */
            char player[2048];
            snprintf(player, sizeof player, "%s/Data/Player", p->root);
            mu_textures_free(&it->textures);
            mu_textures_load_with_effects(&it->textures, &it->bmd, player, NULL);
        }
    }
    q->weapon_kind = weapon_kind(p, q->c.slots[MU_RP_SLOT_WEAPON0].type);
    if (missing[0]) {
        char text[112];
        snprintf(text, sizeof text, "%s: missing %.90s", q->spec.name, missing);
        log_line(p, text);
    }
}

static void place_model(mu_world_players *p, mu_world_player *q)
{
    mu_character *m = &q->model;
    float light[3] = {1.0f, 1.0f, 1.0f};
    if (p->map) {
        mu_obj_terrain_light(p->map->light, 6, 1, q->c.position[0], q->c.position[1], light);
        for (int k = 0; k < 3; ++k)
            light[k] += PLAYER_OBJECT_LIGHT;
    }
    for (int k = 0; k < 3; ++k) {
        m->params.position[k] = q->c.position[k] + q->place_offset[k];   /* the rider lift 0x0103da5c */
        m->params.angles[k] = q->c.angle[k];
        m->params.light[k] = light[k];
    }
}

/* ---------------------------------------------------------------- the name plates */

static mu_hn_character *plate_character(mu_world_players *p, mu_world_player *q)
{
    if (!p->names)
        return NULL;
    mu_hn_character *c = mu_names_character(&p->names->names, q->key);
    if (!c)
        return NULL;
    c->kind = MU_HN_PLAYER;
    c->class_byte = q->c.class_byte;
    c->pk = q->c.pk;
    c->level = q->c.level;
    c->guild = q->c.guild;
    c->guild_relation = (uint8_t)(q->c.guild >= 0 && q->c.guild == p->hero_guild ? 1 : 0);   /* DEMO */
    c->wing = q->c.slots[MU_RP_SLOT_WING].type;
    c->ride = q->c.helper;
    c->monster_class = -1;
    c->live = q->c.live;
    c->max_hp = 100;
    c->hp = q->c.dead ? 0 : 100;   /* DEMO */
    snprintf(c->name, sizeof c->name, "%s", q->c.name);
    memcpy(c->position, q->c.position, sizeof c->position);
    return c;
}

static void guild_lookup(void *context, int32_t index, const char **name, const char **second)
{
    mu_names *n = context;
    const mu_world_players *p = n->user;
    *name = (p && index >= 0 && index < MU_WORLD_PLAYER_GUILDS) ? p->guild_names[index] : "";
    *second = "";
}

static int party_lookup(void *context, const char *name, int32_t *hp)
{
    mu_names *n = context;
    const mu_world_players *p = n->user;
    if (!p)
        return 0;
    if (p->social)
        return mu_social_party_hp(&p->social->party, name, hp);
    for (int32_t i = 0; i < p->count; ++i)
        if (p->list[i].spec.party && !strcmp(p->list[i].spec.name, name)) {
            *hp = p->list[i].c.dead ? 0 : 100;   /* DEMO: the party window's HP percentage */
            return 1;
        }
    return 0;
}

void mu_world_players_attach(mu_world_players *p, struct mu_world_names *names, const struct mu_combat *combat)
{
    p->names = names;
    p->combat = combat;
    if (names) {
        names->names.user = p;
        names->names.env.guild = guild_lookup;
        names->names.env.party_hp = party_lookup;
    }
}

/* ---------------------------------------------------------------- loading */

static uint32_t visual_rand(mu_world_players *p)
{
    p->rng = p->rng * 1664525u + 1013904223u;
    return p->rng;
}

static int load_player(mu_world_players *p, mu_world_player *q, const mu_world_player_spec *s, char *error,
                       size_t error_size)
{
    memset(q, 0, sizeof *q);
    q->spec = *s;
    q->key = p->key0 + (int32_t)(q - p->list);
    char player[2048];
    snprintf(player, sizeof player, "%s/Data/Player/Player.bmd", p->root);
    mu_model_params params;
    mu_model_scene_params(&params);
    params.world = p->map->world;
    if (mu_character_init(&q->model, player, &params, error, error_size))
        return 1;
    q->has_model = 1;
    mu_character_apply_player_speeds(&q->model);
    q->model.params.world_items = 1;
    q->model.params.scale = 0.9f;    /* the character create 0x0137d9dd */
    /* This is a render cache; creation comes only from session frames. */
    q->loaded = 1;
    return 0;
}

int mu_world_players_load_text(mu_world_players *p, const char *root, mu_walk *walk, const mu_world *map,
                               const char *text, int no_textures, char *error, size_t error_size)
{
    memset(p, 0, sizeof *p);
    snprintf(p->root, sizeof p->root, "%s", root);
    p->walk = walk;
    p->map = map;
    p->no_textures = no_textures;
    p->view_range = 12;
    p->key0 = 0x200;
    p->hero_guild = 0;
    p->rng = 0x9a7e2026u;
    snprintf(p->guild_names[0], sizeof p->guild_names[0], "Matrix");
    snprintf(p->guild_names[1], sizeof p->guild_names[1], "Lions");
    snprintf(p->guild_names[2], sizeof p->guild_names[2], "Spiders");
    snprintf(p->guild_names[3], sizeof p->guild_names[3], "Unicorn");
    char path[2048];
    snprintf(path, sizeof path, "%s/Data/Local/item.bmd", root);
    if (mu_data_load(path, NULL, &p->item_table) == 0 && p->item_table.result.status == 0)
        p->has_table = 1;
    else {
        snprintf(path, sizeof path, "%s/Data/Local/Item.bmd", root);
        if (mu_data_load(path, NULL, &p->item_table) == 0 && p->item_table.result.status == 0)
            p->has_table = 1;
    }
    int number = 0;
    const char *q = text;
    while (*q) {
        const char *end = strchr(q, '\n');
        size_t n = end ? (size_t)(end - q) : strlen(q);
        char line[1024];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, q, n);
        line[n] = 0;
        q += n + (end ? 1 : 0);
        ++number;
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        char *s = line;
        while (isspace((unsigned char)*s))
            ++s;
        if (!*s)
            continue;
        if (p->count == MU_WORLD_PLAYERS_MAX) {
            snprintf(error, error_size, "players: more than %d players", MU_WORLD_PLAYERS_MAX);
            mu_world_players_free(p);
            return 1;
        }
        mu_world_player_spec spec;
        if (mu_characters_parse_player(&spec, s, number, error, error_size) ||
            load_player(p, &p->list[p->count], &spec, error, error_size)) {
            mu_world_players_free(p);
            return 1;
        }
        ++p->count;
        char t[112];
        snprintf(t, sizeof t, "player %s class %#x pk %d at %d,%d route %d", spec.name, spec.class_byte, spec.pk,
                 spec.start[0], spec.start[1], spec.route_count);
        log_line(p, t);
    }
    return 0;
}

int mu_world_players_load(mu_world_players *p, const char *root, mu_walk *walk, const mu_world *map, const char *file,
                          int no_textures, char *error, size_t error_size)
{
    FILE *f = fopen(file, "rb");
    if (!f) {
        memset(p, 0, sizeof *p);
        snprintf(error, error_size, "cannot open players file %s", file);
        return 1;
    }
    char *text = calloc(1, 1 << 16);
    size_t n = text ? fread(text, 1, (1 << 16) - 1, f) : 0;
    fclose(f);
    if (!text) {
        memset(p, 0, sizeof *p);
        snprintf(error, error_size, "out of memory");
        return 1;
    }
    text[n] = 0;
    int status = mu_world_players_load_text(p, root, walk, map, text, no_textures, error, error_size);
    free(text);
    return status;
}

void mu_world_players_free(mu_world_players *p)
{
    for (int32_t i = 0; i < p->count; ++i)
        if (p->list[i].has_model)
            mu_character_free(&p->list[i].model);
    if (p->has_table)
        mu_data_free(&p->item_table);
    memset(p, 0, sizeof *p);
}

/* ---------------------------------------------------------------- the client's movement services */

typedef struct step_context {
    mu_world_players *p;
    mu_world_player *q;
} step_context;

static int cb_path(void *context, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_rp_path *path, int32_t mode)
{
    step_context *s = context;
    ++s->p->path_calls;
    mu_client_path cp;
    memcpy(&cp, path, sizeof cp);
    int found = mu_path_finding2(&s->p->walk->finder, sx, sy, tx, ty, &cp, 0.0f, mode, 0) == 1;
    if (found)
        memcpy(path, &cp, sizeof *path);
    return found;
}

static int cb_move_path(void *context, mu_rp_character *c)
{
    (void)context;
    return mu_move_path((mu_path *)&c->path, c->tile, c->position, c->angle, 1);
}

static void set_action(mu_world_player *q, int32_t action, float speed)
{
    if (mu_move_set_action(&q->c.action, &q->c.prior_action, &q->frame, &q->prior_frame,
                           q->model.player_bmd.action_count, action))
        q->action_changed = 1;
    q->play_speed = speed;
}

static void cb_set_action(void *context, mu_rp_character *c, int32_t action)
{
    step_context *s = context;
    (void)c;
    set_action(s->q, action, mu_character_action_speed(&s->q->model, (uint16_t)action));
}

static void run_input(mu_world_players *p, mu_world_player *q, mu_run_input *in)
{
    memset(in, 0, sizeof *in);
    in->stunned = q->c.stunned;
    in->safe_zone = q->safe_zone;
    in->class_byte = q->c.class_byte;
    in->class_value = q->c.class_word;
    in->world = p->map->world;
    in->gloves_type = q->c.slots[MU_RP_SLOT_GLOVES].type;
    in->boots_type = q->c.slots[MU_RP_SLOT_BOOTS].type;
    in->gloves_level = (int8_t)q->c.slots[MU_RP_SLOT_GLOVES].level;
    in->boots_level = (int8_t)q->c.slots[MU_RP_SLOT_BOOTS].level;
    in->mounted_item = 0;
    in->safe_zone_keeps_run = q->riding;   /* 0x0106bdb7 (NATIVE-HELPERS-001) */
}

void mu_world_players_set_action(mu_world_players *p, int32_t i, int32_t action)
{
    if (i < 0 || i >= p->count)
        return;
    mu_world_player *q = &p->list[i];
    set_action(q, action, mu_character_action_speed(&q->model, (uint16_t)action));
    /* Mount rendering may choose the first rider pose between logic ticks. */
    if (p->leased_records && q->session_slot >= 0) {
        p->leased_records[q->session_slot].action = q->c.action;
        p->leased_records[q->session_slot].prior_action = q->c.prior_action;
    } else if (p->record_action) {
        p->record_action(p->record_context, q->session_slot, q->c.action, q->c.prior_action);
    }
}

static void cb_set_walk(void *context, mu_rp_character *c)
{
    step_context *s = context;
    mu_world_player *q = s->q;
    mu_run_input in;
    run_input(s->p, q, &in);
    q->run = mu_player_run_counter(&in, q->run);
    float speed;
    int32_t action;
    /* riding (0x0106bdb7): the rider action 0x0106c382(c, run < 20 ? 1 : 2) (NATIVE-HELPERS-001) */
    if (q->riding && s->p->ride_hook && s->p->ride_hook(s->p->ride_context, (int32_t)(q - s->p->list), q->run < 0x14 ? 1 : 2))
        return;
    if (q->weapon_kind == MU_WEAPON_NONE)
        action = mu_player_walk_action(c->class_byte, q->run, &speed);
    else {   /* static table of the armed walk actions (NATIVE-ACTOR-001); the run threshold as unarmed */
        action = q->run >= 40 ? mu_player_walk_action(c->class_byte, q->run, &speed)
                              : mu_player_pose_action(MU_POSE_WALK, q->weapon_kind, c->class_byte, s->p->map->world);
        speed = mu_character_action_speed(&q->model, (uint16_t)action);
    }
    set_action(q, action, speed);
}

static void cb_set_stop(void *context, mu_rp_character *c)
{
    step_context *s = context;
    mu_world_player *q = s->q;
    q->run = mu_player_stop_run_counter(q->keeps_run, q->run);
    if (q->riding && s->p->ride_hook && s->p->ride_hook(s->p->ride_context, (int32_t)(q - s->p->list), 0)) {
        ++q->arrivals;   /* the rider action 0x0106c382(c, 0) (NATIVE-HELPERS-001) */
        return;
    }
    int32_t action;
    float speed;
    if (q->weapon_kind == MU_WEAPON_NONE) {
        action = mu_player_stop_action(c->class_byte);
        speed = mu_player_stop_speed(action);
    } else {
        action = mu_player_pose_action(MU_POSE_STAND, q->weapon_kind, c->class_byte, s->p->map->world);
        speed = mu_character_action_speed(&q->model, (uint16_t)action);
    }
    set_action(q, action, speed);
    ++q->arrivals;
}

static void cb_move_position(void *context, mu_rp_character *c)
{
    step_context *s = context;
    mu_world_player *q = s->q;
    mu_speed_fields fields;
    memset(&fields, 0, sizeof fields);
    fields.move_speed = c->move_speed;
    fields.object_type = c->model;
    fields.object_kind = c->kind;
    fields.helper_type = c->helper;
    fields.safe_zone = q->safe_zone;
    fields.wing_type = c->slots[MU_RP_SLOT_WING].type;
    fields.transformed = c->transformed;
    fields.world = s->p->map->world;
    fields.stunned = c->stunned;
    mu_move_speed_input in;
    mu_move_speed_input_from(&fields, &in);
    mu_position_input pos;
    memset(&pos, 0, sizeof pos);
    pos.speed = mu_character_move_speed(&in, &q->run);
    pos.world = s->p->map->world;
    pos.helper_type = c->helper;
    pos.safe_zone = q->safe_zone;
    pos.object_type = c->model;
    pos.height = s->p->map->height;
    pos.wall = s->p->map->attributes;
    pos.special_height = s->p->map->water_height;
    pos.scene_state = 6;
    mu_move_character_position(&pos, c->position, c->angle, &q->timer);
    ++q->position_steps;
}

static void make_env(mu_world_players *p, step_context *s, mu_rp_env *env)
{
    memset(env, 0, sizeof *env);
    env->context = s;
    env->world = p->map->world;
    env->scene_state = 6;
    env->path_finding2 = cb_path;
    env->move_path = cb_move_path;
    env->move_character_position = cb_move_position;
    env->set_player_walk = cb_set_walk;
    env->set_player_stop = cb_set_stop;
    env->set_action = cb_set_action;
}

static void animate(mu_world_player *q)
{
    mu_model *player = &q->model.player;
    if (q->action_changed) {   /* SetAction 0x012affa4 on the object: prior = current, frame 0 */
        uint16_t prior = mu_model_action(player);
        float prior_frame = mu_model_frame(player);
        mu_character_set_state(&q->model, q->c.action, 0.0f, prior_frame, prior);
        q->action_changed = 0;
    }
    uint8_t loop = 0;
    mu_character_tick(&q->model, q->play_speed, &loop);
    q->step_result = loop;
    q->frame = mu_model_frame(player);
    q->prior_frame = mu_model_prior_frame(player);
}

static void player_step(mu_world_players *p, mu_world_player *q)
{
    if (!q->in_view) return;
    /* the client: the safe-zone byte of the render pass, the dead fade, MoveCharacters' remote step, the dead
     * counter with SetPlayerDie, the animation step */
    uint16_t attribute = p->map->attributes[((q->c.tile[1] & 0xff) << 8) + (q->c.tile[0] & 0xff)];
    q->safe_zone = (uint8_t)(attribute & 1);
    if (q->c.dead) {
        q->fade.model = q->c.model;
        q->fade.world = p->map->world;
        q->fade.z = q->c.position[2];
        q->fade.is_hero = 0;
        mu_dead_fade(q->c.dead, &q->fade);
        q->c.position[2] = q->fade.z;
        if (q->fade.removed) {   /* the fade's removal: live 0, the plate goes (0x013a5ea1) */
            q->c.live = 0;
            q->in_view = 0;
            if (p->names) {
                mu_names_remove(&p->names->names, q->key, 0);
                ++p->removeinfo;
            }

            char text[112];
            snprintf(text, sizeof text, "%s removed after the dead fade", q->c.name);
            log_line(p, text);
            return;
        }
    }
    step_context ctx = {p, q};
    mu_rp_env env;
    make_env(p, &ctx, &env);
    uint8_t moving = q->c.movement;
    p->calls.count = 0;
    mu_rp_move_step(&q->c, &env, &p->calls);
    if (q->c.movement && !moving)
        ++q->moves;
    animate(q);
    if (q->c.dead) {
        int die = 0;
        q->c.dead = mu_dead_step(q->c.dead, &die);
        if (die && q->voice_3324 == 0.0f) {
            mu_player_state st;
            memset(&st, 0, sizeof st);
            st.class_byte = q->c.class_byte;
            st.class_check = (uint8_t)mu_class_check(st.class_byte);
            st.transform = q->c.helper;
            st.world_voice = (uint8_t)mu_rp_world_rule(p->map->world);
            int32_t rands[4], action = -1, sounds[2];
            for (int k = 0; k < 4; ++k)
                rands[k] = (int32_t)(visual_rand(p) & 0x7fff);
            mu_player_die(&st, rands, 4, &action, sounds);
            set_action(q, action, mu_character_action_speed(&q->model, (uint16_t)action));
            q->voice_3324 = 0.001f;
        }
    }
}

void mu_world_players_step_one(mu_world_players *p, int32_t index, mu_rp_character *record)
{
    mu_world_player *q = &p->list[index];
    q->c = *record;
    player_step(p, q);
    *record = q->c;
}

void mu_world_players_frame(mu_world_players *p)
{
    for (int32_t i = 0; i < p->count; ++i) {
        mu_world_player *q = &p->list[i];
        if (!q->in_view || !q->has_model)
            continue;
        place_model(p, q);
        mu_character_update(&q->model);
        if (p->names)
            plate_character(p, q);
    }
}

float mu_world_players_alpha(const mu_world_players *p, int32_t i)
{
    const mu_world_player *q = &p->list[i];
    if (!q->in_view || !q->c.live)
        return 0.0f;
    return q->c.dead ? q->fade.alpha : 1.0f;
}

void mu_world_players_glow(const mu_world_players *p, int32_t i, int item, int32_t *type, int32_t *level,
                           int32_t *option, int32_t *ext, int *has_record, uint8_t *kind_a, uint8_t *kind_b,
                           uint8_t *item_kind)
{
    static const int slot_of[MU_CHARACTER_ITEMS] = {0, 1, 2, 3, 4, 5, MU_RP_SLOT_WEAPON0, MU_RP_SLOT_WEAPON1, MU_RP_SLOT_WING};
    const mu_rp_slot *s = &p->list[i].c.slots[slot_of[item]];
    *type = s->type;
    *level = s->level;
    *option = s->option;
    *ext = s->ext;
    *has_record = 0;
    *kind_a = *kind_b = *item_kind = 0;
    if (p->has_table && s->type >= 0xae6) {
        mu_item rec;
        if (mu_item_find(&p->item_table, (uint32_t)(s->type - 0xae6), &rec) == 0) {
            *has_record = 1;
            *kind_a = rec.attributes.kind_a;
            *kind_b = rec.attributes.kind_b;
            *item_kind = rec.attributes.type;
        }
    }
}

/* ---------------------------------------------------------------- reports */

void mu_world_players_report_frame(const mu_world_players *p, FILE *out, int32_t frame)
{
    fprintf(out, "{\"players_frame\": %d, \"players\": [", frame);
    for (int32_t i = 0; i < p->count; ++i) {
        const mu_world_player *q = &p->list[i];
        fprintf(out, "%s[%d, %d, %.2f, %.2f, %.2f, %d, %d, %u, %u, %u, %.3f, %d, %u]", i ? ", " : "", q->key, q->in_view,
                (double)q->c.position[0], (double)q->c.position[1], (double)q->c.position[2], q->c.tile[0],
                q->c.tile[1], q->c.action, q->c.movement, q->c.dead, (double)mu_world_players_alpha(p, i),
                q->store_open, q->run);
    }
    fprintf(out, "]}\n");
}

void mu_world_players_report_summary(const mu_world_players *p, FILE *out, int quiet)
{
    fprintf(out, "{\"players\": {\"count\": %d, \"steps\": %u, \"viewport_packets\": %u, \"move_packets\": %u,"
                 " \"destroy_packets\": %u, \"die_packets\": %u, \"store_packets\": %u, \"path_calls\": %u,"
                 " \"teleports\": %u, \"addinfo\": %u, \"removeinfo\": %u, \"item_table\": %d, \"range\": %d}}\n",
            p->count, p->steps, p->viewport_packets, p->move_packets, p->destroy_packets, p->die_packets,
            p->store_packets, p->path_calls, p->teleports, p->addinfo, p->removeinfo, p->has_table, p->view_range);
    for (int32_t i = 0; i < p->count; ++i) {
        const mu_world_player *q = &p->list[i];
        fprintf(out, "{\"player\": %d, \"key\": %d, \"name\": \"%s\", \"class\": %d, \"pk\": %d, \"in_view\": %d,"
                     " \"tile\": [%d, %d], \"action\": %u, \"weapon_kind\": %d, \"moves\": %u, \"arrivals\": %u,"
                     " \"creates\": %u, \"destroys\": %u, \"deaths\": %u, \"position_steps\": %u, \"parts\": [",
                i, q->key, q->spec.name, q->c.class_byte, q->c.pk, q->in_view, q->c.tile[0], q->c.tile[1],
                q->c.action, q->weapon_kind, q->moves, q->arrivals, q->creates, q->destroys, q->deaths,
                q->position_steps);
        for (int k = 0; k < MU_RP_SLOTS; ++k)
            fprintf(out, "%s[%d, %d, %d, %d]", k ? ", " : "", q->c.slots[k].type, q->c.slots[k].level,
                    q->c.slots[k].option, q->c.slots[k].ext);
        fprintf(out, "], \"loaded\": [");
        for (int k = 0; k < MU_CHARACTER_ITEMS; ++k)
            fprintf(out, "%s%d", k ? ", " : "", q->has_model && q->model.items[k].loaded);
        fprintf(out, "], \"light\": [%.3f, %.3f, %.3f], \"textures_missing\": [", (double)q->model.params.light[0],
                (double)q->model.params.light[1], (double)q->model.params.light[2]);
        for (int k = 0; k < MU_CHARACTER_ITEMS; ++k)
            fprintf(out, "%s%d", k ? ", " : "", q->has_model && q->model.items[k].loaded ? q->model.items[k].textures.missing : -1);
        fprintf(out, "], \"effect_textures_loaded\": [");
        for (int k = 0; k < MU_CHARACTER_ITEMS; ++k) {
            const mu_character_item *it = &q->model.items[k];
            int loaded = 0;
            if (q->has_model && it->loaded)
                for (int n = it->textures.model_count; n < it->textures.count; ++n)
                    loaded += it->textures.slots[n] != NULL;
            fprintf(out, "%s%d", k ? ", " : "", loaded);
        }
        fprintf(out, "]}\n");
    }
    if (!quiet)
        for (int32_t i = 0; i < p->log_count; ++i)
            fprintf(out, "{\"players_log\": \"%s\"}\n", p->log[i]);
}

/* Apply-time services and presentation cache refresh. No packet construction here. */
static int port_path(void *ctx, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_rp_path *path, int32_t mode)
{
    step_context s = {ctx, NULL};
    return cb_path(&s, sx, sy, tx, ty, path, mode);
}
static float port_height(void *ctx, float x, float y)
{
    mu_world_players *p = ctx;
    return mu_request_terrain_height(p->map->height,p->map->attributes,p->map->water_height,6,x,y);
}
void mu_world_players_port(mu_world_players *p, mu_world_port *port)
{
    memset(port,0,sizeof *port);
    port->context=p; port->world=p->map->world;
    port->path_finding2=port_path; port->terrain_height=port_height;
}

void mu_world_players_sync(mu_world_players *p, const mu_characters_view *v)
{
    for(int i=0;i<p->count;++i) {
        mu_world_player *q=&p->list[i];
        int slot=-1;
        for(int k=0;k<v->capacity;++k)
            if(v->used[k]&&v->records[k].key==q->key) {slot=k;break;}
        if(slot<0) {
            if(q->in_view) {
                if(p->names) {mu_names_remove(&p->names->names,q->key,0);++p->removeinfo;}
                q->in_view=0;q->store_open=0;++q->destroys;++p->destroy_packets;
                char text[112];snprintf(text,sizeof text,"destroy: %s key %#x (out of the demo range)",q->spec.name,q->key);
                log_line(p,text);
            }
            continue;
        }
        q->session_slot=slot;
        uint8_t was_dead=q->c.dead,was_moving=q->c.movement;
        q->c=v->records[slot];
        if(q->session_equipment_revision!=v->equipment_revision[slot]) {
            q->session_equipment_revision=v->equipment_revision[slot];
            q->session_generation=v->generation[slot];
            q->equip_calls=v->equipment_calls[slot];++q->equip_events;
            memcpy(q->equipment,v->equipment[slot],sizeof q->equipment);
            q->run=0;q->frame=q->prior_frame=0;q->action_changed=1;
            q->play_speed=mu_character_action_speed(&q->model,q->c.action);
            memset(&q->fade,0,sizeof q->fade);q->fade.alpha=1;
            q->voice_3324=0;q->store_open=0;q->in_view=1;
            ++q->creates;++p->viewport_packets;
            load_parts(p,q);
            mu_hn_character *c=plate_character(p,q);
            if(c&&mu_names_add(&p->names->names,q->key))++p->addinfo;
            char text[112];snprintf(text,sizeof text,"viewport: %s key %#x at %d,%d (%s)",q->spec.name,q->key,q->c.tile[0],q->c.tile[1],p->steps==0?"appears":"walks in");
            log_line(p,text);
        }
        if(!was_dead&&q->c.dead) {++q->deaths;++p->die_packets;}
        if(!was_moving&&q->c.movement) {++q->moves;++p->move_packets;}
        if(!q->store_open&&v->store_open[slot]) {
            q->store_open=1;++p->store_packets;
            if (p->names) {
                const mu_lang *lang = p->names->lang;
                const char *label = lang ? mu_lang_text(lang, 0x450) : NULL;
                mu_names_set_store(&p->names->names, q->key, 1, v->store_title[slot], label ? label : "Store");
            }
            char text[112];snprintf(text,sizeof text,"store: %s opens '%s' (demo)",q->spec.name,v->store_title[slot]);log_line(p,text);
        }
    }
}
