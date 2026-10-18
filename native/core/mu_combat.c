/* Combat in the walk-around world (NATIVE-COMBAT-001). See mu_combat.h for
 * the split between client behaviour and the labelled demo / viewer choices. */
#define _POSIX_C_SOURCE 200809L
#include "mu_combat.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/movement/client_movement.h"
#include "mu_raster.h"
#include "mu_scene.h"
#include "../../reconstructed/path/client_path.h"

#define HERO_KEY 0x1234          /* any key: the hero's own key 0x06fca288 */
#define MONSTER_KEY_BASE 0x100   /* demo keys of the placed actors */

static void log_line(mu_combat *c, const char *text)
{
    if (c->log_count < (int32_t)(sizeof c->log / sizeof c->log[0]))
        snprintf(c->log[c->log_count++], sizeof c->log[0], "%s", text);
}

/* Demo randomness (xorshift; not the client's rand()). */
static uint32_t demo_rand(mu_combat *c)
{
    uint32_t x = c->rng ? c->rng : 0x9e3779b9u;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    c->rng = x;
    return x;
}

void mu_combat_default_config(mu_combat_config *config)
{
    memset(config, 0, sizeof *config);
    config->weapon = MU_COMBAT_WEAPON_SWORD;
    config->attack_speed = 40.0f;
    config->magic_speed = 40.0f;
    config->seed = 20261018u;
    config->monster_hp = 260;
    config->damage_min = 30;
    config->damage_max = 95;
    config->latency_steps = 4;
    config->respawn_steps = 125;
    config->counter_attack = 1;
}

/* ---------------------------------------------------------------- weapons */

typedef struct weapon_info {
    int16_t item[2];          /* client item indices (0xae6 + 512 * group + index) */
    uint8_t two_handed, bow_kind;
    const char *file;
} weapon_info;

static const weapon_info weapons[] = {
    [MU_COMBAT_WEAPON_NONE] = {{-1, -1}, 0, 0, NULL},
    [MU_COMBAT_WEAPON_SWORD] = {{0xae6, -1}, 0, 0, "Data/Item/Sword01.bmd"},
    [MU_COMBAT_WEAPON_TWO_HANDED] = {{0xae6 + 9, -1}, 1, 0, "Data/Item/Sword10.bmd"},
    [MU_COMBAT_WEAPON_SPEAR] = {{0x10e6 + 3, -1}, 1, 0, "Data/Item/Spear01.bmd"},
    [MU_COMBAT_WEAPON_BOW] = {{0x12e6, 0x12e6 + 15}, 0, 1, "Data/Item/Bow01.bmd"},
    [MU_COMBAT_WEAPON_CROSSBOW] = {{0x12e6 + 8, 0x12e6 + 7}, 0, 2, "Data/Item/CrossBow01.bmd"},
    [MU_COMBAT_WEAPON_STAFF] = {{0x14e6, -1}, 0, 0, "Data/Item/Staff01.bmd"},
};

const char *mu_combat_weapon_file(int32_t weapon)
{
    if (weapon < 0 || weapon > MU_COMBAT_WEAPON_STAFF)
        return NULL;
    return weapons[weapon].file;
}

/* ---------------------------------------------------------------- resources */

static const struct { int32_t id; const char *dir, *name; char kind; } bitmap_files[] = {
    {MU_BITMAP_FONT_DAMAGE, "Interface", "Font_Damage.tga", 't'},
    {0x7dfe, "Interface", "FontSC.tga", 't'},
    {0x7df3, "Interface", "Hit.tga", 't'},
    {0x7df4, "Interface", "font_miss.tga", 't'},
    {0x7df5, "Interface", "resist.tga", 't'},
    {0x7df6, "Interface", "block.tga", 't'},
    {0x7df7, "Interface", "parry.tga", 't'},
    {0x7df8, "Interface", "absorb.tga", 't'},
    {0x7f2b, "Effect", "Thunder01.jpg", 'j'},
    {0x7f84, "Effect", "Magic_Ground2.jpg", 'j'},
};

static int32_t bitmap_slot(const mu_combat *c, int32_t id)
{
    for (int32_t i = 0; i < c->bitmap_count; ++i)
        if (c->bitmaps[i].id == id)
            return c->bitmaps[i].loaded ? i : -1;
    return -1;
}

static void load_bitmaps(mu_combat *c, const char *root)
{
    for (size_t i = 0; i < sizeof bitmap_files / sizeof bitmap_files[0] && c->bitmap_count < MU_COMBAT_BITMAPS; ++i) {
        mu_combat_bitmap *b = &c->bitmaps[c->bitmap_count++];
        b->id = bitmap_files[i].id;
        char directory[2048], path[4096], error[256], text[96];
        snprintf(directory, sizeof directory, "%s/Data/%s", root, bitmap_files[i].dir);
        if (!mu_image_resolve(directory, bitmap_files[i].name, path, sizeof path) ||
            mu_texture_upload_file(path, bitmap_files[i].kind, &b->image, &b->components, error, sizeof error) !=
                MU_IMAGE_OK) {
            snprintf(text, sizeof text, "bitmap 0x%x (%s) missing", b->id, bitmap_files[i].name);
            log_line(c, text);
            continue;
        }
        b->loaded = 1;
    }
}

static void load_models(mu_combat *c, const char *root)
{
    static const struct { int32_t type; const char *file; } files[MU_COMBAT_MODELS] = {
        {0x43b, "Data/Skill/Arrow01.bmd"},   /* AccessModel(0x43b, "Data\Skill\", "Arrow", 1) */
        {0x413, "Data/Skill/Fire01.bmd"},    /* AccessModel(0x413, "Data\Skill\", "Fire", 1) */
    };
    for (int i = 0; i < MU_COMBAT_MODELS; ++i) {
        mu_combat_model *m = &c->models[i];
        m->type = files[i].type;
        char path[4096], message[512], text[96];
        snprintf(path, sizeof path, "%s/%s", root, files[i].file);
        if (mu_bmd_load_file(path, &m->bmd, message, sizeof message) != MU_BMD_OK) {
            snprintf(text, sizeof text, "model 0x%x missing (%s)", m->type, files[i].file);
            log_line(c, text);
            continue;
        }
        mu_model_params p;
        mu_model_default_params(&p);
        p.world = c->map ? c->map->world : 0;
        if (mu_model_init(&m->model, &m->bmd, &p, message, sizeof message) != MU_MODEL_OK) {
            mu_bmd_free(&m->bmd);
            continue;
        }
        char directory[2048];
        mu_path_directory(path, directory, sizeof directory);
        mu_textures_load(&m->textures, &m->bmd, directory);
        m->loaded = 1;
    }
}

int mu_combat_init(mu_combat *c, const char *root, mu_walk *walk, mu_character *hero, mu_world_actors *actors,
                   const mu_combat_config *config, char *error, size_t error_size)
{
    memset(c, 0, sizeof *c);
    c->config = *config;
    c->walk = walk;
    c->hero_character = hero;
    c->actors = actors;
    c->map = walk ? walk->map : NULL;
    c->rng = config->seed ? config->seed : 1u;
    c->hero_key = HERO_KEY;
    c->target = -1;
    c->intent_skill = -1;
    c->attack_target = -1;
    if (config->weapon < 0 || config->weapon > MU_COMBAT_WEAPON_STAFF) {
        snprintf(error, error_size, "unknown weapon kind %d", config->weapon);
        return 1;
    }
    c->weapon_item[0] = weapons[config->weapon].item[0];
    c->weapon_item[1] = weapons[config->weapon].item[1];
    /* SetAttackSpeed 0x0138dc60 over the Player actions; actions it does not
     * store keep the loader's speed (marked < 0 here) */
    for (int32_t i = 0; i < MU_PLAYER_ACTIONS; ++i)
        c->speeds[i] = -1.0f;
    mu_set_attack_speed(config->attack_speed, config->magic_speed, c->speeds);
    for (int32_t i = 0; actors && i < actors->count; ++i) {
        mu_combat_monster *m = &c->monsters[i];
        m->hp = config->monster_hp;
        m->alpha = 1.0f;
        m->saved_wander = -1;
        memcpy(m->home, actors->list[i].position, sizeof m->home);
    }
    load_bitmaps(c, root);
    load_models(c, root);
    return 0;
}

void mu_combat_free(mu_combat *c)
{
    for (int32_t i = 0; i < c->bitmap_count; ++i)
        if (c->bitmaps[i].loaded)
            mu_image_free(&c->bitmaps[i].image);
    for (int i = 0; i < MU_COMBAT_MODELS; ++i)
        if (c->models[i].loaded) {
            mu_textures_free(&c->models[i].textures);
            mu_model_free(&c->models[i].model);
            mu_bmd_free(&c->models[i].bmd);
        }
    memset(c, 0, sizeof *c);
}

/* ---------------------------------------------------------------- actors */

static int is_monster(const mu_combat *c, int32_t i)
{
    return c->actors && i >= 0 && i < c->actors->count && c->actors->list[i].actor.spec.monster_type >= 0;
}

static int alive(const mu_combat *c, int32_t i)
{
    return is_monster(c, i) && !c->monsters[i].dead && !c->monsters[i].removed;
}

int32_t mu_combat_find_actor(const mu_combat *c, const char *name)
{
    if (!c->actors || !name)
        return -1;
    char *end = NULL;
    long index = strtol(name, &end, 10);
    if (end && end != name && *end == 0)
        return index >= 0 && index < c->actors->count ? (int32_t)index : -1;
    for (int32_t i = 0; i < c->actors->count; ++i)
        if (!strcmp(c->actors->list[i].label, name))
            return i;
    return -1;
}

/* Demo: a hit or an attack puts the monster under combat control (no wander). */
static void engage(mu_combat *c, int32_t i)
{
    mu_world_actor *a = &c->actors->list[i];
    mu_combat_monster *m = &c->monsters[i];
    if (m->saved_wander < 0)
        m->saved_wander = a->wander;
    a->wander = 0;
    a->moving = 0;
}

static void set_monster_action(mu_combat *c, int32_t i, int32_t action)
{
    mu_actor_set_action(&c->actors->list[i].actor, action);   /* SetAction 0x012affa4 */
}

static float hero_distance(const mu_combat *c, int32_t i)
{
    const mu_hero *h = &c->walk->hero;
    const mu_world_actor *a = &c->actors->list[i];
    float dx = (float)(h->tile[0] - a->tile[0]), dy = (float)(h->tile[1] - a->tile[1]);
    return sqrtf(dx * dx + dy * dy);
}

/* ---------------------------------------------------------------- effects */

static mu_combat_fx *new_fx(mu_combat *c, int32_t kind)
{
    for (int i = 0; i < MU_COMBAT_FX; ++i)
        if (!c->fx[i].kind) {
            memset(&c->fx[i], 0, sizeof c->fx[i]);
            c->fx[i].kind = kind;
            c->fx[i].scale = 1.0f;
            ++c->stats.fx_created;
            return &c->fx[i];
        }
    return NULL;
}

/* Direction of heading angle_z (degrees): the client's AngleMatrix turns the
 * local (0, -1, 0) into (sin, -cos): CreateAngle gives 0 toward -y, 90 toward +x. */
static void rotate_z(float angle_z, const float local[3], float out[3])
{
    float r = angle_z * 3.14159265f / 180.0f, s = sinf(r), k = cosf(r);
    out[0] = local[0] * k - local[1] * s;
    out[1] = local[0] * s + local[1] * k;
    out[2] = local[2];
}

static void caster_position(const mu_combat *c, float out[3])
{
    memcpy(out, c->walk->hero.position, 3 * sizeof(float));
}

/* One arrow (CreateArrow 0x0158cf57 -> CreateEffect MODEL_ARROW 0x43b): the
 * init places it at AngleMatrix(angle) * (-10, -60, 135) from the archer with
 * LifeTime 30 (static, 0x013cb34d..0x013cb59a). Viewer choice: it flies
 * straight along the heading at 60 units per step (the arrow branch of
 * MoveEffect 0x0142fd09 was not reduced). */
static void create_arrow(mu_combat *c, float angle_z, int32_t target)
{
    mu_combat_fx *f = new_fx(c, MU_FX_ARROW);
    if (!f)
        return;
    float start[3], offset[3];
    caster_position(c, start);
    const float local[3] = {-10.0f, -60.0f, 135.0f}, forward[3] = {0.0f, -60.0f, 0.0f};
    rotate_z(angle_z, local, offset);
    for (int k = 0; k < 3; ++k)
        f->position[k] = start[k] + offset[k];
    rotate_z(angle_z, forward, f->velocity);
    f->angle[2] = angle_z;
    f->life = 30;
    f->target = target;
    ++c->stats.arrows;
}

static void end_of_attack(mu_combat *c)
{
    const mu_hero *h = &c->walk->hero;
    int32_t t = c->attack_target, skill = c->attack_skill;
    float angle_z = h->angle[2];
    if (skill == 0) {
        /* 0x013aea7a: bow actions 0x7e..0x81 create the arrows */
        if (h->action >= 0x7e && h->action <= 0x81)
            create_arrow(c, angle_z, t);
        return;
    }
    const mu_skill_visual *v = mu_skill_visual_find(skill);
    if (!v)
        return;
    if (v->arrows) {
        /* Triple Shot: two CreateArrows calls; the spread of CreateArrows
         * 0x0158d5bd (+-8 / +-24 degree offsets) is a static reading, three
         * arrows here */
        create_arrow(c, angle_z - 8.0f, t);
        create_arrow(c, angle_z, t);
        create_arrow(c, angle_z + 8.0f, t);
    }
    if (v->effect == 0x413) {
        /* MODEL_FIRE default init (0x013d4086): LifeTime 60, scale (8 + rand%4)
         * * 0.1, z + 120, Direction (0, -50, 0) along the effect angle */
        mu_combat_fx *f = new_fx(c, MU_FX_FIRE);
        if (f) {
            caster_position(c, f->position);
            f->position[2] += 120.0f;
            const float d[3] = {0.0f, -50.0f, 0.0f};
            rotate_z(angle_z, d, f->velocity);
            f->angle[0] = 90.0f;   /* viewer choice: lay the model along the flight */
            f->angle[2] = angle_z;
            f->life = 60;
            f->scale = (float)(8 + (int32_t)(demo_rand(c) % 4u)) * 0.1f;
            f->target = t;
        }
    } else if (v->effect == 0x437) {
        /* Energy Ball for the Player: CreateEffect(0x7f2b Effect\Thunder01.jpg)
         * (0x013b0db4), init 0x013c5bc1: LifeTime 20, z + 100, Direction
         * (0, -60, 0) */
        mu_combat_fx *f = new_fx(c, MU_FX_ENERGY);
        if (f) {
            caster_position(c, f->position);
            f->position[2] += 100.0f;
            const float d[3] = {0.0f, -60.0f, 0.0f};
            rotate_z(angle_z, d, f->velocity);
            f->angle[2] = angle_z;
            f->life = 20;
            f->target = t;
        }
    } else if (v->effect == 0x7f84) {
        /* Heal: CreateEffect(0x7f84 Effect\Magic_Ground2.jpg) at the target,
         * subtype 1 (0x013afaab), LifeTime 20 (0x013c80a3) */
        mu_combat_fx *f = new_fx(c, MU_FX_HEAL);
        if (f) {
            if (t >= 0 && t < c->actors->count)
                memcpy(f->position, c->actors->list[t].position, sizeof f->position);
            else
                caster_position(c, f->position);
            f->life = 20;
            f->target = -2;
        }
    }
}

static void move_fx(mu_combat *c)
{
    for (int i = 0; i < MU_COMBAT_FX; ++i) {
        mu_combat_fx *f = &c->fx[i];
        if (!f->kind)
            continue;
        if (--f->life < 0) {
            f->kind = 0;
            continue;
        }
        if (f->kind == MU_FX_HEAL)
            continue;
        for (int k = 0; k < 3; ++k)
            f->position[k] += f->velocity[k];
        /* viewer choice: a projectile disappears when it reaches or passes
         * its target (horizontal distance below 30 or behind it) */
        if (f->target >= 0 && f->target < c->actors->count) {
            const float *p = c->actors->list[f->target].position;
            float dx = p[0] - f->position[0], dy = p[1] - f->position[1];
            if (dx * dx + dy * dy < 30.0f * 30.0f || dx * f->velocity[0] + dy * f->velocity[1] <= 0.0f)
                f->kind = 0;
        }
    }
}

/* ---------------------------------------------------------------- the demo server */

static void push_event(mu_combat *c, int32_t delay, int32_t kind, int32_t actor, int32_t damage, int32_t type,
                       uint8_t flag8, uint8_t flag_a)
{
    if (c->event_count >= MU_COMBAT_EVENTS)
        return;
    mu_combat_event *e = &c->events[c->event_count++];
    e->step = c->step + delay;
    e->kind = kind;
    e->actor = actor;
    e->damage = damage;
    e->type = type;
    e->flag8 = flag8;
    e->flag_a = flag_a;
}

/* Demo damage roll: 10% miss, 10% critical (type 3), 10% excellent (type 2),
 * 5% double damage (packet[0x0d] bit 7 -> stacked points), else normal. */
static void roll_damage(mu_combat *c, int32_t *damage, int32_t *type, uint8_t *flag8)
{
    uint32_t r = demo_rand(c) % 100u;
    int32_t span = c->config.damage_max - c->config.damage_min + 1;
    int32_t base = c->config.damage_min + (int32_t)(demo_rand(c) % (uint32_t)(span > 0 ? span : 1));
    *flag8 = 0;
    *type = 0;
    if (r < 10) {
        *damage = 0;
        return;
    }
    if (r < 20) {
        *type = 3;
        base = base * 3 / 2;
    } else if (r < 30) {
        *type = 2;
        base = base * 6 / 5;
    } else if (r < 35) {
        *flag8 = 1;
        base *= 2;
    }
    *damage = base;
}

static float terrain_height(void *context, float x, float y)
{
    const mu_world *map = context;   /* RequestTerrainHeight 0x016cc9e2 in scene 6 */
    return map ? mu_request_terrain_height(map->height, map->attributes, map->water_height, 6, x, y) : 0.0f;
}

static void show_damage(mu_combat *c, int32_t key, const float position[3], int32_t damage, int32_t type,
                        uint8_t flag8, uint8_t flag_a)
{
    mu_damage_info info;
    memset(&info, 0, sizeof info);
    info.damage = damage;
    info.type = type;
    info.flag8 = flag8;
    info.flag_a = flag_a;
    float color[3];
    /* 0x01691738(type, key, color, packet[0x10] == 1, packet[0x0c] bit 1) */
    mu_damage_color(type, key, c->hero_key, 0, 0, color);
    float scale = flag8 ? 50.0f : mu_damage_scale(type);   /* packet[0x0d] bit 7: 50 */
    c->stats.points_created += (uint32_t)mu_show_damage(c->points, key, c->hero_key, position, color, scale, &info,
                                                         terrain_height, (void *)c->map);
}

static void monster_hit(mu_combat *c, const mu_combat_event *e)
{
    int32_t i = e->actor;
    if (!alive(c, i))
        return;
    mu_combat_monster *m = &c->monsters[i];
    mu_world_actor *a = &c->actors->list[i];
    engage(c, i);
    /* damage packet 0x01224455: the shock bit set ("Success") calls
     * SetPlayerShock 0x0138f92f before the text */
    if (e->damage > 0) {
        int32_t action = mu_shock_action(m->dead, a->actor.spec.model_index, mu_actor_action(&a->actor),
                                         a->server_class, e->damage, e->type);
        if (action >= 0) {
            set_monster_action(c, i, action);
            ++c->stats.shocks;
        }
        ++c->stats.hits;
    } else {
        ++c->stats.misses;
    }
    show_damage(c, MONSTER_KEY_BASE + i, a->position, e->damage, e->type, e->flag8, e->flag_a);
    m->hp -= e->damage;
    if (c->config.counter_attack)
        m->aggro = 1;
    if (m->hp <= 0) {
        /* die packet 0x01234585: Dead (c + 0x23) = 1, then MoveCharacter
         * counts it up and SetPlayerDie runs from 15 on */
        m->dead = 1;
        m->aggro = 0;
        m->attack_time = 0;
        ++c->stats.kills;
        char text[96];
        snprintf(text, sizeof text, "step %d: %s dies", c->step, a->label[0] ? a->label : "monster");
        log_line(c, text);
        if (c->target == i) {
            c->target = -1;
            c->intent_skill = -1;
        }
    }
}

static void process_events(mu_combat *c)
{
    int32_t kept = 0;
    for (int32_t k = 0; k < c->event_count; ++k) {
        mu_combat_event e = c->events[k];
        if (e.step > c->step) {
            c->events[kept++] = e;
            continue;
        }
        if (e.kind == 1)
            monster_hit(c, &e);
        else if (e.kind == 2) {
            show_damage(c, c->hero_key, c->walk->hero.position, e.damage, e.type, 0, 0);
            ++c->stats.hero_hits;
        }
    }
    c->event_count = kept;
}

/* ---------------------------------------------------------------- the hero */

void mu_combat_attack(mu_combat *c, int32_t actor)
{
    if (!alive(c, actor))
        return;
    c->target = actor;
    c->intent_skill = 0;
}

void mu_combat_cast(mu_combat *c, int32_t skill, int32_t actor)
{
    if (actor < 0)
        actor = c->target;
    if (!alive(c, actor) || !mu_skill_visual_find(skill))
        return;
    c->target = actor;
    c->intent_skill = skill;
}

void mu_combat_stop(mu_combat *c)
{
    c->target = -1;
    c->intent_skill = -1;
}

/* Demo ranges of skills (the skill table's range field is in the encrypted
 * Lang.mpr tables, out of reach): melee skills 2 tiles, the rest 6. */
static float skill_range(int32_t skill)
{
    if ((skill >= 19 && skill <= 23) || (skill >= 41 && skill <= 43))
        return 2.0f;
    return 6.0f;
}

static float player_speed(const mu_combat *c, int32_t action)
{
    if (action >= 0 && action < MU_PLAYER_ACTIONS && c->speeds[action] >= 0.0f)
        return c->speeds[action];
    return c->hero_character ? mu_character_action_speed(c->hero_character, (uint16_t)action) : 0.25f;
}

static void start_attack(mu_combat *c, int32_t t, int32_t skill)
{
    mu_walk *w = c->walk;
    mu_hero *h = &w->hero;
    const mu_world_actor *a = &c->actors->list[t];
    /* face the target: CreateAngle 0x012aed9e(hero x, y, target x, y) */
    h->angle[2] = mu_create_angle(h->position[0], h->position[1], a->position[0], a->position[1]);
    int32_t action = -1;
    int32_t rands[8];
    for (int k = 0; k < 8; ++k)
        rands[k] = (int32_t)(demo_rand(c) & 0x7fff);
    if (skill == 0) {
        mu_attack_input in;
        memset(&in, 0, sizeof in);
        in.object_type = 0xa91;
        in.class_byte = h->class_byte;
        in.safe_zone = h->safe_zone;
        in.counter = c->hero_counter;
        in.weapon[0] = c->weapon_item[0];
        in.weapon[1] = c->weapon_item[1];
        in.wing = -1;
        in.attr_present[0] = c->weapon_item[0] != -1;
        in.attr_present[1] = c->weapon_item[1] != -1;
        in.two_handed = weapons[c->config.weapon].two_handed;
        in.bow_kind = weapons[c->config.weapon].bow_kind;
        in.rand_values = rands;
        in.rand_count = 8;
        mu_attack_result r;
        mu_player_attack_action(&in, &r);
        action = r.action;
        ++c->stats.attacks;
    } else {
        const mu_skill_visual *v = mu_skill_visual_find(skill);
        action = v && v->action >= 0 ? v->action : mu_player_magic_action(h->class_byte, 0, rands[0]);
        ++c->stats.skills;
    }
    if (action >= 0)
        mu_walk_set_action(w, action, player_speed(c, action));
    ++c->hero_counter;              /* SetPlayerAttack's tail: c + 0x28 += 1 */
    c->hero_attack_time = 1;        /* 0x01697ec9 */
    c->attack_target = t;
    c->attack_skill = skill;
    /* demo server: the damage packet arrives latency steps later; buffs and
     * Heal deal no damage */
    if (skill == 26 || skill == 27 || skill == 28)
        return;
    int32_t damage, type;
    uint8_t flag8;
    roll_damage(c, &damage, &type, &flag8);
    push_event(c, c->config.latency_steps, 1, t, damage, type, flag8, 0);
}

/* MoveHero's attack case for the selected target: range, walk, attack. */
static void hero_decide(mu_combat *c)
{
    mu_walk *w = c->walk;
    mu_hero *h = &w->hero;
    if (c->intent_skill < 0 || c->hero_attack_time > 0)
        return;
    int32_t t = c->target;
    if (!alive(c, t)) {
        mu_combat_stop(c);
        return;
    }
    if (h->safe_zone)    /* c + 4 == 1: no attack (0x01697d88) */
        return;
    const mu_world_actor *a = &c->actors->list[t];
    int32_t item = c->weapon_item[0] < 0 ? -1 : c->weapon_item[0] - 0xae6;
    float range = c->intent_skill ? skill_range(c->intent_skill)
                                  : mu_hero_attack_range(item, weapons[c->config.weapon].bow_kind != 0, 0, 0);
    if (!mu_in_range(h->tile[0], h->tile[1], a->tile[0], a->tile[1], range)) {
        /* walk toward the target (the client paths with PathFinding2 and the
         * range for classes 2 and 10; the demo does it for every class) */
        if (!h->movement || w->target[0] != a->tile[0] || w->target[1] != a->tile[1])
            mu_walk_path_to(w, a->tile[0], a->tile[1]);
        return;
    }
    if (h->movement)
        mu_walk_stop(w);
    start_attack(c, t, c->intent_skill);
}

/* Demo picking: the nearest monster whose vertical cylinder (radius 70 *
 * scale, height 200 * scale) the mouse ray passes (not the client's
 * selection routine). */
static int32_t pick_monster(mu_combat *c)
{
    const mu_client_view *v = &c->walk->frame.view;
    float o[3] = {v->position[0], v->position[1], v->position[2]};
    float d[3] = {v->mouse_target[0] - o[0], v->mouse_target[1] - o[1], v->mouse_target[2] - o[2]};
    float len = sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    if (!(len > 0.0f))
        return -1;
    for (int k = 0; k < 3; ++k)
        d[k] /= len;
    int32_t best = -1;
    float best_t = 1e30f;
    for (int32_t i = 0; c->actors && i < c->actors->count; ++i) {
        if (!alive(c, i))
            continue;
        const mu_world_actor *a = &c->actors->list[i];
        float scale = a->actor.spec.scale > 0.0f ? a->actor.spec.scale : 1.0f;
        float radius = 70.0f * scale, height = 200.0f * scale;
        for (int s = 0; s <= 8; ++s) {   /* sample heights of the cylinder axis */
            float axis[3] = {a->position[0], a->position[1], a->position[2] + height * (float)s / 8.0f};
            float w[3] = {axis[0] - o[0], axis[1] - o[1], axis[2] - o[2]};
            float t = w[0] * d[0] + w[1] * d[1] + w[2] * d[2];
            if (t <= 0.0f)
                continue;
            float q[3] = {o[0] + d[0] * t - axis[0], o[1] + d[1] * t - axis[1], o[2] + d[2] * t - axis[2]};
            if (q[0] * q[0] + q[1] * q[1] + q[2] * q[2] <= radius * radius && t < best_t) {
                best_t = t;
                best = i;
            }
        }
    }
    return best;
}

void mu_combat_pre_step(mu_combat *c)
{
    mu_frame_world *f = &c->walk->frame;
    if (f->mouse.left_push) {
        ++c->stats.picks;
        int32_t i = pick_monster(c);
        if (i >= 0) {
            ++c->stats.pick_hits;
            f->mouse.left_push = 0;   /* the click selects a character, not a tile */
            f->mouse.left = 0;
            mu_combat_attack(c, i);
            char text[96];
            snprintf(text, sizeof text, "step %d: target %s", c->step, c->actors->list[i].label);
            log_line(c, text);
        }
    }
    hero_decide(c);
}

/* ---------------------------------------------------------------- monsters */

static void respawn(mu_combat *c, int32_t i)
{
    mu_combat_monster *m = &c->monsters[i];
    mu_world_actor *a = &c->actors->list[i];
    memcpy(a->position, m->home, sizeof a->position);
    a->tile[0] = (int32_t)(m->home[0] / 100.0f);
    a->tile[1] = (int32_t)(m->home[1] / 100.0f);
    if (m->saved_wander >= 0)
        a->wander = m->saved_wander;
    a->moving = 0;
    a->idle_steps = 20;
    m->saved_wander = -1;
    m->hp = c->config.monster_hp;
    m->dead = 0;
    m->removed = 0;
    m->fade_timer = 0.0f;
    m->alpha = 1.0f;
    m->attack_time = 0;
    m->aggro = 0;
    set_monster_action(c, i, 0);
    ++c->stats.respawns;
}

static void monster_step(mu_combat *c, int32_t i)
{
    mu_combat_monster *m = &c->monsters[i];
    mu_world_actor *a = &c->actors->list[i];
    if (m->removed) {
        if (--m->respawn <= 0)
            respawn(c, i);
        return;
    }
    if (m->dead) {
        /* 0x013a5ea1 before the animation step */
        mu_fade_state s;
        memset(&s, 0, sizeof s);
        s.timer = m->fade_timer;
        s.alpha = m->alpha;
        s.z = a->position[2];
        s.model = a->actor.spec.model_index;
        s.world = c->map ? c->map->world : 0;
        mu_dead_fade(m->dead, &s);
        m->fade_timer = s.timer;
        m->alpha = s.alpha;
        a->position[2] = s.z;
        if (s.removed) {
            m->removed = 1;
            m->respawn = c->config.respawn_steps;
            ++c->stats.removed;
            return;
        }
        /* MoveCharacter 0x013a87c4: Dead++ after the animation step;
         * SetPlayerDie 0x01393a61 from 15 on: monsters SetAction(6) */
        int die = 0;
        m->dead = mu_dead_step(m->dead, &die);
        if (die) {
            if (mu_actor_action(&a->actor) != 6)
                ++c->stats.deaths;
            set_monster_action(c, i, 6);
        }
        return;
    }
    if (m->attack_time && mu_attack_time_step(&m->attack_time, MU_ATTACK_TIME_LIMIT)) {
        /* end of the monster's attack: the demo server sends the hero's damage */
        int32_t damage, type;
        uint8_t flag8;
        roll_damage(c, &damage, &type, &flag8);
        push_event(c, 0, 2, i, damage / 3, 0, 0, 0);
    }
    /* demo counter-attack: a monster that was hit attacks the hero within
     * 1.5 tiles every 50 steps, through the action packet 0x78 path:
     * SetPlayerAttack's monster branch and AttackTime = 1 */
    if (m->aggro && !m->attack_time) {
        if (m->cooldown > 0) {
            --m->cooldown;
        } else if (hero_distance(c, i) <= 1.5f) {
            const mu_hero *h = &c->walk->hero;
            a->angle[2] = mu_create_angle(a->position[0], a->position[1], h->position[0], h->position[1]);
            int32_t action = mu_monster_attack_action(m->counter, 0);
            m->counter = (uint8_t)(m->counter + 2);   /* the branch and the common tail */
            if (action >= 0)
                set_monster_action(c, i, action);
            m->attack_time = 1;
            m->cooldown = 50;
            ++c->stats.monster_attacks;
        }
    }
    /* after the hit or attack animation the monster stands (demo: the
     * server's next action packet) */
    uint16_t now = mu_actor_action(&a->actor);
    if ((now == 5 || now == 3 || now == 4) && a->step_result == 0 && !m->attack_time)
        set_monster_action(c, i, 0);
}

/* ---------------------------------------------------------------- step */

void mu_combat_step(mu_combat *c)
{
    ++c->step;
    process_events(c);
    if (c->hero_attack_time && mu_attack_time_step(&c->hero_attack_time, MU_ATTACK_TIME_LIMIT)) {
        end_of_attack(c);
        /* the attack ends: the hero stands again (SetPlayerStop 0x0138fe69) */
        if (!c->walk->hero.movement) {
            int32_t action = mu_player_stop_action(c->walk->hero.class_byte);
            mu_walk_set_action(c->walk, action, mu_player_stop_speed(action));
        }
    }
    for (int32_t i = 0; c->actors && i < c->actors->count; ++i)
        if (is_monster(c, i))
            monster_step(c, i);
    move_fx(c);
    mu_points_move(c->points);       /* MovePoints 0x016914a0 in the logic tick */
}

/* ---------------------------------------------------------------- drawing */

float mu_combat_actor_alpha(const mu_combat *c, int32_t actor)
{
    if (!is_monster(c, actor))
        return 1.0f;
    const mu_combat_monster *m = &c->monsters[actor];
    if (m->removed)
        return 0.0f;
    return m->alpha;
}

static void camera_rows(const mu_combat *c, float camera[12])
{
    const float *m = c->walk->frame.view.modelview;   /* column-major GL matrix */
    for (int r = 0; r < 3; ++r)
        for (int k = 0; k < 4; ++k)
            camera[4 * r + k] = m[4 * k + r];
}

static mu_combat_quad *next_quad(mu_combat_quad *quads, int32_t max, int32_t *n)
{
    if (*n >= max)
        return NULL;
    mu_combat_quad *q = &quads[(*n)++];
    memset(q, 0, sizeof *q);
    return q;
}

int32_t mu_combat_quads(mu_combat *c, mu_combat_quad *quads, int32_t max)
{
    int32_t n = 0;
    float camera[12];
    camera_rows(c, camera);
    static const float uv_full[4][2] = {{0.0f, 1.0f}, {1.0f, 1.0f}, {1.0f, 0.0f}, {0.0f, 0.0f}};
    /* effect bitmaps (viewer choice: additive, billboard size 120 for the
     * Energy Ball, a 220-unit ground quad for Heal fading with its life) */
    for (int i = 0; i < MU_COMBAT_FX; ++i) {
        const mu_combat_fx *f = &c->fx[i];
        if (f->kind != MU_FX_ENERGY && f->kind != MU_FX_HEAL)
            continue;
        mu_combat_quad *q = next_quad(quads, max, &n);
        if (!q)
            break;
        q->additive = 1;
        q->depth_test = 1;
        q->bitmap = bitmap_slot(c, f->kind == MU_FX_ENERGY ? 0x7f2b : 0x7f84);
        memcpy(q->texcoord, uv_full, sizeof q->texcoord);
        float alpha = f->kind == MU_FX_HEAL ? (float)f->life / 20.0f : 1.0f;
        for (int k = 0; k < 4; ++k) {
            q->color[k][0] = q->color[k][1] = q->color[k][2] = alpha;
            q->color[k][3] = 1.0f;
        }
        if (f->kind == MU_FX_ENERGY) {
            q->eye_space = 1;
            mu_sprite_corners(camera, f->position, 120.0f, 120.0f, 0.0f, q->position);
        } else {
            float s = 110.0f, z = f->position[2] + 4.0f;
            const float corners[4][2] = {{-s, -s}, {s, -s}, {s, s}, {-s, s}};
            for (int k = 0; k < 4; ++k) {
                q->position[k][0] = f->position[0] + corners[k][0];
                q->position[k][1] = f->position[1] + corners[k][1];
                q->position[k][2] = z;
            }
        }
    }
    /* RenderPoints 0x0169159e(0) after blend 0x0184a990 (SRC_ALPHA,
     * ONE_MINUS_SRC_ALPHA) and depth test off */
    mu_number_call calls[256];
    int32_t count = mu_points_render(c->points, 0, calls, 256);
    if (count > 256)
        count = 256;
    for (int32_t i = 0; i < count; ++i) {
        mu_sprite_call sprites[16];
        int32_t s = mu_render_number(calls[i].position, calls[i].value, calls[i].color, calls[i].alpha,
                                     calls[i].scale, calls[i].render_arg, sprites, 16);
        if (s > 16)
            s = 16;
        for (int32_t k = 0; k < s; ++k) {
            mu_combat_quad *q = next_quad(quads, max, &n);
            if (!q)
                return n;
            q->eye_space = 1;
            q->bitmap = bitmap_slot(c, sprites[k].bitmap);
            mu_sprite_corners(camera, sprites[k].position, sprites[k].width, sprites[k].height, sprites[k].skew,
                              q->position);
            for (int v = 0; v < 4; ++v) {
                q->texcoord[v][0] = sprites[k].uv[v][0];
                q->texcoord[v][1] = sprites[k].uv[v][1];
                for (int ch = 0; ch < 3; ++ch)
                    q->color[v][ch] = sprites[k].light[v][ch];
                float a = sprites[k].alpha;
                q->color[v][3] = a > 1.0f ? 1.0f : (a < 0.0f ? 0.0f : a);
            }
        }
    }
    return n;
}

uint32_t mu_combat_model_flags(int32_t slot)
{
    return slot == MU_COMBAT_MODEL_FIRE ? 0x42u : 2u;
}

int32_t mu_combat_draw_models(mu_combat *c, mu_combat_model_fn draw, void *context)
{
    int32_t drawn = 0;
    for (int i = 0; i < MU_COMBAT_FX; ++i) {
        const mu_combat_fx *f = &c->fx[i];
        int slot = f->kind == MU_FX_ARROW ? MU_COMBAT_MODEL_ARROW : f->kind == MU_FX_FIRE ? MU_COMBAT_MODEL_FIRE : -1;
        if (slot < 0 || !c->models[slot].loaded)
            continue;
        mu_combat_model *m = &c->models[slot];
        mu_model_params p = m->model.params;
        for (int k = 0; k < 3; ++k) {
            p.origin[k] = f->position[k];
            p.angles[k] = f->angle[k];
            p.color[k] = 1.0f;
        }
        p.body_scale = f->scale;
        mu_model_apply_params(&m->model, &p);
        mu_model_set_state(&m->model, 0, 0.0f, 0.0f, 0);
        if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
            continue;
        draw(context, &m->model, &m->textures, slot);
        ++drawn;
    }
    return drawn;
}

int32_t mu_combat_live_points(const mu_combat *c)
{
    int32_t n = 0;
    for (int32_t i = 0; i < MU_POINTS; ++i)
        n += c->points[i].live != 0;
    return n;
}

int32_t mu_combat_live_fx(const mu_combat *c)
{
    int32_t n = 0;
    for (int i = 0; i < MU_COMBAT_FX; ++i)
        n += c->fx[i].kind != 0;
    return n;
}

/* ---------------------------------------------------------------- software drawing */

static void raster_model(void *context, const mu_model *model, const mu_textures *textures, int32_t slot)
{
    mu_raster *raster = context;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.flags = mu_combat_model_flags(slot);
    options.textures = textures;
    raster->textures = textures->slots;
    raster->texture_count = textures->count;
    raster->texture_filter = textures->filter;
    raster->texture_wrap = textures->wrap;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(model, &options, &backend, &ds);
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
}

/* One quad through the raster backend: blend, depth test as the quad says,
 * depth writes and culling off, bilinear sampling. */
static void raster_quad(mu_raster *raster, const mu_combat_quad *q, const mu_image *texture)
{
    mu_meshdraw_state state;
    mu_meshdraw_state_defaults(&state);
    state.blend = 1;
    state.src = q->additive ? 1u : 0x0302u;     /* GL_ONE / GL_SRC_ALPHA */
    state.dst = q->additive ? 1u : 0x0303u;     /* GL_ONE / GL_ONE_MINUS_SRC_ALPHA */
    state.fog = 0;
    state.depth_test = q->depth_test;
    state.depth_mask = 0;
    state.cull = 0;
    state.alpha_test = 0;
    state.texture = texture != NULL;
    const mu_image *slot = texture;
    const mu_image *const *saved_textures = raster->textures;
    int32_t saved_count = raster->texture_count;
    int saved_linear = raster->linear;
    raster->textures = &slot;
    raster->texture_count = 1;
    raster->linear = 1;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    backend.prepare(backend.context, &state, 0);
    backend.begin(backend.context);
    static const int corner[6] = {0, 1, 2, 0, 2, 3};
    for (int k = 0; k < 6; ++k) {
        int v = corner[k];
        backend.sink.texcoord(backend.sink.context, q->texcoord[v][0], q->texcoord[v][1]);
        backend.sink.color4(backend.sink.context, q->color[v][0], q->color[v][1], q->color[v][2], q->color[v][3]);
        backend.sink.vertex(backend.sink.context, q->position[v]);
    }
    backend.end(backend.context);
    raster->textures = saved_textures;
    raster->texture_count = saved_count;
    raster->linear = saved_linear;
}

void mu_combat_draw_raster(mu_combat *c, mu_raster *raster)
{
    mu_combat_draw_models(c, raster_model, raster);
    static mu_combat_quad quads[1024];
    int32_t n = mu_combat_quads(c, quads, 1024);
    float saved[16];
    memcpy(saved, raster->view, sizeof saved);
    static const float identity[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
    for (int32_t i = 0; i < n; ++i) {
        const mu_combat_quad *q = &quads[i];
        if (q->eye_space)
            memcpy(raster->view, identity, sizeof identity);
        raster_quad(raster, q, q->bitmap >= 0 ? &c->bitmaps[q->bitmap].image : NULL);
        memcpy(raster->view, saved, sizeof saved);
    }
}

/* ---------------------------------------------------------------- script and reports */

int mu_combat_script_parse(mu_combat_script *script, const char *text)
{
    memset(script, 0, sizeof *script);
    const char *p = text;
    while (*p) {
        while (*p == ' ' || *p == ';')
            ++p;
        if (!*p)
            break;
        if (script->count >= MU_COMBAT_SCRIPT)
            return 1;
        mu_combat_script_item *it = &script->items[script->count];
        char token[128];
        size_t n = 0;
        while (p[n] && p[n] != ';' && n + 1 < sizeof token)
            ++n;
        memcpy(token, p, n);
        token[n] = 0;
        p += n;
        char *a = strchr(token, ':');
        if (!a)
            return 1;
        *a++ = 0;
        it->frame = atoi(token);
        char *b = strchr(a, ':');
        if (b)
            *b++ = 0;
        snprintf(it->verb, sizeof it->verb, "%s", a);
        if (!strcmp(it->verb, "stop")) {
            ++script->count;
            continue;
        }
        if (!b)
            return 1;
        if (!strcmp(it->verb, "skill")) {
            char *c2 = strchr(b, ':');
            if (!c2)
                return 1;
            *c2++ = 0;
            it->skill = atoi(b);
            snprintf(it->actor, sizeof it->actor, "%s", c2);
        } else if (!strcmp(it->verb, "attack") || !strcmp(it->verb, "click")) {
            snprintf(it->actor, sizeof it->actor, "%s", b);
        } else {
            return 1;
        }
        ++script->count;
    }
    return 0;
}

void mu_combat_report_frame(const mu_combat *c, FILE *out, int32_t frame)
{
    const mu_hero *h = &c->walk->hero;
    fprintf(out, "{\"combat_frame\": %d, \"step\": %d, \"hero_action\": %u, \"hero_angle\": %.3f,"
            " \"attack_time\": %u, \"target\": %d, \"skill\": %d, \"points\": %d, \"fx\": %d, \"monsters\": [",
            frame, c->step, h->action, (double)h->angle[2], c->hero_attack_time, c->target, c->attack_skill,
            mu_combat_live_points(c), mu_combat_live_fx(c));
    int first = 1;
    for (int32_t i = 0; c->actors && i < c->actors->count; ++i) {
        if (c->actors->list[i].actor.spec.monster_type < 0)
            continue;
        const mu_combat_monster *m = &c->monsters[i];
        const mu_world_actor *a = &c->actors->list[i];
        fprintf(out, "%s{\"actor\": %d, \"hp\": %d, \"action\": %u, \"dead\": %u, \"alpha\": %.4f,"
                " \"z\": %.3f, \"removed\": %u, \"attack_time\": %u}", first ? "" : ", ", i, m->hp,
                mu_actor_action(&a->actor), m->dead, (double)m->alpha, (double)a->position[2], m->removed,
                m->attack_time);
        first = 0;
    }
    fprintf(out, "], \"point_list\": [");
    first = 1;
    for (int32_t i = 0; i < MU_POINTS; ++i) {
        const mu_point *p = &c->points[i];
        if (!p->live)
            continue;
        fprintf(out, "%s[%d, %.3f, %.3f, %.4f, %.3f, %.3f, %.3f, %.3f]", first ? "" : ", ", p->value,
                (double)p->position[2], (double)p->scale, (double)p->gravity, (double)p->color[0],
                (double)p->color[1], (double)p->color[2], (double)p->floor);
        first = 0;
    }
    fprintf(out, "]}\n");
}

void mu_combat_report_summary(const mu_combat *c, FILE *out, int quiet)
{
    const mu_combat_stats *s = &c->stats;
    fprintf(out, "{\"combat\": true, \"weapon\": %d, \"attack_speed\": %.1f, \"attacks\": %u, \"skills\": %u,"
            " \"arrows\": %u, \"fx_created\": %u, \"hits\": %u, \"misses\": %u, \"shocks\": %u, \"kills\": %u,"
            " \"deaths\": %u, \"removed\": %u, \"respawns\": %u, \"points_created\": %u,"
            " \"monster_attacks\": %u, \"hero_hits\": %u, \"picks\": %u, \"pick_hits\": %u,"
            " \"bitmaps_loaded\": %d, \"models_loaded\": %d}\n",
            c->config.weapon, (double)c->config.attack_speed, s->attacks, s->skills, s->arrows, s->fx_created,
            s->hits, s->misses, s->shocks, s->kills, s->deaths, s->removed, s->respawns, s->points_created,
            s->monster_attacks, s->hero_hits, s->picks, s->pick_hits,
            (int)(c->bitmaps[0].loaded + c->bitmaps[1].loaded + c->bitmaps[2].loaded + c->bitmaps[3].loaded +
                  c->bitmaps[4].loaded + c->bitmaps[5].loaded + c->bitmaps[6].loaded + c->bitmaps[7].loaded +
                  c->bitmaps[8].loaded + c->bitmaps[9].loaded),
            c->models[0].loaded + c->models[1].loaded);
    if (!quiet)
        for (int32_t i = 0; i < c->log_count; ++i)
            fprintf(out, "{\"combat_log\": \"%s\"}\n", c->log[i]);
}
