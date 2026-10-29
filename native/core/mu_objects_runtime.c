#include "../../reconstructed/objects/world_visual.h"
/* The client's world-object lifecycle in the native session (NATIVE-OBJECTS-002,
 * docs/research/client-objects-render.md): CreateObject, MoveObjects/MoveObject per logic step,
 * RenderObjects/RenderObject per frame, through reconstructed/objects/object_render.c. The
 * calls those routines log are carried out here: the animation tick through the object's model,
 * AddTerrainLight on the frame light, RenderBody through the mesh-draw port. CreateParticle is a
 * labelled stand-in (mu_object_particle). */
#include "mu_objects.h"
#include "mu_objects_icarus.h"
#include "mu_objects_worlds_p.h"

#include "../../reconstructed/environment/env.h"

#include "../../reconstructed/objects/login_world.h"
#include "../../reconstructed/objects/charsel_world.h"
#include "../../reconstructed/objects/worlds_g.h"
#include "../../reconstructed/objects/worlds_h.h"
#include "../../reconstructed/objects/worlds_i.h"
#include "../../reconstructed/objects/worlds_p.h"
#include "../../reconstructed/objects/worlds_o.h"
#include "../../reconstructed/objects/worlds_r.h"
#include "../../reconstructed/objects/worlds_n.h"
#include "../../reconstructed/objects/worlds_p2.h"
#include "../../reconstructed/objects/worlds_r2.h"
#include "../../reconstructed/joints/joints.h"
#include "../../reconstructed/objects/icarus.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *image(mu_objects *o, int32_t i) { return o->rt.images + (size_t)i * MU_OBJ_SIZE; }

static float fbits(uint32_t u)
{
    float v;
    memcpy(&v, &u, 4);
    return v;
}

static int32_t objects_rand(void *c) { return mu_obj_msvc_rand(&((mu_objects *)c)->rt.seed); }   /* RENDER-WORLDS-R */

static void runtime_free(mu_objects_runtime *rt)
{
    free(rt->images);
    free(rt->pointers);
    free(rt->next);
    free(rt->events);
    free(rt->draw_list);
    free(rt->after_list);
    mu_image_free(&rt->fire);
    mu_image_free(&rt->smoke);
    for (int32_t i = 0; i < rt->bitmap_count; ++i)
        mu_image_free(&rt->bitmaps[i]);
    rt->bitmap_count = 0;
    rt->after_list = NULL;
    rt->images = NULL;
    rt->pointers = NULL;
    rt->next = NULL;
    rt->events = NULL;
    rt->draw_list = NULL;
    rt->ready = 0;
}

/* Effect bitmaps as 0x018202xx loads them (GL_LINEAR, GL_CLAMP): .jpg names resolve to the
 * installed .OZJ through mu_image_resolve. */
static void load_bitmap(const char *root, const char *name, mu_image *out)
{
    char directory[2048], path[4096], message[256];
    if (root && mu_objects_resolve(root, "Data/Effect", directory, sizeof directory) &&
        mu_image_resolve(directory, name, path, sizeof path))
        mu_image_load_file(path, out, message, sizeof message);
}

void mu_objects_runtime_free(mu_objects *o) { runtime_free(&o->rt); }

/* Worlds whose HiddenMesh writes are all reconstructed (creation, move and visual cases): no sidecar there. */
static int runtime_hides_modelled(int32_t world)
{
    return world == 0 || world == 0x8d || world == MU_LOGIN_WORLD || world == MU_CSW_WORLD;
}

/* RENDER-WORLDS-Q: the type's client-layout action table inside its native model window. */
static uint8_t *q_actions(void *context, int32_t type, int32_t *count)
{
    mu_objects *o = context;
    static uint8_t empty[16];
    *count = 0;
    if (type < 0 || type >= MU_OBJECT_TYPES || !o->models[type] || !o->models[type]->loaded)
        return NULL;
    mu_model *m = &o->models[type]->model;
    *count = o->models[type]->bmd.action_count;
    uint8_t *table = *count > 0 ? mu_model_host(m, m->actions, 16u * (uint32_t)*count) : NULL;
    if (!table)
        *count = 0;
    return table ? table : empty;
}

static int32_t q_rand(void *context) { return mu_obj_msvc_rand(&((mu_objects *)context)->rt.seed); }

static mu_q_inputs q_inputs(mu_objects *o, const float hero[3], float time)
{
    mu_q_inputs q;
    memset(&q, 0, sizeof q);
    q.world = o->world;
    q.time = time;
    q.frame_time = 0.1f;   /* 0x01cf103c, as the render pass */
    q.now_ms = o->rt.now_ms;
    if (hero) {
        memcpy(q.hero, hero, sizeof q.hero);
        q.hero_tile[0] = (int32_t)(hero[0] / 100.0f);
        q.hero_tile[1] = (int32_t)(hero[1] / 100.0f);
    }
    q.actions = q_actions;
    q.rand_fn = q_rand;
    q.context = o;
    q.handler = &o->rt.q_handler;
    return q;
}

int mu_objects_start(mu_objects *o, const char *game_root)
{
    mu_objects_runtime *rt = &o->rt;
    float velocity[MU_OBJECT_TYPES];
    uint8_t velocity_set[MU_OBJECT_TYPES];
    const int32_t velocity_types = rt->velocity_types;
    memcpy(velocity, rt->velocity, sizeof velocity);
    memcpy(velocity_set, rt->velocity_set, sizeof velocity_set);
    runtime_free(rt);
    memset(rt, 0, sizeof *rt);
    memcpy(rt->velocity, velocity, sizeof velocity);
    memcpy(rt->velocity_set, velocity_set, sizeof velocity_set);
    rt->velocity_types = velocity_types;
    const int32_t n = o->count > 0 ? o->count : 0;
    rt->q_handler.swamp_variant = 1;   /* Swamp of Darkness constructor (0x00e54359: +0x78 = 1) */
    rt->images = calloc((size_t)(n ? n : 1), MU_OBJ_SIZE);
    rt->pointers = calloc((size_t)(n ? n : 1), sizeof *rt->pointers);
    rt->next = calloc((size_t)(n ? n : 1), sizeof *rt->next);
    rt->event_capacity = 4 * n + 4096;
    rt->events = calloc((size_t)rt->event_capacity, sizeof *rt->events);
    rt->draw_list = calloc((size_t)(n ? n : 1), sizeof *rt->draw_list);
    rt->after_list = calloc((size_t)(n ? n : 1), sizeof *rt->after_list);
    if (!rt->images || !rt->pointers || !rt->next || !rt->events || !rt->draw_list || !rt->after_list) {
        runtime_free(rt);
        return 1;
    }
    int32_t tail[MU_OBJ_SECTORS];
    for (int32_t s = 0; s < MU_OBJ_SECTORS; ++s)
        rt->world.head[s] = tail[s] = -1;
    for (int32_t i = 0; i < n; ++i) {
        uint8_t *img = image(o, i);
        rt->pointers[i] = img;
        rt->next[i] = -1;
        mu_obj_set_f32(img, MU_OBJF_ALPHA_RATE, 0.1f);   /* constructor 0x0129e792 (live value) */
        int32_t sector = -1;
        mu_obj_event created[8];
        mu_obj_log create_log = {0, 8, 0, created};
        int status = mu_obj_create(&o->records[i], o->world, img, &sector, i, &create_log);
        if (status == MU_OBJ_UNSUPPORTED && mu_worlds_q_owns(o->world)) {   /* RENDER-WORLDS-Q slot 0x2c */
            const mu_q_inputs q = q_inputs(o, NULL, 0.0f);
            mu_worlds_q_create(img, i, &q, &create_log);
            status = MU_OBJ_OK;
        }
        for (int32_t k = 0; k < create_log.count; ++k)   /* a handler's PlaySpeed write (login world type 5) */
            if (created[k].call == MU_OBJ_CALL_PLAY_SPEED &&
                (created[k].args[1] == 0 || created[k].args[1] == MU_OBJ_PLAY_SPEED_ALL) &&
                created[k].args[0] < MU_OBJECT_TYPES) {
                rt->play_speed[created[k].args[0]] = fbits(created[k].args[2]);
                rt->play_speed_set[created[k].args[0]] = created[k].args[1] ? 2 : 1;   /* 2: every action */
            } else if (created[k].call == MU_OBJ_CALL_MODEL_STREAM) {
                ++rt->create_unsupported;   /* Ignis StreamMesh byte: no native consumer (RENDER-WORLDS-P2) */
            }
        for (int32_t k = 0; k < create_log.count; ++k)   /* RENDER-WORLDS-P deferred class create */
            if (created[k].call == MU_WP_CREATE)
                mu_objects_worlds_p_create(o, i);
        for (int32_t k = 0; k < create_log.count; ++k)   /* RENDER-WORLDS-R deferred Scorched Canyon create */
            if (created[k].call == MU_WR_CREATE)
                mu_scorched_canyon_create(img, o->world, objects_rand, o);
        for (int32_t k = 0; k < create_log.count; ++k)
            if ((o->world == 2 || o->world == 3 || o->world == 57 || o->world == 58) &&
                created[k].call == MU_OBJ_CALL_CREATE_EFFECT && rt->startup_effect_count < 12)
                rt->startup_effects[rt->startup_effect_count++] = created[k];
        if (status == MU_OBJ_SKIPPED) {
            ++rt->outside;
            continue;
        }
        if (status == MU_OBJ_UNSUPPORTED)
            ++rt->create_unsupported;
        if (status == MU_OBJ_UNSUPPORTED || !runtime_hides_modelled(o->world)) {
            /* live sidecar: types the running client marked HiddenMesh -2. Outside Lorencia, Tormenta and the two
             * scene worlds most of them are set at draw time (emitter markers, NATIVE-FIDELITY-002), which is not
             * ported; CreateObject's own -2 cases are already applied. One-shot visual producers
             * must retain their fresh state until their first draw, as in Icarus C2 and Tarkan K. */
            const int32_t t = o->records[i].type;
            if (t >= 0 && t < MU_OBJECT_TYPES && o->hidden_type[t] &&
                !(o->world == 10 && t <= 5) && !(o->world == 8 && t == 60))
                mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -2);
        }
        const int32_t t = o->records[i].type;
        if (t >= 0 && t < MU_OBJECT_TYPES && rt->velocity_set[t])
            mu_obj_set_f32(img, MU_OBJF_VELOCITY, rt->velocity[t]);   /* live sidecar */
        if (rt->world.head[sector] < 0)
            rt->world.head[sector] = i;
        else
            rt->next[tail[sector]] = i;
        tail[sector] = i;
        ++rt->created;
    }
    rt->world.objects = rt->pointers;
    rt->world.count = n;
    rt->world.next = rt->next;
    rt->seed = 1;
    load_bitmap(game_root, "Fire01.jpg", &rt->fire);
    load_bitmap(game_root, "smoke01.jpg", &rt->smoke);
    if (o->world == MU_LOGIN_WORLD) {   /* the login world's sprite and particle bitmaps (startup loader) */
        static const struct { int32_t id; const char *name; } b[] = {
            {MU_LOGIN_BITMAP_SHINY02, "Shiny02.jpg"}, {MU_LOGIN_BITMAP_FLARE01, "flare01.jpg"},
            {MU_LOGIN_BITMAP_CLOUDS, "clouds.jpg"}, {MU_LOGIN_BITMAP_WATERFALL, "WATERFALL1.jpg"}};
        for (size_t k = 0; k < sizeof b / sizeof b[0] && rt->bitmap_count < MU_OBJECT_BITMAPS; ++k) {
            rt->bitmap_ids[rt->bitmap_count] = b[k].id;
            load_bitmap(game_root, b[k].name, &rt->bitmaps[rt->bitmap_count]);
            ++rt->bitmap_count;
        }
    }
    rt->ready = 1;
    return 0;
}

int32_t mu_objects_animated(const mu_objects *o)
{
    int32_t n = 0;
    for (int32_t i = 0; o->rt.ready && i < o->count; ++i)
        n += mu_obj_f32(o->rt.images + (size_t)i * MU_OBJ_SIZE, MU_OBJF_FRAME) != 0.0f;
    return n;
}

/* ---- logic step ---- */

typedef struct step_context {
    mu_objects *o;
    const mu_objects_step_inputs *in;
} step_context;

static int32_t step_rand(void *context)
{
    step_context *c = context;
    return mu_obj_msvc_rand(&c->o->rt.seed);
}

/* Action PlaySpeeds of object models are set by the model loader (not traced); worlds 0 and 0x8d
 * never ask for them. The login world's creation hook sets type 5 action 0 to 0.23. */
static float step_speed(void *context, int32_t type, int32_t action)
{
    step_context *c = context;
    int set;
    const float wp = mu_objects_worlds_p_speed(c->o, type, action, &set);   /* RENDER-WORLDS-P */
    if (set)
        return wp;
    if (type >= 0 && type < MU_OBJECT_TYPES && c->o->rt.play_speed_set[type] &&
        (action == 0 || c->o->rt.play_speed_set[type] == 2))
        return c->o->rt.play_speed[type];
    return 0.0f;
}

static uint8_t step_handler(void *context, int32_t index)
{
    step_context *c = context;
    if (!c->in->x2d)
        return 0;
    return mu_obj_handler_moves(image(c->o, index), c->o->world, c->in->x2d, c->in->y2d, c->in->scene_state);
}

/* Kanturu Underground's action table (RENDER-WORLDS-P2): key count of the loaded model, PlaySpeed from its
 * creation hook (0.3 for every action). Out-of-range actions and unset speeds are refused. */
static int kanturu_table(void *context, int32_t type, int32_t action, int32_t *count, int16_t *keys, float *speed)
{
    step_context *c = context;
    const mu_object_model *m = type >= 0 && type < MU_OBJECT_TYPES ? c->o->models[type] : NULL;
    if (!m || !m->loaded || action < 0 || action >= m->bmd.action_count || c->o->rt.play_speed_set[type] != 2)
        return 0;
    *count = m->bmd.action_count;
    *keys = (int16_t)m->bmd.actions[action].keys;
    *speed = c->o->rt.play_speed[type];
    return 1;
}

static void tick(mu_objects *o, int32_t index, float speed)
{
    uint8_t *img = image(o, index);
    const int32_t t = mu_obj_i32(img, MU_OBJF_TYPE);
    if (t < 0 || t >= MU_OBJECT_TYPES || !o->models[t] || !o->models[t]->loaded)
        return;
    mu_model *m = &o->models[t]->model;
    if (!o->models[t]->bmd.action_count)
        return;
    mu_model_set_state(m, mu_obj_u16(img, MU_OBJF_ACTION), mu_obj_f32(img, MU_OBJF_FRAME),
                       mu_obj_f32(img, MU_OBJF_PRIOR_FRAME), mu_obj_u16(img, MU_OBJF_PRIOR_ACTION));
    uint8_t loop = 0;
    if (mu_model_tick(m, speed, &loop) != MU_MODEL_OK)
        return;
    mu_obj_set_f32(img, MU_OBJF_FRAME, mu_model_frame(m));
    mu_obj_set_f32(img, MU_OBJF_PRIOR_FRAME, mu_model_prior_frame(m));
    mu_obj_set_u16(img, MU_OBJF_PRIOR_ACTION, mu_model_prior_action(m));
    ++o->rt.ticks;
}

/* Stand-in lifetimes and motion per bitmap (the legacy particle system is not reconstructed). */
static int32_t particle_life(int32_t bitmap)
{
    switch (bitmap) {
    case MU_OBJ_BITMAP_FIRE: return 24;
    case MU_LOGIN_BITMAP_CLOUDS: return 40;
    case MU_LOGIN_BITMAP_WATERFALL: return 20;
    default: return 32;
    }
}

static float particle_rise(int32_t bitmap)
{
    switch (bitmap) {
    case MU_OBJ_BITMAP_FIRE: return 2.5f;
    case MU_LOGIN_BITMAP_CLOUDS: return 1.0f;
    case MU_LOGIN_BITMAP_WATERFALL: return -2.0f;
    default: return 3.0f;
    }
}

static void spawn(mu_objects_runtime *rt, const mu_obj_event *e)
{
    if (rt->particle) {   /* CreateParticle 0x0168fafd (NATIVE-PARTICLE-001) */
        float position[3], angle[3], light[3];
        for (int k = 0; k < 3; ++k) {
            position[k] = fbits(e->args[1 + k]);
            angle[k] = fbits(e->args[4 + k]);
            light[k] = fbits(e->args[7 + k]);
        }
        /* argument 7, the owner: the object when the event carries it (the login world's mist) */
        const int32_t owner = e->count > 12 && e->args[12] ? e->object : -1;
        rt->particle(rt->hook_context, (int32_t)e->args[0], position, angle, light, (int32_t)e->args[10],
                     fbits(e->args[11]), owner);
        return;
    }
    if (rt->particle_count >= MU_OBJECT_PARTICLES)
        return;
    mu_object_particle *p = &rt->particles[rt->particle_count++];
    p->bitmap = (int32_t)e->args[0];
    for (int k = 0; k < 3; ++k) {
        p->position[k] = fbits(e->args[1 + k]);
        p->light[k] = fbits(e->args[7 + k]);
    }
    p->sub = (int32_t)e->args[10];
    p->scale = fbits(e->args[11]);
    p->life = particle_life(p->bitmap);
    p->age = 0;
}

static void particles_step(mu_objects_runtime *rt)
{
    int32_t kept = 0;
    for (int32_t i = 0; i < rt->particle_count; ++i) {
        mu_object_particle p = rt->particles[i];
        if (++p.age >= p.life)
            continue;
        p.position[2] += particle_rise(p.bitmap);
        rt->particles[kept++] = p;
    }
    rt->particle_count = kept;
}

static int pose_object(mu_objects *, uint8_t *, mu_object_model *, const mu_obj_log *);
/* Resolve the deferred market light from this object's current pose. No stale
 * shared model matrices or object-origin approximation when a bone is absent. */
static void market_bone_light(mu_objects *o, int32_t i, const mu_obj_event *e)
{
    uint8_t *img = image(o, i);
    const int32_t t = mu_obj_i32(img, MU_OBJF_TYPE);
    mu_object_model *m = t >= 0 && t < MU_OBJECT_TYPES ? o->models[t] : NULL;
    const int32_t bone = (int32_t)e->args[0];
    if (!m || !m->loaded || bone < 0 || bone >= m->bmd.bone_count ||
        !pose_object(o, img, m, NULL)) {
        ++o->rt.move_unsupported;
        return;
    }
    if (o->rt.light_count >= MU_OBJECT_STEP_LIGHTS) return;
    const float *matrix = mu_model_bone_matrices(&m->model) + 12 * bone;
    mu_object_light *l = &o->rt.lights[o->rt.light_count++];
    l->x = matrix[3]; l->y = matrix[7];
    for (int k=0;k<3;++k) l->rgb[k] = fbits(e->args[1+k]);
    l->range = (int32_t)e->args[4];
    ++o->rt.light_events;
}

/* RENDER-WORLDS-R2: Kardamahal type 115 after the tick (the client's order): pose the object's model and
 * light each named bone E002..E009 the skeleton has. No model pose: refused and counted. */
static void kardamahal_bone_lights(mu_objects *o, int32_t i, const mu_obj_event *e)
{
    uint8_t *img = image(o, i);
    const int32_t t = mu_obj_i32(img, MU_OBJF_TYPE);
    mu_object_model *m = t >= 0 && t < MU_OBJECT_TYPES ? o->models[t] : NULL;
    if (!m || !m->loaded || !pose_object(o, img, m, NULL)) {
        ++o->rt.move_unsupported;
        return;
    }
    for (int32_t k = 0; k < 8; ++k)
        for (int32_t b = 0; b < m->bmd.bone_count; ++b) {
            if (strcmp(m->bmd.bones[b].name, mu_kardamahal_bone_name(k)) != 0) continue;
            if (o->rt.light_count >= MU_OBJECT_STEP_LIGHTS) return;
            const float *matrix = mu_model_bone_matrices(&m->model) + 12 * b;
            mu_object_light *l = &o->rt.lights[o->rt.light_count++];
            l->x = matrix[3]; l->y = matrix[7];
            for (int q = 0; q < 3; ++q) l->rgb[q] = fbits(e->args[q]);
            l->range = (int32_t)e->args[3];
            ++o->rt.light_events;
            break;
        }
}

void mu_objects_step(mu_objects *o, const mu_objects_step_inputs *in)
{
    mu_objects_runtime *rt = &o->rt;
    if (!rt->ready)
        return;
    if (rt->effect) {
        for (int32_t k = 0; k < rt->startup_effect_count; ++k) {
            const mu_obj_event *e = &rt->startup_effects[k];
            const int32_t owner = e->object;
            uint8_t *oimage = image(o, owner);
            float position[3], angle[3], light[3];
            for (int q = 0; q < 3; ++q) {
                position[q] = fbits(e->args[1 + q]);
                angle[q] = mu_obj_f32(oimage, e->args[4] + (uint32_t)q * 4u);
                light[q] = mu_obj_f32(oimage, e->args[5] + (uint32_t)q * 4u);
            }
            rt->effect(rt->hook_context, (int32_t)e->args[0], (int32_t)e->args[6], position, angle, light, -1);
            ++rt->effect_events;
        }
        rt->startup_effect_count = 0;
    }
    particles_step(rt);
    rt->light_count = 0;
    step_context c = {o, in};
    int32_t sky_selected=0, sky_ordinal=0;
    if (o->world == 10) sky_selected=mu_objects_icarus_sky(o,in->hero);
    {   /* NATIVE-FIDELITY-002: MoveObjects' pre-pass in the sky worlds (Icarus's rising cloud puffs) */
        mu_obj_event sky[4];
        mu_obj_log log = {0, 4, 0, sky};
        if (mu_obj_move_pre_sky(o->world, in->hero, step_rand, &c, &log))
            for (int32_t k = 0; k < log.count; ++k) {
                const mu_obj_event *e = &sky[k];
                if (e->call != MU_OBJ_CALL_CREATE_EFFECT)
                    continue;
                float position[3], angle[3], light[3];
                for (int q = 0; q < 3; ++q) {
                    position[q] = fbits(e->args[1 + q]);
                    angle[q] = fbits(e->args[4 + q]);
                    light[q] = fbits(e->args[7 + q]);
                }
                if (rt->effect)
                    rt->effect(rt->hook_context, (int32_t)e->args[0], (int32_t)e->args[10], position, angle, light, -1);
                ++rt->effect_events;
            }
    }
    mu_obj_log pass = {0, rt->event_capacity, 0, rt->events};
    mu_obj_move_pass(&rt->world, o->world, step_handler, &c, &pass);
    mu_obj_move_inputs mi;
    memset(&mi, 0, sizeof mi);
    mi.world = o->world;
    mi.scene_state = in->scene_state;
    mi.hero_tile = in->hero_tile;
    mi.time = in->time;
    memcpy(mi.hero, in->hero, sizeof mi.hero);
    mi.model_has_actions = 1;
    mi.speed = step_speed;
    mi.rand_fn = step_rand;
    mi.context = &c;
    mi.now_ms = rt->now_ms;
    mi.hero_safe = rt->hero_safe;
    uint8_t elbeland_pool[MU_OBJ_SIZE] = {0};
    if (o->world == 51 && rt->environment) {
        mu_env_object_store(&rt->environment->boids[1], elbeland_pool);
        mi.elbeland_pool = elbeland_pool;
    }
    mu_obj_event local[64];
    for (int32_t k = 0; k < pass.count; ++k) {
        const mu_obj_event *e = &pass.events[k];
        if (e->call == MU_OBJ_CALL_MOVE_WORLD10 && o->world == 10)
            mu_objects_icarus_object(o,e->object,sky_selected,&sky_ordinal);
        if (e->call != MU_OBJ_CALL_MOVE_OBJECT)
            continue;
        const int32_t i = e->object, t = mu_obj_i32(image(o, i), MU_OBJF_TYPE);
        mi.has_model = (uint8_t)(t >= 0 && t < MU_OBJECT_TYPES && o->models[t] && o->models[t]->loaded);
        mu_obj_log log = {0, 64, 0, local};
        const int status = mu_obj_move(image(o, i), i, &mi, &log);
        if (status == MU_OBJ_OK) mu_objects_raklion_move(o, t, in->hero);
        ++rt->moved;
        /* RENDER-WORLDS-Q: slot 0x30 follows the generic part, so its events come after the tick's. */
        const int q_move = status == MU_OBJ_UNSUPPORTED && mu_worlds_q_owns(o->world);
        if (status == MU_OBJ_UNSUPPORTED && !q_move)
            ++rt->move_unsupported;
        for (int pass = 0; pass <= q_move; ++pass) {
            if (pass) {
                const mu_q_inputs q = q_inputs(o, in->hero, in->time);
                log.count = 0;
                mu_worlds_q_move(image(o, i), i, &q, &log);
            }
            for (int32_t j = 0; j < log.count; ++j) {
                const mu_obj_event *m = &local[j];
                if (m->call == MU_OBJ_CALL_LOSTTOWER_VISUAL) {
                    mu_obj_event output[1]; mu_obj_log pushed = {0, 1, 0, output};
                    mu_losttower_push(image(o, i), i, in->hero, rt->hero_action, &pushed);
                    if (pushed.count && o->sound) o->sound(o->sound_context, (int32_t)output[0].args[0]);
                } else if (m->call == MU_OBJ_CALL_TICK) {
                    tick(o, i, fbits(m->args[0]));
                } else if (m->call == MU_MARKET_BONE_LIGHT) {
                    market_bone_light(o, i, m);
                } else if (m->call == MU_KANTURU_UG_ACTION_STEP) {   /* after the tick, as in the client */
                    if (!mu_kanturu_ug_move(image(o, i), i, &mi, kanturu_table, 0.1f /* render-pass frame time */, NULL))
                        ++rt->move_unsupported;
                } else if (m->call == MU_KARDAMAHAL_BONE_LIGHTS) {   /* after the tick, as in the client */
                    kardamahal_bone_lights(o, i, m);
                } else if (m->call == MU_WP_MOVE) {
                    mu_objects_worlds_p_move(o, i, in->hero);
                } else if (m->call == MU_WP_CLAMPED_LIGHT && rt->light_count < MU_OBJECT_STEP_LIGHTS) {
                    mu_object_light *l = &rt->lights[rt->light_count++];
                    l->x = fbits(m->args[0]);
                    l->y = fbits(m->args[1]);
                    for (int q = 0; q < 3; ++q)
                        l->rgb[q] = fbits(m->args[2 + q]);
                    l->range = (int32_t)m->args[5] | MU_OBJECT_LIGHT_CLAMPED;
                    ++rt->light_events;
                } else if (m->call == MU_DEEP_DUNGEON_KEYED_EFFECT) {
                    /* RENDER-EFFECTS-005: CreateEffect(0x43a, ..., key 0xffff, word4 = (u16)scale, scale 0.0).
                     * The DungeonStone body reads no info word; the core gets the literal 0.0 scale. */
                    float position[3], angle[3], light[3];
                    for (int q = 0; q < 3; ++q) {
                        position[q] = fbits(m->args[1 + q]);
                        angle[q] = fbits(m->args[4 + q]);
                        light[q] = fbits(m->args[7 + q]);
                    }
                    if (rt->effect_scaled)
                        rt->effect_scaled(rt->hook_context, (int32_t)m->args[0], (int32_t)m->args[10], position, angle,
                                          light, -1, 0.0f);
                    ++rt->effect_events;
                } else if (m->call == MU_OBJ_CALL_ADD_LIGHT && rt->light_count < MU_OBJECT_STEP_LIGHTS) {
                    mu_object_light *l = &rt->lights[rt->light_count++];
                    l->x = fbits(m->args[0]);
                    l->y = fbits(m->args[1]);
                    for (int q = 0; q < 3; ++q)
                        l->rgb[q] = fbits(m->args[2 + q]);
                    l->range = (int32_t)m->args[5];
                    ++rt->light_events;
                } else if (m->call == MU_OBJ_CALL_PARTICLE) {
                    spawn(rt, m);
                    ++rt->particle_events;
                } else if (m->call == MU_OBJ_CALL_SOUND) {
                    ++rt->sound_events;
                    if (o->sound) o->sound(o->sound_context, (int32_t)m->args[0]);
                } else if (m->call == MU_Q_STOP_SOUND) {
                    ++rt->move_unsupported;   /* StopBuffer has no native consumer; refused and counted */
                }
            }
        }
    }
    if (o->world == 10) rt->icarus_count=sky_ordinal;

    if (mi.elbeland_pool)
        mu_env_object_load(&rt->environment->boids[1], elbeland_pool);
    ++rt->steps;
}

void mu_objects_apply_lights(const mu_objects *o, mu_world *map)
{
    if (map && (o->world == 57 || o->world == 58)) map->camera_shake = o->rt.raklion_quake;
    for (int32_t i = 0; map && i < o->rt.light_count; ++i) {
        const mu_object_light *l = &o->rt.lights[i];
        if (l->range & MU_OBJECT_LIGHT_CLAMPED)
            mu_bloody_tarkan_add_light_clamped(l->x, l->y, l->rgb, l->range & ~MU_OBJECT_LIGHT_CLAMPED, map->light);
        else
            mu_world_add_light(map, l->x, l->y, l->rgb, l->range);
    }
}

/* ---- render pass ---- */

typedef struct render_context {
    mu_objects *o;
} render_context;

/* 0x017fcd18 for world 0 (Lorencia): types 0x37 and 0x3c; the predicate's default chain (camera and
 * event-state singletons) answers no here (static reading, not executed). */
static uint8_t render_first(void *context, int32_t index)
{
    render_context *c = context;
    if (c->o->world != 0)
        return 0;
    const int32_t t = mu_obj_i32(image(c->o, index), MU_OBJF_TYPE);
    return (uint8_t)(t == 0x37 || t == 0x3c);
}

void mu_objects_visibility(mu_objects *o, const mu_terrain_frustum *f, int32_t scene_state)
{
    mu_objects_runtime *rt = &o->rt;
    rt->draw_count = 0;
    rt->sprite_count = 0;   /* RenderSprites draws and clears the frame's sprites */
    if (!rt->ready)
        return;
    render_context c = {o};
    mu_obj_render_inputs in;
    memset(&in, 0, sizeof in);
    in.world = o->world;
    in.scene_state = scene_state;
    in.x2d = f->x2d;
    in.y2d = f->y2d;
    in.render_first = render_first;
    in.context = &c;
    in.frame_time = 0.1f;
    mu_obj_log log = {0, rt->event_capacity, 0, rt->events};
    mu_obj_render_pass(&rt->world, &in, &rt->render_counter, &log);
    for (int32_t k = 0; k < log.count; ++k)
        if (log.events[k].call == MU_OBJ_CALL_RENDER_OBJECT && rt->draw_count < o->count)
            rt->draw_list[rt->draw_count++] = log.events[k].object;
    rt->culled = rt->created - rt->draw_count;
}

mu_object_model *mu_objects_prepare(mu_objects *o, int32_t k, const mu_world *map, int32_t scene_state,
                                    mu_draw_options *options)
{
    if (k < 0 || k >= o->rt.draw_count)
        return NULL;
    return mu_objects_prepare_index(o, o->rt.draw_list[k], map, scene_state, options);
}

/* The login world's custom render (slot 0x38) as the custom-render answer of RenderObject: its
 * RenderBody call is kept for the draw. */
typedef struct custom_context {
    mu_objects *o;
    mu_obj_log log;
} custom_context;

static uint8_t login_custom(void *context, int32_t index)
{
    custom_context *c = context;
    return (uint8_t)mu_login_custom_render(image(c->o, index), index, &c->log);
}

/* NATIVE-CHARSEL-002: CGMCharacterScene_Ex's custom render (slot 0x38); the pedestal's RenderMesh call is kept */
static uint8_t charsel_custom(void *context, int32_t index)
{
    custom_context *c = context;
    return (uint8_t)mu_csw_custom_render(image(c->o, index), index, &c->log);
}

/* Pose and skin object i's model at its animation state with the body light of model_fields, with the
 * arguments RenderObject's setup 0x017ec896 passes to Animation and Transform (compared in the render family,
 * scripts/validate_object_render.py). log: mu_obj_render's call log; without its Animation/Transform events
 * (the after-character setup) the static-object call RenderObject(o, 0, ...) is used, whose arguments are the
 * same: Animation(..., !translate = 1) (0x017ed811/0x017ed880) and Transform(bones, min, max, OBB, translate 0,
 * vertex scale 0, ambient 0.4, scale +0xe4, minimum +0xe8) (0x017edc95/0x017edd08).
 *
 * With Animation's translate the pose builder 0x012b5064 puts the body scale and origin into the root bone,
 * and the transform 0x012b5bde rotates normals by the bone 3x3 without renormalizing: the Lambert term of a
 * static object grows with its scale (the login sky, scale 14.84, saturates; the far ship, 0.23, is dark).
 * The light vector is (1.3, 0, 2): the client's light-override byte is 1 (MU_CLIENT_HIGH_LIGHT). Both were
 * missing before NATIVE-LIGHT-001 (docs/research/client-model-light.md). */
static int pose_object(mu_objects *o, uint8_t *img, mu_object_model *m, const mu_obj_log *log)
{
    mu_model_params p = m->model.params;
    if (mu_world_after_enabled(o->world))
        p.light_skip_mesh = -1;
    memcpy(p.origin, img + MU_OBJF_POSITION, 12);
    memcpy(p.angles, img + MU_OBJF_ANGLE, 12);
    p.body_scale = mu_obj_f32(img, MU_OBJF_SCALE);
    memcpy(p.color, o->rt.model_fields + MU_MDL_COLOR, 12);
    p.lighting = o->rt.model_fields[MU_MDL_LIGHTING];
    p.secondary_light = o->rt.model_fields[MU_MDL_SECONDARY];
    if (o->uniform_light > 0.0f)
        for (int q = 0; q < 3; ++q)
            p.color[q] = o->uniform_light;
    p.pose_translate = 1;
    p.transform_translate = 0;
    p.vertex_scale = 0.0f;
    p.light_ambient = 0.4f;
    p.light_scale = mu_obj_f32(img, MU_OBJF_VALUE_E4);
    p.light_minimum = mu_obj_f32(img, MU_OBJF_VALUE_E8);
    for (int32_t k = 0; log && k < log->count; ++k) {
        const mu_obj_event *e = &log->events[k];
        if (e->call == MU_OBJ_CALL_ANIMATION) {
            p.pose_translate = (uint8_t)e->args[5];
        } else if (e->call == MU_OBJ_CALL_TRANSFORM) {
            p.transform_translate = (uint8_t)e->args[1];
            p.vertex_scale = fbits(e->args[2]);
            p.light_ambient = fbits(e->args[3]);
            p.light_scale = fbits(e->args[4]);
            p.light_minimum = fbits(e->args[5]);
        }
    }
    p.light_override = MU_CLIENT_HIGH_LIGHT;
    mu_model_apply_params(&m->model, &p);
    mu_model_set_state(&m->model, mu_obj_u16(img, MU_OBJF_ACTION), mu_obj_f32(img, MU_OBJF_FRAME),
                       mu_obj_f32(img, MU_OBJF_PRIOR_FRAME), mu_obj_u16(img, MU_OBJF_PRIOR_ACTION));
    return mu_model_pose(&m->model) == MU_MODEL_OK && mu_model_transform_all(&m->model) == MU_MODEL_OK;
}

typedef struct visual_context {
    mu_objects *o;
    const mu_object_model *m;
} visual_context;

static int32_t visual_rand(void *context)
{
    visual_context *c = context;
    return mu_obj_msvc_rand(&c->o->rt.seed);
}

/* TransformPosition on the object's posed bones. Static objects are posed with the body origin and scale
 * in the bones (Animation's translate argument, as in the client), so the point is matrix * local. */
static void visual_bone(void *context, int32_t bone, const float local[3], float out[3])
{
    visual_context *c = context;
    out[0] = out[1] = out[2] = 0.0f;
    if (bone < 0 || bone >= c->m->bmd.bone_count)
        return;
    const float *b = mu_model_bone_matrices(&c->m->model) + 12 * bone;
    for (int r = 0; r < 3; ++r) {
        out[r] = b[4 * r] * local[0] + b[4 * r + 1] * local[1] + b[4 * r + 2] * local[2] + b[4 * r + 3];
    }
}

/* Name lookup uses the current object's posed model without allocating per frame. */
static void builtin_bone(void *context, const char *name, const float local[3], float out[3])
{
    visual_context *c = context;
    out[0] = out[1] = out[2] = 0;
    for (int32_t k = 0; k < c->m->bmd.bone_count; ++k)
        if (strcmp(c->m->bmd.bones[k].name, name) == 0) {
            visual_bone(context, k, local, out);
            return;
        }
}

/* RENDER-EFFECTS-006: an owned CreateEffect with info word4 at args[word4]: type, position, angle, light, subtype
 * (args 0..10), the owner flag at args[word4 - 1]. Without the consumer hook it stays refused and counted. */
static void owned_effect(mu_objects_runtime *rt, const mu_obj_event *e, int32_t word4)
{
    if (!rt->effect_word4) {
        ++rt->draw_unsupported;
        return;
    }
    float position[3], angle[3], light[3];
    for (int q = 0; q < 3; ++q) {
        position[q] = fbits(e->args[1 + q]);
        angle[q] = fbits(e->args[4 + q]);
        light[q] = fbits(e->args[7 + q]);
    }
    rt->effect_word4(rt->hook_context, (int32_t)e->args[0], (int32_t)e->args[10], position, angle, light,
                     e->args[word4 - 1] ? e->object : -1, (uint16_t)e->args[word4]);
    ++rt->effect_events;
}

static void consume_visual(mu_objects *o, const mu_obj_log *log)
{
    mu_objects_runtime *rt = &o->rt;
    for (int32_t k = 0; k < log->count; ++k) {
        const mu_obj_event *e = &log->events[k];
        if (e->call == MU_Q_KEYED_EFFECT) {   /* Q: the object is always the owner; args[11] is word4 */
            mu_obj_event owned = *e;
            owned.args[12] = owned.args[11];
            owned.args[11] = 1;
            owned_effect(rt, &owned, 12);
            continue;
        }
        if (e->call == MU_R2_EFFECT || e->call == MU_WR_EFFECT_SCALED) {   /* owner flag args[11], word4 args[12] */
            owned_effect(rt, e, 12);
            continue;
        }
        if (e->call == MU_OBJ_CALL_SPRITE && rt->sprite) {   /* CreateSprite 0x01692eb7 (NATIVE-JOINT-001) */
            float position[3], light[3];
            for (int q = 0; q < 3; ++q) {
                position[q] = fbits(e->args[1 + q]);
                light[q] = fbits(e->args[5 + q]);
            }
            rt->sprite(rt->hook_context, (int32_t)e->args[0], position, fbits(e->args[4]), light,
                       e->args[9] ? e->object : -1, fbits(e->args[8]), (int32_t)e->args[10], (int32_t)e->args[11]);
            ++rt->sprite_events;
        } else if (e->call == MU_OBJ_CALL_SPRITE && rt->sprite_count < MU_OBJECT_SPRITES) {
            mu_object_sprite *sp = &rt->sprites[rt->sprite_count++];
            sp->bitmap = (int32_t)e->args[0];
            for (int q = 0; q < 3; ++q) {
                sp->position[q] = fbits(e->args[1 + q]);
                sp->light[q] = fbits(e->args[5 + q]);
            }
            sp->scale = fbits(e->args[4]);
            sp->rotation = fbits(e->args[8]);
            ++rt->sprite_events;
        } else if (e->call == MU_ICARUS_JOINT && rt->joint) {
            float position[3], target[3], angle[3];
            for (int q = 0; q < 3; ++q) {
                position[q] = fbits(e->args[1 + q]);
                target[q] = fbits(e->args[4 + q]);
                angle[q] = fbits(e->args[7 + q]);
            }
            rt->joint(rt->hook_context, (int32_t)e->args[0], position, target, angle,
                      (int32_t)e->args[10], e->args[11] ? e->object : -1, fbits(e->args[12]));
        } else if (e->call == MU_URUK_KEYED_EFFECT || e->call == MU_URUK_COLORED_JOINT) {
            ++rt->draw_unsupported; /* No native key/color consumer; preserve the refusal. */
        } else if (e->call == MU_OBJ_CALL_SOUND) {
            ++rt->sound_events;
            if (o->sound) o->sound(o->sound_context, (int32_t)e->args[0]);
        } else if (e->call == MU_OBJ_CALL_PARTICLE) {
            spawn(rt, e);
            ++rt->particle_events;
        } else if (e->call == MU_OBJ_CALL_EFFECT) {   /* CreateEffect 0x013c0eaa (NATIVE-CHARSEL-002) */
            float position[3], angle[3], light[3];
            for (int q = 0; q < 3; ++q) {
                position[q] = fbits(e->args[1 + q]);
                angle[q] = fbits(e->args[4 + q]);
                light[q] = fbits(e->args[7 + q]);
            }
            if (e->count == 13 && rt->effect_scaled)
                rt->effect_scaled(rt->hook_context, (int32_t)e->args[0], (int32_t)e->args[10], position,
                                  angle, light, e->args[11] ? e->object : -1, fbits(e->args[12]));
            else if (rt->effect)
                rt->effect(rt->hook_context, (int32_t)e->args[0], (int32_t)e->args[10], position, angle, light,
                           e->args[11] ? e->object : -1);
            ++rt->effect_events;
        }
    }
}
/* RenderObjectVisual's handler slot 0x34 of the login world (CGMLogInScene_Ex) and, NATIVE-CHARSEL-002, of
 * the character-select world (CGMCharacterScene_Ex): its CreateSprite / CreateParticle / CreateEffect calls.
 */
static void handler_visual(mu_objects *o, int32_t i, uint8_t *img, const mu_object_model *m, float world_time, int posed)
{
    visual_context c = {o, m};
    mu_obj_event events[64];
    mu_obj_log log = {0, 64, 0, events};
    if (o->world == 4 || o->world == 7 || o->world == 8)
        mu_builtin_visual(img, i, o->world, m && m->loaded, world_time, visual_rand,
                          posed ? builtin_bone : NULL, &c, &log);
    else if (o->world == 10) {
        /* Existing cover hook consumes the common brightness from the particle RNG. */
        if (o->rt.visual) o->rt.visual(o->rt.hook_context, o, i, m && m->loaded, posed ? (mu_object_model *)m : NULL);
        if (posed) mu_icarus_bone_flare(img, i, builtin_bone, &c, &log);
    }
    else if (o->world == MU_CSW_WORLD)
        mu_csw_visual(img, i, world_time, visual_rand, m && m->loaded ? visual_bone : NULL, NULL, &c, &log);
    else if (o->world == 79 && m && m->loaded) {
        const int32_t type = mu_obj_i32(img, MU_OBJF_TYPE);
        const int needs_bones = type == 30 || type == 35;
        const int bones_ready = posed && m->bmd.bone_count > (type == 30 ? 3 : 2);
        if (needs_bones && !bones_ready) ++o->rt.draw_unsupported;
        mu_market_visual(img, i, o->world, world_time, visual_rand, bones_ready ? visual_bone : NULL, &c, &log);
    }
    else if (o->world == 100 && m && m->loaded)
        mu_uruk_visual(img, i, o->world, o->rt.uruk_weather, world_time, visual_rand, &c, &log);
    else if (o->world == 79 || o->world == 100)
        return;
    else if ((o->world == 80 || o->world == 81) && m && m->loaded) {
        const int32_t type = mu_obj_i32(img, MU_OBJF_TYPE);
        const int needs_bones = type == 66 || type == 72;
        const int bones_ready = posed && m->bmd.bone_count > (type == 66 ? 14 : 11);
        if (needs_bones && !bones_ready) ++o->rt.draw_unsupported;
        (void)visual_rand(&c); /* Existing outer RenderObjectVisual flicker draw. */
        mu_karutan_visual(img, i, o->world, world_time, visual_rand,
                          bones_ready ? visual_bone : NULL, &c, &log);
    }
    else if (o->world == 80 || o->world == 81)
        return;
    else if (o->world == 137) {   /* RENDER-WORLDS-P2: Kanturu Underground slot 0x34 */
        const int32_t type = mu_obj_i32(img, MU_OBJF_TYPE);
        const int bones_ready = posed && m && m->loaded && m->bmd.bone_count > 4;
        if ((type == 8 || (type >= 92 && type <= 96)) && !bones_ready) ++o->rt.draw_unsupported;
        mu_kanturu_ug_visual(img, i, m && m->loaded, world_time, visual_rand, bones_ready ? visual_bone : NULL,
                             &c, &log);
        for (int32_t k = 0; k < log.count; ++k)   /* joint kinds the native pool does not model: refused */
            if (events[k].call == MU_ICARUS_JOINT &&
                !mu_jt_kind_supported((int32_t)events[k].args[0], (int32_t)events[k].args[10])) {
                events[k].call = 0;
                ++o->rt.draw_unsupported;
            }
    }
    else if (o->world >= 142 && o->world <= 144 && m && m->loaded) {   /* RENDER-WORLDS-R2 slot 0x34 */
        const int32_t type = mu_obj_i32(img, MU_OBJF_TYPE);
        const int bones_ready = posed && m->bmd.bone_count > 11;
        if (o->world == 142 && type == 72 && !bones_ready) ++o->rt.draw_unsupported;
        (void)visual_rand(&c); /* Outer RenderObjectVisual flicker draw. */
        if (o->world == 142)
            mu_twisted_karutan_visual(img, i, 1, world_time, visual_rand, bones_ready ? visual_bone : NULL, &c, &log);
        else if (o->world == 143)
            mu_kardamahal_visual(img, i, 1, visual_rand, &c, &log);
        else
            mu_swamp_visual(img, i, 1, visual_rand, &c, &log);
        for (int32_t k = 0; k < log.count; ++k)   /* unmodelled joint kinds: refused (word4 effects: owned_effect) */
            if (events[k].call == MU_ICARUS_JOINT &&
                !mu_jt_kind_supported((int32_t)events[k].args[0], (int32_t)events[k].args[10])) {
                events[k].call = 0;
                ++o->rt.draw_unsupported;
            }
    }
    else if (o->world >= 142 && o->world <= 144)
        return;
    else if ((o->world == 0x87 || o->world == 0x88 || o->world == 0x8c) && m && m->loaded) {   /* RENDER-WORLDS-P */
        const int32_t type = mu_obj_i32(img, MU_OBJF_TYPE);
        const int needs_bones = o->world == 0x87 && (type == 15 || type == 16);
        const int bones_ready = posed && m->bmd.bone_count > (type == 15 ? 4 : 15);
        if (needs_bones && !bones_ready) ++o->rt.draw_unsupported;
        (void)visual_rand(&c); /* Outer RenderObjectVisual flicker draw. */
        if (o->world == 0x87)
            mu_old_kethotum_visual(img, i, 1, world_time, visual_rand, bones_ready ? visual_bone : NULL, &c, &log);
        else if (o->world == 0x88)
            mu_burning_kethotum_visual(img, i, 1, visual_rand, &c, &log);
        else
            mu_bloody_tarkan_visual(img, 1);
    }
    else if (o->world == 0x87 || o->world == 0x88 || o->world == 0x8c)
        return;
    else if (o->world >= 0x83 && o->world <= 0x86 && m && m->loaded) {   /* RENDER-WORLDS-R */
        const int32_t type = mu_obj_i32(img, MU_OBJF_TYPE);
        const int needs_bones = (o->world == 0x84 && type == 0xa) || (o->world == 0x86 && (type == 0x1e || type == 0x47));
        const int bones_ready = posed && m->bmd.bone_count > (o->world == 0x84 ? 3 : 17);
        if (needs_bones && !bones_ready) ++o->rt.draw_unsupported;
        (void)visual_rand(&c); /* Outer RenderObjectVisual flicker draw. */
        if (o->world == 0x84)
            mu_red_smoke_icarus_visual(img, i, 1, bones_ready ? visual_bone : NULL, &c, &log);
        else if (o->world == 0x86)
            mu_gray_aida_visual(img, i, 1, world_time, visual_rand, bones_ready ? visual_bone : NULL, &c, &log);
        for (int32_t k = 0; k < log.count; ++k)   /* no native extra-mesh consumer: refused (0x199: owned_effect) */
            if (events[k].call == MU_OBJ_CALL_MESH) ++o->rt.draw_unsupported;
    }
    else if (o->world >= 0x83 && o->world <= 0x86)
        return;
    else if (o->world >= 128 && o->world <= 130)   /* RENDER-WORLDS-O */
        mu_abyss_visual(o->world, img, o->world, m && m->loaded);
    else if (mu_worlds_q_owns(o->world)) {   /* RENDER-WORLDS-Q; the outer RenderObjectVisual draws one rand first */
        if (m && m->loaded) (void)visual_rand(&c);
        mu_q_inputs q = q_inputs(o, NULL, world_time);
        q.actions = NULL;   /* the visual slots read no action table */
        const int32_t last_bone = o->world == 91 ? mu_acheron_visual_bones(mu_obj_i32(img, MU_OBJF_TYPE)) : -1;
        q.bone = posed && m->bmd.bone_count > last_bone ? visual_bone : NULL;
        q.context = &c;
        q.rand_fn = visual_rand;
        if (mu_worlds_q_visual(img, i, m && m->loaded, &q, &log) < 0) ++o->rt.draw_unsupported;
    }
    else if (o->world == 57 || o->world == 58)
        mu_raklion_visual(img, i, m && m->loaded, visual_rand, &c, &log);
    else if (o->world == 64)
        mu_duel_visual(img, i, m && m->loaded, visual_rand, &c, &log);
    else if (o->world == 82)
        mu_world82_visual(img, i, o->world, m && m->loaded, world_time, visual_rand, &c, &log);
    else if (o->world == 62)
        mu_santa_visual(img, i, m && m->loaded, world_time, &log);
    else if (o->world == 63)
        mu_vulcanus_visual(img, i, o->world, m && m->loaded, world_time, visual_rand, &c, &log);
    else
        mu_login_visual(img, i, visual_rand, m && m->loaded ? visual_bone : NULL, &c, &log);
    consume_visual(o, &log);
}

/* Scoped per-world RenderObjectVisual hooks. The initial flicker rand in
 * 0x017f9758 is consumed before its world dispatch, even when the hook has no flame. */
static int world_flames(mu_objects *o, int32_t i, uint8_t *img, const mu_object_model *m, float time, int posed)
{
    if (!m || !m->loaded)
        return 0;
    if (o->world != 0x25 && o->world != 0x28)
        return 0;
    visual_context c = {o, m};
    mu_obj_event events[64];
    mu_obj_log log = {0, 64, 0, events};
    (void)visual_rand(&c);
    const int status = mu_kanturu_flames(img, i, o->world, time, visual_rand,
                                         posed ? visual_bone : NULL, &c, &log);
    consume_visual(o, &log);
    return status != MU_OBJ_UNSUPPORTED;
}

/* Draw options of a RenderMesh(mesh, flags, alpha, blend mesh, blend light, u, v, texture) event. */
static void mesh_options(const mu_obj_event *ev, mu_object_model *m, const mu_world *map, mu_draw_options *options)
{
    mu_draw_default_options(options);
    options->textures = &m->textures;
    options->mesh_plus_one = (int32_t)ev->args[0] + 1;
    options->flags = ev->args[1];
    options->alpha = fbits(ev->args[2]);
    options->select = (int32_t)ev->args[3];
    options->color_scale = fbits(ev->args[4]);
    options->u_offset = fbits(ev->args[5]);
    options->v_offset = fbits(ev->args[6]);
    options->texture = (int32_t)ev->args[7];
    options->time = map ? map->time : 0.0f;
}

/* Draw options of a RenderBody(flags, alpha, blend mesh, blend light, u, v, hidden mesh, texture) event. */
static void body_options(const mu_obj_event *body, mu_object_model *m, const mu_world *map, mu_draw_options *options)
{
    mu_draw_default_options(options);
    options->textures = &m->textures;
    options->flags = body->args[0];
    options->alpha = fbits(body->args[1]);
    options->select = (int32_t)body->args[2];
    options->color_scale = fbits(body->args[3]);
    options->u_offset = fbits(body->args[4]);
    options->v_offset = fbits(body->args[5]);
    options->skip_mesh = (int32_t)body->args[6];
    options->texture = (int32_t)body->args[7];
    options->time = map ? map->time : 0.0f;
}

mu_object_model *mu_objects_prepare_index(mu_objects *o, int32_t i, const mu_world *map, int32_t scene_state,
                                          mu_draw_options *options)
{
    mu_objects_runtime *rt = &o->rt;
    if (!rt->ready || i < 0 || i >= o->count)
        return NULL;
    uint8_t *img = image(o, i);
    const int32_t t = mu_obj_i32(img, MU_OBJF_TYPE);
    mu_object_model *m = t >= 0 && t < MU_OBJECT_TYPES ? o->models[t] : NULL;
    const int login = o->world == MU_LOGIN_WORLD, charsel = o->world == MU_CSW_WORLD;
    const int primary_visual = o->world == 4 || o->world == 7 || o->world == 8 || (o->world == 10 && t == 10) ||
                               o->world == 62 || o->world == 63 || o->world == 64 || o->world == 82 ||
                               o->world == 79 || o->world == 100 || o->world == 57 || o->world == 58 ||
                               o->world == 80 || o->world == 81 || (o->world >= 128 && o->world <= 130) ||
                               o->world == 0x87 || o->world == 0x88 || o->world == 0x8c || o->world == 137 ||
                               (o->world >= 142 && o->world <= 144) ||
                               (o->world >= 0x83 && o->world <= 0x86) ||
                               (mu_worlds_q_owns(o->world) && o->world != 112);   /* RENDER-WORLDS-Q */
    mu_obj_draw_inputs in;
    memset(&in, 0, sizeof in);
    in.world = o->world;
    in.scene_state = scene_state;
    in.has_model = (uint8_t)(m && m->loaded);
    in.light.primary = map ? map->primary : NULL;
    in.light.frame = map ? map->light : NULL;
    in.light.scene_state = scene_state;
    in.light.terrain_ready = map != NULL;
    in.light.time = map ? map->time : 0.0f;
    mu_obj_event custom_events[4];
    custom_context cc = {o, {0, 4, 0, custom_events}};
    if (login || charsel) {
        in.custom_render = login ? login_custom : charsel_custom;
        in.context = &cc;
    }
    mu_obj_event local[16];
    mu_obj_log log = {0, 16, 0, local};
    memset(rt->model_fields, 0, sizeof rt->model_fields);
    const int status = mu_obj_render(img, i, rt->model_fields, 0, &in, &log);
    const int deferred =
        !login && !charsel && in.has_model && status != MU_OBJ_SKIPPED && mu_world_defer(img, o->world);
    int posed = 0;
    if (login || charsel || primary_visual) {   /* RenderObjectVisual follows RenderObject, also for hidden objects (slot 0x34) */
        if (m && m->loaded && (status != MU_OBJ_SKIPPED || (o->world == 79 && log.count > 0) ||
                               o->world == 80 || o->world == 81 || o->world == 0x87 || (o->world == 8 && t == 63)))
            posed = pose_object(o, img, m, &log);
        handler_visual(o, i, img, primary_visual ? m : posed ? m : NULL, in.light.time, posed);
        if (rt->ein_update && rt->ein_listed && rt->ein_listed(rt->hook_context, i))   /* 0x016d51d8..0x016d51f5 */
            rt->ein_update(rt->hook_context, i, img, posed ? mu_model_bone_matrices(&m->model) : NULL,
                           posed ? m->bmd.bone_count : 0, 0.1f /* [0x01cf103c] */);
    } else if (!rt->visual) {
        mu_obj_visual(img, o->world, in.light.time);   /* RenderObjectVisual follows RenderObject */
    }
    /* NATIVE-PARTICLE-001: RenderObjectVisual through the particle module, after RenderObject */
    int flame = 0;
    if (!login && !charsel &&
        (o->world == 0x25 || o->world == 0x28)) {
        if (m && m->loaded && !posed)
            posed = pose_object(o, img, m, &log);
        flame = world_flames(o, i, img, m, in.light.time, posed);
    }
    const int hook = rt->visual && !login && !charsel && !flame && !primary_visual, has_model = m && m->loaded;
    if (deferred && !((o->world == 0x39 || o->world == 0x3a) && (t == 0x53 || t == 0x5c))) {
        if (hook)
            rt->visual(rt->hook_context, o, i, has_model, posed ? m : NULL);
        return NULL;
    }
    if (status == MU_OBJ_SKIPPED) {
        ++rt->draw_skipped;
        if (hook)
            rt->visual(rt->hook_context, o, i, has_model, NULL);
        return NULL;
    }
    if (!has_model) {
        if (hook)
            rt->visual(rt->hook_context, o, i, 0, NULL);
        return NULL;
    }
    if (status == MU_OBJ_UNSUPPORTED)
        ++rt->draw_unsupported;
    const mu_obj_event *body = NULL, *mesh = NULL;
    for (int32_t j = 0; j < log.count; ++j)
        if (local[j].call == MU_OBJ_CALL_BODY)
            body = &local[j];
    for (int32_t j = 0; !body && j < cc.log.count; ++j)
        if (custom_events[j].call == MU_OBJ_CALL_BODY)
            body = &custom_events[j];   /* the login world's custom render drew the body */
    for (int32_t j = 0; !body && !mesh && j < cc.log.count; ++j)
        if (custom_events[j].call == MU_OBJ_CALL_MESH)
            mesh = &custom_events[j];   /* the character select's pedestal: one mesh (slot 0x38) */
    if (status == MU_OBJ_OK && !body && !mesh) {
        if (hook)
            rt->visual(rt->hook_context, o, i, 1, NULL);
        return NULL;   /* a per-world custom render took the object */
    }
    if (!posed && !pose_object(o, img, m, &log)) {
        if (hook)
            rt->visual(rt->hook_context, o, i, 1, NULL);
        return NULL;
    }
    mu_draw_default_options(options);
    options->textures = &m->textures;
    if (mesh) {
        mesh_options(mesh, m, map, options);
    } else if (body) {
        body_options(body, m, map, options);
    } else {   /* unsupported branch: the generic RenderBody arguments */
        options->alpha = mu_obj_f32(img, MU_OBJF_ALPHA);
        options->select = mu_obj_i32(img, MU_OBJF_BLEND_MESH);
        options->color_scale = mu_obj_f32(img, MU_OBJF_BLEND_LIGHT);
        options->u_offset = mu_obj_f32(img, MU_OBJF_BLEND_U);
        options->v_offset = mu_obj_f32(img, MU_OBJF_BLEND_V);
        options->skip_mesh = mu_obj_i32(img, MU_OBJF_HIDDEN_MESH);
    }
    if (deferred) { /* Raklion's opaque meshes precede its deferred glow. */
        if (t == 0x53)
            options->skip_mesh = 4;
        else if (t == 0x5c)
            options->mesh_plus_one = 1;
    }
    options->time = map ? map->time : 0.0f;
    ++rt->drawn;
    if (hook)   /* after RenderObject's draw arguments, as in RenderObjects */
        rt->visual(rt->hook_context, o, i, 1, m);
    return m;
}

int32_t mu_objects_first_meshes(mu_objects *o, int32_t k, const mu_world *map, mu_object_model *m,
                                mu_object_mesh *meshes, int32_t capacity)
{
    if ((o->world != 0x39 && o->world != 0x3a) || k < 0 || k >= o->rt.draw_count)
        return 0;
    const int32_t i = o->rt.draw_list[k];
    mu_obj_event events[4];
    mu_obj_log log = {0, 4, 0, events};
    if (mu_raklion_before(image(o, i), i, &log) != MU_OBJ_OK)
        return 0;
    int32_t count = 0;
    for (int32_t j = 0; j < log.count && count < capacity; ++j) {
        mu_object_mesh *mesh = &meshes[count++];
        mesh_options(&events[j], m, map, &mesh->options);
        memset(&mesh->fields, 0, sizeof mesh->fields);
        memcpy(mesh->fields.color, m->model.params.color, 12);
    }
    return count;
}

uint8_t *mu_objects_object_image(mu_objects *o, int32_t index)
{
    if (!o->rt.ready || index < 0 || index >= o->count)
        return NULL;
    return image(o, index);
}

void mu_objects_light_report(mu_objects *o, const mu_world *map, int32_t scene_state, FILE *out)
{
    for (int32_t index = 0; o->rt.ready && index < o->count; ++index) {
        mu_draw_options options;
        mu_object_model *m = mu_objects_prepare_index(o, index, map, scene_state, &options);
        if (!m)
            continue;
        const mu_model_params *p = &m->model.params;
        const uint8_t *img = image(o, index);
        fprintf(out, "{\"object_light\": %d, \"type\": %d, \"scale\": %.9g, \"origin\": [%.9g, %.9g, %.9g], "
                "\"angles\": [%.9g, %.9g, %.9g], \"action\": %u, \"prior_action\": %u, \"frame\": %.9g, "
                "\"prior_frame\": %.9g, \"pose_translate\": %d, \"transform_translate\": %d, \"light_override\": %d, "
                "\"ambient\": %.9g, \"light_scale\": %.9g, \"light_minimum\": %.9g, \"lighting\": %d, "
                "\"color\": [%.9g, %.9g, %.9g], \"model\": \"%s\", \"lights\": [",
                index, m->type, (double)p->body_scale, (double)p->origin[0], (double)p->origin[1], (double)p->origin[2],
                (double)p->angles[0], (double)p->angles[1], (double)p->angles[2], mu_obj_u16(img, MU_OBJF_ACTION),
                mu_obj_u16(img, MU_OBJF_PRIOR_ACTION), (double)mu_obj_f32(img, MU_OBJF_FRAME),
                (double)mu_obj_f32(img, MU_OBJF_PRIOR_FRAME), p->pose_translate, p->transform_translate,
                p->light_override, (double)p->light_ambient, (double)p->light_scale, (double)p->light_minimum,
                p->lighting, (double)p->color[0], (double)p->color[1], (double)p->color[2], m->path);
        for (int32_t mesh = 0; mesh < m->bmd.mesh_count && mesh < 8; ++mesh) {
            const float *l = mu_model_lights(&m->model, mesh);
            fprintf(out, "%s[", mesh ? ", " : "");
            for (int32_t n = 0; n < m->bmd.meshes[mesh].normal_count && n < 64; ++n)
                fprintf(out, "%s%.9g", n ? ", " : "", (double)l[n]);
            fprintf(out, "]");
        }
        fprintf(out, "]}\n");
    }
}

/* ---- NATIVE-LOGIN-001: the after-character pass ---- */

void mu_objects_set_clock(mu_objects *o, uint32_t now_ms) { o->rt.now_ms = now_ms; }

void mu_objects_after_visibility(mu_objects *o, const mu_terrain_frustum *f, int32_t scene_state)
{
    mu_objects_runtime *rt = &o->rt;
    rt->after_count = 0;
    if (!rt->ready ||
        (o->world != MU_LOGIN_WORLD && o->world != MU_CSW_WORLD && !mu_world_after_enabled(o->world)))
        return;
    mu_obj_render_inputs in;
    memset(&in, 0, sizeof in);
    in.world = o->world;
    in.scene_state = scene_state;
    in.x2d = f->x2d;
    in.y2d = f->y2d;
    mu_obj_log log = {0, rt->event_capacity, 0, rt->events};
    if (mu_world_after_enabled(o->world))
        mu_world_after_pass(&rt->world, &in, &rt->render_counter, &log);
    else
        mu_login_after_pass(&rt->world, &in, &rt->render_counter, &log);
    for (int32_t k = 0; k < log.count; ++k)
        if (log.events[k].call == MU_OBJ_CALL_AFTER_DRAW && rt->after_count < o->count)
            rt->after_list[rt->after_count++] = log.events[k].object;
}

/* Texture slot whose BMD texture name is `name` (case-insensitive), or -1. */
static int32_t texture_slot(const mu_object_model *m, const char *name)
{
    for (int32_t k = 0; k < m->bmd.mesh_count; ++k) {
        const char *a = m->bmd.meshes[k].texture, *b = name;
        while (*a && *b && (*a | 0x20) == (*b | 0x20)) {
            ++a;
            ++b;
        }
        if (!*a && !*b)
            return k;
    }
    return -1;
}

mu_object_model *mu_objects_prepare_after(mu_objects *o, int32_t k, const mu_world *map, int32_t scene_state,
                                          mu_object_mesh *meshes, int32_t capacity, int32_t *count)
{
    mu_objects_runtime *rt = &o->rt;
    *count = 0;
    if (!rt->ready || k < 0 || k >= rt->after_count)
        return NULL;
    const int32_t i = rt->after_list[k];
    uint8_t *img = image(o, i);
    const int32_t t = mu_obj_i32(img, MU_OBJF_TYPE);
    mu_object_model *m = t >= 0 && t < MU_OBJECT_TYPES ? o->models[t] : NULL;
    if (!m || !m->loaded || 0.01f > mu_obj_f32(img, MU_OBJF_ALPHA))
        return NULL;   /* the setup 0x017ec896 refuses */
    mu_obj_light_inputs light;
    memset(&light, 0, sizeof light);
    light.primary = map ? map->primary : NULL;
    light.frame = map ? map->light : NULL;
    light.scene_state = scene_state;
    light.terrain_ready = map != NULL;
    light.time = map ? map->time : 0.0f;
    memset(rt->model_fields, 0, sizeof rt->model_fields);
    mu_obj_body_light(img, rt->model_fields, &light);
    if (mu_obj_i32(img, MU_OBJF_HIDDEN_MESH) == -2 || !pose_object(o, img, m, NULL))
        return NULL;
    mu_obj_event events[40];
    mu_obj_log log = {0, 40, 0, events};
    if (o->world == MU_CSW_WORLD)
        mu_csw_after_render(img, i, &log);   /* NATIVE-CHARSEL-002: RenderBody or the pedestal's glow mesh */
    else if (o->world == MU_LOGIN_WORLD)
        mu_login_after_render(img, rt->model_fields, i, rt->now_ms, NULL, NULL, &log);
    else {
        visual_context c = {o, m};
        mu_world_after_render(img, i, o->world, map ? map->time : 0.0f, &log, visual_bone, &c);
        if ((o->world == 0x50 || o->world == 0x51) && (t == 0x37 || t == 0x39)) {
            mu_model_params params = m->model.params;
            params.light_skip_mesh = 0;
            mu_model_apply_params(&m->model, &params);
        }
        consume_visual(o, &log);
    }
    float color[3];
    memcpy(color, rt->model_fields + MU_MDL_COLOR, 12);   /* the colour the slot restores last */
    float current[3];
    memcpy(current, m->model.params.color, 12);
    for (int32_t e = 0; e < log.count; ++e) {
        const mu_obj_event *ev = &events[e];
        if (ev->call == MU_OBJ_CALL_COLOR) {
            for (int q = 0; q < 3; ++q)
                current[q] = fbits(ev->args[q]);
            continue;
        }
        if (ev->call == MU_OBJ_CALL_BODY && *count < capacity) {   /* the whole body (character select) */
            mu_object_mesh *whole = &meshes[(*count)++];
            body_options(ev, m, map, &whole->options);
            memset(&whole->fields, 0, sizeof whole->fields);
            memcpy(whole->fields.color, current, sizeof current);
            whole->options.fields = NULL;
            ++rt->after_meshes;
            continue;
        }
        if (ev->call != MU_OBJ_CALL_MESH || *count >= capacity)
            continue;
        mu_object_mesh *mesh = &meshes[(*count)++];
        mu_draw_default_options(&mesh->options);
        mesh->options.textures = &m->textures;
        mesh->options.mesh_plus_one = (int32_t)ev->args[0] + 1;
        mesh->options.flags = ev->args[1];
        mesh->options.alpha = fbits(ev->args[2]);
        mesh->options.select = (int32_t)ev->args[3];
        mesh->options.color_scale = fbits(ev->args[4]);
        mesh->options.u_offset = fbits(ev->args[5]);
        mesh->options.v_offset = fbits(ev->args[6]);
        int32_t texture = (int32_t)ev->args[7];
        if (texture == MU_LOGIN_BITMAP_SAILBOAT) {   /* Object95\HSSailboat04_R.jpg: the model's own slot */
            const int32_t slot = texture_slot(m, "HSSailboat04_R.jpg");
            texture = slot >= 0 ? MU_SCENE_TEXTURE_BASE + slot : -1;
        }
        mesh->options.texture = texture;
        mesh->options.time = map ? map->time : 0.0f;
        memset(&mesh->fields, 0, sizeof mesh->fields);
        memcpy(mesh->fields.color, current, sizeof current);
        mesh->options.fields = NULL;   /* set by the caller after copying (points into the array) */
        ++rt->after_meshes;
    }
    (void)color;
    return m;
}

uint32_t mu_objects_billboard_quads(const mu_objects *o, int32_t slot, const float eye[3], const float target[3],
                                    mu_fx_vertex *v, uint32_t capacity, mu_fx_draw_state *state)
{
    const mu_objects_runtime *rt = &o->rt;
    memset(state, 0, sizeof *state);
    if (slot < 0 || slot >= rt->bitmap_count)
        return 0;
    const int32_t bitmap = rt->bitmap_ids[slot];
    const mu_image *image = &rt->bitmaps[slot];
    state->visible = 1;
    state->blend = 1;
    state->texture = image->width > 0;
    state->src = 1u;   /* additive (ONE, ONE), as sprites and these particles are drawn bright */
    state->dst = 1u;
    float forward[3] = {target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]};
    float right[3] = {forward[1], -forward[0], 0.0f};
    float len = sqrtf(right[0] * right[0] + right[1] * right[1]);
    if (len <= 0.0f)
        len = 1.0f;
    right[0] /= len;
    right[1] /= len;
    /* up = right x forward, normalised (the billboard faces the camera) */
    float up[3] = {right[1] * forward[2] - right[2] * forward[1], right[2] * forward[0] - right[0] * forward[2],
                   right[0] * forward[1] - right[1] * forward[0]};
    float ul = sqrtf(up[0] * up[0] + up[1] * up[1] + up[2] * up[2]);
    if (ul <= 0.0f)
        ul = 1.0f;
    for (int q = 0; q < 3; ++q)
        up[q] /= ul;
    const float base = image->width > 0 ? (float)image->width * 0.5f : 32.0f;
    uint32_t n = 0;
    static const float corner[4][2] = {{-1, -1}, {1, -1}, {1, 1}, {-1, 1}};
    static const float uv[4][2] = {{0, 1}, {1, 1}, {1, 0}, {0, 0}};
    for (int32_t i = 0; i < rt->sprite_count && n + 4 <= capacity; ++i) {
        const mu_object_sprite *sp = &rt->sprites[i];
        if (sp->bitmap != bitmap)
            continue;
        const float size = base * sp->scale;
        const float rc = cosf(sp->rotation * 0.017453292f), rs = sinf(sp->rotation * 0.017453292f);
        const float color[4] = {sp->light[0], sp->light[1], sp->light[2], 1.0f};
        for (int q = 0; q < 4; ++q) {
            const float cx = corner[q][0] * rc - corner[q][1] * rs, cy = corner[q][0] * rs + corner[q][1] * rc;
            mu_fx_vertex *x = &v[n++];
            for (int k = 0; k < 3; ++k)
                x->position[k] = sp->position[k] + (right[k] * cx + up[k] * cy) * size;
            x->texcoord[0] = uv[q][0];
            x->texcoord[1] = uv[q][1];
            memcpy(x->color, color, sizeof color);
        }
    }
    for (int32_t i = 0; i < rt->particle_count && n + 4 <= capacity; ++i) {
        const mu_object_particle *p = &rt->particles[i];
        if (p->bitmap != bitmap)
            continue;
        const float f = (float)p->age / (float)p->life;
        const float size = base * 0.5f * p->scale * (1.0f + f);
        const float fade = f < 0.2f ? f * 5.0f : (1.0f - f) * 1.25f;
        const float color[4] = {p->light[0] * fade * 4.0f, p->light[1] * fade * 4.0f, p->light[2] * fade * 4.0f, 1.0f};
        for (int q = 0; q < 4; ++q) {
            mu_fx_vertex *x = &v[n++];
            for (int k = 0; k < 3; ++k)
                x->position[k] = p->position[k] + (right[k] * corner[q][0] + up[k] * corner[q][1]) * size;
            x->texcoord[0] = uv[q][0];
            x->texcoord[1] = uv[q][1];
            memcpy(x->color, color, sizeof color);
        }
    }
    state->vertex_count = n;
    return n;
}

/* ---- stand-in particles ---- */

uint32_t mu_objects_particle_quads(const mu_objects *o, int32_t bitmap, const float eye[3], const float target[3],
                                   mu_fx_vertex *v, uint32_t capacity, mu_fx_draw_state *state)
{
    const mu_objects_runtime *rt = &o->rt;
    const int32_t want = bitmap == 0 ? MU_OBJ_BITMAP_FIRE : MU_OBJ_BITMAP_SMOKE;
    memset(state, 0, sizeof *state);
    state->visible = 1;
    state->blend = 1;
    state->texture = bitmap == 0 ? rt->fire.width > 0 : rt->smoke.width > 0;
    state->src = bitmap == 0 ? 1u : 0x302u;     /* fire: ONE, ONE; smoke: SRC_ALPHA, ONE_MINUS_SRC_ALPHA */
    state->dst = bitmap == 0 ? 1u : 0x303u;
    float forward[3] = {target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]};
    float right[3] = {forward[1], -forward[0], 0.0f};
    float len = sqrtf(right[0] * right[0] + right[1] * right[1]);
    if (len <= 0.0f)
        len = 1.0f;
    right[0] /= len;
    right[1] /= len;
    uint32_t n = 0;
    for (int32_t i = 0; i < rt->particle_count && n + 4 <= capacity; ++i) {
        const mu_object_particle *p = &rt->particles[i];
        if (p->bitmap != want)
            continue;
        const float f = (float)p->age / (float)p->life;
        const float size = bitmap == 0 ? 36.0f * p->scale * (1.0f - 0.6f * f) : 30.0f * p->scale * (1.0f + 1.5f * f);
        const float fade = 1.0f - f;
        const float color[4] = {bitmap == 0 ? p->light[0] * fade : 0.6f, bitmap == 0 ? p->light[1] * fade : 0.6f,
                                bitmap == 0 ? p->light[2] * fade : 0.6f, bitmap == 0 ? 1.0f : 0.5f * fade};
        static const float corner[4][2] = {{-1, -1}, {1, -1}, {1, 1}, {-1, 1}};
        static const float uv[4][2] = {{0, 1}, {1, 1}, {1, 0}, {0, 0}};
        for (int q = 0; q < 4; ++q) {
            mu_fx_vertex *x = &v[n++];
            x->position[0] = p->position[0] + right[0] * corner[q][0] * size;
            x->position[1] = p->position[1] + right[1] * corner[q][0] * size;
            x->position[2] = p->position[2] + corner[q][1] * size;
            x->texcoord[0] = uv[q][0];
            x->texcoord[1] = uv[q][1];
            memcpy(x->color, color, sizeof color);
        }
    }
    state->vertex_count = n;
    return n;
}

long mu_objects_render_raster(mu_objects *o, const mu_world *map, mu_raster *raster, const mu_terrain_frustum *f,
                              int32_t scene_state, const float eye[3], const float target[3])
{
    mu_objects_visibility(o, f, scene_state);
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    const int linear = raster->linear;
    raster->linear = 1;
    long drawn = 0;
    for (int32_t k = 0; k < o->rt.draw_count; ++k) {
        mu_draw_options options;
        mu_object_model *m = mu_objects_prepare(o, k, map, scene_state, &options);
        if (!m)
            continue;
        raster->textures = m->textures.slots;
        raster->texture_count = m->textures.count;
        raster->texture_filter = m->textures.filter;
        raster->texture_wrap = m->textures.wrap;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_object_mesh meshes[4];
        const int32_t count = mu_objects_first_meshes(o, k, map, m, meshes, 4);
        if (count) {
            for (int32_t j = 0; j < count; ++j) {
                meshes[j].options.fields = &meshes[j].fields;
                mu_scene_draw_model(&m->model, &meshes[j].options, &backend, &ds);
            }
            ++drawn;
        } else if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
            ++drawn;
    }
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    raster->linear = linear;
    mu_fx_vertex quads[4 * MU_OBJECT_PARTICLES];
    for (int32_t b = 0; b < 2 && eye && target; ++b) {
        mu_fx_draw_state state;
        const uint32_t n = mu_objects_particle_quads(o, b, eye, target, quads, 4 * MU_OBJECT_PARTICLES, &state);
        if (n)
            mu_effect_raster_quads(raster, quads, n, &state, b == 0 ? &o->rt.fire : &o->rt.smoke, NULL);
    }
    return drawn;
}
