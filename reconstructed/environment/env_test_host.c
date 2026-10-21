/* Deterministic host for the tests and the Unicorn validator (not client
 * code): synthetic terrain and frustum answers, SetAction with four actions
 * per model, and a log of every host call. scripts/validate_environment.py
 * gives the client's routines the same answers through its stubs. */
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "env.h"
#include "env_test_host.h"

static uint32_t bits(float v)
{
    uint32_t b;
    memcpy(&b, &v, 4);
    return b;
}

uint32_t mu_env_test_mix(uint32_t a, uint32_t b)
{
    uint32_t m = a * 0x9e3779b1u ^ b * 0x85ebca77u;
    m ^= m >> 15;
    m *= 0x2c1b3c6du;
    m ^= m >> 12;
    return m;
}

float mu_env_test_height(const mu_env_test_host *t, float x, float y)
{
    uint32_t m = mu_env_test_mix(bits(x) >> t->height_shift, bits(y) >> t->height_shift);
    return t->height_base + (float)(int32_t)(m % (uint32_t)t->height_span);
}

static mu_env_event *push(mu_env_test_host *t, int32_t kind)
{
    if (t->count >= MU_ENV_TEST_EVENTS) {
        t->overflow = 1;
        return &t->scratch;
    }
    mu_env_event *e = &t->events[t->count++];
    memset(e, 0, sizeof *e);
    e->kind = kind;
    return e;
}

int32_t mu_env_test_index(const mu_env_test_host *t, const mu_env_object *o)
{
    if (!o || !t->env)
        return -1;
    if (o >= t->env->boids && o < t->env->boids + MU_ENV_BOIDS)
        return (int32_t)(o - t->env->boids);
    if (o >= t->env->fishs && o < t->env->fishs + MU_ENV_FISHS)
        return 100 + (int32_t)(o - t->env->fishs);
    return -2;
}

static float h_terrain(void *c, float x, float y) { return mu_env_test_height(c, x, y); }

static void h_sound(void *c, int32_t id, const mu_env_object *o, int32_t loop)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_SOUND);
    e->a = id;
    e->b = mu_env_test_index(c, o);
    e->c = loop;
}

static void h_set_action(void *c, mu_env_object *o, int32_t action)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_SET_ACTION);
    e->a = mu_env_test_index(c, o);
    e->b = action;
    if (action >= 0 && action < 4 && action != o->action) {   /* SetAction with four actions */
        o->prior_action = o->action;
        o->prior_frame = o->frame;
        o->action = (uint16_t)action;
        o->frame = 0.0f;
    }
}

static void h_animate(void *c, mu_env_object *o, float speed)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_ANIMATE);
    e->a = mu_env_test_index(c, o);
    e->b = o->action;
    e->c = o->prior_action;
    e->f[0] = speed;
    e->f[1] = o->frame;
    e->f[2] = o->prior_frame;
}

static void h_particle(void *c, int32_t bitmap, const float p[3], const float a[3], const float l[3], int32_t subtype,
                       float scale)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_PARTICLE);
    e->a = bitmap;
    e->b = subtype;
    for (int k = 0; k < 3; ++k) {
        e->f[k] = p[k];
        e->f[3 + k] = a[k];
        e->f[6 + k] = l[k];
    }
    e->f[9] = scale;
}

static void h_kill(void *c, mu_env_object *o)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_KILL);
    e->a = mu_env_test_index(c, o);
}

static void h_init(void *c, mu_env_object *o)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_INIT);
    e->a = mu_env_test_index(c, o);
}

static int h_has_model(void *c, int32_t model)
{
    const mu_env_test_host *t = c;
    for (int32_t i = 0; i < t->missing_models; ++i)
        if (t->missing_model[i] == model)
            return 0;
    return 1;
}

static void h_effect(void *c, int32_t bitmap, const mu_env_object *o, float scale, int32_t argument)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_EFFECT);
    e->a = bitmap;
    e->b = mu_env_test_index(c, o);
    e->c = argument;
    e->f[0] = scale;
}

void mu_env_test_host_init(mu_env_test_host *t, mu_env *env)
{
    memset(t, 0, sizeof *t);
    t->env = env;
    t->height_base = -100.0f;
    t->height_span = 600;
    t->height_shift = 12;
    t->frustum_mask = 3;
}

void mu_env_test_host_bind(mu_env_test_host *t, mu_env_host *h)
{
    memset(h, 0, sizeof *h);
    h->context = t;
    h->terrain_height = h_terrain;
    h->play_sound = h_sound;
    h->set_action = h_set_action;
    h->animate = h_animate;
    h->create_particle = h_particle;
    h->kill = h_kill;
    h->init = h_init;
    h->has_model = h_has_model;
    h->create_effect = h_effect;
}

/* ---- render ---- */

static int r_frustum(void *c, float x, float y, float range)
{
    mu_env_test_host *t = c;
    int visible = (mu_env_test_mix(bits(x), bits(y) ^ bits(range)) & (uint32_t)t->frustum_mask) != 0;
    mu_env_event *e = push(t, MU_ENV_EVENT_FRUSTUM);
    e->a = visible;
    e->f[0] = x;
    e->f[1] = y;
    e->f[2] = range;
    return visible;
}

static void r_object(void *c, const mu_env_object *o, int32_t a1)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_OBJECT);
    e->a = mu_env_test_index(c, o);
    e->b = a1;
    e->c = o->type;
    for (int k = 0; k < 3; ++k) {
        e->f[k] = o->position[k];
        e->f[3 + k] = o->angle[k];
        e->f[6 + k] = o->light[k];
    }
    e->f[9] = o->scale;
    e->f[10] = o->alpha;
    e->f[11] = o->frame;
}

static void r_sprite(void *c, int32_t bitmap, const float p[3], float scale, const float l[3], const mu_env_object *o)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_SPRITE);
    e->a = bitmap;
    e->b = mu_env_test_index(c, o);
    for (int k = 0; k < 3; ++k) {
        e->f[k] = p[k];
        e->f[4 + k] = l[k];
    }
    e->f[3] = scale;
}

static void r_bone(void *c, const mu_env_object *o, int32_t bone, const float v[3], float out[3])
{
    mu_env_event *e = push(c, MU_ENV_EVENT_BONE);
    e->a = mu_env_test_index(c, o);
    e->b = bone;
    for (int k = 0; k < 3; ++k) {
        e->f[k] = v[k];
        out[k] = v[k] * 2.0f + (float)(k + 1);   /* synthetic bone transform */
    }
}

static void r_alpha_test(void *c, int32_t arg)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_ALPHA_TEST);
    e->a = arg;
}

static void r_alpha_blend(void *c) { push(c, MU_ENV_EVENT_ALPHA_BLEND); }

static void r_color4(void *c, float r, float g, float b, float a)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_COLOR4);
    e->f[0] = r;
    e->f[1] = g;
    e->f[2] = b;
    e->f[3] = a;
}

static void r_color3(void *c, float r, float g, float b)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_COLOR3);
    e->f[0] = r;
    e->f[1] = g;
    e->f[2] = b;
}

static void r_shadow(void *c, const mu_env_object *o, const float origin[3])
{
    mu_env_event *e = push(c, MU_ENV_EVENT_SHADOW);
    e->a = mu_env_test_index(c, o);
    for (int k = 0; k < 3; ++k)
        e->f[k] = origin[k];
}

static void r_bind(void *c, int32_t bitmap)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_BIND);
    e->a = bitmap;
}

static void r_plane(void *c, const float p[3], const float corners[4][3], int32_t count)
{
    mu_env_event *e = push(c, MU_ENV_EVENT_PLANE);
    e->a = count;
    for (int k = 0; k < 3; ++k)
        e->f[k] = p[k];
    if (corners)
        for (int i = 0; i < 4; ++i)
            for (int k = 0; k < 3; ++k)
                e->f[3 + 3 * i + k] = corners[i][k];
}

static void r_billboard(void *c, int32_t bitmap, const float p[3], float w, float h, const float l[3])
{
    mu_env_event *e = push(c, MU_ENV_EVENT_BILLBOARD);
    e->a = bitmap;
    for (int k = 0; k < 3; ++k) {
        e->f[k] = p[k];
        e->f[5 + k] = l[k];
    }
    e->f[3] = w;
    e->f[4] = h;
}

static int r_has_bitmap(void *c, int32_t bitmap)
{
    const mu_env_test_host *t = c;
    for (int32_t i = 0; i < t->missing_bitmaps; ++i)
        if (t->missing_bitmap[i] == bitmap)
            return 0;
    return 1;
}

void mu_env_test_render_bind(mu_env_test_host *t, mu_env_render_host *r)
{
    memset(r, 0, sizeof *r);
    r->context = t;
    r->frustum = r_frustum;
    r->draw_object = r_object;
    r->sprite = r_sprite;
    r->bone_position = r_bone;
    r->has_model = h_has_model;
    r->alpha_test = r_alpha_test;
    r->alpha_blend = r_alpha_blend;
    r->color4 = r_color4;
    r->color3 = r_color3;
    r->shadow = r_shadow;
    r->bind = r_bind;
    r->plane = r_plane;
    r->billboard = r_billboard;
    r->has_bitmap = r_has_bitmap;
}

/* ---- one-allocation session for ctypes ---- */

typedef struct mu_env_test_session {
    mu_env env;
    mu_env_test_host host;
    mu_env_render_host render;
    mu_env_inputs inputs;
} mu_env_test_session;

void *mu_env_test_new(uint32_t seed)
{
    mu_env_test_session *s = calloc(1, sizeof *s);
    if (!s)
        return NULL;
    mu_env_test_host_init(&s->host, &s->env);
    mu_env_host h;
    mu_env_test_host_bind(&s->host, &h);
    mu_env_init(&s->env, seed, &h);
    mu_env_test_render_bind(&s->host, &s->render);
    s->inputs.frame_time = 0.1f;
    return s;
}

void mu_env_test_free(void *session) { free(session); }
mu_env *mu_env_test_env(void *session) { return &((mu_env_test_session *)session)->env; }
mu_env_test_host *mu_env_test_host_of(void *session) { return &((mu_env_test_session *)session)->host; }
mu_env_inputs *mu_env_test_inputs(void *session) { return &((mu_env_test_session *)session)->inputs; }

/* step: 1 leaves, 2 boids, 3 fishs, 4 render boids pass 0, 5 pass 1, 6 render fishs, 7 render leaves */
void mu_env_test_run(void *session, int32_t step)
{
    mu_env_test_session *s = session;
    switch (step) {
    case 1: mu_env_move_leaves(&s->env, &s->inputs); break;
    case 2: mu_env_move_boids(&s->env, &s->inputs); break;
    case 3: mu_env_move_fishs(&s->env, &s->inputs); break;
    case 4: mu_env_render_boids(&s->env, &s->inputs, 0, &s->render); break;
    case 5: mu_env_render_boids(&s->env, &s->inputs, 1, &s->render); break;
    case 6: mu_env_render_fishs(&s->env, &s->inputs, &s->render); break;
    case 7: mu_env_render_leaves(&s->env, &s->inputs, &s->render); break;
    default: break;
    }
}

void mu_env_test_clear_events(void *session)
{
    mu_env_test_session *s = session;
    s->host.count = 0;
    s->host.overflow = 0;
}

void mu_env_test_store(void *session, uint8_t *boids, uint8_t *fishs, uint8_t *leaves)
{
    mu_env_test_session *s = session;
    for (int i = 0; i < MU_ENV_BOIDS && boids; ++i)
        mu_env_object_store(&s->env.boids[i], boids + i * MU_ENV_OBJECT_BYTES);
    for (int i = 0; i < MU_ENV_FISHS && fishs; ++i)
        mu_env_object_store(&s->env.fishs[i], fishs + i * MU_ENV_OBJECT_BYTES);
    for (int i = 0; i < MU_ENV_LEAVES && leaves; ++i)
        mu_env_leaf_store(&s->env.leaves[i], leaves + i * MU_ENV_LEAF_BYTES);
}

void mu_env_test_load(void *session, const uint8_t *boids, const uint8_t *fishs, const uint8_t *leaves)
{
    mu_env_test_session *s = session;
    for (int i = 0; i < MU_ENV_BOIDS && boids; ++i)
        mu_env_object_load(&s->env.boids[i], boids + i * MU_ENV_OBJECT_BYTES);
    for (int i = 0; i < MU_ENV_FISHS && fishs; ++i)
        mu_env_object_load(&s->env.fishs[i], fishs + i * MU_ENV_OBJECT_BYTES);
    for (int i = 0; i < MU_ENV_LEAVES && leaves; ++i)
        mu_env_leaf_load(&s->env.leaves[i], leaves + i * MU_ENV_LEAF_BYTES);
}

/* Field offsets for ctypes (the validator and the tests). */
int32_t mu_env_test_offset(int32_t which)
{
    switch (which) {
    case 0: return (int32_t)offsetof(mu_env, rand_state);
    case 1: return (int32_t)offsetof(mu_env, rand_calls);
    case 2: return (int32_t)offsetof(mu_env, rain_target);
    case 3: return (int32_t)offsetof(mu_env, rain_level);
    case 4: return (int32_t)offsetof(mu_env, wind_8ca8);
    case 5: return (int32_t)offsetof(mu_env, wind_8cac);
    case 6: return (int32_t)offsetof(mu_env, wind_8cb0);
    case 7: return (int32_t)offsetof(mu_env, tormenta.weather);
    case 8: return (int32_t)offsetof(mu_env, tormenta.rain_max);
    case 9: return (int32_t)offsetof(mu_env, tormenta.rain);
    case 20: return (int32_t)offsetof(mu_env_test_host, height_base);
    case 21: return (int32_t)offsetof(mu_env_test_host, height_span);
    case 22: return (int32_t)offsetof(mu_env_test_host, height_shift);
    case 23: return (int32_t)offsetof(mu_env_test_host, frustum_mask);
    case 24: return (int32_t)offsetof(mu_env_test_host, missing_models);
    case 25: return (int32_t)offsetof(mu_env_test_host, missing_model);
    case 26: return (int32_t)offsetof(mu_env_test_host, missing_bitmaps);
    case 27: return (int32_t)offsetof(mu_env_test_host, missing_bitmap);
    case 28: return (int32_t)offsetof(mu_env_test_host, count);
    case 29: return (int32_t)offsetof(mu_env_test_host, events);
    case 30: return (int32_t)sizeof(mu_env_event);
    default: return -1;
    }
}

/* NATIVE-FIDELITY-001: the body light of boid (which 0) or fish (which 1) `index` (mu_env_body_light). */
void mu_env_test_body_light(void *session, int32_t which, int32_t index, const float frame_light[3], float color[3],
                            uint8_t *lighting)
{
    mu_env_test_session *s = session;
    const mu_env_object *o = which ? &s->env.fishs[index] : &s->env.boids[index];
    mu_env_body_light(o, frame_light, color, lighting);
}
