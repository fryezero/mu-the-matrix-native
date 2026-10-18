/* The client's world-object lifecycle in the native session (NATIVE-OBJECTS-002,
 * docs/research/client-objects-render.md): CreateObject, MoveObjects/MoveObject per logic step,
 * RenderObjects/RenderObject per frame, through reconstructed/objects/object_render.c. The
 * calls those routines log are carried out here: the animation tick through the object's model,
 * AddTerrainLight on the frame light, RenderBody through the mesh-draw port. CreateParticle is a
 * labelled stand-in (mu_object_particle). */
#include "mu_objects.h"

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

static void runtime_free(mu_objects_runtime *rt)
{
    free(rt->images);
    free(rt->pointers);
    free(rt->next);
    free(rt->events);
    free(rt->draw_list);
    mu_image_free(&rt->fire);
    mu_image_free(&rt->smoke);
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
    rt->images = calloc((size_t)(n ? n : 1), MU_OBJ_SIZE);
    rt->pointers = calloc((size_t)(n ? n : 1), sizeof *rt->pointers);
    rt->next = calloc((size_t)(n ? n : 1), sizeof *rt->next);
    rt->event_capacity = 4 * n + 4096;
    rt->events = calloc((size_t)rt->event_capacity, sizeof *rt->events);
    rt->draw_list = calloc((size_t)(n ? n : 1), sizeof *rt->draw_list);
    if (!rt->images || !rt->pointers || !rt->next || !rt->events || !rt->draw_list) {
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
        const int status = mu_obj_create(&o->records[i], o->world, img, &sector, i, NULL);
        if (status == MU_OBJ_SKIPPED) {
            ++rt->outside;
            continue;
        }
        if (status == MU_OBJ_UNSUPPORTED) {
            ++rt->create_unsupported;
            const int32_t t = o->records[i].type;
            if (t >= 0 && t < MU_OBJECT_TYPES && o->hidden_type[t])
                mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -2);   /* live sidecar */
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
 * never ask for them. */
static float step_speed(void *context, int32_t type, int32_t action)
{
    (void)context;
    (void)type;
    (void)action;
    return 0.0f;
}

static uint8_t step_handler(void *context, int32_t index)
{
    step_context *c = context;
    if (!c->in->x2d)
        return 0;
    return mu_obj_handler_moves(image(c->o, index), c->o->world, c->in->x2d, c->in->y2d, c->in->scene_state);
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

static void spawn(mu_objects_runtime *rt, const mu_obj_event *e)
{
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
    p->life = p->bitmap == MU_OBJ_BITMAP_FIRE ? 24 : 32;
    p->age = 0;
}

static void particles_step(mu_objects_runtime *rt)
{
    int32_t kept = 0;
    for (int32_t i = 0; i < rt->particle_count; ++i) {
        mu_object_particle p = rt->particles[i];
        if (++p.age >= p.life)
            continue;
        p.position[2] += p.bitmap == MU_OBJ_BITMAP_FIRE ? 2.5f : 3.0f;
        rt->particles[kept++] = p;
    }
    rt->particle_count = kept;
}

void mu_objects_step(mu_objects *o, const mu_objects_step_inputs *in)
{
    mu_objects_runtime *rt = &o->rt;
    if (!rt->ready)
        return;
    particles_step(rt);
    rt->light_count = 0;
    step_context c = {o, in};
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
    mu_obj_event local[64];
    for (int32_t k = 0; k < pass.count; ++k) {
        const mu_obj_event *e = &pass.events[k];
        if (e->call != MU_OBJ_CALL_MOVE_OBJECT)
            continue;
        const int32_t i = e->object, t = mu_obj_i32(image(o, i), MU_OBJF_TYPE);
        mi.has_model = (uint8_t)(t >= 0 && t < MU_OBJECT_TYPES && o->models[t] && o->models[t]->loaded);
        mu_obj_log log = {0, 64, 0, local};
        const int status = mu_obj_move(image(o, i), i, &mi, &log);
        ++rt->moved;
        if (status == MU_OBJ_UNSUPPORTED)
            ++rt->move_unsupported;
        for (int32_t j = 0; j < log.count; ++j) {
            const mu_obj_event *m = &local[j];
            if (m->call == MU_OBJ_CALL_TICK) {
                tick(o, i, fbits(m->args[0]));
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
            }
        }
    }
    ++rt->steps;
}

void mu_objects_apply_lights(const mu_objects *o, mu_world *map)
{
    for (int32_t i = 0; map && i < o->rt.light_count; ++i) {
        const mu_object_light *l = &o->rt.lights[i];
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

mu_object_model *mu_objects_prepare_index(mu_objects *o, int32_t i, const mu_world *map, int32_t scene_state,
                                          mu_draw_options *options)
{
    mu_objects_runtime *rt = &o->rt;
    if (!rt->ready || i < 0 || i >= o->count)
        return NULL;
    uint8_t *img = image(o, i);
    const int32_t t = mu_obj_i32(img, MU_OBJF_TYPE);
    mu_object_model *m = t >= 0 && t < MU_OBJECT_TYPES ? o->models[t] : NULL;
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
    mu_obj_event local[16];
    mu_obj_log log = {0, 16, 0, local};
    memset(rt->model_fields, 0, sizeof rt->model_fields);
    const int status = mu_obj_render(img, i, rt->model_fields, 0, &in, &log);
    mu_obj_visual(img, o->world, in.light.time);   /* RenderObjectVisual follows RenderObject */
    if (status == MU_OBJ_SKIPPED) {
        ++rt->draw_skipped;
        return NULL;
    }
    if (!m || !m->loaded)
        return NULL;
    if (status == MU_OBJ_UNSUPPORTED)
        ++rt->draw_unsupported;
    const mu_obj_event *body = NULL;
    for (int32_t j = 0; j < log.count; ++j)
        if (local[j].call == MU_OBJ_CALL_BODY)
            body = &local[j];
    if (status == MU_OBJ_OK && !body)
        return NULL;   /* a per-world custom render took the object */
    mu_model_params p = m->model.params;
    memcpy(p.origin, img + MU_OBJF_POSITION, 12);
    memcpy(p.angles, img + MU_OBJF_ANGLE, 12);
    p.body_scale = mu_obj_f32(img, MU_OBJF_SCALE);
    memcpy(p.color, rt->model_fields + MU_MDL_COLOR, 12);
    p.lighting = rt->model_fields[MU_MDL_LIGHTING];
    if (o->uniform_light > 0.0f)
        for (int q = 0; q < 3; ++q)
            p.color[q] = o->uniform_light;
    mu_model_apply_params(&m->model, &p);
    mu_model_set_state(&m->model, mu_obj_u16(img, MU_OBJF_ACTION), mu_obj_f32(img, MU_OBJF_FRAME),
                       mu_obj_f32(img, MU_OBJF_PRIOR_FRAME), mu_obj_u16(img, MU_OBJF_PRIOR_ACTION));
    if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
        return NULL;
    mu_draw_default_options(options);
    options->textures = &m->textures;
    if (body) {
        options->flags = body->args[0];
        options->alpha = fbits(body->args[1]);
        options->select = (int32_t)body->args[2];
        options->color_scale = fbits(body->args[3]);
        options->u_offset = fbits(body->args[4]);
        options->v_offset = fbits(body->args[5]);
        options->skip_mesh = (int32_t)body->args[6];
        options->texture = (int32_t)body->args[7];
    } else {   /* unsupported branch: the generic RenderBody arguments */
        options->alpha = mu_obj_f32(img, MU_OBJF_ALPHA);
        options->select = mu_obj_i32(img, MU_OBJF_BLEND_MESH);
        options->color_scale = mu_obj_f32(img, MU_OBJF_BLEND_LIGHT);
        options->u_offset = mu_obj_f32(img, MU_OBJF_BLEND_U);
        options->v_offset = mu_obj_f32(img, MU_OBJF_BLEND_V);
        options->skip_mesh = mu_obj_i32(img, MU_OBJF_HIDDEN_MESH);
    }
    options->time = map ? map->time : 0.0f;
    ++rt->drawn;
    return m;
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
        if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
            ++drawn;
    }
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    raster->linear = linear;
    static mu_fx_vertex quads[4 * MU_OBJECT_PARTICLES];
    for (int32_t b = 0; b < 2 && eye && target; ++b) {
        mu_fx_draw_state state;
        const uint32_t n = mu_objects_particle_quads(o, b, eye, target, quads, 4 * MU_OBJECT_PARTICLES, &state);
        if (n)
            mu_effect_raster_quads(raster, quads, n, &state, b == 0 ? &o->rt.fire : &o->rt.smoke, NULL);
    }
    return drawn;
}
