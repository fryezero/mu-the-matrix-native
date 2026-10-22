/* The Dark Raven (Dark Spirit): see raven.h and docs/research/client-dark-spirit.md. */
#include "raven.h"

#include <math.h>
#include <string.h>

#include "../movement/client_movement.h"
#include "../record-math/record_math.h"

#ifndef MU_RV_MUTATION
#define MU_RV_MUTATION 0
#endif

void mu_rv_init(mu_raven *r, uint32_t rand_seed, mu_rv_owner *owners, int32_t owner_count, const mu_rv_host *host)
{
    memset(r, 0, sizeof *r);
    r->rand_state = rand_seed;
    r->owners = owners;
    r->owner_count = owner_count;
    if (host)
        r->host = *host;
}

int32_t mu_rv_rand(mu_raven *r)
{
    r->rand_state = r->rand_state * 214013u + 2531011u;
    ++r->rand_calls;
    return (int32_t)((r->rand_state >> 16) & 0x7fff);
}

static mu_rv_owner *owner_of(mu_raven *r, int32_t owner)
{
    if (owner < 0 || owner >= r->owner_count || owner >= MU_RV_OWNERS)
        return NULL;
    return &r->owners[owner];
}

static int has_model(const mu_raven *r, int32_t model)
{
    return r->host.has_model ? r->host.has_model(r->host.context, model) : 1;
}

/* the client's sqrtf 0x00961a07: (float)sqrt((double)x) */
static float sqrt_f(float x)
{
    return (float)sqrt((double)x);
}

/* ------------------------------------------------------------------ creation */

/* 0x009ec878 */
void mu_rv_set_ai(mu_rv_pet *p, uint8_t ai)
{
    p->object.ai = ai;
    p->object.lifetime = 0;
}

/* 0x009ecb21 */
void mu_rv_alpha_step(mu_rv_pet *p, float step)
{
    mu_rv_object *o = &p->object;
    o->alpha = o->alpha + step;
    if (o->alpha <= 0.0f) {   /* comiss 0, alpha; jb: taken when 0 < alpha or unordered */
        o->alpha = 0.0f;
        p->fade_out = 0;
    } else if (o->alpha >= 1.0f) {
        o->alpha = 1.0f;
        p->fade_in = 0;
    }
}

/* ObjectInit 0x0129eb81 on the modelled fields */
static void object_init(mu_rv_object *o)
{
    memset(o, 0, sizeof *o);
}

void mu_rv_create_pointer(mu_raven *r, mu_rv_pet *p, int32_t type, int32_t x, int32_t y, float angle)
{
    mu_rv_object *o = &p->object;
    p->target = -1;
    p->command = 0;
    p->info_level = -1;
    object_init(o);
    p->tile[0] = x & 0xff;
    p->tile[1] = y & 0xff;
    p->tile_byte[0] = (uint8_t)x;
    p->tile_byte[1] = (uint8_t)y;
    p->byte_29 = 0;
    uint16_t wall = r->host.terrain_wall ? r->host.terrain_wall(r->host.context, p->tile[0], p->tile[1]) : 0;
    p->safe = (uint8_t)((wall & 1) ? 1 : 0);   /* 0x0129de3a */
    o->live = 1;                               /* SetLive 0x0129f4a5 */
    o->visible = 0;
    o->alpha_enable = 1;
    o->lighting = 1;
    o->flag_0e = 0;
    o->flag_0d = 1;
    o->flag_04 = 0;
    p->counter = 0;
    o->type = type;
    o->scale = 0.7f;
    o->field_b4 = 0.0f;
    o->alpha = 1.0f;
    o->alpha_target = 1.0f;
    o->velocity = 0.0f;
    o->field_c4 = 0.0f;
    o->flag_40 = 0;
    o->ai = 0;
    o->velocity = 1.0f;
    o->field_c8 = 13.0f;
    o->target = 0;
    o->flag_44 = 0;
    o->prior_action = 0;
    o->action = 0;
    o->frame = 0.0f;
    o->prior_frame = 0.0f;
    o->hidden_mesh = -1;
    o->subtype = 0;
    o->uv[0] = 0.0f;
    o->uv[1] = 0.0f;
    o->position[0] = (float)p->tile[0] * 100.0f + 50.0f;
    o->position[1] = (float)p->tile[1] * 100.0f + 50.0f;
    o->time = 0;   /* [0x0bdc5eb0]: set by the caller (mu_rv_create) */
    o->position[2] = r->host.terrain_height ? r->host.terrain_height(r->host.context, o->position[0], o->position[1])
                                            : 0.0f;
    o->angle[0] = 0.0f;
    o->angle[1] = 0.0f;
    o->angle[2] = angle;
    o->light[0] = o->light[1] = o->light[2] = 0.5f;
    o->box_min[0] = -60.0f;
    o->box_min[1] = -60.0f;
    o->box_min[2] = 0.0f;
    o->box_max[0] = 50.0f;
    o->box_max[1] = 50.0f;
    o->box_max[2] = 150.0f;
    if (has_model(r, type)) {
        o->field_c0 = 200.0f;
        p->level = 0;
        o->blend_mesh = -1;
        o->blend_light = 1.0f;
        p->command = 0;
    }
}

static void mount_lift(mu_raven *r, const mu_rv_owner *w, float *z)
{
    (void)r;
    if (w->has_mount) {   /* 0x0106b93a: the mount's rider offset z + 30 */
        float t = w->mount_offset_z + 30.0f;
        *z = t + *z;
    }
}

/* the Dark Raven's constructor 0x009ecbdf */
static void raven_ctor(mu_raven *r, const mu_rv_inputs *in, mu_rv_pet *p, int32_t owner)
{
    mu_rv_owner *w = owner_of(r, owner);
    memset(p, 0, sizeof *p);
    p->live = 1;
    p->cls = 1;
    p->slot = 0;
    p->owner = owner;
    p->target = -1;
    p->info_level = -1;
    int32_t x = w->tile[0], y = w->tile[1];
    int model = has_model(r, w->type);
    int bone = r->host.bone ? r->host.bone(r->host.context, MU_RV_OWNER_OBJECT, owner, 0x23) : 0;
    int32_t type = w->safe == 1 ? MU_RV_MODEL_SOUL : MU_RV_MODEL_RAVEN;
    if (!bone || !model) {
        mu_rv_create_pointer(r, p, type, x, y, 0.0f);
        p->object.position[2] = p->object.position[2] + (type == MU_RV_MODEL_SOUL ? 250.0f : 300.0f);
    } else {
        const float v[3] = {0.0f, 20.0f, 20.0f};
        float out[3] = {0.0f, 0.0f, 0.0f};
        if (r->host.transform_base)
            r->host.transform_base(r->host.context, w->type, MU_RV_OWNER_OBJECT, owner, 0x23, w->position, v, out);
        mount_lift(r, w, &out[2]);
        out[2] = out[2] + 30.0f;
        x = (int32_t)(out[0] / 100.0f);
        y = (int32_t)(out[1] / 100.0f);
        if (x < 0 || y < 0) {
            x = w->tile[0];
            y = w->tile[1];
            out[2] = w->position[2] + 250.0f;
        }
        mu_rv_create_pointer(r, p, type, x, y, 0.0f);
        p->object.position[2] = out[2];
    }
    p->object.time = in->tick;
    p->object.action = 0;
    p->object.alpha = 0.1f;
    p->fade_in = 1;
    p->fade_out = 0;
}

void mu_rv_delete(mu_raven *r, int32_t owner)
{
    if (owner < 0 || owner >= MU_RV_OWNERS)
        return;
    memset(&r->pets[owner], 0, sizeof r->pets[owner]);
}

void mu_rv_create(mu_raven *r, const mu_rv_inputs *in, int32_t owner)
{
    mu_rv_owner *w = owner_of(r, owner);
    if (!w)
        return;
    mu_rv_delete(r, owner);
    int32_t item = w->pet_item;
    if (item == MU_RV_ITEM_DARK_RAVEN) {
        raven_ctor(r, in, &r->pets[owner], owner);
        return;
    }
    if (item == 0x28f8 || item == 0x28f9 || item == 0x28fa || item == 0x2900) {
        /* 0x009f0258: the later raven class (vtable 0x01a7fae8), not ported */
        if (r->host.unsupported)
            r->host.unsupported(r->host.context, owner, item);
    }
}

int mu_rv_set_type(mu_raven *r, const mu_rv_inputs *in, int32_t owner, uint8_t value)
{
    mu_rv_owner *w = owner_of(r, owner);
    if (!w)
        return 0;
    switch (value) {
    case 0:
        w->pet_item = -1;
        w->pet_level = 0;
        mu_rv_delete(r, owner);
        return 1;
    case 1: w->pet_item = MU_RV_ITEM_DARK_RAVEN; w->pet_level = 1; break;
    case 2: w->pet_item = MU_RV_ITEM_DARK_RAVEN; w->pet_level = 0x14; break;
    case 3: w->pet_item = MU_RV_ITEM_DARK_RAVEN; w->pet_level = 0x28; break;
    case 10: w->pet_item = 0x28f8; w->pet_level = 1; break;
    case 11: w->pet_item = 0x28f9; w->pet_level = 1; break;
    case 12: w->pet_item = 0x28fa; w->pet_level = 1; break;
    case 13: w->pet_item = 0x2900; w->pet_level = 1; break;
    default:
        return 0;
    }
    mu_rv_create(r, in, owner);
    if (r->pets[owner].live && (value == 2 || value == 3))
        r->pets[owner].level = w->pet_level;   /* 0x009ec097 */
    return 1;
}

int mu_rv_model_fits(const mu_raven *r, int32_t owner)
{
    if (owner < 0 || owner >= r->owner_count || owner >= MU_RV_OWNERS)
        return 1;
    const mu_rv_pet *p = &r->pets[owner];
    if (p->slot != 0)
        return 1;
    int32_t t = p->object.type;
    if (r->owners[owner].safe == 1)
        return t == 0x748 || t == 0x750 || t == 0x751 || t == 0x752;
    return t == 0x411 || t == 0x74d || t == 0x74e || t == 0x74f;
}

/* ------------------------------------------------------------------ MovePet 0x009ecfe9 */

static int buff(const mu_rv_owner *w, int32_t id)
{
    switch (id) {
    case 0x12: return w->buff_12;
    case 0x3d: return w->buff_3d;
    case 0xb2: return w->buff_b2;
    case 0x118: return w->buff_118;
    default: return 0;
    }
}

static int pet_bone(mu_raven *r, int32_t which, int32_t owner, int32_t index)
{
    return r->host.bone ? r->host.bone(r->host.context, which, owner, index) : 0;
}

/* AI 0 / 1 (0x009ed8bf..0x009ee19d). Returns 0 for the early return. */
static int fly(mu_raven *r, const mu_rv_inputs *in, mu_rv_pet *p, mu_rv_owner *w, const float target[3],
               const float delta[3])
{
    mu_rv_object *o = &p->object;
    const float range = 150.0f;
    o->target = 0;
    const float light[3] = {0.3f, 0.4f, 0.7f};
    if (!w->buff_12) {
        int32_t b = mu_rv_rand(r) % 0x42;
        if (!pet_bone(r, MU_RV_PET_OBJECT, p->owner, b))
            return 0;
        const float zero[3] = {0.0f, 0.0f, 0.0f};
        float out[3] = {0.0f, 0.0f, 0.0f};
        if (r->host.transform)
            r->host.transform(r->host.context, w->type, MU_RV_PET_OBJECT, p->owner, b, zero, out, 1);
        if (r->host.particle)
            r->host.particle(r->host.context, MU_RV_BITMAP_SPARK3, out, o->angle, light, 5, 0.8f);
    }
    float d2 = delta[0] * delta[0];
    d2 = d2 + delta[1] * delta[1];
    if (d2 >= range * range) {   /* comiss d2, 150²; jb skip */
        float a = mu_create_angle(o->position[0], o->position[1], target[0], target[1]);
#if MU_RV_MUTATION == 1
        float step = (float)(mu_rv_rand(r) % 0xf) + 6.0f;
#else
        float step = (float)(mu_rv_rand(r) % 0xf) + 5.0f;
#endif
        o->angle[2] = mu_turn_angle2(o->angle[2], a, step);
    }
    mu_angle_matrix(o->angle, o->matrix);
    float v[3];
    mu_vector_rotate(o->direction, o->matrix, v);
    o->position[0] = o->position[0] + v[0];
    o->position[1] = o->position[1] + v[1];
    o->position[2] = o->position[2] + v[2];
    int32_t modulus = 0x1c, altitude = 0xfa, band = 0x64;
    uint16_t ride = w->ride;
    int horse = ride == 0x1a04 || ride == 0x28f7;   /* 0x00c92e9a == 1 */
    if (horse || in->world == 0x37) {
        altitude = 0x15e;
    } else if (w->mount_state2) {
        altitude = 0x154;
        band = 0x1e;
    }
    float high = (float)altitude + target[2];
    if (high > o->position[2]) {   /* comiss high, z; jbe skip */
        modulus = 10;
        o->angle[0] = o->angle[0] - 2.0f;
        if (-15.0f > o->angle[0])
            o->angle[0] = -15.0f;
    } else if (o->position[2] > (float)band + high) {
        modulus = 0x14;
        o->angle[0] = o->angle[0] + 2.0f;
        if (o->angle[0] > 15.0f)
            o->angle[0] = 15.0f;
    }
    float dy = 0.0f;
    if (mu_rv_rand(r) % modulus == 0) {
        if (d2 >= range * range) {   /* comiss d2, 150²; jb */
            dy = -(float)(mu_rv_rand(r) % 64 + 0x80) * 0.1f;
        } else {
            dy = -(float)(mu_rv_rand(r) % 8 + 0x20) * 0.1f;
            o->angle[2] = (float)(mu_rv_rand(r) % 0x3c) + o->angle[2];
        }
        dy = dy + o->direction[1];
        dy = dy / 2.0f;
        int32_t low = 0x20, span = low + 0x20;
        if (w->mount_state2) {
            low = high > o->position[2] ? 0 : 0x10;
            span = o->position[2] > (float)band + high ? low : low + 0x10;
        }
        o->direction[0] = 0.0f;
        o->direction[1] = dy;
        o->direction[2] = (float)(mu_rv_rand(r) % span - low) * 0.1f;
    }
    if (-12.0f > o->direction[1]) {
        if (o->ai != 0)
            mu_rv_set_ai(p, 0);
    } else if (o->ai != 1) {
        mu_rv_set_ai(p, 1);
    }
    if (p->fade_in)
        o->direction[1] = o->direction[1] - 1.5f;
    return 1;
}

/* MoveHumming 0x012af2f1(position, angle, target, turn): the turn toward the target, the returned distance */
static float move_humming(const float position[3], float angle[3], const float target[3], float turn)
{
    float a = mu_create_angle(position[0], position[1], target[0], target[1]);
    angle[2] = mu_turn_angle2(angle[2], a, turn);
    float d[3] = {position[0] - target[0], position[1] - target[1], position[2] - target[2]};
    float h = sqrt_f(d[0] * d[0] + d[1] * d[1]);
    float b = mu_create_angle(position[2], h, target[2], 0.0f);
    angle[0] = mu_turn_angle2(angle[0], 360.0f - b, turn);
    float l = d[0] * d[0];
    l = l + d[1] * d[1];
    l = l + d[2] * d[2];
    return sqrt_f(l);
}

/* AI 3 (0x009ee66e..0x009ef3b0). Returns 0 for the early return. */
static int sit(mu_raven *r, mu_rv_pet *p, mu_rv_owner *w)
{
    mu_rv_object *o = &p->object;
    const float v[3] = {0.0f, 20.0f, 20.0f};
    if (o->type == MU_RV_MODEL_RAVEN) {
        mu_angle_matrix(o->angle, o->matrix);
        if (!(o->velocity == 0.0f)) {   /* ucomiss/lahf/jnp: skipped only for an ordered equal */
            float d[3] = {0.0f, -o->velocity, 0.0f}, m[3];
            mu_vector_rotate(d, o->matrix, m);
            o->position[0] = o->position[0] + m[0];
            o->position[1] = o->position[1] + m[1];
            o->position[2] = o->position[2] + m[2];
        }
        int32_t bone = 0x23;
        if (!pet_bone(r, MU_RV_OWNER_OBJECT, p->owner, bone)) {
            bone = 0;
            if (!pet_bone(r, MU_RV_OWNER_OBJECT, p->owner, bone))
                return 0;
        }
        float out[3] = {0.0f, 0.0f, 0.0f};
        if (r->host.transform)
            r->host.transform(r->host.context, w->type, MU_RV_OWNER_OBJECT, p->owner, bone, v, out, 0);
        out[0] = w->scale * out[0];
        out[1] = w->scale * out[1];
        out[2] = w->scale * out[2];
        out[0] = w->position[0] + out[0];
        out[1] = w->position[1] + out[1];
        out[2] = w->position[2] + out[2];
        mount_lift(r, w, &out[2]);
        float d = move_humming(o->position, o->angle, out, o->velocity);
        o->velocity = o->velocity + 1.0f;
        if (50.0f > d) {
            o->velocity = 0.0f;
            if (r->host.set_action)
                r->host.set_action(r->host.context, o, 0);
        }
        return 1;
    }
    float k = 1.0f, divisor = 5.0f, bob = 0.0f;
    if (!pet_bone(r, MU_RV_OWNER_OBJECT, p->owner, 0x23))
        return 0;
    float out[3] = {0.0f, 0.0f, 0.0f};
    if (r->host.transform_base)
        r->host.transform_base(r->host.context, w->type, MU_RV_OWNER_OBJECT, p->owner, 0x23, w->position, v, out);
    mount_lift(r, w, &out[2]);
    out[2] = out[2] + 30.0f;
    int32_t keys = r->host.action_keys ? r->host.action_keys(r->host.context, w->type, w->action) : 1;
    float n = (float)keys;
    float t = w->frame - 3.0f;
    if (0.0f > t)
        t = n + t;
    float q = (float)fabs((double)(n * 0.5f - t));
    q = q / (n * 0.5f);
#if MU_RV_MUTATION == 2
    bob = q * 2.0f;
#else
    bob = q * 2.5f;
#endif
    float dx = o->position[0] - out[0], dy = o->position[1] - out[1];
    float dist = sqrt_f(dx * dx + dy * dy);   /* 0x00d01566 */
    float start[3];
    if (500.0f > dist)
        memcpy(start, o->position, sizeof start);
    else
        memcpy(start, out, sizeof start);
    float diff[3] = {start[0] - out[0], start[1] - out[1], start[2] - out[2]};
    diff[0] = -k * diff[0];
    diff[1] = -k * diff[1];
    diff[2] = -k * diff[2];
    if (o->type == MU_RV_MODEL_RAVEN)
        divisor = 20.0f;
    float step[3] = {1.0f / divisor * diff[0], 1.0f / divisor * diff[1], 1.0f / divisor * diff[2]};
    float next[3] = {start[0] + step[0], start[1] + step[1], start[2] + step[2]};
    next[2] = next[2] + bob;
    if (r->host.model_origin)
        r->host.model_origin(r->host.context, o->type, next);
    memcpy(o->position, next, sizeof next);
    /* the parent matrix 0x078965ac: AngleMatrix(model +0x84) . AngleMatrix(0) */
    float zero[3] = {0.0f, 0.0f, 0.0f}, body[3] = {0.0f, 0.0f, 0.0f};
    float local[3][4], parent[3][4], out_m[3][4];
    mu_angle_matrix(zero, local);
    if (r->host.body_angle)
        r->host.body_angle(r->host.context, o->type, body);
    mu_angle_matrix(body, parent);
    mu_pose_concat(parent, local, out_m);
    if (r->host.parent_matrix)
        r->host.parent_matrix(r->host.context, (const float (*)[4])out_m);
    return 1;
}

int mu_rv_move_pet(mu_raven *r, const mu_rv_inputs *in, int32_t owner)
{
    mu_rv_owner *w = owner_of(r, owner);
    if (!w)
        return 0;
    mu_rv_pet *p = &r->pets[owner];
    mu_rv_object *o = &p->object;
    if (p->fade_in) {
        mu_rv_alpha_step(p, 0.1f);
    } else if (p->fade_out) {
        float dx = w->position[0] - o->position[0];
        float dy = w->position[1] - o->position[1];
        float d = sqrt_f(dx * dx + dy * dy);
        if (50.0f > d)
            mu_rv_alpha_step(p, -0.1f);
        else
            mu_rv_alpha_step(p, 7.5f / d * -1.0f);
    } else if (1.0f > o->alpha) {
        o->alpha = 1.0f;
    }
    if (buff(w, 0x3d) || buff(w, 0xb2) || buff(w, 0x118))
        return 0;
    if (!has_model(r, w->type) || !has_model(r, o->type))
        return 0;
    o->level = (uint8_t)p->level;
    if (!r->requested) {
        p->command = 0;
        if (r->host.request)   /* the pet-info request (0xc1 0xc8 slot 0x78 0xff 0xff), then [0x01d1e028 + 8] = 1 */
            r->host.request(r->host.context, owner, p->slot);
        r->requested = 1;
    }
    /* the target character 0x009a13f4(key): none offline (the attack branches are not ported) */
    if (r->host.find)
        r->host.find(r->host.context, p->target_key);
    if (w->buff_12 && (o->ai == 4 || o->ai == 2 || o->ai == 5)) {
        p->target_key = -1;
        if (r->host.request)
            r->host.request(r->host.context, owner, p->slot);
    }
    p->safe = w->safe;   /* 0x0129de3a */
    if (o->ai != 3 && w->safe == 1 && p->safe == 1)
        mu_rv_set_ai(p, 3);
    float speed = p->slot != 0 ? 0.1f : 0.4f;
    int playing = 0;
    if (has_model(r, o->type) && r->host.animate)
        playing = r->host.animate(r->host.context, o, o->type, speed);
    if (!playing && r->host.set_action) {
        int32_t action;
        switch (o->ai) {
        case 0: action = 1; break;
        case 1: action = 0; break;
        case 2: action = 3; break;
        case 3: action = 1; break;
        case 4: action = 3; break;
        default: action = 0; break;
        }
        r->host.set_action(r->host.context, o, action);
    }
    float target[3], delta[3];
    memcpy(target, w->position, sizeof target);   /* (a target character only through the server's commands) */
    delta[0] = target[0] - o->position[0];
    delta[1] = target[1] - o->position[1];
    delta[2] = target[2] - o->position[2];
    switch (o->ai) {
    case 0:
    case 1:
        if (!fly(r, in, p, w, target, delta))
            return 0;
        break;
    case 3:
        if (!sit(r, p, w))
            return 0;
        break;
    default:
        break;   /* 2, 4, 5: the attacks (static, not ported) */
    }
    if (o->ai >= 4 && o->ai <= 5) {
        p->counter = (uint8_t)(p->counter + 1);
        if (p->counter >= 0xf)
            p->counter = 0xf;
    }
    if (mu_rv_rand(r) % 100 == 0 && (int32_t)in->tick % 0x3c == 0 && r->host.sound)
        r->host.sound(r->host.context, 0x1d1, owner);
    float back[3] = {w->position[0] - o->position[0], w->position[1] - o->position[1], w->position[2] - o->position[2]};
    float far2 = back[0] * back[0];
    far2 = far2 + back[1] * back[1];
#if MU_RV_MUTATION == 3
    if (w->position[2] - 200.0f > o->position[2] || far2 > 360000.0f)
#else
    if (w->position[2] - 200.0f > o->position[2] || far2 > 409600.0f)
#endif
        o->lifetime++;
    if (o->lifetime > 0x5a) {
        o->lifetime = 0;
        memcpy(o->position, w->position, sizeof o->position);
        o->position[2] = o->position[2] + 250.0f;
    }
    return 1;
}

void mu_rv_move(mu_raven *r, const mu_rv_inputs *in, int32_t owner)
{
    if (owner < 0 || owner >= r->owner_count || owner >= MU_RV_OWNERS || !r->pets[owner].live)
        return;
    mu_rv_pet *p = &r->pets[owner];
    if (p->cls == 1)
        mu_rv_move_pet(r, in, owner);   /* vtable +4 */
    if (0.0f >= p->object.alpha) {      /* comiss 0, alpha; jb skip */
        mu_rv_create(r, in, owner);
        p = &r->pets[owner];
        if (!p->live)
            return;
    }
    if (!(p->fade_in | p->fade_out) && !mu_rv_model_fits(r, owner))
        p->fade_out = 1;   /* 0x00c96119 */
}

/* ------------------------------------------------------------------ render */

int mu_rv_world_9dacb8(int32_t world)
{
    return (world >= 0x12 && world <= 0x17) || world == 0x35 || world == 0x61;
}

/* RenderPet 0x009ef6d5 */
static void render_pet(mu_raven *r, mu_rv_pet *p, int32_t a3, const mu_rv_render_host *rh)
{
    mu_rv_object *o = &p->object;
    if (p->info_level >= 0)
        o->level = (uint8_t)p->info_level;
    if (!o->live)
        return;
    int v = rh->frustum ? rh->frustum(rh->context, o->position[0] * 0.01f, o->position[1] * 0.01f, -20.0f) : 1;
    o->visible = (uint8_t)v;
    if (!o->visible) {
        o->velocity = 3.0f;
        return;
    }
    const mu_rv_owner *w = &r->owners[p->owner];
    if (w->type == MU_RV_MODEL_PLAYER || o->type == MU_RV_MODEL_RAVEN || o->type == MU_RV_MODEL_SOUL) {
        if (o->type == MU_RV_MODEL_SOUL)
            o->scale = 0.3f;
        if (rh->draw_object)
            rh->draw_object(rh->context, o, p->owner, a3);
        /* the effects 0x009ef9a5: the attack AI 4 / 5 only (not ported) */
    }
}

void mu_rv_render(mu_raven *r, const mu_rv_inputs *in, int32_t owner, const mu_rv_render_host *rh)
{
    mu_rv_owner *w = owner_of(r, owner);
    if (!w || !r->pets[owner].live)
        return;
    mu_rv_pet *p = &r->pets[owner];
    if (w->buff_12) {
        if (p->cls == 1)
            render_pet(r, p, 10, rh);
        return;
    }
    if (w->hero) {
        p->info_level = w->has_info ? w->info_level : -1;   /* 0x00c08bcd(0x0129dabe(c, 0)) */
        if (w->has_info && w->info_type != -1 && !mu_rv_world_9dacb8(in->world) && p->cls == 1)
            render_pet(r, p, 0, rh);
    } else if (!mu_rv_world_9dacb8(in->world) && p->cls == 1) {
        render_pet(r, p, 0, rh);
    }
}

/* ------------------------------------------------------------------ the render functors */

static mu_rv_draw *push(mu_rv_draw_list *l, int32_t kind, const float color[3])
{
    if (l->count >= (int32_t)(sizeof l->items / sizeof l->items[0]))
        return NULL;
    mu_rv_draw *d = &l->items[l->count++];
    memset(d, 0, sizeof *d);
    d->kind = kind;
    d->mesh = -1;
    d->hidden = -1;
    d->texture = -1;
    if (color)
        memcpy(d->color, color, sizeof d->color);
    return d;
}

static void mesh(mu_rv_draw_list *l, const float color[3], int32_t index, int32_t flags, float alpha, int32_t blend,
                 float blend_light, const float uv[2], int32_t texture)
{
    mu_rv_draw *d = push(l, MU_RV_DRAW_MESH, color);
    if (!d)
        return;
    d->mesh = index;
    d->flags = flags;
    d->alpha = alpha;
    d->blend_mesh = blend;
    d->blend_light = blend_light;
    d->uv[0] = uv[0];
    d->uv[1] = uv[1];
    d->texture = texture;
}

static void shadow(mu_rv_draw_list *l, const float color[3], const mu_rv_draw_inputs *in, float alpha,
                   const float origin[3])
{
    if (in->world == 10 || in->world == 0x84 || in->shadow_world || in->event_block)
        return;
    mu_rv_draw *d = push(l, MU_RV_DRAW_SHADOW, color);
    if (!d)
        return;
    d->alpha = alpha;
    memcpy(d->vector, origin, sizeof d->vector);
}

int mu_rv_draw_raven(const mu_rv_object *o, const mu_rv_draw_inputs *in, const mu_rv_draw_host *h,
                     mu_rv_draw_list *out)
{
    out->count = 0;
    float color[3] = {in->color[0], in->color[1], in->color[2]};
    mu_rv_draw *d = push(out, MU_RV_DRAW_COLOR3, color);
    if (d)
        d->vector[0] = d->vector[1] = d->vector[2] = 1.0f;
    d = push(out, MU_RV_DRAW_PUSH, color);
    if (d)
        d->alpha = o->alpha;
    mesh(out, color, 3, 2, o->alpha, o->blend_mesh, o->blend_light, o->uv, o->hidden_mesh);
    int8_t level = (int8_t)o->level;
#if MU_RV_MUTATION == 4
    if (level < 0x20) {
#else
    if (level < 0x28) {
#endif
        mesh(out, color, level < 0x14 ? 2 : 1, 2, o->alpha, o->blend_mesh, o->blend_light, o->uv, o->hidden_mesh);
    } else {
        mesh(out, color, 0, 2, o->alpha, o->blend_mesh, o->blend_light, o->uv, o->hidden_mesh);
        color[0] = 0.3f;
        color[1] = 0.6f;
        color[2] = 1.0f;
        mesh(out, color, 0, 0x44, o->alpha, o->blend_mesh, o->blend_light, o->uv, o->hidden_mesh);
        color[0] = color[1] = color[2] = 1.0f;
        float s = h && h->sine ? h->sine(h->context, in->time * 0.001f) : 0.0f;
        mesh(out, color, 3, 0x42, o->alpha, 3, s, o->uv, MU_RV_TEXTURE_RAVEN);
    }
    push(out, MU_RV_DRAW_POP, color);
    float origin[3] = {o->position[0], o->position[1], 0.0f};
    origin[2] = h && h->terrain_height ? h->terrain_height(h->context, o->position[0], o->position[1]) : 0.0f;
    shadow(out, color, in, in->dim_world ? 0.2f : 1.0f, origin);
    return 1;
}

int mu_rv_draw_soul(mu_rv_object *o, const mu_rv_draw_inputs *in, const mu_rv_draw_host *h, mu_rv_draw_list *out)
{
    out->count = 0;
    o->angle[2] = o->angle[2] + 2.0f;
    if (o->angle[2] >= 360.0f)
        o->angle[2] = 0.0f;
    float saved[3] = {in->color[0], in->color[1], in->color[2]};
    float color[3] = {saved[0], saved[1], saved[2]};
    mu_rv_draw *d = push(out, MU_RV_DRAW_BODY, color);
    if (d) {
        d->flags = 2;
        d->alpha = o->alpha;
        d->blend_mesh = o->blend_mesh;
        d->blend_light = o->blend_light;
        d->uv[0] = o->uv[0];
        d->uv[1] = o->uv[1];
        d->hidden = o->hidden_mesh;
    }
    color[0] = 0.5f;
    color[1] = 0.1f;
    color[2] = 0.9f;
    mesh(out, color, 0, 0x44, o->alpha, 0, o->blend_light, o->uv, MU_RV_TEXTURE_SOUL);
    color[0] = color[1] = color[2] = 0.3f;
    mesh(out, color, 1, 0x42, o->alpha, 1, o->blend_light, o->uv, -1);
    memcpy(color, saved, sizeof color);
    float k = h && h->wave ? h->wave(h->context, -4.0f, 0) : 0.0f;
    color[0] = color[0] * k;
    color[1] = color[1] * k;
    color[2] = color[2] * k;
    mesh(out, color, 1, 0x42, o->alpha, 1, o->blend_light, o->uv, -1);
    float light[3] = {0.6f, 0.2f, 0.9f};
    d = push(out, MU_RV_DRAW_SPRITE, color);
    if (d) {
        d->bitmap = MU_RV_BITMAP_FLARE;
        d->scale = 1.0f;
        memcpy(d->vector, o->position, sizeof d->vector);
        memcpy(d->light, light, sizeof d->light);
    }
    float z = h && h->random_float ? h->random_float(h->context, -10.0f, 10.0f, 100) : 0.0f;
    float y = h && h->random_float ? h->random_float(h->context, -3.0f, 3.0f, 100) : 0.0f;
    float x = h && h->random_float ? h->random_float(h->context, -3.0f, 3.0f, 100) : 0.0f;
    float s = h && h->random_float ? h->random_float(h->context, 0.0f, 0.12f, 100) : 0.0f;
    d = push(out, MU_RV_DRAW_PARTICLE, color);
    if (d) {
        d->bitmap = MU_RV_BITMAP_SOUL;
        d->subtype = 0xb;
        d->scale = s + 0.18f;
        d->vector[0] = o->position[0] + x;
        d->vector[1] = o->position[1] + y;
        d->vector[2] = o->position[2] + z;
        memcpy(d->light, light, sizeof d->light);
    }
    return 1;
}
