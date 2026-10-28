/* Combat in the walk-around world (NATIVE-COMBAT-001). See mu_combat.h for
 * the split between client behaviour and the labelled demo / viewer choices. */
#define _POSIX_C_SOURCE 200809L
#include "mu_combat.h"
#include "mu_combat_audio.h"
#include "../session/mu_session.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/movement/client_movement.h"
#include "mu_lang.h"
#include "mu_raster.h"
#include "mu_scene.h"
#include "mu_particles.h"
#include "../../reconstructed/path/client_path.h"

#define HERO_KEY 0x1234          /* any key: the hero's own key 0x06fca288 */
#define MONSTER_KEY_BASE 0x100   /* demo keys of the placed actors */

static void log_line(mu_combat *c, const char *text)
{
    if (c->log_count < (int32_t)(sizeof c->log / sizeof c->log[0]))
        snprintf(c->log[c->log_count++], sizeof c->log[0], "%s", text);
}

/* Presentation randomness for bounded player action services. */
static uint32_t visual_rand(mu_combat *c)
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
    config->hero_hp = 400;
    config->hero_respawn_steps = 100;
}

static void play(mu_combat *c, mu_combat_audio d, int16_t key)
{
    int32_t id=d.id;
    if (id < 0 || !d.site) return;
    mu_combat_audio_emit(c->session,d,key);
    ++c->sounds_played;
    c->last_sound=id;
    if (!c->session && c->play_sound) c->play_sound(c->sound_context,id);
}

static mu_player_state hero_state(const mu_combat *c)
{
    mu_player_state st;
    memset(&st, 0, sizeof st);
    st.class_byte = c->walk->hero.class_byte;
    st.class_check = (uint8_t)mu_class_check(st.class_byte);
    st.field_3324 = c->hero_3324;
    return st;
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

static void init_env(mu_combat *c);

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
    {0x7f3c, "Effect", "Fire01.jpg", 'j'},          /* LoadBitmap 0x0185baac call sites (static) */
    {0x7f26, "Effect", "Spark03.jpg", 'j'},
    {0x7fd8, "Effect", "JointEnergy01.jpg", 'j'},
    {0x7fd3, "Effect", "JointSpirit01.jpg", 'j'},
    {0x7fd5, "Effect", "Spark01.jpg", 'j'},         /* the Twisting Slash swirl's spark joints (NATIVE-JOINT-001) */
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
    /* AccessModel(index, "Data\Skill\", name, number) of the loader 0x018202b4 (static) */
    static const struct { int32_t type; const char *file; } files[MU_COMBAT_MODELS] = {
        {0x43b, "Data/Skill/Arrow01.bmd"}, {0x413, "Data/Skill/Fire01.bmd"}, {0x41c, "Data/Skill/Circle01.bmd"},
        {0x41d, "Data/Skill/Circle02.bmd"}, {0x457, "Data/Skill/Inferno01.bmd"}, {0x421, "Data/Skill/Laser01.bmd"},
        {0x419, "Data/Skill/Stone01.bmd"}, {0x41a, "Data/Skill/Stone02.bmd"}, {MU_SFX_TWISTING_SWIRL, NULL},
        {0x412, "Data/Skill/Ice01.bmd"}, {0x41b, "Data/Skill/Ice02.bmd"}, {0x41f, "Data/Skill/Magic02.bmd"},
    };
    for (int i = 0; i < MU_COMBAT_MODELS; ++i) {
        mu_combat_model *m = &c->models[i];
        m->type = files[i].type;
        const char *file = files[i].file;
        if (i == MU_COMBAT_MODEL_WEAPON)
            file = mu_combat_weapon_file(c->config.weapon);   /* Twisting Slash draws the weapon */
        if (!file)
            continue;
        char path[4096], message[512], text[96];
        snprintf(path, sizeof path, "%s/%s", root, file);
        if (mu_bmd_load_file(path, &m->bmd, message, sizeof message) != MU_BMD_OK) {
            snprintf(text, sizeof text, "model 0x%x missing (%s)", m->type, file);
            log_line(c, text);
            continue;
        }
        mu_model_params p;
        mu_model_scene_params(&p);   /* light override 1 (NATIVE-LIGHT-001) */
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
    c->audio_rng = config->seed;
    c->hero_key = HERO_KEY;
    c->target = -1;
    c->intent_skill = -1;
    c->lang = mu_lang_load_default();   /* NATIVE-LANG-001: the client's skill table when MU_LANG_DIR has it */
    c->attack_target = -1;
    c->last_sound = -1;
    c->hero_hp = 0;
    c->crt_seed = config->seed ? config->seed : 1u;
    c->time_step = 0.1f;
    init_env(c);
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
    /* the Player model's base speeds and loop flags of the player loader
     * 0x01830aa6 (NATIVE-ACTOR-001's table): the hit actions 0x134..0x13a and
     * the death actions 0x142..0x147 (which stop on their last key) */
    if (hero)
        mu_character_apply_player_speeds(hero);
    for (int32_t i = 0; actors && i < actors->count; ++i) {
        mu_combat_monster *m = &c->monsters[i];
        m->alpha = 1.0f;
        m->saved_wander = -1;
    }
    load_bitmaps(c, root);
    load_models(c, root);
    return 0;
}

void mu_combat_free(mu_combat *c)
{
    mu_lang_free(c->lang);
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

/* ---------------------------------------------------------------- effects (NATIVE-COMBAT-002) */

/* The client's rand() 0x01989721: the MSVC CRT recurrence. The effect
 * randomness draws from it; the demo server keeps its own generator. */
static int32_t crt_rand(void *context)
{
    mu_combat *c = context;
    c->crt_seed = c->crt_seed * 214013u + 2531011u;
    return (int32_t)((c->crt_seed >> 16) & 0x7fffu);
}

static float env_terrain_height(void *context, float x, float y);

static const mu_sfx_object *env_object(void *context, int32_t index)
{
    mu_combat *c = context;
    if (index < 0 || index > MU_COMBAT_HERO_OBJECT)
        return NULL;
    return &c->objects[index];
}

/* The objects the effects read: the placed actors by index, the hero at
 * MU_COMBAT_HERO_OBJECT. visible: live and drawn (the client's frustum test
 * +0x0b is taken as true for everything near the hero). */
static void refresh_objects(mu_combat *c)
{
    memset(c->objects, 0, sizeof c->objects);
    for (int32_t i = 0; c->actors && i < c->actors->count && i < MU_WORLD_ACTORS_MAX; ++i) {
        mu_sfx_object *o = &c->objects[i];
        const mu_combat_monster *m = &c->monsters[i];
        o->live = !m->removed;
        o->visible = !m->removed;
        memcpy(o->position, c->actors->list[i].position, sizeof o->position);
    }
    mu_sfx_object *h = &c->objects[MU_COMBAT_HERO_OBJECT];
    h->live = 1;
    h->visible = 1;
    h->weapon = (int16_t)(c->weapon_item[0] < 0 ? -1 : c->weapon_item[0] - 0xae6);   /* TS: o + 0x56 */
    memcpy(h->position, c->walk->hero.position, sizeof h->position);
}

static mu_sfx_effect *effect_slot(mu_combat *c)
{
    for (int i = 0; i < MU_SFX_EFFECTS; ++i)
        if (!c->effects[i].live)
            return &c->effects[i];
    return NULL;
}

static void create_effect(mu_combat *c, int32_t type, int32_t subtype, const float position[3], const float angle[3],
                          const float light[3], int32_t owner, const mu_sfx_info *info)
{
    mu_sfx_effect *e = effect_slot(c);   /* the first free record of the 200 (0x013c0f46) */
    if (!e)
        return;
    float creation_light[3];
    memcpy(creation_light, light, sizeof creation_light);
    if (mu_sfx_effect_create(e, type, subtype, position, angle, creation_light, owner, 0.0f, info, &c->env)) {
        ++c->stats.fx_created;
        if (type == MU_SFX_MODEL_ARROW)
            ++c->stats.arrows;
    } else {
        ++c->stats.unsupported;
    }
}

static void create_particle(mu_combat *c, const mu_sfx_call *call)
{
    if (c->particle_count >= MU_COMBAT_PARTICLES)
        return;
    mu_sfx_particle *p = &c->particles[c->particle_count];   /* appended to the list (0x01691232) */
    if (mu_sfx_particle_create(p, call->type, call->position, call->angle, call->light, call->subtype, call->scale,
                               call->owner >= 0 ? call->owner : -1, 0, &c->env)) {
        ++c->particle_count;
        ++c->stats.particles_created;
    } else if (c->legacy_particles && mu_pt_kind_supported(call->type, call->subtype)) {
        /* NATIVE-PARTICLE-001: kinds of the legacy particle module (Fire01 1..3, smoke01 3, Spark02 0);
         * the owner is not modelled there (these calls pass none) */
        mu_world_particles_create(c->legacy_particles, call->type, call->position, call->angle, call->light,
                                  call->subtype, call->scale);
        ++c->stats.particles_created;
    } else {
        ++c->stats.unsupported;
    }
}

/* CreateJoint through the shared joint pool helpers (NATIVE-JOINT-001: reconstructed/joints). */
static void create_joint(mu_combat *c, int32_t type, const float position[3], const float target_position[3],
                         const float angle[3], int32_t subtype, int32_t target, float scale, uint16_t key,
                         uint16_t skill)
{
    c->jenv.serial = c->serial;
    const int32_t i = mu_joints_create(c->joints, MU_SFX_JOINTS, type, position, target_position, angle, subtype,
                                       target, scale, key, skill, 0, 0xffff, 0, &c->jenv);
    if (i >= 0)
        ++c->stats.joints_created;
    else if (i == -2)
        ++c->stats.unsupported;
}

static void add_light(mu_combat *c, float x, float y, const float rgb[3], int32_t range)
{
    if (c->light_count >= MU_COMBAT_LIGHTS)
        return;
    mu_combat_light *l = &c->lights[c->light_count++];
    l->x = x;
    l->y = y;
    memcpy(l->rgb, rgb, sizeof l->rgb);
    l->range = range;
}


/* The arrow hit check 0x013bd374 (static reading of its default path): an
 * arrow the client tests itself (+0x3b) ends when it comes within 100 units
 * (x/y) of a live, visible character other than its owner, not dead; the
 * key test is the target's (the demo's attack target). */
static void check_arrow(mu_combat *c, mu_sfx_effect *e)
{
    if (!e->client_hit)
        return;
    for (int32_t i = 0; c->actors && i < c->actors->count; ++i) {
        if (!is_monster(c, i) || c->monsters[i].dead || c->monsters[i].removed)
            continue;
        const float *p = c->actors->list[i].position;
        float dx = e->position[0] - p[0], dy = e->position[1] - p[1];
        if (!(100.0f >= sqrtf(dx * dx + dy * dy)))
            continue;
        e->live = 0;   /* SetLive(0), 0x013bd6d9 */
        ++c->stats.projectile_hits;
        return;
    }
}

static int env_call(void *context, const mu_sfx_call *call, mu_sfx_effect *e)
{
    mu_combat *c = context;
    switch (call->routine) {
    case MU_SFX_CALL_TERRAIN_LIGHT:
        add_light(c, call->position[0], call->position[1], call->light, call->range);
        return 0;
    case MU_SFX_CALL_PARTICLE:
        create_particle(c, call);
        return 0;
    case MU_SFX_CALL_JOINT:
        create_joint(c, call->type, call->position, call->target, call->angle, call->subtype, call->owner,
                     call->scale, c->hero_key & 0xffff, 0);
        return 0;
    case MU_SFX_CALL_EFFECT: {
        mu_sfx_info info;
        memset(&info, 0, sizeof info);
        int32_t owner = call->owner == -2 ? -1 : call->owner;
        create_effect(c, call->type, call->subtype, call->position, call->angle, call->light, owner, &info);
        return 0;
    }
    case MU_SFX_CALL_ANIMATION: {
        /* viewer choice: the model's action 0 advances by the effect's speed and loops */
        int16_t keys = 1;
        if (e && c->env.model)
            c->env.model(c, e->type, e->action, &keys);
        if (e) {
            e->frame = e->frame + e->velocity;
            if (keys > 1 && e->frame >= (float)keys)
                e->frame = e->frame - (float)keys;
        }
        return 1;
    }
    case MU_SFX_CALL_CHECK_ARROW:
        if (e)
            check_arrow(c, e);
        return 0;
    case MU_SFX_CALL_CHECK_MAGIC:
        if (e) {
            int32_t before = e->lifetime;
            mu_sfx_check_magic(e, &c->env);
            if (e->lifetime == 1 && before != 1) {
                ++c->stats.projectile_hits;
            }
        }
        return 0;
    case MU_SFX_CALL_SOUND:
        play(c, mu_combat_effect_sound(call->type), -3);
        return 0;
    case MU_SFX_CALL_SERIAL:
        ++c->serial;
        c->env.serial = c->serial;
        return 0;
    case MU_SFX_CALL_AREA: {   /* = MU_SFX_CALL_AREA_ATTACK */
        /* The visual request is counted; server answers arrive independently as frames. */
        ++c->stats.area_requests;
        return 0;
    }
    case MU_SFX_CALL_SPRITE:
        ++c->stats.sprites;
        /* CreateSprite 0x01692eb7(bitmap, position, scale, light, owner, rotation = angle x, 0, 0)
         * through the legacy particle module (NATIVE-PARTICLE-001) */
        if (c->legacy_particles)
            mu_world_particles_sprite(c->legacy_particles, call->type, call->position, call->scale, call->light,
                                      call->owner, call->angle[0], 0, 0);
        return 0;
    default:
        return 0;
    }
}

static int env_model(void *context, int32_t type, uint16_t action, int16_t *keys)
{
    mu_combat *c = context;
    *keys = 1;
    for (int i = 0; i < MU_COMBAT_MODELS; ++i)
        if (c->models[i].type == type && c->models[i].loaded) {
            const mu_bmd *b = &c->models[i].bmd;
            if (b->action_count > 0) {
                int32_t a = action < b->action_count ? action : 0;
                *keys = (int16_t)b->actions[a].keys;
            }
            return 1;
        }
    return 1;   /* a missing native model: the client has it */
}

/* The joint module's view of the skill environment. */
static int32_t jt_rand(void *context) { return crt_rand(context); }
static float jt_height(void *context, float x, float y) { return env_terrain_height(context, x, y); }
static const mu_jt_object *jt_object(void *context, int32_t index) { return env_object(context, index); }
static void jt_call(void *context, const mu_jt_call *call) { env_call(context, call, NULL); }

/* MoveJoint's inputs: the wall test under the head (Evil Spirit's wide spirits) and the hero target. */
static void joint_inputs(void *context, const mu_jt_joint *j, mu_jt_move_inputs *in)
{
    mu_combat *c = context;
    in->wall = c->map ? c->map->attributes[(((int32_t)(j->position[1] / 100.0f) & 0xff) << 8) +
                                           ((int32_t)(j->position[0] / 100.0f) & 0xff)] : 0;
    in->wall_scene = 1;
    in->is_hero_target = j->target == MU_COMBAT_HERO_OBJECT;
}

static void init_env(mu_combat *c)
{
    memset(&c->jenv, 0, sizeof c->jenv);
    c->jenv.context = c;
    c->jenv.rand = jt_rand;
    c->jenv.height = jt_height;
    c->jenv.object = jt_object;
    c->jenv.call = jt_call;
    c->jenv.serial = c->serial;
    memset(&c->env, 0, sizeof c->env);
    c->env.context = c;
    c->env.rand = crt_rand;
    c->env.height = env_terrain_height;
    c->env.object = env_object;
    c->env.call = env_call;
    c->env.model = env_model;
    c->env.serial = c->serial;
    c->env.report_checks = 1;
    c->env.hero_object = MU_COMBAT_HERO_OBJECT;
}

/* The hero's object fields an effect is created from (o + 0x158, + 0x164,
 * + 0xec: light (1, 1, 1) for the demo). */
static void hero_frame(const mu_combat *c, float position[3], float angle[3], float light[3])
{
    const mu_hero *h = &c->walk->hero;
    memcpy(position, h->position, 3 * sizeof(float));
    memcpy(angle, h->angle, 3 * sizeof(float));
    light[0] = light[1] = light[2] = 1.0f;
}

/* CreateArrow 0x0158cf57 for the hero's bow: the arrow starts at the
 * archer's ground position (z = RequestTerrainHeight) with its angle, owned
 * by the archer, tested by the client (+0x3b = 1: the hero's own arrows). */
static void create_arrow(mu_combat *c, float angle_offset)
{
    float pos[3], angle[3], light[3];
    hero_frame(c, pos, angle, light);
    pos[2] = env_terrain_height(c, pos[0], pos[1]);
    angle[2] = angle[2] + angle_offset;
    mu_sfx_info info;
    memset(&info, 0, sizeof info);
    info.key = (uint16_t)c->hero_key;
    info.word4 = 1;
    create_effect(c, MU_SFX_MODEL_ARROW, 0, pos, angle, light, MU_COMBAT_HERO_OBJECT, &info);
}

/* Inferno's ring 0x0142da3e(position, 0) (static reading): eight points at
 * 45-degree steps, 220 units out; at each a burst 0x013c07f4 (not
 * reconstructed) and two stones, Stone 0x419 + rand % 2 of subtype 1 and of
 * subtype 0. */
static void inferno_ring(mu_combat *c, const float center[3])
{
    static const float reach[3] = {0.0f, -220.0f, 0.0f};
    const float white[3] = {1.0f, 1.0f, 1.0f};
    for (int k = 0; k < 8; ++k) {
        float a[3] = {0.0f, 0.0f, (float)k * 45.0f}, m[12], p[3];
        mu_angle_matrix(a, m);
        mu_vector_rotate(reach, m, p);
        p[0] = p[0] + center[0];
        p[1] = p[1] + center[1];
        p[2] = p[2] + center[2];
        ++c->stats.unsupported;   /* the burst 0x013c07f4 */
        const float zero[3] = {0.0f, 0.0f, 0.0f};
        create_effect(c, MU_SFX_MODEL_STONE1 + crt_rand(c) % 2, 1, p, zero, white, -1, NULL);
        create_effect(c, MU_SFX_MODEL_STONE1 + crt_rand(c) % 2, 0, p, zero, white, -1, NULL);
    }
}

/* The end of the hero's attack: the area skills' switch 0x013a90c0 and the
 * end-of-attack switch 0x013af035 with the client's CreateEffect /
 * CreateJoint calls (static readings of the call sites; the effects
 * themselves are the verified reconstruction). */
static void end_of_attack(mu_combat *c)
{
    const mu_hero *h = &c->walk->hero;
    int32_t t = c->attack_target, skill = c->attack_skill;
    float pos[3], angle[3], light[3];
    hero_frame(c, pos, angle, light);
    mu_sfx_info info;
    memset(&info, 0, sizeof info);
    info.key = (uint16_t)c->hero_key;
    int target_ok = c->actors && t >= 0 && t < c->actors->count;
    if (target_ok)   /* the end-of-attack angle: CreateAngle toward the target (0x013af01b) */
        angle[2] = mu_create_angle(pos[0], pos[1], c->actors->list[t].position[0], c->actors->list[t].position[1]);
    play(c, mu_combat_skill_sound(skill, 1, -1, 0), -1);   /* the end-of-attack blocks' sounds (0x42, 0x75, 0x77, 0x73, ...) */
    switch (skill) {
    case 0:
        if (h->action >= 0x7e && h->action <= 0x81)   /* 0x013aea7a: bow actions shoot */
            create_arrow(c, 0.0f);
        break;
    case 24:
        /* Triple Shot: two CreateArrows calls (static: spread of +-8 degrees here) */
        create_arrow(c, -8.0f);
        create_arrow(c, 0.0f);
        create_arrow(c, 8.0f);
        break;
    case 1:
        /* 0x013affd6..0x013b0075: the player emits ten smoke01/1 particles.
         * Poison01 is restricted to monster model 0xa91 at this call site. */
        if (target_ok) {
            mu_sfx_call call;
            memset(&call, 0, sizeof call);
            call.type = 0x7f5a;
            call.subtype = 1;
            call.scale = 1.0f;
            call.owner = -1;
            memcpy(call.position, c->actors->list[t].position, sizeof call.position);
            memcpy(call.angle, h->angle, sizeof call.angle);
            call.light[0] = 0.4f; call.light[1] = 0.6f; call.light[2] = 1.0f;
            for (int k = 0; k < 10; ++k) create_particle(c, &call);
        }
        break;
    case 7:
        /* 0x013afd61: target ice and five debris pieces, no owner. */
        if (target_ok) {
            const float *at = c->actors->list[t].position;
            create_effect(c, 0x412, 0, at, h->angle, light, -1, NULL);
            for (int k = 0; k < 5; ++k)
                create_effect(c, 0x41b, 0, at, h->angle, light, -1, NULL);
        }
        break;
    case 11:
        /* 0x013b05eb: one wave for a player. Only monster 0x7b7 adds +/-10 degrees. */
        create_effect(c, 0x41f, 0, pos, angle, light, -1, NULL);
        break;
    case 4:
        /* 0x013b0397: MODEL_FIRE subtype 1 from the caster, owned by the target */
        create_effect(c, MU_SFX_MODEL_FIRE, 1, pos, angle, light, target_ok ? t : -1, &info);
        break;
    case 17:
        /* 0x013b0db4: Thunder01 subtype 0 from the caster, owned by the target */
        create_effect(c, MU_SFX_BITMAP_THUNDER, 0, pos, angle, light, target_ok ? t : -1, &info);
        break;
    case 26:
        /* 0x013afaab: Magic_Ground2 subtype 1 at the target, owned by it */
        if (target_ok) {
            const mu_world_actor *a = &c->actors->list[t];
            create_effect(c, MU_SFX_BITMAP_MAGIC_GROUND2, 1, a->position, a->angle, light, t, &info);
        }
        break;
    case 9: {
        /* Evil Spirit 0x013acd62: four directions, a wide (80) and a narrow
         * (20) JointSpirit01 each, from the caster's position + 100,
         * chasing the caster */
        float from[3] = {pos[0], pos[1], pos[2] + 100.0f};
        for (int k = 0; k < 4; ++k) {
            float a[3] = {0.0f, 0.0f, (float)k * 90.0f};
            create_joint(c, MU_SFX_BITMAP_JOINT_SPIRIT, from, pos, a, 0, MU_COMBAT_HERO_OBJECT, 80.0f,
                         (uint16_t)c->hero_key, 9);
            create_joint(c, MU_SFX_BITMAP_JOINT_SPIRIT, from, pos, a, 0, MU_COMBAT_HERO_OBJECT, 20.0f,
                         (uint16_t)c->hero_key, 9);
        }
        ++c->serial;
        c->env.serial = c->serial;
        break;
    }
    case 10:
        /* Hellfire 0x013abb52: Circle01 (owned by the caster) and Circle02 */
        info.skill = 10;
        create_effect(c, MU_SFX_MODEL_CIRCLE, 0, pos, h->angle, light, MU_COMBAT_HERO_OBJECT, &info);
        create_effect(c, MU_SFX_MODEL_CIRCLE_LIGHT, 0, pos, h->angle, light, -1, NULL);
        break;
    case 14:
        /* Inferno 0x013acc46: the ring, then Inferno01 owned by the caster */
        info.skill = 14;
        inferno_ring(c, pos);
        create_effect(c, MU_SFX_MODEL_INFERNO, 0, pos, h->angle, light, MU_COMBAT_HERO_OBJECT, &info);
        ++c->serial;
        c->env.serial = c->serial;
        break;
    case 41:
        /* Twisting Slash 0x013aba81: o + 0x56 = the weapon, then the spawner */
        info.skill = 41;
        create_effect(c, MU_SFX_TWISTING_SLASH, 0, pos, h->angle, light, MU_COMBAT_HERO_OBJECT, &info);
        break;
    default:
        break;
    }
}

/* One logic step of the three pools in the client's order: MoveEffects
 * 0x0150ddb1, MoveJoints 0x01589b06, MoveParticles 0x0159122d. */
static void move_pools(mu_combat *c)
{
    c->light_count = 0;
    refresh_objects(c);
    for (int i = 0; i < MU_SFX_EFFECTS; ++i)
        if (c->effects[i].live && !mu_sfx_effect_move(&c->effects[i], &c->env))
            c->effects[i].live = 0;   /* an unsupported kind ends at once */
    c->jenv.serial = c->serial;
    mu_joints_move_all(c->joints, MU_SFX_JOINTS, &c->jenv, c->time_step, joint_inputs, c);
    int32_t kept = 0;
    for (int32_t i = 0; i < c->particle_count; ++i) {
        mu_sfx_particle *p = &c->particles[i];
        if (!mu_sfx_particle_move(p, c->time_step))
            continue;   /* erased at the head of the step */
        if (kept != i)
            c->particles[kept] = *p;
        ++kept;
    }
    c->particle_count = kept;
}

/* ---------------------------------------------------------------- receive presentation */

static float terrain_height(void *context, float x, float y)
{
    const mu_world *map = context;   /* RequestTerrainHeight 0x016cc9e2 in scene 6 */
    return map ? mu_request_terrain_height(map->height, map->attributes, map->water_height, 6, x, y) : 0.0f;
}

static float env_terrain_height(void *context, float x, float y)
{
    const mu_combat *c = context;
    return terrain_height((void *)c->map, x, y);
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

/* NATIVE-ITEMS-001: the voice inputs of a monster (SetPlayerShock / SetPlayerDie's monster branches):
 * the model's sound slots from OpenMonsterModel (extracted); o + 0x60 is taken as 0 (viewer choice: the
 * demo actors carry no subtype). */
static mu_monster_voice monster_voice(const mu_combat *c, int32_t i)
{
    const mu_world_actor *a = &c->actors->list[i];
    mu_monster_voice v;
    memset(&v, 0, sizeof v);
    v.object_type = a->actor.spec.model_index;
    v.object_kind = 0;
    v.field_3324 = c->monsters[i].voice_3324;
    v.has_model = mu_monster_sound_slots(a->actor.spec.model_index - 0x7a5, v.slots);
    return v;
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
    if (e->shock && mu_shock_gate(m->dead,mu_actor_action(&a->actor),e->damage,e->type)) {
        int32_t action = mu_shock_action(m->dead, a->actor.spec.model_index, mu_actor_action(&a->actor),
                                         a->server_class, e->damage, e->type);
        if (action >= 0) {
            set_monster_action(c, i, action);
            ++c->stats.shocks;
        }
        if (mu_shock_gate(m->dead, mu_actor_action(&a->actor), e->damage, e->type) &&
            a->actor.spec.model_index != 0xa91) {   /* SetPlayerShock's sound tail (NATIVE-ITEMS-001) */
            mu_monster_voice v = monster_voice(c, i);
            uint32_t saved = c->crt_seed;
            int32_t r[2] = {crt_rand(c), 0}, act, snd;
            int32_t used = mu_monster_shock(&v, a->server_class, mu_actor_action(&a->actor), r, 1, &act, &snd);
            if (!used)
                c->crt_seed = saved;   /* rand() is called only on the slot path */
            if (snd >= 0) {
                play(c, mu_combat_voice_sound(MU_COMBAT_AUDIO_SHOCK, 1, snd), a->session_key);
                ++c->stats.monster_voices;
            }
            /* The model 0x7e2 tail follows the primary voice, after its five
             * particle iterations. Native audio does not consume that visual RNG. */
            play(c,mu_combat_extra_shock_sound(v.object_type,v.field_3324,snd),a->session_key);
        }
    }
    if(e->damage>0)++c->stats.hits;else ++c->stats.misses;
    show_damage(c, MONSTER_KEY_BASE + i, a->position, e->damage, e->type, e->flag8, e->flag_a);

}

static float player_speed(const mu_combat *c, int32_t action);

/* The damage packet on the hero: SetPlayerShock 0x0138f92f's Player branch
 * (verified) and, with the demo's hit points, the die packet. */
static void hero_hit(mu_combat *c, int32_t damage, int32_t type)
{
    mu_hero *h = &c->walk->hero;
    if (mu_shock_gate(c->hero_dead, h->action, damage, type)) {
        mu_player_state st = hero_state(c);
        int32_t rands[4], action = -1, sound = -1;
        for (int k = 0; k < 4; ++k)
            rands[k] = (int32_t)(visual_rand(c) & 0x7fff);
        mu_player_shock(&st, rands, 4, &action, &sound);
        mu_walk_set_action(c->walk, action, player_speed(c, action));   /* SetAction 0x012affa4 */
        play(c, mu_combat_voice_sound(MU_COMBAT_AUDIO_SHOCK, 0, sound), -1);
        ++c->stats.hero_shocks;
    }

}

/* MoveCharacter's dead counter for the hero: SetPlayerDie from 15 on
 * (Player branch verified); the demo respawn after the configured delay. */
static void hero_dead_step(mu_combat *c)
{
    if (!c->hero_dead)
        return;
    int die = 0;
    c->hero_dead = mu_dead_step(c->hero_dead, &die);
    if (die && c->hero_3324 == 0.0f) {
        mu_player_state st = hero_state(c);
        int32_t rands[4], action = -1, sounds[2];
        for (int k = 0; k < 4; ++k)
            rands[k] = (int32_t)(visual_rand(c) & 0x7fff);
        mu_player_die(&st, rands, 4, &action, sounds);
        mu_walk_set_action(c->walk, action, player_speed(c, action));
        play(c, mu_combat_voice_sound(MU_COMBAT_AUDIO_DIE, 0, sounds[0]), -1);
        play(c, mu_combat_voice_sound(MU_COMBAT_AUDIO_DIE, 0, sounds[1]), -1);
        c->hero_3324 = 0.001f;   /* the voice played once */
        ++c->stats.hero_deaths;
    }
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
    c->intent_skill_checked = 0;
    int32_t mana = 0, distance = 0, ag = 0;
    const char *name = mu_lang_skill_info(c->lang, skill, 0, &mana, &distance, &ag);
    if (name) {   /* GetSkillInformation 0x01696458 over the client's table */
        char line[96], clean[48];
        snprintf(line, sizeof line, "skill %d %s: mana %d, AG %d, distance %d", skill,
                 mu_lang_ascii(clean, sizeof clean, name), mana, ag, distance);
        log_line(c, line);
    }
}

void mu_combat_cast_checked(mu_combat *c, int32_t skill, int32_t actor)
{
    mu_combat_cast(c,skill,actor);
    if(c->intent_skill==skill)c->intent_skill_checked=1;
}

void mu_combat_stop(mu_combat *c)
{
    c->target = -1;
    c->intent_skill = -1;
}

/* Range of a skill in tiles: the skill table's distance (+0x34, the base of
 * GetSkillDistance 0x01696630; the character's class and skill-tree bonuses
 * are not applied) when the client's table is loaded (NATIVE-LANG-001), else
 * the demo ranges: melee skills 2 tiles, the rest 6. */
static float skill_range(const mu_combat *c, int32_t skill)
{
    const mu_lang_skill *s = mu_lang_skill_get(c->lang, skill);
    if (s && s->distance > 0)
        return (float)s->distance;
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
    if (skill && c->session && c->intent_skill_checked) {
        mu_intent in={.kind=MU_INTENT_SKILL_CAST};in.u.skill_cast.skill=skill;
        in.u.skill_cast.x=(uint8_t)a->tile[0];in.u.skill_cast.y=(uint8_t)a->tile[1];
        mu_session_submit(c->session,&in);
        if(mu_session_skills_last_cast(c->session)!=MU_SKILL_CAST_OK)return;
        ++c->stats.requests_unsent; /* the existing cast builder requires crypto */
    }
    /* face the target: CreateAngle 0x012aed9e(hero x, y, target x, y) */
    h->angle[2] = mu_create_angle(h->position[0], h->position[1], a->position[0], a->position[1]);
    int32_t action = -1;
    int32_t rands[8];
    for (int k = 0; k < 8; ++k)
        rands[k] = (int32_t)(visual_rand(c) & 0x7fff);
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
        /* SetPlayerAttack's sound tail (0x01393924): the swing, bow or crossbow */
        mu_player_state st = hero_state(c);
        int32_t sound = -1;
        int32_t used = r.rand_used < 8 ? r.rand_used : 8;
        mu_player_attack_sound(&st, in.bow_kind, in.weapon[0], in.weapon[1], c->map ? c->map->world : 0,
                               rands + used, 8 - used, &sound);
        play(c, mu_combat_voice_sound(MU_COMBAT_AUDIO_ATTACK, 0, sound), -1);
    } else {
        const mu_skill_visual *v = mu_skill_visual_find(skill);
        action = v && v->action >= 0 ? v->action
                                     : mu_player_magic_action(h->class_byte, mu_class_check(h->class_byte), rands[0]);
        ++c->stats.skills;
        /* the receive handlers' sounds of the melee skills and buffs (0x70..0x73, 0x6f) */
        play(c, mu_combat_skill_sound(skill, 0, -1, 0), -1);
    }
    if (action >= 0)
        mu_walk_set_action(w, action, player_speed(c, action));
    ++c->hero_counter;              /* SetPlayerAttack's tail: c + 0x28 += 1 */
    c->hero_attack_time = 1;        /* 0x01697ec9 */
    engage(c, t);                   /* demo: the target stops wandering once attacked */
    c->attack_target = t;
    c->attack_skill = skill;
    if (c->session && (!skill || !c->intent_skill_checked)) {
        mu_intent in = {0};
        if (!skill) {
            in.kind=MU_INTENT_COMBAT_ATTACK;
            in.u.combat_attack.target=(uint16_t)a->session_key;
            in.u.combat_attack.direction=mu_attack_direction(h->angle[2]);
        } else {
            in.kind=MU_INTENT_COMBAT_CAST;
            in.u.combat_cast.x=(uint8_t)a->tile[0];in.u.combat_cast.y=(uint8_t)a->tile[1];
            in.u.combat_cast.skill=(uint8_t)skill;
        }
        mu_submit submitted=mu_session_submit(c->session,&in);
        if(submitted.status==MU_SUBMIT_SENT)++c->stats.requests_sent;else ++c->stats.requests_unsent;
    }

}

/* MoveHero's attack case for the selected target: range, walk, attack. */
static void hero_decide(mu_combat *c)
{
    mu_walk *w = c->walk;
    mu_hero *h = &w->hero;
    if (c->intent_skill < 0 || c->hero_attack_time > 0 || c->hero_dead)
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
    float range = c->intent_skill ? skill_range(c, c->intent_skill)
                                  : mu_hero_attack_range(item, weapons[c->config.weapon].bow_kind != 0, 0, 0);
    if (!mu_in_range(h->tile[0], h->tile[1], a->tile[0], a->tile[1], range)) {
        /* walk toward the target (the client paths with PathFinding2 and the
         * range for classes 2 and 10; the demo does it for every class) */
        if (!h->movement || w->target[0] != a->tile[0] || w->target[1] != a->tile[1]) {
            mu_walk_path_to(w, a->tile[0], a->tile[1]);
            if(c->session && h->movement) {
                mu_intent in={.kind=MU_INTENT_COMBAT_MOVE};
                memcpy(in.u.combat_move.x,h->path.x,15);memcpy(in.u.combat_move.y,h->path.y,15);
                in.u.combat_move.count=h->path.count;in.u.combat_move.target_x=(uint8_t)w->target[0];
                in.u.combat_move.target_y=(uint8_t)w->target[1];in.u.combat_move.angle=h->angle[2];
                mu_submit submitted=mu_session_submit(c->session,&in);
                if(submitted.status==MU_SUBMIT_SENT)++c->stats.requests_sent;else ++c->stats.requests_unsent;
            }
        }
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

int32_t mu_combat_pick(mu_combat *c)
{
    return pick_monster(c);
}

void mu_combat_pre_step(mu_combat *c)
{
    mu_frame_world *f = &c->walk->frame;
    if (c->hero_dead) {   /* a dead hero neither walks nor attacks (demo) */
        f->mouse.left_push = 0;
        f->mouse.left = 0;
        return;
    }
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



static void monster_step(mu_combat *c, int32_t i)
{
    mu_combat_monster *m = &c->monsters[i];
    mu_world_actor *a = &c->actors->list[i];
    if (m->removed) return;
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
            /* SetPlayerDie's sound block, once: c + 0x3324 = 0.001 after it (NATIVE-ITEMS-001) */
            mu_monster_voice v = monster_voice(c, i);
            int32_t r[1] = {0}, act, snd;
            mu_monster_die(&v, r, 0, &act, &snd);
            if (snd >= 0) {
                play(c, mu_combat_voice_sound(MU_COMBAT_AUDIO_DIE, 1, snd), a->session_key);
                ++c->stats.monster_voices;
            }
            if (m->voice_3324 == 0.0f && v.has_model)
                m->voice_3324 = 0.001f;
        }
        return;
    }
    if (m->attack_time) mu_attack_time_step(&m->attack_time,MU_ATTACK_TIME_LIMIT);
    /* after the hit or attack animation the monster stands (demo: the
     * server's next action packet) */
    uint16_t now = mu_actor_action(&a->actor);
    if ((now == 5 || now == 3 || now == 4) && a->step_result == 0 && !m->attack_time)
        set_monster_action(c, i, 0);
}

/* Ordered session outputs are the only source of damage, death and remote attacks. */
void mu_combat_receive(mu_combat *c)
{
    if(!c->session)return;
    c->hero_key=mu_session_combat_hero_key(c->session);
    mu_place place=mu_session_place(c->session);
    if(c->place_sequence!=place.seq) {
        c->place_sequence=place.seq;c->hero_dead=0;c->hero_3324=0;
        int32_t action=mu_player_stop_action(c->walk->hero.class_byte);
        mu_walk_set_action(c->walk,action,mu_player_stop_speed(action));
    }
    mu_hero_stats hero;mu_session_hero(c->session,&hero);c->hero_hp=hero.hp;
    mu_characters_view view=mu_session_characters(c->session);
    for(int32_t k=0;c->actors && k<c->actors->count;++k) {
        int32_t slot=c->actors->list[k].session_slot;
        if(slot<0 || slot>=view.capacity)continue;
        if(c->actor_revisions[k]!=view.equipment_revision[slot]) {
            if(c->actor_revisions[k] && c->monsters[k].dead) ++c->stats.respawns;
            memset(&c->monsters[k],0,sizeof c->monsters[k]);c->monsters[k].alpha=1;
            c->monsters[k].saved_wander=-1;
            c->actor_revisions[k]=view.equipment_revision[slot];
        }
        c->monsters[k].hp=view.records[slot].hp;c->monsters[k].max_hp=view.records[slot].max_hp;
    }
    mu_combat_frame_event events[MU_COMBAT_HISTORY];uint32_t lost=0;
    size_t n=mu_session_combat_events(c->session,&c->receive_cursor,events,MU_COMBAT_HISTORY,&lost);c->receive_lost+=lost;
    for(size_t j=0;j<n;++j) {
        const mu_combat_frame_event *e=&events[j];int32_t i=-1;
        for(int32_t k=0;c->actors && k<c->actors->count;++k)
            if((uint16_t)c->actors->list[k].session_key==e->key) {i=k;break;}
        if(e->kind==4) {if(c->drop)c->drop(c->drop_context,e->drop);}
        else if(e->kind==1) {
            mu_combat_event hit={.actor=i,.damage=e->damage.amount,.type=e->damage.type,
                .flag8=e->damage.flags[3],.flag_a=e->damage.flags[4],.shock=e->damage.shock};
            if(e->key==c->hero_key) {
                show_damage(c,c->hero_key,c->walk->hero.position,hit.damage,hit.type,hit.flag8,hit.flag_a);
                if(hit.shock)hero_hit(c,hit.damage,hit.type);++c->stats.hero_hits;
            } else if(i>=0)monster_hit(c,&hit);
        } else if(e->kind==2) {
            if(e->key==c->hero_key) {c->hero_dead=1;c->hero_attack_time=0;mu_combat_stop(c);mu_walk_stop(c->walk);}
            else if(i>=0 && !c->monsters[i].dead) {
                c->monsters[i].dead=1;c->monsters[i].attack_time=0;++c->stats.kills;
                char text[96];snprintf(text,sizeof text,"step %d: %s dies (server frame)",c->step,c->actors->list[i].label);log_line(c,text);
                if(c->target==i)mu_combat_stop(c);
            }
        } else if(e->kind==3 && i>=0) {
            mu_combat_monster *m=&c->monsters[i];
            int32_t action=mu_monster_attack_action(m->counter,0);m->counter=(uint8_t)(m->counter+2);
            if(action>=0)set_monster_action(c,i,action);m->attack_time=1;++c->stats.monster_attacks;
            mu_monster_voice voice=monster_voice(c,i);
            if ((!c->map || c->map->world!=0x49) && voice.field_3324==0.0f && voice.has_model && voice.slots[2]!=-1) {
                c->audio_rng=c->audio_rng*214013u+2531011u;
                int32_t id=mu_combat_monster_attack(c->map?c->map->world:0,voice.field_3324,voice.has_model,voice.object_kind,voice.slots[2],voice.slots[3],
                                                   (int32_t)((c->audio_rng>>16)&0x7fffu));
                play(c,mu_combat_voice_sound(MU_COMBAT_AUDIO_ATTACK,1,id),c->actors->list[i].session_key);
            }
        }
    }
}

/* ---------------------------------------------------------------- step */

void mu_combat_step(mu_combat *c)
{
    ++c->step;
    mu_combat_receive(c);
    hero_dead_step(c);
    if (c->hero_attack_time && mu_attack_time_step(&c->hero_attack_time, MU_ATTACK_TIME_LIMIT)) {
        refresh_objects(c);
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
    move_pools(c);
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
    /* RenderJoints 0x01589b56(0) through the shared joint helpers (NATIVE-JOINT-001): ribbons in world
     * space, in the blend of their render type, with the colour in effect for each quad; GL clamps the
     * vertex colour (glColor3f) to 0..1 */
    mu_joint_quad jq[4096];
    const int32_t joint_quads = mu_joints_quads(c->joints, MU_SFX_JOINTS, 0, c->map ? c->map->time : 0.0f, jq, 4096);
    for (int32_t k = 0; k < joint_quads; ++k) {
        mu_combat_quad *q = next_quad(quads, max, &n);
        if (!q)
            return n;
        q->bitmap = bitmap_slot(c, jq[k].bitmap);
        q->depth_test = 1;
        switch (jq[k].render_type) {
        case 3: q->src = 0; q->dst = 0x0301; break;          /* (ZERO, ONE_MINUS_SRC_COLOR) */
        case 4: q->src = 0x0301; q->dst = 1; break;          /* (ONE_MINUS_SRC_COLOR, ONE) */
        case 2: q->src = 0x0302; q->dst = 0x0303; break;     /* 0x0184a990(1) */
        default: q->additive = 1; break;                     /* (ONE, ONE) */
        }
        for (int v = 0; v < 4; ++v) {
            memcpy(q->position[v], jq[k].position[v], sizeof q->position[v]);
            q->texcoord[v][0] = jq[k].uv[v][0];
            q->texcoord[v][1] = jq[k].uv[v][1];
            for (int ch = 0; ch < 3; ++ch) {
                const float col = jq[k].color[ch];
                q->color[v][ch] = col < 0.0f ? 0.0f : (col > 1.0f ? 1.0f : col);
            }
            q->color[v][3] = 1.0f;
        }
    }
    /* RenderParticles 0x0159123f(0): RenderSprite billboards, additive for
     * 3-component bitmaps */
    for (int32_t i = 0; i < c->particle_count; ++i) {
        const mu_sfx_particle *p = &c->particles[i];
        if (!p->live)
            continue;
        int32_t slot = bitmap_slot(c, p->tex_type);
        if (slot < 0)
            continue;
        const mu_combat_bitmap *bm = &c->bitmaps[slot];
        mu_sfx_bitmap_info info = {(float)bm->image.width, (float)bm->image.height, bm->components};
        mu_sfx_sprite sprite;
        if (!mu_sfx_particle_render(p, &info, 0, &sprite))
            continue;
        mu_combat_quad *q = next_quad(quads, max, &n);
        if (!q)
            return n;
        float corners[4][3], uv[4][2];
        mu_sfx_sprite_corners(camera, &sprite, corners, uv);
        q->eye_space = 1;
        q->bitmap = slot;
        q->depth_test = 1;
        q->additive = sprite.additive;
        for (int v = 0; v < 4; ++v) {
            memcpy(q->position[v], corners[v], sizeof q->position[v]);
            q->texcoord[v][0] = uv[v][0];
            q->texcoord[v][1] = uv[v][1];
            for (int ch = 0; ch < 3; ++ch)
                q->color[v][ch] = sprite.light[ch] < 0.0f ? 0.0f : (sprite.light[ch] > 1.0f ? 1.0f : sprite.light[ch]);
            q->color[v][3] = 1.0f;
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

static int32_t model_slot(const mu_combat *c, int32_t type)
{
    for (int i = 0; i < MU_COMBAT_MODELS; ++i)
        if (c->models[i].type == type)
            return c->models[i].loaded ? i : -1;
    return -1;
}

int32_t mu_combat_draw_models(mu_combat *c, mu_combat_model_fn draw, void *context)
{
    int32_t drawn = 0;
    for (int i = 0; i < MU_SFX_EFFECTS; ++i) {
        mu_sfx_effect *e = &c->effects[i];
        if (!e->live)
            continue;
        int32_t slot = model_slot(c, e->type);
        float origin[3], angles[3];
        memcpy(origin, e->position, sizeof origin);
        memcpy(angles, e->angle, sizeof angles);
        float alpha = e->alpha;
        if (e->type == MU_SFX_TWISTING_SWIRL) {
            /* RenderEffects 0x015332ac (static): the caster's weapon, the
             * record's direction z less 30 per frame turning it, angle y 90,
             * 100 up, the effect's alpha */
            slot = c->models[MU_COMBAT_MODEL_WEAPON].loaded ? MU_COMBAT_MODEL_WEAPON : -1;
            e->direction[2] = e->direction[2] - 30.0f;
            e->angle[2] = e->angle[2] + e->direction[2];
            angles[0] = e->angle[0];
            angles[1] = 90.0f;
            angles[2] = e->angle[2];
            origin[2] = origin[2] + 100.0f;
        } else if (e->type >= 0x7a4 || slot < 0) {
            continue;   /* bitmap effects draw nothing themselves; missing models */
        }
        if (slot < 0)
            continue;
        mu_combat_model *m = &c->models[slot];
        mu_model_params p = m->model.params;
        for (int k = 0; k < 3; ++k) {
            p.origin[k] = origin[k];
            p.angles[k] = angles[k];
            p.color[k] = e->type == MU_SFX_TWISTING_SWIRL ? 1.0f : e->light[k];
        }
        p.body_scale = e->type == MU_SFX_TWISTING_SWIRL ? 1.0f : e->scale;
        mu_model_apply_params(&m->model, &p);
        int32_t keys = m->bmd.action_count > 0 ? m->bmd.actions[0].keys : 1;
        float frame = e->frame;
        if (keys > 0 && frame >= (float)keys)
            frame = 0.0f;
        mu_model_set_state(&m->model, 0, frame, frame, 0);
        if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
            continue;
        /* RenderObject 0x017edf43: RenderBody(flags, alpha, BlendMesh +0x74,
         * BlendMeshLight +0xa8, U +0xac, V +0xb0, hidden +0x68, -1) with flags 2,
         * or 0x82 when +0x80 == 0x80 (static reading) */
        mu_draw_options options;
        mu_draw_default_options(&options);
        options.flags = e->field_80 == 0x80 ? 0x82u : 2u;
        options.alpha = alpha;
        options.select = e->blend_mesh;
        options.color_scale = e->blend_light;
        options.u_offset = e->blend_u;
        options.v_offset = e->blend_v;
        options.textures = &m->textures;
        draw(context, &m->model, &m->textures, slot, &options);
        ++drawn;
    }
    return drawn;
}

void mu_combat_terrain_lights(const mu_combat *c, mu_world *map)
{
    if (!map)
        return;
    for (int32_t i = 0; i < c->light_count; ++i)
        mu_world_add_light(map, c->lights[i].x, c->lights[i].y, c->lights[i].rgb, c->lights[i].range);
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
    for (int i = 0; i < MU_SFX_EFFECTS; ++i)
        n += c->effects[i].live != 0;
    return n;
}

int32_t mu_combat_live_particles(const mu_combat *c)
{
    return c->particle_count;
}

int32_t mu_combat_live_joints(const mu_combat *c)
{
    int32_t n = mu_joints_live(c->joints, MU_SFX_JOINTS);
    return n;
}

/* NATIVE-PROGRESS-001: the level-up handler's calls at the hero's object (0x01250b05, verified as lines by
 * scripts/validate_progress.py): CreateJoint(type, o+0x158, o+0x158, o+0x164, subtype, o, scale, key) and
 * CreateEffect(type, o+0x158, o+0x164, light, subtype, o). */
void mu_combat_hero_joint(mu_combat *c, int32_t type, int32_t subtype, float scale, uint16_t key)
{
    float pos[3], angle[3], light[3];
    hero_frame(c, pos, angle, light);
    create_joint(c, type, pos, pos, angle, subtype, MU_COMBAT_HERO_OBJECT, scale, key, 0);
}

void mu_combat_hero_effect(mu_combat *c, int32_t type, int32_t subtype)
{
    float pos[3], angle[3], light[3];
    hero_frame(c, pos, angle, light);
    mu_sfx_info info;
    memset(&info, 0, sizeof info);
    info.key = 0xffff;   /* the call's PKKey -1 */
    create_effect(c, type, subtype, pos, angle, light, MU_COMBAT_HERO_OBJECT, &info);
}

/* ---------------------------------------------------------------- software drawing */

static void raster_model(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                         const mu_draw_options *draw_options)
{
    (void)slot;
    mu_raster *raster = context;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    mu_draw_options options = *draw_options;
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
    if (q->src || q->dst) {
        state.src = q->src;
        state.dst = q->dst;
    }
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
    mu_combat_quad quads[1024];
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

/* Item boundaries: ';' or ',' always end an item; whitespace ends one only
 * when the next word starts a new item ("FRAME:"), so labels with spaces
 * ("budge dragon") stay whole.  The header documents space-separated items;
 * before the fix only ';' separated them, so "2:skill:4:a 60:skill:9:b" was
 * one item whose actor "a 60:skill:9:b" resolved to nothing and the whole
 * script cast nothing (reported by NATIVE-LANG-001). */
static int script_item_start(const char *p)
{
    const char *q = p;
    while (*q >= '0' && *q <= '9')
        ++q;
    return q > p && *q == ':';
}

static size_t script_token_length(const char *p)
{
    size_t n = 0;
    while (p[n] && p[n] != ';' && p[n] != ',') {
        if ((p[n] == ' ' || p[n] == '\t') && n > 0) {
            size_t k = n;
            while (p[k] == ' ' || p[k] == '\t')
                ++k;
            if (!p[k] || script_item_start(p + k))
                break;
        }
        ++n;
    }
    return n;
}

int mu_combat_script_parse(mu_combat_script *script, const char *text)
{
    memset(script, 0, sizeof *script);
    const char *p = text;
    while (*p) {
        while (*p == ' ' || *p == '\t' || *p == ';' || *p == ',')
            ++p;
        if (!*p)
            break;
        if (script->count >= MU_COMBAT_SCRIPT)
            return 1;
        mu_combat_script_item *it = &script->items[script->count];
        char token[128];
        size_t n = script_token_length(p);
        if (n + 1 > sizeof token)
            return 1;
        memcpy(token, p, n);
        token[n] = 0;
        p += n;
        while (n > 0 && (token[n - 1] == ' ' || token[n - 1] == '\t'))
            token[--n] = 0;
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
            " \"attack_time\": %u, \"target\": %d, \"skill\": %d, \"points\": %d, \"fx\": %d, \"particles\": %d,"
            " \"joints\": %d, \"lights\": %d, \"hero_hp\": %d, \"hero_dead\": %u, \"sound\": %d, \"monsters\": [",
            frame, c->step, h->action, (double)h->angle[2], c->hero_attack_time, c->target, c->attack_skill,
            mu_combat_live_points(c), mu_combat_live_fx(c), mu_combat_live_particles(c), mu_combat_live_joints(c),
            c->light_count, c->hero_hp, c->hero_dead, c->last_sound);
    int first = 1;
    for (int32_t i = 0; c->actors && i < c->actors->count; ++i) {
        if (c->actors->list[i].actor.spec.monster_type < 0)
            continue;
        const mu_combat_monster *m = &c->monsters[i];
        const mu_world_actor *a = &c->actors->list[i];
        fprintf(out, "%s{\"actor\": %d, \"hp\": %u, \"action\": %u, \"dead\": %u, \"alpha\": %.4f,"
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
    fprintf(out, "], \"effect_types\": [");
    first = 1;
    for (int i = 0; i < MU_SFX_EFFECTS; ++i) {
        if (!c->effects[i].live) continue;
        fprintf(out, "%s%d", first ? "" : ", ", c->effects[i].type);
        first = 0;
    }
    fprintf(out, "]}\n");
}

static int loaded_bitmaps(const mu_combat *c)
{
    int n = 0;
    for (int32_t i = 0; i < c->bitmap_count; ++i)
        n += c->bitmaps[i].loaded != 0;
    return n;
}

static int loaded_models(const mu_combat *c)
{
    int n = 0;
    for (int i = 0; i < MU_COMBAT_MODELS; ++i)
        n += c->models[i].loaded != 0;
    return n;
}

void mu_combat_report_summary(const mu_combat *c, FILE *out, int quiet)
{
    const mu_combat_stats *s = &c->stats;
    fprintf(out, "{\"combat\": true, \"weapon\": %d, \"attack_speed\": %.1f, \"attacks\": %u, \"skills\": %u,"
            " \"arrows\": %u, \"fx_created\": %u, \"hits\": %u, \"misses\": %u, \"shocks\": %u, \"kills\": %u,"
            " \"deaths\": %u, \"removed\": %u, \"respawns\": %u, \"points_created\": %u,"
            " \"monster_attacks\": %u, \"hero_hits\": %u, \"picks\": %u, \"pick_hits\": %u,"
            " \"particles_created\": %u, \"joints_created\": %u, \"projectile_hits\": %u, \"area_requests\": %u,"
            " \"sprites\": %u, \"unsupported\": %u, \"hero_shocks\": %u, \"hero_deaths\": %u,"
            " \"monster_voices\": %u, \"requests_sent\": %u, \"requests_unsent\": %u,"
            " \"sounds\": %u, \"bitmaps_loaded\": %d, \"models_loaded\": %d, \"skill_table\": %d}\n",
            c->config.weapon, (double)c->config.attack_speed, s->attacks, s->skills, s->arrows, s->fx_created,
            s->hits, s->misses, s->shocks, s->kills, s->deaths, s->removed, s->respawns, s->points_created,
            s->monster_attacks, s->hero_hits, s->picks, s->pick_hits, s->particles_created, s->joints_created,
            s->projectile_hits, s->area_requests, s->sprites, s->unsupported, s->hero_shocks, s->hero_deaths,
            s->monster_voices, s->requests_sent, s->requests_unsent,
            c->sounds_played, loaded_bitmaps(c), loaded_models(c), (int)mu_lang_skill_count(c->lang));
    if (!quiet)
        for (int32_t i = 0; i < c->log_count; ++i)
            fprintf(out, "{\"combat_log\": \"%s\"}\n", c->log[i]);
}
