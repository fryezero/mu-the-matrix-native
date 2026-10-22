/* Helpers (pets and mounts) in the walk-around world (NATIVE-HELPERS-001). See mu_world_helpers.h. */
#include "mu_world_helpers.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_character.h"
#include "mu_objects.h"
#include "mu_particles.h"
#include "mu_renderchar.h"
#include "mu_walk.h"
#include "mu_world_players.h"
#include "../../reconstructed/environment/env.h"
#include "../../reconstructed/movement/client_movement.h"
#include "../../reconstructed/objects/object_render.h"
#include "../../reconstructed/particles/particles.h"

/* The Imp's attachment per owner (lazy). */
typedef struct imp_slot {
    int tried;
    mu_renderchar_attachment a;
    struct mu_character *host;
} imp_slot;

static imp_slot imps[MU_WH_OWNERS];

static void log_line(mu_world_helpers *w, const char *text)
{
    if (w->log_count < 32)
        snprintf(w->log[w->log_count++], sizeof w->log[0], "%s", text);
}

/* ---------------------------------------------------------------- models */

/* The model file of a helper model index: the Item.bmd records 13,0 / 13,1 (helper01.bmd, helper02.bmd, the item
 * model indices 0x24e6 / 0x24e7) and the mount classes' AccessModel(index, "Data\Skill\", name, -1). */
static int model_file(int32_t index, char *out, size_t size)
{
    if (index == MU_HP_MODEL_ANGEL)
        return snprintf(out, size, "Data/Item/helper01.bmd") > 0;
    if (index == MU_HP_MODEL_IMP)
        return snprintf(out, size, "Data/Item/helper02.bmd") > 0;
    static const struct { int32_t index; const char *name; } fenrir[] = {
        {0x4a8, "fenrir_black"}, {0x4a9, "fenrir_red"}, {0x4aa, "fenrir_blue"}, {0x4ab, "fenrir_gold"}};
    for (size_t i = 0; i < sizeof fenrir / sizeof fenrir[0]; ++i)
        if (fenrir[i].index == index)
            return snprintf(out, size, "Data/Skill/%s.bmd", fenrir[i].name) > 0;
    for (int32_t c = MU_HP_MOUNT_UNIRIA; c < MU_HP_MOUNT_CLASSES; ++c) {
        const mu_hp_mount_info *i = mu_hp_mount_class_info(c);
        if (i && i->model == index && i->file)
            return snprintf(out, size, "Data/Skill/%s.bmd", i->file) > 0;
    }
    return 0;
}

static mu_wh_model *model_of(mu_world_helpers *w, int32_t index)
{
    for (int32_t i = 0; i < w->model_count; ++i)
        if (w->models[i].index == index)
            return &w->models[i];
    if (w->model_count >= MU_WH_MODELS)
        return NULL;
    mu_wh_model *m = &w->models[w->model_count++];
    memset(m, 0, sizeof *m);
    m->index = index;
    m->tried = 1;
    char relative[256], message[512];
    if (w->no_assets || !model_file(index, relative, sizeof relative) ||
        !mu_objects_resolve(w->root, relative, m->path, sizeof m->path) ||
        mu_bmd_load_file(m->path, &m->bmd, message, sizeof message) != MU_BMD_OK)
        return m;
    mu_model_params p;
    mu_model_scene_params(&p);   /* light override 1 (NATIVE-LIGHT-001) */
    p.world = w->map ? w->map->world : 0;
    if (mu_model_init(&m->model, &m->bmd, &p, message, sizeof message) != MU_MODEL_OK) {
        mu_bmd_free(&m->bmd);
        return m;
    }
    char directory[2048];
    mu_path_directory(m->path, directory, sizeof directory);
    mu_textures_load(&m->textures, &m->bmd, directory);
    m->loaded = 1;
    char text[96];
    snprintf(text, sizeof text, "model %#x: %s", index, relative);
    log_line(w, text);
    return m;
}

static int32_t slot_of(const mu_world_helpers *w, const mu_wh_model *m)
{
    return (int32_t)(m - w->models);
}

/* ---------------------------------------------------------------- host of the reconstructed routines */

static float h_terrain(void *c, float x, float y)
{
    mu_world_helpers *w = c;
    return mu_request_terrain_height(w->map->height, w->map->attributes, w->map->water_height, 6, x, y);
}

static int h_has_model(void *c, int32_t index)
{
    mu_world_helpers *w = c;
    if (w->no_assets)
        return 1;   /* logic runs: the client's model getter answers for every loaded index */
    mu_wh_model *m = model_of(w, index);
    return m && m->loaded;
}

static void h_animate(void *c, mu_hp_object *o, int32_t index, float speed)
{
    mu_world_helpers *w = c;
    mu_wh_model *m = model_of(w, index);
    if (!m || !m->loaded || m->bmd.action_count <= 0)
        return;
    uint8_t loop = 0;
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    mu_model_tick(&m->model, speed, &loop);
    o->frame = mu_model_frame(&m->model);
    o->prior_frame = mu_model_prior_frame(&m->model);
    o->prior_action = mu_model_prior_action(&m->model);
}

static void h_set_action(void *c, mu_hp_object *o, int32_t action)
{
    mu_world_helpers *w = c;
    mu_wh_model *m = model_of(w, o->type);
    int32_t count = m && m->loaded ? m->bmd.action_count : 0;
    mu_move_set_action(&o->action, &o->prior_action, &o->frame, &o->prior_frame, count, action);
    w->stats.set_actions++;
}

static void h_owner_action(void *c, int32_t owner, int32_t action)
{
    mu_world_helpers *w = c;
    w->stats.rider_actions++;
    if (owner == 0 && w->walk) {
        const mu_character *hero = w->hero_character;
        float speed = hero ? mu_character_action_speed(hero, (uint16_t)action) : 0.25f;
        mu_walk_set_action(w->walk, action, speed);
    } else if (owner > 0 && w->players) {
        mu_world_players_set_action(w->players, owner - 1, action);
    }
}

static void h_particle(void *c, int32_t bitmap, const float p[3], const float a[3], const float l[3], int32_t sub,
                       float scale)
{
    mu_world_helpers *w = c;
    w->stats.particles++;
    if (w->particles)   /* CreateParticle 0x0168fafd (NATIVE-PARTICLE-001; kinds it does not port are dropped) */
        mu_world_particles_create(w->particles, bitmap, p, a, l, sub, scale);
}

static void h_effect(void *c, int32_t type, const float p[3], const float a[3], const float l[3], int32_t sub,
                     int32_t owner)
{
    mu_world_helpers *w = c;
    w->stats.effects++;
    if (w->particles)   /* CreateEffect 0x013c0eaa: the effect pool of NATIVE-COMBAT-002 (unported types dropped) */
        mu_world_particles_effect(w->particles, type, sub, p, a, l, owner, 1.0f, NULL);
}

static void h_joint(void *c, int32_t type, const float p[3], const float a[3], const mu_hp_object *o, float scale)
{
    mu_world_helpers *w = c;
    (void)o;
    w->stats.joints++;
    if (w->particles)   /* CreateJoint 0x0153b02c(type, p, p, angle, 0, object, 40, 2, 0, 0, -1, 0, -1, 0) */
        mu_world_particles_joint(w->particles, type, p, p, a, 0, -1, scale, 2, 0, 0, 0xffff, 0);
}

/* The bone matrix lookup 0x0129f18a(object, name, 1) and TransformPosition 0x012b6ef1(.., 0): the bone of the
 * model's last pose (the mount's draw), without the body scale and origin. */
static int h_bone(void *c, const mu_hp_object *o, int32_t index, const char *name, const float v[3], float out[3])
{
    mu_world_helpers *w = c;
    (void)o;
    mu_wh_model *m = model_of(w, index);
    if (!m || !m->loaded || m->bmd.bone_count <= 0)
        return 0;
    const char *names[MU_MODEL_MAX_BONES];
    int32_t n = m->bmd.bone_count < MU_MODEL_MAX_BONES ? m->bmd.bone_count : MU_MODEL_MAX_BONES;
    for (int32_t i = 0; i < n; ++i)
        names[i] = m->bmd.bones[i].name;
    int32_t bone = mu_pt_find_bone(names, n, name);
    const float *bones = mu_model_bone_matrices(&m->model);
    if (bone < 0 || !bones)
        return 0;
    mu_pt_transform_position(bones + 12 * bone, v, out, 0, 1.0f, NULL);
    return 1;
}

/* 0x012b6a2b (the Dark Horse dust): taken as TransformPosition with the world translation (static reading). */
static void h_bone_vector(void *c, const mu_hp_object *o, int32_t index, const char *name, const float v[3],
                          float out[3])
{
    mu_world_helpers *w = c;
    (void)o;
    mu_wh_model *m = model_of(w, index);
    if (m && m->loaded)
        mu_world_particles_named_bone_position(&m->model, &m->bmd, name, v, out);
}

static void h_kill(void *c, mu_hp_object *o)
{
    mu_world_helpers *w = c;
    (void)o;
    w->stats.bugs_deleted++;
}

/* ---------------------------------------------------------------- open / close */

int32_t mu_world_helpers_parse(const char *text, int32_t *state)
{
    static const struct { const char *name; int32_t item, state; } names[] = {
        {"none", -1, 0}, {"angel", MU_HP_ITEM_ANGEL, 0}, {"guardian-angel", MU_HP_ITEM_ANGEL, 0},
        {"imp", MU_HP_ITEM_IMP, 0}, {"uniria", MU_HP_ITEM_UNIRIA, 0}, {"dinorant", MU_HP_ITEM_DINORANT, 0},
        {"darkhorse", MU_HP_ITEM_DARK_HORSE, 0}, {"dark-horse", MU_HP_ITEM_DARK_HORSE, 0},
        {"fenrir", MU_HP_ITEM_FENRIR, 0}, {"fenrir-red", MU_HP_ITEM_FENRIR, 0}, {"fenrir-black", MU_HP_ITEM_FENRIR, 1},
        {"fenrir-blue", MU_HP_ITEM_FENRIR, 2}, {"fenrir-gold", MU_HP_ITEM_FENRIR, 4},
        {"ghost-horse", 0x19d7, 0}, {"ice-dragon", 0x19e3, 0}, {"pierce-lion", 0x184b, 0}, {"shining-tail", 0x1853, 0},
        {"ur", 0x185d, 0}, {"leviathan", 0x1833, 0}, {"tauros", 0x1835, 0}, {"divine-horse", 0x28f7, 0}};
    if (state)
        *state = 0;
    for (size_t i = 0; i < sizeof names / sizeof names[0]; ++i)
        if (!strcmp(text, names[i].name)) {
            if (state)
                *state = names[i].state;
            return names[i].item;
        }
    int g, ix;
    if (sscanf(text, "%d:%d", &g, &ix) == 2 && g >= 0 && g < 16 && ix >= 0 && ix < 512)
        return g * 512 + ix;
    char *end = NULL;
    long v = strtol(text, &end, 0);
    if (end && end != text && *end == 0 && v >= 0 && v < 0x4000)
        return (int32_t)v;
    return -2;
}

int mu_world_helpers_open(mu_world_helpers *w, const char *game_root, const mu_world *map, struct mu_walk *walk,
                          struct mu_world_players *players, int32_t hero_item, int32_t hero_state, uint32_t seed,
                          int no_assets, char *error, size_t error_size)
{
    memset(w, 0, sizeof *w);
    memset(imps, 0, sizeof imps);
    snprintf(w->root, sizeof w->root, "%s", game_root ? game_root : "");
    w->map = map;
    w->walk = walk;
    w->players = players;
    w->no_assets = no_assets;
    if (!map) {
        snprintf(error, error_size, "helpers: no world");
        return 1;
    }
    mu_hp_host host;
    memset(&host, 0, sizeof host);
    host.context = w;
    host.terrain_height = h_terrain;
    host.has_model = h_has_model;
    host.animate = h_animate;
    host.set_action = h_set_action;
    host.set_owner_action = h_owner_action;
    host.particle = h_particle;
    host.effect = h_effect;
    host.joint = h_joint;
    host.bone_position = h_bone;
    host.bone_vector = h_bone_vector;
    host.kill = h_kill;
    mu_hp_init(&w->h, seed, w->owners, MU_WH_OWNERS, &host);
    for (int32_t i = 0; i < MU_WH_OWNERS; ++i) {
        w->who[i].helper_item = -1;
        w->who[i].helper_slot = -1;
        w->who[i].ride = 0xffff;
        w->who[i].key = i == 0 ? 0x7fff : -1;
    }
    w->who[0].helper_item = hero_item;
    w->who[0].ride_state = (uint8_t)(hero_state < 0 ? 0 : hero_state);
    w->inputs.world = map->world;
    w->inputs.scene = 6;
    if (hero_item >= 0) {
        int32_t route = mu_hp_helper_route(hero_item, 0);
        if (route == MU_HP_HELPER_NONE || route == MU_HP_HELPER_PET) {
            snprintf(error, error_size, "helpers: item %#x is not a helper this module draws (%s)", hero_item,
                     route == MU_HP_HELPER_PET ? "a data-driven pet, not reconstructed" : "unknown");
            return 1;
        }
    }
    return 0;
}

void mu_world_helpers_close(mu_world_helpers *w)
{
    for (int32_t i = 0; i < w->model_count; ++i)
        if (w->models[i].loaded) {
            mu_model_free(&w->models[i].model);
            mu_bmd_free(&w->models[i].bmd);
            mu_textures_free(&w->models[i].textures);
        }
    for (int32_t i = 0; i < MU_WH_OWNERS; ++i)
        mu_renderchar_attach_free(&imps[i].a);
    memset(imps, 0, sizeof imps);
    memset(w, 0, sizeof *w);
}

void mu_world_helpers_attach_particles(mu_world_helpers *w, struct mu_world_particles *particles)
{
    w->particles = particles;
}

void mu_world_helpers_attach_hero(mu_world_helpers *w, struct mu_character *hero)
{
    w->hero_character = hero;
}

/* ---------------------------------------------------------------- owners and equipment */

static void sync_owners(mu_world_helpers *w)
{
    mu_hp_owner *o = &w->owners[0];
    if (w->walk) {
        const mu_hero *h = &w->walk->hero;
        o->live = 1;
        o->fade = 0;
        o->kind = 1;
        o->action = h->action;
        o->type = MU_HP_MODEL_PLAYER;
        memcpy(o->position, h->position, sizeof o->position);
        memcpy(o->angle, h->angle, sizeof o->angle);
        o->class_byte = h->class_byte;
        o->safe_zone = h->safe_zone;
        o->hidden = 0;
        o->weapon[0] = o->weapon[1] = -1;   /* DEMO hero: no weapon slots */
        w->who[0].active = 1;
        w->who[0].key = 0x7fff;
    }
    for (int32_t i = 0; w->players && i < w->players->count && i + 1 < MU_WH_OWNERS; ++i) {
        const mu_world_player *q = &w->players->list[i];
        mu_hp_owner *p = &w->owners[1 + i];
        p->live = (uint8_t)(q->in_view && q->c.live);
        p->fade = (uint8_t)(q->c.dead ? 1 : 0);
        p->kind = 1;
        p->action = q->c.action;
        p->type = q->c.model;
        memcpy(p->position, q->c.position, sizeof p->position);
        memcpy(p->angle, q->c.angle, sizeof p->angle);
        p->class_byte = q->c.class_byte;
        p->safe_zone = q->safe_zone;
        p->hidden = 0;
        p->weapon[0] = q->c.slots[MU_RP_SLOT_WEAPON0].type;
        p->weapon[1] = q->c.slots[MU_RP_SLOT_WEAPON1].type;
        w->who[1 + i].key = q->key;
    }
}

static void delete_owner_helpers(mu_world_helpers *w, int32_t owner)
{
    mu_wh_owner *s = &w->who[owner];
    mu_hp_delete_bug(&w->h, owner);   /* DeleteCharacter 0x0137c457 releases the helpers (static reading) */
    if (mu_hp_mount_find(&w->mounts, s->key)) {
        mu_hp_mount_reset(&w->h, &w->mounts, s->key, owner);
        w->stats.mounts_reset++;
    }
    s->helper_slot = -1;
    s->ride = 0xffff;
}

static void create_angel(mu_world_helpers *w, int32_t owner)
{
    if (mu_hp_create_bug(&w->h, &w->inputs, MU_HP_MODEL_ANGEL, w->owners[owner].position, owner, 0) >= 0) {
        w->stats.bugs_created++;
        char text[96];
        snprintf(text, sizeof text, "angel: CreateBug for owner %d", owner);
        log_line(w, text);
    }
}

static void set_mount(mu_world_helpers *w, int32_t owner, int32_t item, int32_t state)
{
    mu_wh_owner *s = &w->who[owner];
    mu_hp_mount *m = mu_hp_mount_set(&w->h, &w->mounts, &w->inputs, s->key, owner, item, state, 0,
                                     0 /* 0x00e136f3: the shadow argument's worlds, not traced */);
    if (m) {
        w->stats.mounts_set++;
        char text[96];
        snprintf(text, sizeof text, "mount: owner %d item %#x state %d -> class %d model %#x", owner, item, state,
                 m->cls, m->model);
        log_line(w, text);
    }
}

/* The hero (DEMO): the helper item becomes the slot / ride word the client's equipment code would write. */
static void apply_hero(mu_world_helpers *w)
{
    mu_wh_owner *s = &w->who[0];
    if (s->applied || !w->walk)
        return;
    s->applied = 1;
    int32_t item = s->helper_item;
    if (item < 0)
        return;
    switch (mu_hp_helper_route(item, 0)) {
    case MU_HP_HELPER_BUG:   /* ChangeCharacterExt's v == 0: slot 0x24e6 and the effect 0x24e6 (verified) */
        s->helper_slot = MU_HP_MODEL_ANGEL;
        create_angel(w, 0);
        break;
    case MU_HP_HELPER_LINK:
        s->helper_slot = MU_HP_MODEL_IMP;
        break;
    case MU_HP_HELPER_MOUNT:
        s->ride = (uint16_t)item;
        w->walk->helper_type = (uint16_t)item;   /* CharacterMoveSpeed's ride word */
        set_mount(w, 0, item, s->ride_state);
        break;
    default:
        break;
    }
}

/* A player's viewport record ran ChangeCharacterExt: its recorded engine calls, in order. */
static void apply_player(mu_world_helpers *w, int32_t i)
{
    mu_world_player *q = &w->players->list[i];
    int32_t owner = 1 + i;
    mu_wh_owner *s = &w->who[owner];
    if (!q->in_view) {
        if (s->active)
            delete_owner_helpers(w, owner);
        s->active = 0;
        return;
    }
    s->active = 1;
    if (s->equip_events == q->equip_events)
        return;
    s->equip_events = q->equip_events;
    s->helper_slot = q->c.slots[MU_RP_SLOT_HELPER].type;
    s->ride = q->c.helper;
    s->ride_state = q->c.ride_state;
    for (int32_t k = 0; k < q->equip_calls.count; ++k) {
        const mu_rp_call *c = &q->equip_calls.list[k];
        switch (c->kind) {
        case MU_RP_CALL_C9EA70:   /* DeleteBug 0x00c9ea70(o) */
            mu_hp_delete_bug(&w->h, owner);
            break;
        case MU_RP_CALL_EFFECT_24E6:
        case MU_RP_CALL_EFFECT_24E6_A14:   /* CreateBug 0x00c9d8df(0x24e6, position, o, ...) */
            create_angel(w, owner);
            break;
        case MU_RP_CALL_MOUNT_RESET:
            if (mu_hp_mount_find(&w->mounts, s->key)) {
                mu_hp_mount_reset(&w->h, &w->mounts, s->key, owner);
                w->stats.mounts_reset++;
            }
            break;
        case MU_RP_CALL_MOUNT_SET:
            if (c->a >= 0)
                set_mount(w, owner, c->a, c->b);
            break;
        default:   /* the data-driven pet process 0x00b990b0 (HELPER_MODEL / HELPER_EFFECT_OFF): not reconstructed */
            break;
        }
    }
}

/* ---------------------------------------------------------------- step */

static mu_hp_mount *mount_of_owner(mu_world_helpers *w, int32_t owner)
{
    return w->who[owner].key < 0 ? NULL : mu_hp_mount_find(&w->mounts, w->who[owner].key);
}

void mu_world_helpers_step(mu_world_helpers *w)
{
    w->inputs.world = w->map->world;
    sync_owners(w);
    apply_hero(w);
    for (int32_t i = 0; w->players && i < w->players->count && i + 1 < MU_WH_OWNERS; ++i)
        apply_player(w, i);
    mu_hp_move_bugs(&w->h, &w->inputs);
    mu_hp_mounts_move(&w->h, &w->mounts, &w->inputs);
    /* the riders: the manager's predicates and the lift the next placement adds */
    for (int32_t owner = 0; owner < MU_WH_OWNERS; ++owner) {
        mu_hp_mount *m = mount_of_owner(w, owner);
        uint8_t riding = (uint8_t)(m && !w->owners[owner].hidden && m->riding);   /* 0x0106bdb7 */
        uint8_t keeps = (uint8_t)(m != NULL);                                     /* 0x0106bd76 */
        float offset[3] = {0.0f, 0.0f, 0.0f};
        if (m && mu_hp_mount_lifts(&w->h, m))   /* 0x0103da5c(1): owner = mount position + offset */
            for (int k = 0; k < 3; ++k)
                offset[k] = m->object.position[k] + m->offset[k] - w->owners[owner].position[k];
        if (owner == 0 && w->walk) {
            w->walk->riding = riding;
            w->walk->keeps_run = keeps;
            memcpy(w->walk->place_offset, offset, sizeof offset);
        } else if (owner > 0 && w->players && owner - 1 < w->players->count) {
            mu_world_player *q = &w->players->list[owner - 1];
            q->riding = riding;
            q->keeps_run = keeps;
            memcpy(q->place_offset, offset, sizeof offset);
        }
        if (w->who[owner].helper_slot == MU_HP_MODEL_IMP)
            w->who[owner].imp_frame += 0.5f;   /* the slot's part speed +0x14 (static reading) */
    }
    w->stats.live_bugs = 0;
    for (int32_t i = 0; i < MU_HP_BUGS; ++i)
        w->stats.live_bugs += w->h.bugs[i].live;
    w->stats.live_mounts = (uint32_t)w->mounts.count;
    w->stats.steps++;
}

int mu_world_helpers_ride(mu_world_helpers *w, int32_t owner, int32_t how)
{
    if (owner < 0 || owner >= MU_WH_OWNERS || !mount_of_owner(w, owner))
        return 0;
    return mu_hp_rider_action(&w->h, owner, how) != 0;
}

/* ---------------------------------------------------------------- draw */

typedef struct draw_context {
    mu_world_helpers *w;
    const mu_world_helpers_target *target;
    const mu_terrain_frustum *frustum;
    long drawn;
    float color[4];
} draw_context;

static int r_frustum(void *c, float x, float y, float range)
{
    draw_context *d = c;
    if (!d->frustum)
        return 1;
    return mu_terrain_test_frustum_2d(d->frustum->x2d, d->frustum->y2d, 6, x, y, range);
}

/* RenderObject's setup 0x017ec896 and body for a helper object: the body light 0x017ec3d8 (lighting = +5, colour =
 * the frame light + the object light with ObjectInit's +6 = +7 = 1), scale +0xa0, Animation(!a1) / Transform(a1). */
static int pose_and_draw(draw_context *d, const mu_hp_object *o, int32_t a1)
{
    mu_world_helpers *w = d->w;
    mu_wh_model *m = model_of(w, o->type);
    if (!m || !m->loaded || o->alpha <= 0.01f)
        return 0;
    mu_model_params p = m->model.params;
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = o->position[k];
        p.angles[k] = o->angle[k];
    }
    float frame_light[3] = {0.0f, 0.0f, 0.0f};
    if (w->map)
        mu_obj_terrain_light(w->map->light, 6, 1, o->position[0], o->position[1], frame_light);
    mu_env_object e;
    memset(&e, 0, sizeof e);
    e.flag_05 = o->lighting;
    memcpy(e.light, o->light, sizeof e.light);
    mu_env_body_light(&e, frame_light, p.color, &p.lighting);
    p.light_ambient = MU_ENV_LIGHT_AMBIENT;
    p.light_scale = MU_ENV_LIGHT_SCALE;
    p.light_minimum = MU_ENV_LIGHT_MINIMUM;
    p.body_scale = o->scale;
    p.pose_translate = a1 ? 0 : 1;
    p.transform_translate = a1 ? 1 : 0;
    mu_model_apply_params(&m->model, &p);
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
        return 0;
    if (!d->target)
        return 1;
    mu_render_backend backend;
    if (d->target->backend(d->target->context, w, slot_of(w, m), &backend))
        return 0;
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = &m->textures;
    options.alpha = o->alpha < 1.0f ? o->alpha : 1.0f;
    /* RenderBody(flags, alpha, BlendMesh +0x74, BlendMeshLight +0xa8, +0xac, +0xb0, -1, -1) (NATIVE-RENDERCHAR-001) */
    options.select = o->blend_mesh;
    options.color_scale = o->blend_light;
    mu_draw_stats ds = {0, 0, 0, 0};
    if (mu_scene_draw_model(&m->model, &options, &backend, &ds))
        return 0;
    d->drawn++;
    return 1;
}

static void r_object(void *c, const mu_hp_object *o, int32_t a1, int32_t a2, int32_t a3, int32_t a4, int32_t a5)
{
    draw_context *d = c;
    (void)a2, (void)a3, (void)a4, (void)a5;
    if (pose_and_draw(d, o, a1))
        d->w->stats.drawn_bugs++;
}

static int r_body(void *c, const mu_hp_object *o, int32_t a1, int32_t a2, int32_t a3)
{
    draw_context *d = c;
    (void)a2, (void)a3;
    int drawn = pose_and_draw(d, o, a1);
    if (drawn)
        d->w->stats.drawn_mounts++;
    return drawn;
}

static void r_after(void *c, const mu_hp_object *o, int32_t a1, int32_t a2, int32_t a3, int32_t a4, int32_t a5)
{
    (void)c, (void)o, (void)a1, (void)a2, (void)a3, (void)a4, (void)a5;   /* 0x017edf43: visuals not ported */
}

static void r_sprite(void *c, int32_t bitmap, const float p[3], float scale, const float l[3], const mu_hp_object *o)
{
    draw_context *d = c;
    (void)o;
    d->w->stats.sprites++;
    if (d->w->particles)   /* CreateSprite 0x01692eb7(bitmap, position, scale, light, owner, 0, 0, 4) */
        mu_world_particles_sprite(d->w->particles, bitmap, p, scale, l, -1, 0.0f, 0, 4);
}

static void r_alpha(void *c, int32_t arg)
{
    (void)c, (void)arg;
}

static void r_color4(void *c, float r, float g, float b, float a)
{
    draw_context *d = c;
    d->color[0] = r;
    d->color[1] = g;
    d->color[2] = b;
    d->color[3] = a;
}

static void r_shadow(void *c, const mu_hp_object *o, int32_t index, int32_t arg, int32_t routine)
{
    draw_context *d = c;
    (void)o, (void)arg, (void)routine;
    mu_wh_model *m = model_of(d->w, index);
    if (!m || !m->loaded || !d->target || !d->target->shadow)
        return;
    d->w->stats.shadows++;
    d->target->shadow(d->target->context, d->w, slot_of(d->w, m), d->color);
}

/* The Imp on its owner (BackCarry's helper block, static reading): RenderLinkItem's hand path on bone 0x22 with the
 * block's vector, then the flare sprite at the bone. */
static void draw_imp(draw_context *d, int32_t owner, struct mu_character *host)
{
    mu_world_helpers *w = d->w;
    mu_wh_owner *s = &w->who[owner];
    mu_hp_imp_link plan;
    if (!host || !host->player_loaded ||
        !mu_hp_imp_link_plan(s->helper_slot, 6, 0, w->owners[owner].class_byte, w->owners[owner].weapon[0], &plan))
        return;
    imp_slot *slot = &imps[owner];
    if (slot->host != host) {
        mu_renderchar_attach_free(&slot->a);
        slot->tried = 0;
        slot->host = host;
    }
    if (!slot->tried) {
        slot->tried = 1;
        char path[1024], message[512];
        mu_renderchar_host shared = {host->shared_bones, host->shared_root, host->shared_quaternions};
        if (!w->no_assets && mu_objects_resolve(w->root, "Data/Item/helper02.bmd", path, sizeof path))
            mu_renderchar_attach_load(&slot->a, &shared, path, plan.bone, 0, message, sizeof message);
    }
    if (!slot->a.loaded)
        return;
    /* the Player bones again (the items after it re-posed the shared buffer) */
    if (mu_model_pose(&host->player) != MU_MODEL_OK)
        return;
    float out[3];
    if (mu_model_rotation_position(&host->player, plan.bone, plan.vector, out) != MU_MODEL_OK)
        return;
    mu_model_params p = slot->a.model.params;
    p.body_scale = host->params.scale;
    for (int k = 0; k < 3; ++k) {
        volatile float sum = host->params.position[k] + out[k];
        p.origin[k] = sum;
        p.color[k] = host->params.light[k];
        p.angles[k] = 0.0f;
    }
    p.pose_translate = 1;
    p.transform_translate = 1;
    p.vertex_scale = 0.0f;
    p.light_ambient = 0.4f;
    p.light_scale = 0.8f;
    p.light_minimum = 0.2f;
    p.lighting = 0;
    mu_model_apply_params(&slot->a.model, &p);
    int32_t keys = slot->a.bmd.action_count > 0 ? slot->a.bmd.actions[0].keys : 1;
    float frame = keys > 1 ? fmodf(s->imp_frame, (float)keys) : 0.0f;
    mu_model_set_state(&slot->a.model, 0, frame, frame, 0);
    if (mu_model_pose_keep_root(&slot->a.model) != MU_MODEL_OK || mu_model_transform_all(&slot->a.model) != MU_MODEL_OK)
        return;
    w->stats.drawn_imps++;
    if (d->target) {
        mu_render_backend backend;
        mu_wh_model *m = model_of(w, MU_HP_MODEL_IMP);   /* its texture slot (the same file) */
        if (m && m->loaded && !d->target->backend(d->target->context, w, slot_of(w, m), &backend)) {
            mu_draw_options options;
            mu_draw_default_options(&options);
            options.textures = &m->textures;
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&slot->a.model, &options, &backend, &ds))
                d->drawn++;
        }
    }
    /* the flare: TransformPosition(bone 0x22, sprite vector, world) and light (0.5 k, 0, 0) */
    float k = (float)(mu_hp_rand(&w->h) % 0x1e + 0x46) * 0.01f;
    float light[3] = {k * 0.5f, k * 0.0f, k * 0.0f};
    float pos[3];
    if (mu_world_particles_bone_position(&host->player, plan.bone, plan.sprite_vector, pos) && w->particles) {
        mu_world_particles_sprite(w->particles, MU_HP_BITMAP_FLARE, pos, 1.5f, light, -1, 0.0f, 0, 4);
        w->stats.sprites++;
    }
}

long mu_world_helpers_draw(mu_world_helpers *w, const mu_terrain_frustum *frustum, struct mu_character *hero,
                           const mu_world_helpers_target *target)
{
    draw_context d;
    memset(&d, 0, sizeof d);
    d.w = w;
    d.target = target;
    d.frustum = frustum;
    mu_hp_render_host r;
    memset(&r, 0, sizeof r);
    r.context = &d;
    r.frustum = r_frustum;
    r.draw_object = r_object;
    r.draw_body = r_body;
    r.draw_after = r_after;
    r.sprite = r_sprite;
    r.alpha_test = r_alpha;
    r.color4 = r_color4;
    r.shadow = r_shadow;
    w->stats.drawn_bugs = w->stats.drawn_mounts = w->stats.drawn_imps = w->stats.shadows = 0;
    /* the render scene's order: RenderBugs 0x00c9e4e3, the mount render loop 0x0106bc2b */
    mu_hp_render_bugs(&w->h, &w->inputs, &r);
    mu_hp_mounts_render(&w->h, &w->mounts, &w->inputs, &r);
    /* the Imps are part of their owners' RenderCharacter */
    if (hero)
        draw_imp(&d, 0, hero);
    for (int32_t i = 0; w->players && i < w->players->count && i + 1 < MU_WH_OWNERS; ++i)
        if (w->players->list[i].in_view && mu_world_players_alpha(w->players, i) > 0.0f)
            draw_imp(&d, 1 + i, &w->players->list[i].model);
    return d.drawn;
}

typedef struct raster_target {
    mu_raster *raster;
    mu_render_backend backend;
} raster_target;

static int raster_backend(void *c, const mu_world_helpers *w, int32_t slot, mu_render_backend *out)
{
    raster_target *t = c;
    const mu_textures *tex = &w->models[slot].textures;
    t->raster->textures = tex->slots;
    t->raster->texture_count = tex->count;
    t->raster->texture_filter = tex->filter;
    t->raster->texture_wrap = tex->wrap;
    *out = t->backend;
    return 0;
}

long mu_world_helpers_draw_raster(mu_world_helpers *w, mu_raster *raster, const mu_terrain_frustum *frustum,
                                  struct mu_character *hero)
{
    raster_target t = {raster, {0}};
    mu_raster_backend(raster, &t.backend);
    mu_world_helpers_target target = {&t, raster_backend, NULL};
    long n = mu_world_helpers_draw(w, frustum, hero, &target);
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    return n;
}

/* ---------------------------------------------------------------- reports */

void mu_world_helpers_report_frame(const mu_world_helpers *w, FILE *out, int32_t frame)
{
    fprintf(out, "{\"helpers_frame\": %d, \"bugs\": %u, \"mounts\": %u, \"drawn_bugs\": %u, \"drawn_mounts\": %u,"
                 " \"drawn_imps\": %u, \"riding\": %d",
            frame, w->stats.live_bugs, w->stats.live_mounts, w->stats.drawn_bugs, w->stats.drawn_mounts,
            w->stats.drawn_imps, w->walk ? w->walk->riding : 0);
    for (int32_t i = 0; i < MU_HP_BUGS; ++i) {
        const mu_hp_object *o = &w->h.bugs[i];
        if (o->live)
            fprintf(out, ", \"bug%d\": [%d, %d, %.2f, %.2f, %.2f]", i, o->type, o->owner, (double)o->position[0],
                    (double)o->position[1], (double)o->position[2]);
    }
    for (int32_t i = 0; i < w->mounts.count; ++i) {
        const mu_hp_mount *m = &w->mounts.list[i];
        fprintf(out, ", \"mount%d\": [%d, %d, %d, %d, %.2f, %.2f, %.2f]", i, m->cls, m->owner, m->action,
                w->owners[m->owner].action, (double)m->offset[0], (double)m->offset[1], (double)m->offset[2]);
    }
    fprintf(out, "}\n");
}

void mu_world_helpers_report_summary(const mu_world_helpers *w, FILE *out, int quiet)
{
    fprintf(out, "{\"helpers\": {\"steps\": %u, \"bugs_created\": %u, \"bugs_deleted\": %u, \"mounts_set\": %u,"
                 " \"mounts_reset\": %u, \"particles\": %u, \"sprites\": %u, \"effects\": %u, \"joints\": %u,"
                 " \"set_actions\": %u, \"rider_actions\": %u, \"live_bugs\": %u, \"live_mounts\": %u,"
                 " \"models\": %d}}\n",
            w->stats.steps, w->stats.bugs_created, w->stats.bugs_deleted, w->stats.mounts_set, w->stats.mounts_reset,
            w->stats.particles, w->stats.sprites, w->stats.effects, w->stats.joints, w->stats.set_actions,
            w->stats.rider_actions, w->stats.live_bugs, w->stats.live_mounts, w->model_count);
    if (!quiet)
        for (int32_t i = 0; i < w->log_count; ++i)
            fprintf(out, "helpers: %s\n", w->log[i]);
}
