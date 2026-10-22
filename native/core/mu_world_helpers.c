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
#include "mu_world_raven.h"
#include "mu_world_pets.h"
#include "../../reconstructed/actors/actors.h"
#include "../../reconstructed/environment/env.h"
#include "../../reconstructed/movement/client_movement.h"
#include "../../reconstructed/objects/object_render.h"
#include "../../reconstructed/particles/particles.h"
#include "../../reconstructed/helpers/mount_render.h"
#include "../../reconstructed/helpers/mount_class.h"

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
    if (index == MU_RV_MODEL_RAVEN)   /* NATIVE-HELPERS-002: AccessModel(0x411, "Data\Skill\", "DarkSpirit") */
        return snprintf(out, size, "Data/Skill/DarkSpirit.bmd") > 0;
    if (index == MU_RV_MODEL_SOUL)    /* AccessModel(0x748, "Data\Item\", "Dark_Soul") */
        return snprintf(out, size, "Data/Item/Dark_Soul.bmd") > 0;
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
    return mu_world_pets_model_file(index, out, size);   /* NATIVE-HELPERS-002 */
}

/* NATIVE-HELPERS-002: the client bitmaps the mounts' registry functors draw their glow passes with (LoadBitmap
 * indices and files, static readings of the loaders 0x01824500.., 0x0182e695.., 0x01838105.., 0x0182f49c..). */
static const struct { int32_t index; const char *directory, *name; } pass_bitmaps[] = {
    {0x82e3, "Data/Effect", "black_gold_crom02_mono.jpg"}, {0x82e4, "Data/Effect", "black_gold_crom04_mono.jpg"},
    {0x831a, "Data/Effect", "black_gold_crom02.jpg"},
    {0x83ea, "Data/Skill", "hs_fiercelion01B_render.jpg"}, {0x83eb, "Data/Skill", "hs_fiercelion01R_render.jpg"},
    {0x83ec, "Data/Skill", "hs_fiercelion02B_render.jpg"}, {0x83ed, "Data/Skill", "hs_fiercelion02R_render.jpg"},
    {0x8430, "Data/Skill", "shiningtails_render.jpg"}, {0x8431, "Data/Skill", "shiningtails_2_render.jpg"},
    {0x8432, "Data/Skill", "shiningtails_3_render.jpg"}, {0x8433, "Data/Skill", "shiningtails_4_render.jpg"},
    {0x8434, "Data/Skill", "rare_shiningtails_1_render.jpg"}, {0x8435, "Data/Skill", "rare_shiningtails_2_render.jpg"},
    {0x8436, "Data/Skill", "rare_shiningtails_3_render.jpg"}, {0x8437, "Data/Skill", "rare_shiningtails_4_render.jpg"},
    {0x848a, "Data/Item/texture", "ursh_overlay.jpg"}, {0x848b, "Data/Item/texture", "goms5cha_02_R.jpg"},
    {0x848c, "Data/Item/texture", "ursh_gold_overlay.jpg"}, {0x848d, "Data/Item/texture", "goms5cha_02s_Red.jpg"},
    {0x8239, "Data/Item/Texture", "black_gold_crom05.jpg"},
    {0x853d, "Data/Skill", "Leviathan_001_rare_R.jpg"}, {0x853e, "Data/Skill", "hs_TaurosG05.jpg"},
    {0x853f, "Data/Skill", "hs_TaurosGR05.jpg"}, {0x8540, "Data/Skill", "hs_TaurosG01_r.jpg"},
    {0x8541, "Data/Skill", "hs_TaurosG02_r.jpg"}, {0x8542, "Data/Skill", "hs_TaurosGR01_r.jpg"},
    {0x8543, "Data/Skill", "hs_TaurosGR02_r.jpg"}, {0x8544, "Data/Skill", "hs_TaurosGR04_r.jpg"},
    {0x8530, "Data/Effect", "Divinehorse_01_render.jpg"}, {0x8531, "Data/Effect", "ef_line01.jpg"},
    {0x84e8, "Data/Skill", "Giant_darkW_Neon_render.jpg"}, {0x84e9, "Data/Skill", "Giant_Elf_Neon_r.jpg"},
    {0x84ea, "Data/Skill", "Giant_GrowLancer_Neon_render.jpg"},
    {0x84eb, "Data/Skill", "Giant_GrowLancer_Jewel_render.jpg"},
    /* the Shining Tail's rune circles and glows (its class visuals' terrain decals) */
    {0x8438, "Data/Effect", "lightmarks_mzin.jpg"}, {0x7ef7, "Data/Effect", "flare01.jpg"}};

/* The bitmaps a mount model's functor names (mount_render.c). */
static int32_t model_pass_bitmaps(int32_t model, int32_t out[8])
{
    static const struct { int32_t model; int32_t list[8]; } uses[] = {
        {0x671, {0x82e3, 0x82e4}}, {0x69a, {0x82e4}}, {0x69b, {0x831a}},
        {0x6cb, {0x83ea, 0x83ec, 0x82e4}}, {0x6cc, {0x83eb, 0x83ed, 0x82e4}},
        {0x6f4, {0x8430, 0x8431, 0x8432, 0x8433, 0x82e3, 0x8438, 0x7ef7}},
        {0x6f5, {0x8434, 0x8435, 0x8436, 0x8437, 0x82e3}},
        {0x736, {0x848a, 0x848b, 0x8239}}, {0x737, {0x848c, 0x848d}}, {0x74a, {0x853d}},
        {0x77c, {0x853e, 0x8541, 0x8531, 0x8540, 0x82e3}}, {0x77d, {0x8544, 0x853f, 0x8543, 0x8531, 0x8542, 0x82e3}},
        {0x753, {0x8530, 0x8531}}, {0x73f, {0x84e8}}, {0x740, {0x84e9}}, {0x741, {0x84ea, 0x84eb}}};
    for (size_t i = 0; i < sizeof uses / sizeof uses[0]; ++i)
        if (uses[i].model == model) {
            int32_t n = 0;
            while (n < 8 && uses[i].list[n])
                out[n] = uses[i].list[n], ++n;
            return n;
        }
    return 0;
}

static void load_pass_bitmaps(mu_world_helpers *w, mu_wh_model *m)
{
    int32_t want[8];
    int32_t n = model_pass_bitmaps(m->index, want);
    int32_t index[8];
    const char *dirs[8], *names[8];
    char paths[8][1024];
    int32_t k = 0;
    for (int32_t i = 0; i < n; ++i)
        for (size_t j = 0; j < sizeof pass_bitmaps / sizeof pass_bitmaps[0]; ++j)
            if (pass_bitmaps[j].index == want[i]) {
                if (!mu_objects_resolve(w->root, pass_bitmaps[j].directory, paths[k], sizeof paths[k]))
                    snprintf(paths[k], sizeof paths[k], "%s/%s", w->root, pass_bitmaps[j].directory);
                index[k] = want[i];
                dirs[k] = paths[k];
                names[k] = pass_bitmaps[j].name;
                ++k;
            }
    /* the glow overlays scroll and repeat (GL_REPEAT); the decal bitmaps lie once on the terrain (GL_CLAMP) */
    for (int32_t i = 0; i < k; ++i) {
        const int clamp = index[i] == 0x8438 || index[i] == 0x7ef7;
        mu_textures_add_extras(&m->textures, &index[i], &dirs[i], &names[i], 1, 0x2601 /* GL_LINEAR */,
                               clamp ? 0x2900u /* GL_CLAMP */ : 0x2901u /* GL_REPEAT */);
    }
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
    if (m->textures.missing > 0) {   /* the later items keep their textures in Data/Item/Texture (NATIVE-HELPERS-002) */
        char sub[2100];
        mu_textures retry;
        snprintf(sub, sizeof sub, "%s/texture", directory);
        if (mu_textures_load(&retry, &m->bmd, sub) == 0 && retry.missing < m->textures.missing) {
            mu_textures_free(&m->textures);
            m->textures = retry;
        } else {
            mu_textures_free(&retry);
        }
    }
    load_pass_bitmaps(w, m);   /* NATIVE-HELPERS-002 */
    m->loaded = 1;
    char text[96];
    snprintf(text, sizeof text, "model %#x: %s (%d textures missing)", index, relative, m->textures.missing);
    log_line(w, text);
    return m;
}

mu_wh_model *mu_world_helpers_model(mu_world_helpers *w, int32_t index)
{
    return model_of(w, index);
}

static int32_t slot_of(const mu_world_helpers *w, const mu_wh_model *m)
{
    return (int32_t)(m - w->models);
}

mu_wh_model *mu_world_helpers_model(mu_world_helpers *w, int32_t index)
{
    return model_of(w, index);
}

int32_t mu_world_helpers_model_slot(const mu_world_helpers *w, const mu_wh_model *m)
{
    return slot_of(w, m);
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
        /* the Player loader's play speed of the action (NATIVE-ACTOR-001's table; 0.25 where it sets none) */
        float speed = mu_player_action_speed(action);
        mu_walk_set_action(w->walk, action, speed > 0.0f ? speed : 0.25f);
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

/* ---------------------------------------------------------------- the later classes (NATIVE-HELPERS-002) */

static mu_hp_class_state *class_state_of(mu_world_helpers *w, int32_t key)
{
    for (int32_t i = 0; i < w->class_state_count; ++i)
        if (w->class_keys[i] == key)
            return &w->class_states[i];
    if (w->class_state_count >= MU_HP_MOUNTS)
        return NULL;
    int32_t i = w->class_state_count++;
    w->class_keys[i] = key;
    memset(&w->class_states[i], 0, sizeof w->class_states[i]);   /* the model load writes +0xa4 = 0 */
    return &w->class_states[i];
}

typedef struct class_host_ctx {
    mu_world_helpers *w;
    mu_wh_model *m;
} class_host_ctx;

static void c_named_bone(void *c, const char *name, float out[3])
{
    class_host_ctx *x = c;
    const float zero[3] = {0.0f, 0.0f, 0.0f};
    out[0] = out[1] = out[2] = 0.0f;
    if (x->m && x->m->loaded)
        mu_world_particles_named_bone_position(&x->m->model, &x->m->bmd, name, zero, out);
}

static void c_object_bone(void *c, int32_t bone, float out[3])
{
    class_host_ctx *x = c;
    const float zero[3] = {0.0f, 0.0f, 0.0f};
    out[0] = out[1] = out[2] = 0.0f;
    if (x->m && x->m->loaded)
        mu_world_particles_bone_position(&x->m->model, bone, zero, out);
}

/* The calls the class code makes into the other pools. */
static void class_calls(mu_world_helpers *w, const mu_hp_after_call *calls, int32_t n, mu_wh_model *m)
{
    (void)m;
    for (int32_t i = 0; i < n; ++i) {
        const mu_hp_after_call *a = &calls[i];
        switch (a->kind) {
        case MU_HP_AC_SPRITE:
            w->stats.sprites++;
            if (w->particles)
                mu_world_particles_sprite(w->particles, a->type, a->position, a->scale, a->light, -1, 0.0f, 0, 4);
            break;
        case MU_HP_AC_PARTICLE:
            w->stats.particles++;
            if (w->particles)
                mu_world_particles_create(w->particles, a->type, a->position, a->angle, a->light, a->subtype, a->scale);
            break;
        case MU_HP_AC_EFFECT:
            w->stats.effects++;
            if (w->particles)
                mu_world_particles_effect(w->particles, a->type, a->subtype, a->position, a->angle, a->light, -1,
                                          a->scale, NULL);
            break;
        case MU_HP_AC_JOINT:
            w->stats.joints++;
            if (w->particles)
                mu_world_particles_joint(w->particles, a->type, a->position, a->position, a->angle, a->subtype, -1,
                                         a->scale, 0xffff, 0, 0, 0xffff, 0);
            break;
        default:
            break;
        }
    }
}

/* The mount move loop 0x0106bbb2 with the class's own step (vtable +0xc after the base move, before the
 * action map): mu_hp_mounts_move plus the reconstructed class steps. */
static void move_mounts(mu_world_helpers *w)
{
    for (int32_t i = 0; i < w->mounts.count; ++i) {
        mu_hp_mount *m = &w->mounts.list[i];
        if (!mu_hp_mount_move(&w->h, m, &w->inputs))
            continue;
        mu_hp_class_inputs in;
        memset(&in, 0, sizeof in);
        in.world_time = w->world_time;
        in.action = (uint16_t)m->action;   /* the mount's action +0x30 */
        in.frame = m->object.frame;
        in.alpha = m->object.alpha;
        memcpy(in.position, m->object.position, sizeof in.position);
        memcpy(in.angle, m->object.angle, sizeof in.angle);
        class_host_ctx x = {w, model_of(w, m->object.type)};
        mu_hp_class_host host = {&x, c_object_bone, c_named_bone};
        mu_hp_after_call calls[16];
        int32_t n = 0;
        if (mu_hp_mount_class_step(&w->h, m->cls, &in, &host, calls, 16, &n))
            class_calls(w, calls, n < 16 ? n : 16, x.m);
        mu_hp_mount_follow_action(&w->h, m);
    }
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
        {"ur", 0x185d, 0}, {"leviathan", 0x1833, 0}, {"tauros", 0x1835, 0}, {"divine-horse", 0x28f7, 0},
        {"dark-raven", MU_RV_ITEM_DARK_RAVEN, 1}, {"darkraven", MU_RV_ITEM_DARK_RAVEN, 1},
        {"dark-raven-20", MU_RV_ITEM_DARK_RAVEN, 2}, {"dark-raven-40", MU_RV_ITEM_DARK_RAVEN, 3}};
    if (state)
        *state = 0;
    for (size_t i = 0; i < sizeof names / sizeof names[0]; ++i)
        if (!strcmp(text, names[i].name)) {
            if (state)
                *state = names[i].state;
            return names[i].item;
        }
    int32_t pet = mu_world_pets_parse(text);   /* NATIVE-HELPERS-002 */
    if (pet != -2)
        return pet;
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
    if (hero_item == MU_RV_ITEM_DARK_RAVEN || players) {   /* NATIVE-HELPERS-002: the Dark Raven */
        w->raven = calloc(1, sizeof *w->raven);
        if (w->raven)
            mu_world_raven_init(w->raven, w, seed ^ 0x5a17u);
    }
    if (hero_item >= 0 && hero_item != MU_RV_ITEM_DARK_RAVEN) {
        int32_t route = mu_hp_helper_route(hero_item, 0);
        if (route == MU_HP_HELPER_NONE && !mu_world_pets_is_pet(hero_item)) {
            snprintf(error, error_size, "helpers: item %#x is not a helper this module draws (unknown)", hero_item);
            return 1;
        }
    }
    int hero_pet = hero_item >= 0 && (mu_hp_helper_route(hero_item, 0) == MU_HP_HELPER_PET ||
                                      mu_world_pets_is_pet(hero_item));
    if (hero_pet || players) {   /* NATIVE-HELPERS-002: the pet process */
        w->pets = mu_world_pets_new(w->root, hero_pet ? hero_item : -1, seed ^ 0x9e7, no_assets);
        if (hero_pet)
            w->who[0].helper_item = -1;
    }
    return 0;
}

void mu_world_helpers_close(mu_world_helpers *w)
{
    free(w->raven);
    w->raven = NULL;
    mu_world_pets_free(w->pets);
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
    if (w->pets)
        mu_world_pets_owner_gone(w->pets, owner);
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
        case MU_RP_CALL_HELPER_EFFECT_OFF:   /* DeletePet 0x00eb1015(c, the former slot type) (NATIVE-HELPERS-002) */
            if (w->pets)
                mu_world_pets_delete(w->pets, owner, c->a);
            break;
        case MU_RP_CALL_HELPER_MODEL:   /* CreatePet 0x00eb0e78(0x1a00 + w, the slot type, position, c, 0, 0) */
            if (w->pets)
                mu_world_pets_create(w->pets, w, owner, c->a, c->b);
            break;
        default:
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
    move_mounts(w);   /* mu_hp_mounts_move with the class steps (NATIVE-HELPERS-002) */
    if (w->pets)   /* UpdatePets 0x00eb0d64 (NATIVE-HELPERS-002) */
        mu_world_pets_step(w->pets, w);
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
    w->world_time = w->world_time + 40.0f;   /* NATIVE-HELPERS-002: the functors' glow pulse */
    if (w->raven)   /* NATIVE-HELPERS-002: MovePet per character (MoveCharacter's 0x00c930df) */
        mu_world_raven_step(w->raven);
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
    mu_wh_model *posed;   /* the mount the body pass posed (its after-pass draws it) */
} draw_context;

static int r_frustum(void *c, float x, float y, float range)
{
    draw_context *d = c;
    if (!d->frustum)
        return 1;
    return mu_terrain_test_frustum_2d(d->frustum->x2d, d->frustum->y2d, 6, x, y, range);
}

/* RenderObject's setup 0x017ec896 for a helper object: the body light 0x017ec3d8 (lighting = +5, colour = the
 * frame light + the object light with ObjectInit's +6 = +7 = 1), scale +0xa0, Animation(!a1) / Transform(a1).
 * Returns the model, NULL when nothing is drawn. */
static mu_wh_model *pose_object(draw_context *d, const mu_hp_object *o, int32_t a1)
{
    mu_world_helpers *w = d->w;
    mu_wh_model *m = model_of(w, o->type);
    if (!m || !m->loaded || o->alpha <= 0.01f)
        return NULL;
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
        return NULL;
    return m;
}

/* One RenderBodyDefault 0x00966def / RenderMeshDefault 0x00966e4a call on a posed model (mesh < 0: the body),
 * with the model colour +0x54 of the call. */
static int draw_pass(draw_context *d, mu_wh_model *m, int32_t mesh, uint32_t flags, float alpha, int32_t blend_mesh,
                     float blend_light, float u, float v, int32_t hidden, int32_t texture, const float color[3])
{
    if (!d->target)
        return 1;
    mu_render_backend backend;
    if (d->target->backend(d->target->context, d->w, slot_of(d->w, m), &backend))
        return 0;
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = &m->textures;
    options.flags = flags;
    options.alpha = alpha < 1.0f ? alpha : 1.0f;
    /* RenderBody(flags, alpha, BlendMesh +0x74, BlendMeshLight +0xa8, +0xac, +0xb0, hidden, texture)
     * (NATIVE-RENDERCHAR-001) */
    options.select = blend_mesh;
    options.color_scale = blend_light;
    options.u_offset = u;
    options.v_offset = v;
    options.skip_mesh = hidden;
    options.texture = texture;
    options.mesh_plus_one = mesh >= 0 ? mesh + 1 : 0;
    mu_draw_model_fields fields;
    memset(&fields, 0, sizeof fields);
    if (color) {
        memcpy(fields.color, color, sizeof fields.color);
        options.fields = &fields;
    }
    mu_draw_stats ds = {0, 0, 0, 0};
    if (mesh >= (int32_t)m->bmd.mesh_count)
        return 1;   /* the functors name meshes some models do not have (the Dark Horse's 0xd..0xf) */
    if (mu_scene_draw_model(&m->model, &options, &backend, &ds))
        return 0;
    d->drawn++;
    d->w->stats.passes++;
    return 1;
}

/* RenderObject 0x016d4fe4 for a bug (the angel): the setup, then the draw (its registry functor 0x00a6a730
 * answers 0: the default body). */
static int pose_and_draw(draw_context *d, const mu_hp_object *o, int32_t a1)
{
    mu_wh_model *m = pose_object(d, o, a1);
    if (!m)
        return 0;
    return draw_pass(d, m, -1, 2, o->alpha, o->blend_mesh, o->blend_light, 0.0f, 0.0f, -1, -1, NULL);
}

int mu_world_helpers_draw_object(mu_world_helpers *w, const mu_world_helpers_target *target, const mu_hp_object *o,
                                 int32_t a1)
{
    draw_context d;
    memset(&d, 0, sizeof d);
    d.w = w;
    d.target = target;
    return pose_and_draw(&d, o, a1);
}

static void r_object(void *c, const mu_hp_object *o, int32_t a1, int32_t a2, int32_t a3, int32_t a4, int32_t a5)
{
    draw_context *d = c;
    (void)a2, (void)a3, (void)a4, (void)a5;
    if (pose_and_draw(d, o, a1))
        d->w->stats.drawn_bugs++;
}

/* The mount's body (vtable +0x14 0x0103d6d5): RenderObject's setup 0x017ec896 only; the draw is the after-pass. */
static int r_body(void *c, const mu_hp_object *o, int32_t a1, int32_t a2, int32_t a3)
{
    draw_context *d = c;
    (void)a2, (void)a3;
    d->posed = pose_object(d, o, a1);
    if (d->posed)
        d->w->stats.drawn_mounts++;
    return d->posed != NULL;
}

static void after_bone(void *c, int32_t bone, const float in[3], float out[3])
{
    draw_context *d = c;
    out[0] = out[1] = out[2] = 0.0f;
    if (d->posed)   /* TransformPosition(.., BoneTransform + 0x30 * bone, .., 0): the bone in the world (viewer choice) */
        mu_world_particles_bone_position(&d->posed->model, bone, in, out);
}

/* NATIVE-HELPERS-002: RenderTerrainAlphaBitmap 0x016cdd5f of a class visual through the model's render backend: the
 * terrain decal's fans become triangles; the bitmap is one of the model's extra slots. */
typedef struct decal_adapter {
    const mu_render_backend *backend;
    const mu_textures *textures;
    mu_meshdraw_state state;
    int32_t texture;
    float v[64][3], t[64][2], c[64][4];
    int32_t n;
    float color[4], uv[2];
} decal_adapter;

static void da_state(void *c, int32_t state, int32_t argument)
{
    decal_adapter *a = c;
    mu_world_state(state, argument, &a->state);
}

static void da_bind(void *c, int32_t texture)
{
    decal_adapter *a = c;
    a->texture = -1;
    const mu_textures *t = a->textures;
    for (int32_t j = 0; t && j < t->extra_count; ++j)
        if (t->extra_index[j] == texture)
            a->texture = t->model_count + MU_TEXTURE_SPECIAL_COUNT + j;
}

static void da_begin(void *c, int32_t mode)
{
    decal_adapter *a = c;
    (void)mode;   /* GL_TRIANGLE_FAN */
    a->n = 0;
}

static void da_tex(void *c, float s, float t)
{
    decal_adapter *a = c;
    a->uv[0] = s;
    a->uv[1] = t;
}

static void da_c3(void *c, const float rgb[3])
{
    decal_adapter *a = c;
    a->color[0] = rgb[0], a->color[1] = rgb[1], a->color[2] = rgb[2], a->color[3] = 1.0f;
}

static void da_c4(void *c, float r, float g, float b, float al)
{
    decal_adapter *a = c;
    a->color[0] = r, a->color[1] = g, a->color[2] = b, a->color[3] = al;
}

static void da_v(void *c, const float xyz[3])
{
    decal_adapter *a = c;
    if (a->n >= 64)
        return;
    memcpy(a->v[a->n], xyz, sizeof a->v[0]);
    memcpy(a->t[a->n], a->uv, sizeof a->t[0]);
    memcpy(a->c[a->n], a->color, sizeof a->c[0]);
    a->n++;
}

static void da_end(void *c)
{
    decal_adapter *a = c;
    const mu_render_backend *b = a->backend;
    if (a->n < 3 || a->texture < 0)
        return;
    if (b->prepare)
        b->prepare(b->context, &a->state, a->texture);
    if (b->begin)
        b->begin(b->context);
    for (int32_t i = 1; i + 1 < a->n; ++i) {
        const int32_t k[3] = {0, i, i + 1};
        for (int32_t j = 0; j < 3; ++j) {
            b->sink.texcoord(b->sink.context, a->t[k[j]][0], a->t[k[j]][1]);
            b->sink.color4(b->sink.context, a->c[k[j]][0], a->c[k[j]][1], a->c[k[j]][2], a->c[k[j]][3]);
            b->sink.vertex(b->sink.context, a->v[k[j]]);
        }
    }
    if (b->end)
        b->end(b->context);
}

static void draw_decals(draw_context *d, mu_wh_model *m, const mu_hp_after_call *calls, int32_t n)
{
    mu_world_helpers *w = d->w;
    if (!d->target || !w->map)
        return;
    mu_render_backend backend;
    if (d->target->backend(d->target->context, w, slot_of(w, m), &backend))
        return;
    decal_adapter a;
    memset(&a, 0, sizeof a);
    a.backend = &backend;
    a.textures = &m->textures;
    a.texture = -1;
    mu_meshdraw_state_defaults(&a.state);
    mu_terrain_sink sink = {&a, da_state, da_bind, da_begin, da_tex, da_c3, da_c4, da_v, da_end};
    mu_terrain_scene scene;
    mu_world_scene((mu_world *)w->map, &scene);   /* read only */
    for (int32_t i = 0; i < n; ++i) {
        const mu_hp_after_call *c = &calls[i];
        if (c->kind == MU_HP_AC_BLEND) {
            da_state(&a, c->flags == 0x0184aa2b ? MU_TERRAIN_STATE_ADDITIVE : MU_TERRAIN_STATE_OPAQUE, 1);
            continue;
        }
        if (c->kind != MU_HP_AC_DECAL)
            continue;
        mu_terrain_decal(&scene, c->type, c->position[0], c->position[1], c->scale, c->scale, c->light, c->angle[0],
                         c->alpha, 5.0f, 1, 0, &sink);
        w->stats.decals++;
    }
}

/* The class visuals (vtable +0x1c) of a drawn mount (NATIVE-HELPERS-002: the Shining Tail). */
static void class_visuals(draw_context *d, mu_wh_model *m, const mu_hp_object *o)
{
    mu_world_helpers *w = d->w;
    mu_hp_mount *mount = NULL;
    for (int32_t i = 0; i < w->mounts.count; ++i)
        if (&w->mounts.list[i].object == o)
            mount = &w->mounts.list[i];
    if (!mount)
        return;
    mu_hp_class_state *st = class_state_of(w, mount->key);
    if (!st)
        return;
    mu_hp_class_inputs in;
    memset(&in, 0, sizeof in);
    in.world_time = w->world_time;
    in.action = o->action;
    in.frame = o->frame;
    in.alpha = o->alpha;
    memcpy(in.position, o->position, sizeof in.position);
    memcpy(in.angle, o->angle, sizeof in.angle);
    class_host_ctx x = {w, m};
    mu_hp_class_host host = {&x, c_object_bone, c_named_bone};
    mu_hp_after_call calls[160];
    int32_t n = 0;
    if (!mu_hp_mount_class_visuals(&w->h, mount->cls, st, &in, &host, calls, 160, &n))
        return;
    if (n > 160)
        n = 160;
    class_calls(w, calls, n, m);
    draw_decals(d, m, calls, n);
}

/* The after-pass (vtable +0x18 0x0103d830 -> RenderObject's draw 0x017edf43): the registry functor of the mount
 * model (mount_render.c, NATIVE-HELPERS-002) or the default body RenderBody(2, ...). */
static void r_after(void *c, const mu_hp_object *o, int32_t a1, int32_t a2, int32_t a3, int32_t a4, int32_t a5)
{
    draw_context *d = c;
    mu_world_helpers *w = d->w;
    (void)a1, (void)a3, (void)a4, (void)a5;
    mu_wh_model *m = d->posed;
    if (!m || o->field_68 == -2)
        return;
    const float *body_light = m->model.params.color;   /* model +0x54: the setup's body light */
    mu_hp_after_inputs in;
    memset(&in, 0, sizeof in);
    in.world = w->inputs.world;
    in.world_time = w->world_time;
    in.world_9b0418 = (uint8_t)((in.world >= 0x18 && in.world <= 0x1d) || in.world == 0x24);
    in.event_block = (uint8_t)(in.world == 0x27 && !(w->inputs.event_state >= 3 && w->inputs.event_state <= 5));
    memcpy(in.color, body_light, sizeof in.color);
    in.model_94 = 0xff;
    in.object_a4 = 0.0f;   /* the later classes' model load writes 0; their visuals (+0x1c) fade it (not ported) */
    mu_hp_after_host host = {d, after_bone};
    mu_hp_after_call calls[96];
    int32_t n = 0;
    int r = a2 == 10 ? -1 : mu_hp_mount_after(&w->h, o, &in, &host, calls, 96, &n);   /* buff: 0x017f746f, static */
    if (n > 96)
        n = 96;
    if (r <= 0) {
        draw_pass(d, m, -1, 2, o->alpha, o->blend_mesh, o->blend_light, in.object_u, in.object_v, o->field_68, -1,
                  NULL);
        return;
    }
    float shadow_rgba[4] = {0.0f, 0.0f, 0.0f, 0.7f};
    for (int32_t i = 0; i < n; ++i) {
        const mu_hp_after_call *a = &calls[i];
        switch (a->kind) {
        case MU_HP_AC_BODY:
            draw_pass(d, m, -1, a->flags, a->alpha, a->blend_mesh, a->blend_light, a->u, a->v, a->hidden, a->texture,
                      a->color);
            break;
        case MU_HP_AC_MESH:
            draw_pass(d, m, a->mesh, a->flags, a->alpha, a->blend_mesh, a->blend_light, a->u, a->v, -1, a->texture,
                      a->color);
            break;
        case MU_HP_AC_COLOR4:
            shadow_rgba[3] = a->scale;
            break;
        case MU_HP_AC_SHADOW:
            if (d->target && d->target->shadow_range)
                d->target->shadow_range(d->target->context, w, slot_of(w, m), shadow_rgba, a->mesh, a->texture);
            w->stats.shadows++;
            break;
        case MU_HP_AC_SPRITE:
            w->stats.sprites++;
            if (w->particles)
                mu_world_particles_sprite(w->particles, a->type, a->position, a->scale, a->light, -1, 0.0f, 0, 4);
            break;
        case MU_HP_AC_PARTICLE:
            w->stats.particles++;
            if (w->particles)
                mu_world_particles_create(w->particles, a->type, a->position, a->angle, a->light, a->subtype, a->scale);
            break;
        case MU_HP_AC_EFFECT:
            w->stats.effects++;
            if (w->particles)
                mu_world_particles_effect(w->particles, a->type, a->subtype, a->position, a->angle, a->light, -1, 1.0f,
                                          NULL);
            break;
        default:
            break;   /* the pose push/pop, the bone lookups (done through the host), EnableAlphaTest */
        }
    }
    class_visuals(d, m, o);   /* vtable +0x1c after the after-pass (0x0106bc2b) */
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
    w->stats.drawn_bugs = w->stats.drawn_mounts = w->stats.drawn_imps = w->stats.shadows = w->stats.passes = w->stats.decals = 0;
    /* the render scene's order: RenderBugs 0x00c9e4e3, the mount render loop 0x0106bc2b */
    mu_hp_render_bugs(&w->h, &w->inputs, &r);
    mu_hp_mounts_render(&w->h, &w->mounts, &w->inputs, &r);
    if (w->raven)   /* NATIVE-HELPERS-002: RenderPet per character (RenderCharacter's 0x00c9314f) */
        d.drawn += mu_world_raven_draw(w->raven, frustum, target);
    if (w->pets)   /* RenderPets 0x00eb0dee (NATIVE-HELPERS-002) */
        d.drawn += mu_world_pets_draw(w->pets, w, frustum, target);
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
    mu_world_helpers_target target = {&t, raster_backend, NULL, NULL};
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
                 " \"drawn_imps\": %u, \"riding\": %d, \"passes\": %u",
            frame, w->stats.live_bugs, w->stats.live_mounts, w->stats.drawn_bugs, w->stats.drawn_mounts,
            w->stats.drawn_imps, w->walk ? w->walk->riding : 0, w->stats.passes);
    if (w->raven && w->raven->stats.live)
        fprintf(out, ", \"ravens\": %u, \"raven_drawn\": %u", w->raven->stats.live, w->raven->stats.drawn);
    for (int32_t i = 0; i < MU_HP_BUGS; ++i) {
        const mu_hp_object *o = &w->h.bugs[i];
        if (o->live)
            fprintf(out, ", \"bug%d\": [%d, %d, %.2f, %.2f, %.2f]", i, o->type, o->owner, (double)o->position[0],
                    (double)o->position[1], (double)o->position[2]);
    }
    for (int32_t i = 0; i < w->mounts.count; ++i) {
        const mu_hp_mount *m = &w->mounts.list[i];
        fprintf(out, ", \"mount%d\": [%d, %d, %d, %d, %.2f, %.2f, %.2f, %.1f]", i, m->cls, m->owner, m->action,
                w->owners[m->owner].action, (double)m->offset[0], (double)m->offset[1], (double)m->offset[2],
                (double)m->object.angle[2]);
    }
    fprintf(out, "}\n");
    if (w->raven)
        mu_world_raven_report_frame(w->raven, out);
    if (w->pets)
        mu_world_pets_report_frame(w->pets, out, frame);
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
    if (w->raven)
        mu_world_raven_report_summary(w->raven, out);
    if (w->pets)
        mu_world_pets_report_summary(w->pets, out);
    if (!quiet)
        for (int32_t i = 0; i < w->log_count; ++i)
            fprintf(out, "helpers: %s\n", w->log[i]);
}
