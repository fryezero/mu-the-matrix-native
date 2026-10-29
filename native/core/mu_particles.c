/* The client's legacy particles, sprites and blob shadows in the native
 * session (NATIVE-PARTICLE-001). */
#include <stdio.h>
#include "mu_frame_time.h"
#include <stdlib.h>
#include <string.h>

#include "mu_particles.h"
#include "../../reconstructed/objects/world_warp.h"
#include "mu_world_actors.h"
#include "mu_objects.h"
#include "mu_env.h"
#include "../../reconstructed/objects/icarus.h"
#include "mu_world_helpers.h"
#include "mu_meshdraw.h"
#include "../../reconstructed/environment/env.h"
#include "../../reconstructed/movement/client_movement.h"

/* Effect bitmaps first (MU_WORLD_PT_EFFECTS of them), then the world's rain02/rain03. NATIVE-JOINT-001 adds
 * the joints' textures (JointThunder01, Spark01, JointSpirit01, JointEnergy01; LoadBitmap 0x0182239b..) and
 * the login scene's clouds and WATERFALL1; NATIVE-CHARSEL-002 the character-select scene's WATERFALL2/3,
 * fantaB, Spark04, magic_ground1_3 and Impack03 (the selection light 0x8022 subtype 5 draws Impack03). */
#define MU_WORLD_PT_EFFECTS 58
static const int32_t bitmap_ids[MU_WORLD_PT_BITMAPS] = {
    MU_PT_BITMAP_FIRE, MU_PT_BITMAP_SMOKE, MU_PT_BITMAP_FLARE, MU_PT_BITMAP_SPARK3, MU_PT_BITMAP_THUNDER,
    MU_PT_BITMAP_SPARK2, MU_PT_BITMAP_SHINY2, MU_JT_BITMAP_THUNDER, MU_JT_BITMAP_SPARK, MU_JT_BITMAP_SPIRIT,
    MU_JT_BITMAP_ENERGY, MU_PT_BITMAP_CLOUDS, MU_PT_BITMAP_WATERFALL1, MU_PT_BITMAP_LIGHTNING2,
    MU_PT_BITMAP_SHINY1, MU_PT_BITMAP_WATERFALL2, MU_PT_BITMAP_WATERFALL3, MU_PT_BITMAP_FANTA_B,
    MU_PT_BITMAP_SPARK04, MU_PT_BITMAP_MAGIC_GROUND13, MU_PT_BITMAP_IMPACK03,
    /* NATIVE-HELPERS-002: the helpers' smoke02 and drop01, the Dark Horse ring's Flare and the flying step's
     * ShockWave (LoadBitmap 0x0182166f, 0x0183930b, 0x0182253b, 0x0182150f) */
    MU_PT_BITMAP_SMOKE2, MU_PT_BITMAP_DROP, MU_JT_BITMAP_FLARE, MU_SFX_BITMAP_SHOCKWAVE,
    /* NATIVE-HELPERS-002: the Shining Tail's glints (pin_star, pin_star02, bostar3_R, Shiny03) */
    0x8108, 0x8109, 0x8179, 0x7f68,
    /* Fenrir's paw marks eff_lightinga01..05 (LoadBitmap 0x01822cdb..) */
    MU_SFX_BITMAP_LIGHTING_A, MU_SFX_BITMAP_LIGHTING_A + 1, MU_SFX_BITMAP_LIGHTING_A + 2,
    MU_SFX_BITMAP_LIGHTING_A + 3, MU_SFX_BITMAP_LIGHTING_A + 4, 0x831d, 0x83b3, 0x8086, 0x8438, 0x7fdd,
    0x7fe0, 0x8098, MU_JT_BITMAP_LASER, MU_PT_BITMAP_SMOKE5, 0x8016, 0x806e, 0x8084, 0x8085, 0x7f8a, 0x7f21,
    0x7f54, 0x7f84, 0x7f38, 0x8021, 0x7f6b, 0x8087, 0x8089, 0x801e, 0x8184, MU_PT_BITMAP_RAIN_SPLASH, MU_PT_BITMAP_RAIN_RING};
static const char *const effect_files[MU_WORLD_PT_EFFECTS] = {
    "Data/Effect/Fire01.OZJ", "Data/Effect/smoke01.OZJ", "Data/Effect/flare01.OZJ", "Data/Effect/Spark03.OZJ",
    "Data/Effect/Thunder01.OZJ", "Data/Effect/Spark02.OZJ", "Data/Effect/Shiny02.OZJ",
    "Data/Effect/JointThunder01.OZJ", "Data/Effect/Spark01.OZJ", "Data/Effect/JointSpirit01.OZJ",
    "Data/Effect/JointEnergy01.OZJ", "Data/Effect/clouds.OZJ", "Data/Effect/WATERFALL1.OZJ",
    "Data/Effect/lightning2.OZJ", "Data/Effect/Shiny01.OZJ", "Data/Effect/WATERFALL2.OZJ",
    "Data/Effect/WATERFALL3.OZJ", "Data/Effect/fantaB.OZJ", "Data/Effect/Spark04.OZJ",
    "Data/Effect/magic_ground1_3.OZJ", "Data/Effect/Impack03.OZJ", "Data/Effect/smoke02.ozt",
    "Data/Object8/drop01.OZJ", "Data/Effect/Flare.OZJ", "Data/Effect/Shockwave.OZJ",
    "Data/Effect/pin_star.OZJ", "Data/Effect/pin_star02.OZJ", "Data/Effect/bostar3_R.OZJ",
    "Data/Effect/Shiny03.OZJ", "Data/Effect/eff_lightinga01.OZJ", "Data/Effect/eff_lightinga02.OZJ",
    "Data/Effect/eff_lightinga03.OZJ", "Data/Effect/eff_lightinga04.OZJ", "Data/Effect/eff_lightinga05.OZJ",
    "Data/Effect/Steam_01.OZJ", "Data/Effect/Smoke_line.OZJ", "Data/Effect/firehik_mono01.OZJ",
    "Data/Effect/lightmarks_mzin.OZJ", "Data/Effect/flareBlue.OZJ", "Data/Effect/flareRed.OZJ",
    "Data/Effect/lightmarks.OZJ", "Data/Effect/JointLaser01.OZJ", "Data/Effect/smoke05.ozt",
    /* LoadBitmap 01820fcf,0182188f,01821b2f,01821b4f, RENDER-WORLDS-A. */
    "Data/Effect/fantaF.OZJ", "Data/Effect/firehik02.OZJ", "Data/Effect/firehik01.OZJ",
    "Data/Effect/firehik03.OZJ", "Data/Effect/cloudLight.OZJ", "Data/Effect/Map_Smoke1.OZJ", "Data/Effect/Explotion01.OZJ",
    /* LoadBitmap 0x01821599 / 0x01822345 / 0x01821f65, LINEAR/CLAMP/1/0. */
    "Data/Effect/Magic_Ground2.OZJ", "Data/Effect/lightning3.OZJ", "Data/Effect/Impack03.OZJ",
    /* RENDER-WORLDS-L: exact loader mappings, LINEAR/CLAMP/1/0. */
    "Data/Effect/Shiny04.OZJ", "Data/Effect/firehik_mono02.OZJ",
    "Data/Effect/firehik_mono03.OZJ", "Data/Effect/WATERFALL5.OZJ",
    /* RENDER-WORLDS-M: flare_mono, LoadBitmap 0x0184119c (Uruk's 0x8184/2), LINEAR/CLAMP/1/0. */
    "Data/Effect/flare_mono.OZJ"};

/* The world objects' effect models (AccessModel, static readings of the loaders): the Tormenta handler's
 * hs_fieldtornado (0x00e4c4de). */
static const struct { int32_t type, world; const char *file; } fx_model_files[MU_WORLD_FX_MODELS] = {
    {MU_SFX_MODEL_TORNADO, 0x8d, "Data/Object142/hs_fieldtornado.bmd"},
    /* NATIVE-CHARSEL-003: the character select's sky dragon and its glint (AccessModel 0x018363e8/0x0183641d,
     * textures from Data\Effect\) */
    {MU_SFX_MODEL_STAR_DRAGON, 0x5d, "Data/Effect/stardr01.bmd"},
    {MU_SFX_MODEL_STAR_GLINT, 0x5d, "Data/Effect/stardr02.bmd"},
    /* NATIVE-HELPERS-002: Fenrir's body lightning (AccessModel 0x01834a74, every world: world -1) */
    {MU_SFX_MODEL_FENRIR_LIGHTNING, -1, "Data/Effect/lightning_type01.bmd"},
    /* AccessModels 0x0183943f/0x018397d1/0x0183f529: shared warp models. */
    {0x1a8, -1, "Data/Npc/warp01.bmd"}, {0x1a9, -1, "Data/Npc/warp02.bmd"},
    {0x1aa, -1, "Data/Npc/warp03.bmd"}, {0x1ab, -1, "Data/Npc/warp01.bmd"},
    {0x1ac, -1, "Data/Npc/warp02.bmd"}, {0x1ad, -1, "Data/Npc/warp03.bmd"},
    {MU_SFX_MODEL_CLOUD, 10, "Data/Object11/cloud.bmd"},
    /* RENDER-EFFECTS-004: Spirit of Guardian's wing 0x460 (AccessModel 0x0183375e, every world) */
    {MU_SFX_MODEL_GUARDIAN_WING, -1, "Data/Skill/darkwing_hetachi.bmd"}};

static int32_t slot_of(int32_t bitmap)
{
    for (int32_t i = 0; i < MU_WORLD_PT_BITMAPS; ++i)
        if (bitmap_ids[i] == bitmap)
            return i;
    return -1;
}

int32_t mu_world_particles_rand(mu_world_particles *p)
{
    p->rand_state = p->rand_state * 214013u + 2531011u;   /* rand() 0x01989721 */
    p->rand_calls++;
    return (int32_t)((p->rand_state >> 16) & 0x7fff);
}

/* ---- host of the reconstructed routines ---- */

static int32_t h_rand(void *c) { return mu_world_particles_rand(c); }

static float h_terrain(void *c, float x, float y)
{
    const mu_world_particles *p = c;
    if (!p->map)
        return 0.0f;
    return mu_request_terrain_height(p->map->height, p->map->attributes, p->map->water_height, 6, x, y);
}

static const mu_jt_object *fx_object(mu_world_particles *p, int32_t index);

/* The owner OBJECT's +0x158 (world objects or helper OBJECTs). */
static void h_owner(void *c, int32_t owner, float out[3])
{
    const mu_jt_object *o = fx_object(c, owner);
    if (o)
        memcpy(out, o->position, 12);
}

/* The bitmap record's height +0x208 (NATIVE-HELPERS-002: smoke02 sits on the terrain by half of it). */
static float h_bitmap_height(void *c, int32_t bitmap)
{
    const mu_world_particles *p = c;
    const int32_t s = slot_of(bitmap);
    return s >= 0 && p->bitmap_present[s] ? (float)p->bitmaps.images[s].height : 0.0f;
}

static int h_cloud_owner(void *c, int32_t index, int reset)
{
    mu_world_particles *p = c;
    uint8_t *o = p->objects ? mu_objects_object_image(p->objects, index) : NULL;
    if (!o) return 0;
    if (reset) mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, 0);
    return o[MU_OBJF_VISIBLE] == 1;
}

static void h_sound(void *context, int32_t id)
{
    (void)id;
    ((mu_world_particles *)context)->stats.sounds++;
}

static void h_light(void *context, float x, float y, const float rgb[3], int32_t range)
{
    mu_world_particles *p = context;
    if (p->light_count >= MU_WORLD_FX_LIGHTS) return;
    mu_world_fx_light *l = &p->lights[p->light_count++];
    l->x = x; l->y = y; l->range = range;
    memcpy(l->rgb, rgb, sizeof l->rgb);
}

static void host(mu_world_particles *p, mu_pt_host *h)
{
    memset(h, 0, sizeof *h);
    h->context = p;
    h->rand = h_rand;
    h->terrain_height = h_terrain;
    h->owner_position = h_owner;
    h->world = p->world;
    h->world_time = p->world_time;
    h->frame_time = mu_frame_time_value();   /* [0x01cf103c] */
    h->drop_divisor = 1;
    h->scene_state = p->scene_state;   /* SceneFlag (NATIVE-CHARSEL-002: WATERFALL2 in scene 5) */
    h->bitmap_height = h_bitmap_height;
    h->cloud_owner = h_cloud_owner;
    h->sound = h_sound;
    h->light = h_light;
}

/* ---- assets ---- */

static void load_bitmaps(mu_world_particles *p, const char *root, int no_assets)
{
    mu_textures *t = &p->bitmaps;
    t->count = t->model_count = MU_WORLD_PT_BITMAPS;
    t->images = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->images);
    t->slots = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->slots);
    t->components = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->components);
    t->filter = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->filter);
    t->wrap = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->wrap);
    if (!t->images || !t->slots || !t->components || !t->filter || !t->wrap)
        return;
    for (int32_t i = 0; i < MU_WORLD_PT_BITMAPS; ++i) {
        char relative[512], path[2048], error[256];
        if (bitmap_ids[i] == 0x7f21 && p->world != 51) continue;
        if (i < MU_WORLD_PT_EFFECTS) {
            /* LoadBitmap("Effect\\...", index, GL_LINEAR, GL_CLAMP) in the effect loader (0x01820f19 ...);
             * Impack03 0x7b78: GL_NEAREST in OpenCharacterSceneData (0x0182a6c2, static) */
            t->filter[i] = bitmap_ids[i] == MU_PT_BITMAP_IMPACK03 ? 0x2600 : 0x2601;
            t->wrap[i] = bitmap_ids[i] == 0x7f21 ? 0x2901 : 0x2900;
            snprintf(relative, sizeof relative, "%s", effect_files[i]);
        } else {
            /* the world's rain02/rain03: GL_NEAREST, GL_CLAMP (0x01829e21) */
            t->filter[i] = 0x2600;
            t->wrap[i] = 0x2900;
            if (!mu_env_bitmap_file(p->world, bitmap_ids[i], relative, sizeof relative))
                continue;
        }
        if (no_assets || !mu_objects_resolve(root, relative, path, sizeof path))
            continue;
        size_t n = strlen(path);
        char kind = (n > 0 && (path[n - 1] == 'J' || path[n - 1] == 'j')) ? 'j' : 't';
        if (mu_texture_upload_file(path, kind, &t->images[i], &t->components[i], error, sizeof error) == 0 &&
            t->images[i].width > 0) {
            t->slots[i] = &t->images[i];
            p->bitmap_present[i] = 1;
        }
    }
}

int mu_world_particles_open(mu_world_particles *p, const char *root, const mu_world *map, int32_t world,
                            uint32_t seed, int no_assets, char *error, size_t error_size)
{
    memset(p, 0, sizeof *p);
    p->world = world;
    p->map = map;
    p->rand_state = seed;
    p->scene_state = 6;   /* the in-world scene; the login and character-select sessions set theirs */
    p->sprites = calloc(1, sizeof *p->sprites);
    if (!p->sprites || mu_pt_system_init(&p->list, MU_WORLD_PT_CAPACITY)) {
        snprintf(error, error_size, "out of memory");
        free(p->sprites);
        p->sprites = NULL;
        return 1;
    }
    load_bitmaps(p, root, no_assets);
    p->joints = calloc(MU_JT_JOINTS, sizeof *p->joints);
    p->effects = calloc(MU_WORLD_FX_EFFECTS, sizeof *p->effects);
    p->joint_quads = calloc(MU_WORLD_FX_QUADS, sizeof *p->joint_quads);
    if (!p->joints || !p->effects || !p->joint_quads) {
        snprintf(error, error_size, "out of memory");
        mu_world_particles_close(p);
        return 1;
    }
    for (int i = 0; i < MU_WORLD_FX_MODELS; ++i) {
        mu_world_fx_model *m = &p->models[i];
        m->type = fx_model_files[i].type;
        if (mu_world_warp_type(m->type) && world != 2 && world != 3 && world != 57 && world != 58)
            continue;
        if (no_assets || (fx_model_files[i].world != world && fx_model_files[i].world != -1))
            continue;
        char path[4096], message[512], directory[2048];
        if (!mu_objects_resolve(root, fx_model_files[i].file, path, sizeof path) ||
            mu_bmd_load_file(path, &m->bmd, message, sizeof message) != MU_BMD_OK)
            continue;
        mu_model_params params;
        mu_model_default_params(&params);
        params.world = world;
        if (mu_model_init(&m->model, &m->bmd, &params, message, sizeof message) != MU_MODEL_OK) {
            mu_bmd_free(&m->bmd);
            continue;
        }
        mu_path_directory(path, directory, sizeof directory);
        mu_textures_load(&m->textures, &m->bmd, directory);
        m->loaded = 1;
    }
    return 0;
}

void mu_world_particles_close(mu_world_particles *p)
{
    mu_textures *t = &p->bitmaps;
    if (t->images)
        for (int i = 0; i < t->count; ++i)
            mu_image_free(&t->images[i]);
    free(t->images);
    free(t->slots);
    free(t->components);
    free(t->filter);
    free(t->wrap);
    mu_pt_system_free(&p->list);
    free(p->sprites);
    for (int i = 0; i < MU_WORLD_FX_MODELS; ++i)
        if (p->models[i].loaded) {
            mu_textures_free(&p->models[i].textures);
            mu_model_free(&p->models[i].model);
            mu_bmd_free(&p->models[i].bmd);
        }
    free(p->joints);
    free(p->effects);
    free(p->joint_quads);
    memset(p, 0, sizeof *p);
}

/* ---- creation and the step ---- */

int mu_world_particles_create(mu_world_particles *p, int32_t type, const float position[3], const float angle[3],
                              const float light[3], int32_t subtype, float scale)
{
    return mu_world_particles_create_owned(p, type, position, angle, light, subtype, scale, MU_PT_NO_OWNER);
}

int mu_world_particles_create_owned(mu_world_particles *p, int32_t type, const float position[3],
                                    const float angle[3], const float light[3], int32_t subtype, float scale,
                                    int32_t owner)
{
    mu_pt_host h;
    host(p, &h);
    if (owner >= 0 && !fx_object(p, owner))
        owner = MU_PT_NO_OWNER;
    const int kept = mu_pt_create(&p->list, &h, type, position, angle, light, subtype, scale, owner, 0);
    p->stats.created = p->list.created;
    p->stats.dropped = p->list.dropped;
    p->stats.unsupported = p->list.unsupported;
    p->stats.overflow = p->list.overflow;
    return kept;
}

int32_t mu_world_particles_sprite(mu_world_particles *p, int32_t bitmap, const float position[3], float scale,
                                  const float light[3], int32_t owner, float rotation, int32_t blend, int32_t axes)
{
    static const mu_pt_sheet sheet = {1, 1, 1.0f};   /* 0x00a0c1d0 */
    const int32_t i = mu_pt_sprite_create(p->sprites, bitmap, position, scale, light, owner, rotation, blend, axes,
                                          &sheet);
    p->stats.sprites_created = p->sprites->created;
    p->stats.sprites_full = p->sprites->full;
    return i;
}

/* ---- the world objects' joints and effects (NATIVE-JOINT-001) ---- */

static mu_jt_object view_of(const mu_world_particles *p, int32_t index)
{
    mu_jt_object o;
    memset(&o, 0, sizeof o);
    const uint8_t *img = p->objects ? mu_objects_object_image(p->objects, index) : NULL;
    if (img) {
        o.live = img[MU_OBJF_LIVE];
        o.visible = img[MU_OBJF_VISIBLE];
        memcpy(o.position, img + MU_OBJF_POSITION, 12);
        memcpy(o.light, img + MU_OBJF_LIGHT, 12);
    }
    return o;
}

static mu_jt_object hero_view(const mu_world_particles *p)
{
    mu_jt_object o;
    memset(&o, 0, sizeof o);
    o.live = o.visible = 1;
    memcpy(o.position, p->hero_position, sizeof o.position);
    return o;
}


static const mu_jt_object *fx_object(mu_world_particles *p, int32_t index)
{
    mu_jt_object *o = &p->object_scratch[p->object_next++ & 3];
    if (index == MU_WORLD_FX_HERO_OBJECT) {
        if (!p->has_hero)
            return NULL;
        *o = hero_view(p);
        return o;
    }
    if (index >= MU_WORLD_FX_BOID_BASE && index < MU_WORLD_FX_BOID_BASE + MU_ENV_BOIDS) {
        if (!p->environment) return NULL;
        const mu_env_object *b = &p->environment->env.boids[index - MU_WORLD_FX_BOID_BASE];
        memset(o, 0, sizeof *o); o->live = b->live; o->visible = b->visible; o->type = b->type;
        memcpy(o->position, b->position, 12); memcpy(o->light, b->light, 12);
        return o;
    }
    if (index >= MU_WH_EFFECT_BASE && index < MU_WORLD_FX_HERO_OBJECT)
        return mu_world_helpers_effect_object(p->helpers, index, o) ? o : NULL;
    if (index >= MU_WORLD_ACTOR_FX_BASE && index < MU_WH_EFFECT_BASE) {
        int32_t i = index - MU_WORLD_ACTOR_FX_BASE;
        if (!p->actors || i >= p->actors->count)
            return NULL;
        const mu_world_actor *a = &p->actors->list[i];
        memset(o, 0, sizeof *o);
        o->live = (uint8_t)(a->player != NULL || a->actor.loaded);
        memcpy(o->position, a->position, sizeof o->position);
        o->type = a->actor.spec.model_index;
        return o;
    }
    if (!p->objects || !mu_objects_object_image(p->objects, index))
        return NULL;
    *o = view_of(p, index);
    return o;
}

static int32_t jt_rand(void *c) { return mu_world_particles_rand(c); }
static float jt_height(void *c, float x, float y) { return h_terrain(c, x, y); }
static const mu_jt_object *jt_object(void *c, int32_t index) { return fx_object(c, index); }

static int fx_call(mu_world_particles *p, const mu_jt_call *call, mu_sfx_effect *e);

static void jt_call(void *c, const mu_jt_call *call)
{
    fx_call(c, call, NULL);
}

static void joint_env(mu_world_particles *p, mu_jt_env *env)
{
    memset(env, 0, sizeof *env);
    env->context = p;
    env->rand = jt_rand;
    env->height = jt_height;
    env->object = jt_object;
    env->call = jt_call;
    env->world_time = p->world_time;
    env->ambient_clock = p->environment ? p->environment->inputs.ambient_clock : 0;
}

static int32_t sfx_rand(void *c) { return mu_world_particles_rand(c); }
static float sfx_height(void *c, float x, float y) { return h_terrain(c, x, y); }
static const mu_sfx_object *sfx_object(void *c, int32_t index) { return fx_object(c, index); }
static int sfx_call(void *c, const mu_sfx_call *call, mu_sfx_effect *e) { return fx_call(c, call, e); }

static int sfx_model(void *c, int32_t type, uint16_t action, int16_t *keys)
{
    const mu_world_particles *p = c;
    *keys = 1;
    for (int i = 0; i < MU_WORLD_FX_MODELS; ++i)
        if (p->models[i].type == type && p->models[i].loaded) {
            const mu_bmd *b = &p->models[i].bmd;
            if (b->action_count > 0)
                *keys = (int16_t)b->actions[action < b->action_count ? action : 0].keys;
            return 1;
        }
    return 1;   /* a missing native model: the client has it */
}

static mu_world_fx_model *fx_model_of(mu_world_particles *p, int32_t type)
{
    for (int k = 0; k < MU_WORLD_FX_MODELS; ++k)
        if (p->models[k].type == type && p->models[k].loaded)
            return &p->models[k];
    return NULL;
}

/* Animation(bones, frame, prior, prior action, angle, head angle, 0, 0) on the effect's model: model-space bones
 * turned by the effect's angle, the body scale and origin applied later (translate 0) */
static int fx_pose(mu_world_fx_model *m, const mu_sfx_effect *e)
{
    mu_model_params params = m->model.params;
    for (int k = 0; k < 3; ++k) {
        params.origin[k] = e->position[k];
        params.angles[k] = e->angle[k];
        params.color[k] = e->light[k];
    }
    params.body_scale = e->scale;
    params.lighting = e->flag5;
    mu_model_apply_params(&m->model, &params);
    const int32_t keys = m->bmd.action_count > 0 ? m->bmd.actions[0].keys : 1;
    float frame = e->frame;
    if (keys > 0 && frame >= (float)keys)
        frame = 0.0f;
    mu_model_set_state(&m->model, 0, frame, frame, 0);
    return mu_model_pose(&m->model) == MU_MODEL_OK;
}

/* TransformByObjectBone 0x012b678d(out, o, bone, 0): out = BodyScale * bone translation + o->Position */
static void sfx_bone(void *c, const mu_sfx_effect *e, int32_t bone, float out[3])
{
    mu_world_particles *p = c;
    mu_world_fx_model *m = fx_model_of(p, e->type);
    const float zero[3] = {0.0f, 0.0f, 0.0f};
    if (!m || !fx_pose(m, e) || !mu_world_particles_bone_position(&m->model, bone, zero, out))
        memcpy(out, e->position, 3 * sizeof *out);
}

static uint32_t sfx_time(void *c)
{
    const mu_world_particles *p = c;
    return p->world_time > 0.0f ? (uint32_t)p->world_time : 0u;
}

static void sfx_owner_bone(void *c, int32_t owner, int32_t bone, const float in[3], float out[3])
{
    mu_world_particles *p = c;
    mu_world_helpers_effect_bone(p->helpers, owner, bone, in, out);
}

static void effect_env(mu_world_particles *p, mu_sfx_env *env)
{
    memset(env, 0, sizeof *env);
    env->world_time = p->world_time;
    env->bone = sfx_bone;
    env->owner_bone = sfx_owner_bone;
    env->context = p;
    env->rand = sfx_rand;
    env->height = sfx_height;
    env->object = sfx_object;
    env->call = sfx_call;
    env->model = sfx_model;
    env->hero_object = MU_WORLD_FX_HERO_OBJECT;
    env->time_ms = sfx_time;   /* NATIVE-HELPERS-002: timeGetTime as the world time (viewer choice) */
}

static int fx_call(mu_world_particles *p, const mu_jt_call *call, mu_sfx_effect *e)
{
    switch (call->routine) {
    case MU_JT_CALL_TERRAIN_LIGHT:
        if (p->light_count < MU_WORLD_FX_LIGHTS) {
            mu_world_fx_light *l = &p->lights[p->light_count++];
            l->x = call->position[0];
            l->y = call->position[1];
            memcpy(l->rgb, call->light, sizeof l->rgb);
            l->range = call->range;
        }
        return 0;
    case MU_JT_CALL_SPRITE:
        mu_world_particles_sprite(p, call->type, call->position, call->scale, call->light, call->owner, call->angle[0],
                                  call->subtype, call->range);
        return 0;
    case MU_JT_CALL_PARTICLE:
        mu_world_particles_create_owned(p, call->type, call->position, call->angle, call->light, call->subtype,
                                        call->scale, call->owner >= 0 ? call->owner : MU_PT_NO_OWNER);
        return 0;
    case MU_JT_CALL_JOINT:
        mu_world_particles_joint(p, call->type, call->position, call->target, call->angle, call->subtype,
                                 call->owner, call->scale, 0xffff, 0, 0, 0xffff, 0, call->light);
        return 0;
    case MU_JT_CALL_DELETE:
        for (int i = 0; p->joints && i < MU_JT_JOINTS; i++)
            if (p->joints[i].type == call->type && p->joints[i].target == call->owner &&
                p->joints[i].subtype == call->subtype)
                p->joints[i].live = 0;
        return 0;
    case MU_JT_CALL_EFFECT:
        mu_world_particles_effect(p, call->type, call->subtype, call->position, call->angle, call->light,
                                  call->owner == -2 ? -1 : call->owner, 0.0f, NULL);
        return 0;
    case MU_SFX_CALL_ANIMATION: {
        /* viewer choice: the model's first action advances by the effect's speed and loops */
        int16_t keys = 1;
        if (e) {
            sfx_model(p, e->type, e->action, &keys);
            e->frame = e->frame + e->velocity;
            if (keys > 1 && e->frame >= (float)keys)
                e->frame = e->frame - (float)keys;
        }
        return 1;
    }
    case MU_SFX_CALL_ATTRIBUTE: {
        if (!p->map)
            return 0;
        const int32_t index = ((call->range & 0xff) << 8) + (call->subtype & 0xff);   /* TERRAIN_INDEX 0x016d34db */
        return p->map->attributes[index];
    }
    case MU_SFX_CALL_SOUND:
        p->stats.sounds++;
        return 0;
    default:
        return 0;
    }
}

int32_t mu_world_particles_joint(mu_world_particles *p, int32_t type, const float position[3],
                                 const float target_position[3], const float angle[3], int32_t subtype, int32_t target,
                                 float scale, uint16_t key, uint16_t skill, uint8_t byte10, uint16_t word13,
                                 int32_t arg14, const float *creation_light)
{
    if (!p->joints)
        return -1;
    mu_jt_env env;
    joint_env(p, &env);
    if (creation_light) memcpy(env.creation_light, creation_light, sizeof env.creation_light);
    const int32_t i = mu_joints_create(p->joints, MU_JT_JOINTS, type, position, target_position, angle, subtype,
                                       target, scale, key, skill, byte10, word13, arg14, &env);
    if (i >= 0)
        p->stats.joints_created++;
    else if (i == -2)
        p->stats.joints_unsupported++;
    else
        p->stats.joints_full++;
    p->stats.joints++;
    return i;
}

int mu_world_particles_effect(mu_world_particles *p, int32_t type, int32_t subtype, const float position[3],
                              const float angle[3], const float light[3], int32_t owner, float scale,
                              const mu_sfx_info *info)
{
    p->stats.effects++;
    if (!p->effects)
        return 0;
    for (int i = 0; i < MU_WORLD_FX_EFFECTS; ++i) {   /* the first free record of the 200 (0x013c0f46) */
        mu_sfx_effect *e = &p->effects[i];
        if (e->live)
            continue;
        mu_sfx_env env;
        effect_env(p, &env);
        float creation_light[3];
        memcpy(creation_light, light, sizeof creation_light);
        if (mu_sfx_effect_create(e, type, subtype, position, angle, creation_light, owner, scale, info, &env)) {
            p->stats.effects_created++;
            return 1;
        }
        p->stats.effects_unsupported++;
        return 0;
    }
    p->stats.effects_full++;
    return 0;
}

void mu_world_particles_discard_sprites(mu_world_particles *p)
{
    for (int32_t i = 0; p->sprites && i < MU_PT_SPRITES; ++i)
        p->sprites->records[i].live = 0;
}

void mu_world_particles_set_hero(mu_world_particles *p, const float position[3])
{
    memcpy(p->hero_position, position, sizeof p->hero_position);
    p->has_hero = 1;
}

int32_t mu_world_particles_live_joints(const mu_world_particles *p)
{
    return p->joints ? mu_joints_live(p->joints, MU_JT_JOINTS) : 0;
}

int32_t mu_world_particles_live_effects(const mu_world_particles *p)
{
    int32_t n = 0;
    for (int i = 0; p->effects && i < MU_WORLD_FX_EFFECTS; ++i)
        n += p->effects[i].live != 0;
    return n;
}

void mu_world_particles_step(mu_world_particles *p, float world_time)
{
    p->world_time = world_time;
    p->light_count = 0;
    if (p->effects) {   /* MoveEffects 0x0150ddb1 */
        mu_sfx_env env;
        effect_env(p, &env);
        for (int i = 0; i < MU_WORLD_FX_EFFECTS; ++i)
            if (p->effects[i].live && !mu_sfx_effect_move(&p->effects[i], &env))
                p->effects[i].live = 0;
    }
    if (p->joints) {    /* MoveJoints 0x01589b06 */
        mu_jt_env env;
        joint_env(p, &env);
        mu_joints_move_all(p->joints, MU_JT_JOINTS, &env, 0.1f, NULL, NULL);
        p->stats.live_joints = (uint32_t)mu_world_particles_live_joints(p);
        if (p->stats.live_joints > p->stats.max_joints)
            p->stats.max_joints = p->stats.live_joints;
        p->stats.live_effects = (uint32_t)mu_world_particles_live_effects(p);
    }
    mu_pt_host h;
    host(p, &h);
    mu_pt_move_all(&p->list, &h);
    p->stats.steps++;
    p->stats.live = (uint32_t)p->list.count;
    if (p->stats.live > p->stats.max_live)
        p->stats.max_live = p->stats.live;
}

void mu_world_particles_apply_lights(const mu_world_particles *p, mu_world *map)
{
    for (int32_t i = 0; map && i < p->light_count; ++i) {
        const mu_world_fx_light *l = &p->lights[i];
        mu_world_add_light(map, l->x, l->y, l->rgb, l->range);
    }
}

/* ---- the GL stream through a render backend ---- */

typedef struct draw_context {
    mu_world_particles *p;
    const mu_world_particles_target *target;
    mu_meshdraw_state state;
    int32_t slot;
    int32_t mode;
    float color[4];
    float uv[4][2];
    float v[4][3];
    int32_t corners;
    int32_t pending_uv;
    long quads;
    /* shadows */
    const mu_render_backend *backend;
    float shadow_rgba[4];
    int32_t shadow_vertices;
    int shadow_open;
} draw_context;

static void apply_state(mu_meshdraw_state *s, int32_t wrapper, int32_t argument)
{
    switch (wrapper) {
    case MU_PT_STATE_ADD:          /* 0x0184aa2b */
        s->blend = 1;
        s->src = MU_GL_ONE;
        s->dst = MU_GL_ONE;
        s->depth_mask = 0;
        s->alpha_test = 0;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_SUBTRACT:     /* 0x0184aab7 */
        s->blend = 1;
        s->src = MU_GL_ZERO;
        s->dst = MU_GL_ONE_MINUS_SRC_COLOR;
        s->depth_mask = 0;
        s->alpha_test = 0;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_ADD_INVERSE:  /* 0x0184ab46 */
        s->blend = 1;
        s->src = MU_GL_ONE_MINUS_SRC_COLOR;
        s->dst = MU_GL_ONE;
        s->depth_mask = 0;
        s->alpha_test = 0;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_ALPHA:        /* 0x0184a990(arg): the depth mask is turned on only for arg != 0 */
        s->blend = 1;
        s->src = MU_GL_SRC_ALPHA;
        s->dst = MU_GL_ONE_MINUS_SRC_ALPHA;
        if (argument)
            s->depth_mask = 1;
        s->alpha_test = 1;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_OPAQUE:       /* 0x0184a7f3 */
        s->blend = 0;
        s->depth_mask = 1;
        s->alpha_test = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_BLEND:        /* 0x0184abd5 (NATIVE-HELPERS-002: smoke02) */
        s->blend = 1;
        s->src = MU_GL_SRC_ALPHA;
        s->dst = MU_GL_ONE_MINUS_SRC_ALPHA;
        s->depth_mask = 0;
        s->alpha_test = 0;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_UNTEXTURED:   /* 0x0184a783(0) */
        s->depth_mask = 1;
        s->alpha_test = 0;
        s->texture = 0;
        break;
    case MU_PT_STATE_DEPTH_OFF:
        s->depth_mask = 0;
        break;
    case MU_PT_STATE_DEPTH_ON:
        s->depth_mask = 1;
        break;
    default:
        break;
    }
}

static void g_state(void *c, int32_t wrapper, int32_t argument)
{
    apply_state(&((draw_context *)c)->state, wrapper, argument);
}

static void g_bind(void *c, int32_t bitmap)
{
    draw_context *d = c;
    const int32_t s = slot_of(bitmap);
    d->slot = s >= 0 && d->p->bitmap_present[s] ? s : -1;
}

static void g_begin(void *c, int32_t mode)
{
    draw_context *d = c;
    d->mode = mode;
    d->corners = 0;
    d->color[0] = d->color[1] = d->color[2] = d->color[3] = 1.0f;
}

static void g_color3(void *c, const float rgb[3])
{
    draw_context *d = c;
    d->color[0] = rgb[0];
    d->color[1] = rgb[1];
    d->color[2] = rgb[2];
    d->color[3] = 1.0f;
}

static void g_color4(void *c, float r, float g, float b, float a)
{
    draw_context *d = c;
    d->color[0] = r;
    d->color[1] = g;
    d->color[2] = b;
    d->color[3] = a;
}

static void g_tex(void *c, float u, float v)
{
    draw_context *d = c;
    if (d->corners < 4) {
        d->uv[d->corners][0] = u;
        d->uv[d->corners][1] = v;
    }
}

static void g_vertex(void *c, const float v[3])
{
    draw_context *d = c;
    if (d->corners < 4) {
        d->v[d->corners][0] = v[0];
        d->v[d->corners][1] = v[1];
        d->v[d->corners][2] = v[2];
        d->corners++;
    }
}

/* view space back to world space: x = R^T (v - t) (the camera rows are orthonormal) */
static void to_world(const float camera[12], const float v[3], float out[3])
{
    for (int k = 0; k < 3; ++k) {
        float s = 0.0f;
        for (int r = 0; r < 3; ++r)
            s += camera[4 * r + k] * (v[r] - camera[4 * r + 3]);
        out[k] = s;
    }
}

static void g_end(void *c)
{
    draw_context *d = c;
    if (d->mode != MU_PT_GL_QUADS || d->corners != 4 || d->slot < 0)
        return;
    mu_render_backend b;
    if (d->target->backend(d->target->context, d->p, &b))
        return;
    mu_meshdraw_state s = d->state;
    s.texture = 1;
    s.depth_test = 1;
    b.prepare(b.context, &s, d->slot);
    b.begin(b.context);
    static const int order[6] = {0, 1, 2, 0, 2, 3};
    for (int i = 0; i < 6; ++i) {
        float w[3];
        to_world(d->p->camera, d->v[order[i]], w);
        b.sink.texcoord(b.sink.context, d->uv[order[i]][0], d->uv[order[i]][1]);
        b.sink.color4(b.sink.context, d->color[0], d->color[1], d->color[2], d->color[3]);
        b.sink.vertex(b.sink.context, w);
    }
    b.end(b.context);
    d->quads++;
}

static int bitmap_info(void *c, int32_t bitmap, mu_pt_bitmap *out)
{
    const mu_world_particles *p = c;
    const int32_t s = slot_of(bitmap);
    if (s < 0 || !p->bitmap_present[s])
        return 0;
    out->width = (float)p->bitmaps.images[s].width;     /* +0x204: the uploaded size */
    out->height = (float)p->bitmaps.images[s].height;   /* +0x208 */
    out->components = p->bitmaps.components[s];          /* +0x214 */
    return 1;
}

/* RenderJoints(0) (NATIVE-JOINT-001): the joints' quads in world space, in the state of their render type. */
static long draw_joints(mu_world_particles *p, const mu_world_particles_target *t)
{
    if (!p->joints || !p->joint_quads)
        return 0;
    const int32_t n = mu_joints_quads(p->joints, MU_JT_JOINTS, 0, p->world_time, p->joint_quads, MU_WORLD_FX_QUADS);
    p->stats.drawn_joint_quads = (uint32_t)n;
    long drawn = 0;
    for (int32_t i = 0; i < n; ++i) {
        const mu_joint_quad *q = &p->joint_quads[i];
        const int32_t s = slot_of(q->bitmap);
        if (s < 0 || !p->bitmap_present[s])
            continue;
        mu_render_backend b;
        if (t->backend(t->context, p, &b))
            return drawn;
        mu_meshdraw_state state;
        mu_meshdraw_state_defaults(&state);
        mu_joints_state(q->render_type, &state);
        state.depth_test = 1;
        b.prepare(b.context, &state, s);
        b.begin(b.context);
        static const int order[6] = {0, 1, 2, 0, 2, 3};
        for (int k = 0; k < 6; ++k) {
            b.sink.texcoord(b.sink.context, q->uv[order[k]][0], q->uv[order[k]][1]);
            b.sink.color4(b.sink.context, q->color[0], q->color[1], q->color[2], 1.0f);
            b.sink.vertex(b.sink.context, q->position[order[k]]);
        }
        b.end(b.context);
        ++drawn;
    }
    return drawn;
}

/* ---- NATIVE-HELPERS-002: effects drawn as terrain decals (RenderTerrainAlphaBitmap 0x016cdd5f) ---- */

typedef struct decal_draw {
    mu_world_particles *p;
    const mu_world_particles_target *t;
    int32_t slot, mode, n;
    float color[4], uv[2];
    float fan[64][5];
    long fans;
} decal_draw;

static void ds_state(void *c, int32_t state, int32_t argument)
{
    (void)c, (void)state, (void)argument;   /* the caller chose the blend (EnableAlphaBlend) */
}

static void ds_bind(void *c, int32_t texture)
{
    decal_draw *d = c;
    const int32_t s = slot_of(texture);
    d->slot = s >= 0 && d->p->bitmap_present[s] ? s : -1;
}

static void ds_begin(void *c, int32_t mode)
{
    decal_draw *d = c;
    d->mode = mode;
    d->n = 0;
}

static void ds_tex(void *c, float u, float v)
{
    decal_draw *d = c;
    d->uv[0] = u;
    d->uv[1] = v;
}

static void ds_color3(void *c, const float rgb[3])
{
    decal_draw *d = c;
    d->color[0] = rgb[0], d->color[1] = rgb[1], d->color[2] = rgb[2], d->color[3] = 1.0f;
}

static void ds_color4(void *c, float r, float g, float b, float a)
{
    decal_draw *d = c;
    d->color[0] = r, d->color[1] = g, d->color[2] = b, d->color[3] = a;
}

static void ds_vertex(void *c, const float xyz[3])
{
    decal_draw *d = c;
    if (d->n < 64) {
        float *v = d->fan[d->n++];
        v[0] = xyz[0], v[1] = xyz[1], v[2] = xyz[2], v[3] = d->uv[0], v[4] = d->uv[1];
    }
}

static void ds_end(void *c)
{
    decal_draw *d = c;
    if (d->slot < 0 || d->n < 3)
        return;
    mu_render_backend b;
    if (d->t->backend(d->t->context, d->p, &b))
        return;
    mu_meshdraw_state s;
    mu_meshdraw_state_defaults(&s);
    apply_state(&s, MU_PT_STATE_ADD, 0);   /* EnableAlphaBlend 0x0184aa2b before the decal */
    s.depth_test = 1;
    b.prepare(b.context, &s, d->slot);
    b.begin(b.context);
    for (int32_t i = 1; i + 1 < d->n; ++i) {   /* the GL_TRIANGLE_FAN as triangles */
        const int32_t k[3] = {0, i, i + 1};
        for (int j = 0; j < 3; ++j) {
            const float *v = d->fan[k[j]];
            b.sink.texcoord(b.sink.context, v[3], v[4]);
            b.sink.color4(b.sink.context, d->color[0], d->color[1], d->color[2], d->color[3]);
            b.sink.vertex(b.sink.context, v);
        }
    }
    b.end(b.context);
    d->fans++;
}

static int decal_texture_size(void *c, int32_t texture, float *width, float *height)
{
    const mu_world_particles *p = c;
    const int32_t s = slot_of(texture);
    if (s < 0 || !p->bitmap_present[s])
        return 0;
    *width = (float)p->bitmaps.images[s].width;
    *height = (float)p->bitmaps.images[s].height;
    return 1;
}

/* The flying step's shock ring 0x8012 (RenderTerrainEffects 0x0150f00e, default branch 0x015158df: outside the
 * worlds 0x18..0x1d / 0x24) and Fenrir's paw marks 0x4ad (RenderEffects 0x0151a680: 0x7ff4 + frame % 5, 0.6 wide). */
static long draw_effect_decals(mu_world_particles *p, const mu_world_particles_target *t)
{
    if (!p->map || !p->effects || !t)
        return 0;
    mu_terrain_scene scene;
    mu_world_scene((mu_world *)p->map, &scene);
    scene.texture_size = decal_texture_size;
    scene.texture_context = p;
    decal_draw d;
    memset(&d, 0, sizeof d);
    d.p = p;
    d.t = t;
    d.slot = -1;
    const mu_terrain_sink sink = {&d, ds_state, ds_bind, ds_begin, ds_tex, ds_color3, ds_color4, ds_vertex, ds_end};
    const int32_t w = p->world;
    for (int32_t i = 0; i < MU_WORLD_FX_EFFECTS; ++i) {
        const mu_sfx_effect *e = &p->effects[i];
        if (!e->live)
            continue;
        mu_sfx_decal a;
        if (mu_sfx_effect_decal(e, w, &a)) {
            /* 0x00deec1f uses a separate signed-integer height grid (50-unit cells, +400),
             * which this world loader does not recover. Do not substitute ordinary terrain or z=0. */
            if (a.flat) continue;
            mu_terrain_decal(&scene, a.texture, e->position[0], e->position[1], a.size, a.size,
                             a.light, a.rotation, 1.0f, 5.0f, 1, 0, &sink);
        }
    }
    p->stats.drawn_decals = (uint32_t)d.fans;
    p->stats.decals_total += (uint64_t)d.fans;
    return d.fans;
}

long mu_world_particles_draw(mu_world_particles *p, const float modelview[16], const mu_world_particles_target *t)
{
    draw_effect_decals(p, t);   /* NATIVE-HELPERS-002 */
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 4; ++j)
            p->camera[4 * i + j] = modelview[4 * j + i];   /* 0x0184a569: CameraMatrix[i][j] = gl[4j + i] */
    const long joints = draw_joints(p, t);
    draw_context d;
    memset(&d, 0, sizeof d);
    d.p = p;
    d.target = t;
    d.slot = -1;
    d.quads = joints;
    mu_meshdraw_state_defaults(&d.state);
    d.state.depth_mask = 0;
    mu_pt_gl gl = {&d, g_state, g_bind, g_begin, g_end, g_color3, g_color4, g_tex, g_vertex, NULL, NULL};
    mu_pt_sprites_mark_visible(p->sprites);   /* 0x01692887 */
    const int32_t sprites = mu_pt_sprites_render(p->sprites, 0, p->world_time, p->camera, bitmap_info, p, &gl,
                                                 NULL, NULL);
    const int32_t particles = mu_pt_render_all(&p->list, 0, p->camera, p->world_time, bitmap_info, p, &gl);
    p->stats.drawn_sprites = (uint32_t)sprites;
    p->stats.drawn_particles = (uint32_t)particles;
    p->stats.shadows = p->stats.pending_shadows;   /* the frame's RenderBoids/RenderFishs ran before the sprite pass */
    p->stats.shadow_vertices = p->stats.pending_shadow_vertices;
    p->stats.pending_shadows = p->stats.pending_shadow_vertices = 0;
    return d.quads;
}

typedef struct raster_target {
    mu_raster *raster;
    mu_render_backend backend;
} raster_target;

static int raster_backend(void *c, const mu_world_particles *p, mu_render_backend *out)
{
    raster_target *t = c;
    t->raster->textures = p->bitmaps.slots;
    t->raster->texture_count = p->bitmaps.count;
    t->raster->texture_filter = p->bitmaps.filter;
    t->raster->texture_wrap = p->bitmaps.wrap;
    *out = t->backend;
    return 0;
}

long mu_world_particles_draw_raster(mu_world_particles *p, mu_raster *raster, const float modelview[16])
{
    raster_target t = {raster, {0}};
    mu_raster_backend(raster, &t.backend);
    const int linear = raster->linear;
    raster->linear = 1;
    mu_world_particles_target target = {&t, raster_backend};
    long n = mu_world_particles_draw(p, modelview, &target);
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    raster->linear = linear;
    return n;
}

/* ---- effect models (NATIVE-JOINT-001) ---- */

/* RenderEffects 0x0151e980 for stardr02 (static reading): Animation, PlayAnimation(velocity) in the render pass,
 * the Spark04 flash while 20 < LifeTime < 25, light and scale */
static void glint_render(mu_world_particles *p, mu_sfx_effect *e)
{
    mu_world_fx_model *m = fx_model_of(p, e->type);
    if (!m)
        return;
    const int32_t keys = m->bmd.action_count > 0 ? m->bmd.actions[0].keys : 1;
    e->frame = e->frame + e->velocity;   /* the module's PlayAnimation (viewer choice: loops) */
    if (keys > 1 && e->frame >= (float)keys)
        e->frame = e->frame - (float)keys;
    if (e->lifetime > 0x14 && e->lifetime < 0x19) {
        const float light[3] = {0.8f, 0.8f, 1.0f};
        mu_world_particles_sprite(p, 0x8155, e->position, 0.7f, light, -1, 0.0f, 0, 4);
        e->light[0] = e->light[1] = e->light[2] = 0.6f;
        if (e->subtype == 0)
            e->scale = 0.8f;
        else if (e->subtype == 1)
            e->scale = 0.6f;
    } else if (e->subtype == 0) {
        e->scale = 0.5f;
    } else if (e->subtype == 1) {
        e->scale = 0.3f;
    }
}

int32_t mu_world_particles_draw_models(mu_world_particles *p, mu_world_particles_model_fn draw, void *context)
{
    int32_t drawn = 0;
    for (int i = 0; p->effects && i < MU_WORLD_FX_EFFECTS; ++i) {
        mu_sfx_effect *e = &p->effects[i];
        if (!e->live)
            continue;
        if (e->type == MU_SFX_MODEL_STAR_GLINT)
            glint_render(p, e);
        int32_t slot = -1;
        for (int k = 0; k < MU_WORLD_FX_MODELS; ++k)
            if (p->models[k].type == e->type && p->models[k].loaded)
                slot = k;
        if (slot < 0)
            continue;
        mu_world_fx_model *m = &p->models[slot];
        if (mu_world_warp_type(e->type)) {
            if (!mu_world_warp_render(e, p->frustum ? p->frustum->normal : NULL,
                p->frustum ? p->frustum->d : NULL, 0, m->bmd.mesh_count))
                continue;
        }
        mu_model_params params = m->model.params;
        for (int k = 0; k < 3; ++k) {
            params.origin[k] = e->position[k];
            params.angles[k] = e->angle[k];
            params.color[k] = e->light[k];
        }
        params.body_scale = e->scale;
        params.lighting = e->flag5;   /* +0x05 LightEnable (the tornado clears it; static reading) */
        mu_model_apply_params(&m->model, &params);
        const int32_t keys = m->bmd.action_count > 0 ? m->bmd.actions[0].keys : 1;
        float frame = e->frame;
        if (keys > 0 && frame >= (float)keys)
            frame = 0.0f;
        mu_model_set_state(&m->model, 0, frame, frame, 0);
        if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
            continue;
        /* RenderObject: RenderBody(flags 2, or 0x82 when +0x80 == 0x80, alpha +0xdc, BlendMesh +0x74,
         * BlendMeshLight +0xa8, U +0xac, V +0xb0) (NATIVE-COMBAT-002's static reading) */
        mu_draw_options options;
        mu_draw_default_options(&options);
        options.flags = e->field_80 == 0x80 ? 0x82u : 2u;
        options.alpha = e->alpha;
        options.select = e->blend_mesh;
        options.color_scale = e->blend_light;
        options.u_offset = e->blend_u;
        options.v_offset = e->blend_v;
        options.textures = &m->textures;
        options.time = p->world_time;
        draw(context, &m->model, &m->textures, slot, &options);
        ++drawn;
    }
    p->stats.drawn_effect_models = (uint32_t)drawn;
    return drawn;
}

static void raster_model(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                         const mu_draw_options *options)
{
    mu_raster *raster = context;
    (void)slot;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    raster->textures = textures->slots;
    raster->texture_count = textures->count;
    raster->texture_filter = textures->filter;
    raster->texture_wrap = textures->wrap;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(model, options, &backend, &ds);
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
}

int32_t mu_world_particles_draw_models_raster(mu_world_particles *p, mu_raster *raster)
{
    const int linear = raster->linear;
    raster->linear = 1;
    const int32_t n = mu_world_particles_draw_models(p, raster_model, raster);
    raster->linear = linear;
    return n;
}

/* ---- shadows ---- */

static void s_state(void *c, int32_t wrapper, int32_t argument)
{
    apply_state(&((draw_context *)c)->state, wrapper, argument);
}

static void s_begin(void *c, int32_t mode)
{
    draw_context *d = c;
    const mu_render_backend *b = d->backend;
    if (mode != MU_PT_GL_TRIANGLES || !b)
        return;
    mu_meshdraw_state s = d->state;
    s.texture = 0;
    s.depth_test = 1;
    s.cull = 0;
    b->prepare(b->context, &s, -1);
    b->begin(b->context);
    d->shadow_open = 1;
}

static void s_vertex(void *c, const float v[3])
{
    draw_context *d = c;
    const mu_render_backend *b = d->backend;
    if (!d->shadow_open)
        return;
    b->sink.color4(b->sink.context, d->shadow_rgba[0], d->shadow_rgba[1], d->shadow_rgba[2], d->shadow_rgba[3]);
    b->sink.vertex(b->sink.context, v);
    d->shadow_vertices++;
}

static void s_end(void *c)
{
    draw_context *d = c;
    if (d->shadow_open && d->backend)
        d->backend->end(d->backend->context);
    d->shadow_open = 0;
}

static int32_t shadow_with(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd, const float rgba[4],
                           int32_t state, int32_t z_offset, const mu_render_backend *backend);

int32_t mu_world_particles_shadow(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd, const float rgba[4],
                                  const mu_render_backend *backend)
{
    /* EnableAlphaTest(1) before the call (RenderBoids/RenderFishs, RenderObject's shadow block) */
    return shadow_with(p, model, bmd, rgba, MU_PT_STATE_ALPHA, 0, backend);
}

int32_t mu_world_particles_character_shadow(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd,
                                            const mu_render_backend *backend)
{
    const int32_t w = p->world;
    /* the item render's shadow block 0x0176cfab..0x0176d15b (static reading) */
    if ((w >= 0x18 && w <= 0x1d) || w == 0x24 || w == 0xa || w == 0x84)   /* 0x009b0418, Icarus worlds */
        return 0;
    const int translucent = w == 7 || (w >= 0x80 && w <= 0x82);       /* 0x016a88ae */
    const float black[4] = {0.0f, 0.0f, 0.0f, translucent ? 0.2f : 1.0f};
    return shadow_with(p, model, bmd, black, translucent ? MU_PT_STATE_ALPHA : MU_PT_STATE_OPAQUE,
                       w == 0x8f ? 5 : 0, backend);   /* 0x00e136f3: z offset 5 in world 0x8f */
}

static int32_t shadow_meshes(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd, const float rgba[4],
                             int32_t state, int32_t z_offset, int32_t first, int32_t end,
                             const mu_render_backend *backend);

static int32_t shadow_with(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd, const float rgba[4],
                           int32_t state, int32_t z_offset, const mu_render_backend *backend)
{
    return shadow_meshes(p, model, bmd, rgba, state, z_offset, -1, -1, backend);
}

int32_t mu_world_particles_shadow_range(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd,
                                        const float rgba[4], int32_t first, int32_t end,
                                        const mu_render_backend *backend)
{
    return shadow_meshes(p, model, bmd, rgba, MU_PT_STATE_ALPHA, 0, first, end, backend);
}

static int32_t shadow_meshes(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd, const float rgba[4],
                             int32_t state, int32_t z_offset, int32_t first, int32_t end,
                             const mu_render_backend *backend)
{
    if (!model || !bmd || !backend)
        return 0;
    mu_pt_shadow_mesh meshes[MU_WORLD_PT_SHADOW_MESHES];
    int32_t count = bmd->mesh_count < MU_WORLD_PT_SHADOW_MESHES ? bmd->mesh_count : MU_WORLD_PT_SHADOW_MESHES;
    for (int32_t i = 0; i < count; ++i) {
        const mu_bmd_mesh *m = &bmd->meshes[i];
        meshes[i].triangle_count = (int16_t)m->polygon_count;
        meshes[i].texture = m->texture_index;
        meshes[i].triangles = mu_model_triangles(model, i);
        meshes[i].vertices = mu_model_vertices(model, i);
        meshes[i].vertex_count = m->vertex_count;
    }
    draw_context d;
    memset(&d, 0, sizeof d);
    d.p = p;
    d.backend = backend;
    mu_meshdraw_state_defaults(&d.state);
    apply_state(&d.state, state, 1);
    for (int k = 0; k < 4; ++k)
        d.shadow_rgba[k] = rgba[k];
    mu_pt_gl gl = {&d, s_state, NULL, s_begin, s_end, NULL, NULL, NULL, s_vertex, NULL, NULL};
    mu_pt_host h;
    host(p, &h);
    const float *origin = mu_model_origin(model);
    const int32_t n = mu_pt_render_body_shadow(meshes, count, origin, -1, -1, first, end, z_offset, &h, &gl);
    p->stats.pending_shadows++;
    p->stats.pending_shadow_vertices += (uint32_t)n;
    p->stats.shadows_total++;
    return n;
}

/* ---- bones ---- */

int mu_world_particles_bone_position(const mu_model *model, int32_t bone, const float in[3], float out[3])
{
    const float *bones = model ? mu_model_bone_matrices(model) : NULL;
    if (!bones || !model->bmd || bone < 0 || bone >= model->bmd->bone_count || bone >= MU_MODEL_MAX_BONES)
        return 0;
    /* TransformPosition 0x012b6ef1: bones posed with Animation's translate (static objects, NATIVE-LIGHT-001)
     * already hold the body scale and origin; model-space bones take them here */
    mu_pt_transform_position(bones + 12 * bone, in, out, model->params.pose_translate ? 0 : 1, model->params.body_scale,
                             model->params.origin);
    return 1;
}

int mu_world_particles_named_bone_position(const mu_model *model, const mu_bmd *bmd, const char *name,
                                           const float in[3], float out[3])
{
    if (!model || !bmd || bmd->bone_count <= 0)
        return 0;
    const char *names[MU_MODEL_MAX_BONES];
    int32_t n = bmd->bone_count < MU_MODEL_MAX_BONES ? bmd->bone_count : MU_MODEL_MAX_BONES;
    for (int32_t i = 0; i < n; ++i)
        names[i] = bmd->bones[i].name;
    const int32_t bone = mu_pt_find_bone(names, n, name);
    if (bone < 0)
        return 0;   /* 0x0129f18a returns NULL; TransformPosition then leaves `out` alone */
    return mu_world_particles_bone_position(model, bone, in, out);
}

/* ---- object visuals ---- */

typedef struct visual_context {
    mu_world_particles *p;
    int has_model;
    const mu_model *model;
    const mu_bmd *bmd;
} visual_context;

static int32_t v_rand(void *c) { return mu_world_particles_rand(((visual_context *)c)->p); }

static int v_has_model(void *c, const mu_pt_visual_object *o)
{
    (void)o;
    return ((visual_context *)c)->has_model;
}

static void v_bone(void *c, const mu_pt_visual_object *o, const char *bone, const float in[3], float out[3])
{
    visual_context *v = c;
    (void)o;
    mu_world_particles_named_bone_position(v->model, v->bmd, bone, in, out);
}

/* TransformPosition(BoneTransform + 0x30 * bone, in, out, 0) (Dungeon's lightning, NATIVE-JOINT-001) */
static void v_bone_index(void *c, const mu_pt_visual_object *o, int32_t bone, const float in[3], float out[3])
{
    visual_context *v = c;
    (void)o;
    if (v->model && v->bmd && bone < v->bmd->bone_count)
        mu_world_particles_bone_position(v->model, bone, in, out);
}

static void v_particle(void *c, int32_t type, const float position[3], const float angle[3], const float light[3],
                       int32_t subtype, float scale, int32_t owner)
{
    (void)owner;
    mu_world_particles_create(((visual_context *)c)->p, type, position, angle, light, subtype, scale);
}

static void v_sprite(void *c, int32_t bitmap, const float position[3], float scale, const float light[3],
                     int32_t owner, float rotation, int32_t blend, int32_t axes)
{
    mu_world_particles_sprite(((visual_context *)c)->p, bitmap, position, scale, light, owner, rotation, blend, axes);
}

/* CreateJoint(bitmap, position, position, angle, subtype, the object, scale, -1, 0, 0, -1, 0, -1, 0) of the
 * Tormenta handler (NATIVE-JOINT-001). */
static void v_joint(void *c, int32_t bitmap, const float position[3], const float angle[3], int32_t subtype,
                    int32_t owner, float scale)
{
    mu_world_particles_joint(((visual_context *)c)->p, bitmap, position, position, angle, subtype, owner, scale,
                             0xffff, 0, 0, 0xffff, 0, NULL);
}

/* CreateEffect 0x013c0eaa(type, position, angle, light, subtype, the object, -1, 0, (u16)scale, 0, 0.0, -1,
 * 0, 0): the core with scale 0 and the info block {key -1, skill 0, (u16)(int)scale, 0, -1} (NATIVE-JOINT-001). */
static void v_effect(void *c, int32_t type, const float position[3], const float angle[3], const float light[3],
                     int32_t subtype, int32_t owner)
{
    mu_world_particles *p = ((visual_context *)c)->p;
    mu_sfx_info info;
    memset(&info, 0, sizeof info);
    info.key = 0xffff;
    const uint8_t *img = p->objects ? mu_objects_object_image(p->objects, owner) : NULL;
    if (img) {
        const float scale = mu_obj_f32(img, MU_OBJF_SCALE);
        info.word4 = (uint16_t)(scale > -2147483904.0f && scale < 2147483648.0f ? (int32_t)scale : INT32_MIN);
    }
    info.field8 = 0xffff;
    mu_world_particles_effect(p, type, subtype, position, angle, light, owner, 0.0f, &info);
}

int mu_world_particles_object_visual(mu_world_particles *p, mu_pt_visual_object *object, int has_model,
                                     const mu_model *model, const mu_bmd *bmd)
{
    visual_context v = {p, has_model, model, bmd};
    mu_pt_visual_host h;
    memset(&h, 0, sizeof h);
    h.context = &v;
    h.rand = v_rand;
    h.has_model = v_has_model;
    h.bone_position = v_bone;
    h.particle = v_particle;
    h.sprite = v_sprite;
    h.joint = v_joint;
    h.effect = v_effect;
    h.bone_index_position = v_bone_index;
    h.world = p->world;
    h.world_time = p->world_time;
    const int handled = mu_pt_object_visual(object, &h);
    if (handled)
        p->stats.visuals++;
    return handled;
}

/* ---- hooks ---- */

static void o_particle(void *c, int32_t bitmap, const float position[3], const float angle[3], const float light[3],
                       int32_t subtype, float scale, int32_t owner)
{
    mu_world_particles_create_owned(c, bitmap, position, angle, light, subtype, scale, owner);
}

/* The login world's CreateSprite calls (CGMLogInScene_Ex slot 0x34: the ship's lanterns). */
static void o_sprite(void *c, int32_t bitmap, const float position[3], float scale, const float light[3],
                     int32_t owner, float rotation, int32_t blend, int32_t axes)
{
    mu_world_particles_sprite(c, bitmap, position, scale, light, owner, rotation, blend, axes);
}

/* The character-select world's CreateEffect calls (CGMCharacterScene_Ex slot 0x34, NATIVE-CHARSEL-002): the
 * wrapper 0x013c0eaa(type, position, angle, light, subtype, the object, -1, 0, 0, 0, 0.0, -1, 0, 0), i.e. the
 * core with scale 0 and the info block {key -1, skill 0, word4 0, 0, -1}. */
static void o_effect(void *c, int32_t type, int32_t subtype, const float position[3], const float angle[3],
                     const float light[3], int32_t owner)
{
    mu_sfx_info info;
    memset(&info, 0, sizeof info);
    info.key = 0xffff;
    info.field8 = 0xffff;
    mu_world_particles_effect(c, type, subtype, position, angle, light, owner, 0.0f, &info);
}

static void o_effect_scaled(void *c, int32_t type, int32_t subtype, const float position[3],
                            const float angle[3], const float light[3], int32_t owner, float scale)
{
    mu_sfx_info info = {0};
    info.key = 0xffff; info.field8 = 0xffff;
    mu_world_particles_effect(c, type, subtype, position, angle, light, owner, scale, &info);
}

/* Icarus consumes the authored visual events here, keeping object-only tools independent of UI hosts. */
static void icarus_cover(mu_world_particles *p, mu_objects *o, int32_t index)
{
    mu_obj_event events[20]; mu_obj_log log = {0, 20, 0, events};
    (void)mu_world_particles_rand(p); /* RenderObjectVisual's common brightness. */
    mu_icarus_cover(mu_objects_object_image(o, index), index, &log);
    for (int i = 0; i < log.count; ++i) {
        const mu_obj_event *e = &events[i];
        float pos[3], angle[3], light[3], scale;
        memcpy(pos, e->args + 1, 12); memcpy(angle, e->args + 4, 12);
        memcpy(light, e->args + 7, 12); memcpy(&scale, e->args + 11, 4);
        mu_world_particles_create_owned(p, 0x7f89, pos, angle, light, (int32_t)e->args[10], scale, index);
    }
}

static void o_visual(void *c, struct mu_objects *o, int32_t index, int has_model, mu_object_model *m)
{
    mu_world_particles *p = c;
    uint8_t *img = mu_objects_object_image(o, index);
    if (!img)
        return;
    if (o->world == 10) {
        if (has_model) icarus_cover(p, o, index);
        return;
    }
    mu_pt_visual_object v;
    memset(&v, 0, sizeof v);
    v.index = index;
    v.type = mu_obj_i32(img, MU_OBJF_TYPE);
    memcpy(v.position, img + MU_OBJF_POSITION, 12);
    memcpy(v.angle, img + MU_OBJF_ANGLE, 12);
    memcpy(v.light, img + MU_OBJF_LIGHT, 12);
    v.scale = mu_obj_f32(img, MU_OBJF_SCALE);
    v.blend_light = mu_obj_f32(img, MU_OBJF_BLEND_LIGHT);
    v.blend_v = mu_obj_f32(img, MU_OBJF_BLEND_V);
    if (p->map)
        p->world_time = p->map->time;   /* 0x06fce370 */
    if (!mu_world_particles_object_visual(p, &v, has_model, m ? &m->model : NULL, m ? &m->bmd : NULL)) {
        mu_obj_visual(img, o->world, p->world_time);   /* other worlds: the reconstructed scroll part */
        return;
    }
    memcpy(img + MU_OBJF_LIGHT, v.light, 12);
    mu_obj_set_f32(img, MU_OBJF_BLEND_LIGHT, v.blend_light);
    mu_obj_set_f32(img, MU_OBJF_BLEND_V, v.blend_v);
}

static void o_joint(void *c,int32_t type,const float p[3],const float t[3],const float a[3],int32_t sub,int32_t owner,float scale)
{
    mu_world_particles_joint(c,type,p,t,a,sub,owner,scale,0xffff,0,0,0xffff,0,NULL);
}

void mu_world_particles_attach(mu_world_particles *p, struct mu_objects *objects, struct mu_world_env *env)
{
    if (objects) {
        objects->rt.particle = o_particle;
        objects->rt.visual = o_visual;
        objects->rt.sprite = o_sprite;
        objects->rt.effect = o_effect;
        objects->rt.effect_scaled = o_effect_scaled;
        objects->rt.joint = o_joint;
        objects->rt.hook_context = p;
        p->objects = objects;
    }
    p->environment = env;
    if (env) {
        env->particles = p;
    }
}
