/* The pet process (NATIVE-HELPERS-002). See pets.h and docs/research/client-pets.md.
 * Comparisons follow the client's comiss/jcc pairs, so NaN inputs take the same branches. */
#include "pets.h"

#include <math.h>
#include <string.h>

#include "../movement/client_movement.h"
#include "../record-math/record_math.h"

#ifndef MU_PET_MUTATION
#define MU_PET_MUTATION 0   /* negative controls (scripts/validate_pets.py --mutations): 1..6 plant one mistake */
#endif

/* ---------------------------------------------------------------- the client's libm wrappers */

/* 0x009681bd / 0x009fa223 / 0x00961a07 / 0x00ad320c: float -> double CRT sin, cos, sqrt, log -> float */
static float csin(float x) { return (float)sin((double)x); }
static float ccos(float x) { return (float)cos((double)x); }
static float csqrt(float x) { return (float)sqrt((double)x); }
static float clog(float x) { return (float)log((double)x); }

/* ---------------------------------------------------------------- petdata.bmd */

uint32_t mu_pet_checksum(const uint8_t *data, uint32_t size, uint16_t key)
{
    uint32_t sum = (uint32_t)key << 9;
    for (uint32_t i = 0; size >= 4 && i <= size - 4; i += 4) {
        uint32_t word;
        memcpy(&word, data + i, 4);
        uint32_t k = ((i >> 2) + key) % 2u;
        if (k == 0)
            sum ^= word;
        else
            sum += word;
        if (i % 16u == 0)
#if MU_PET_MUTATION == 4
            sum ^= (key + sum) >> ((i >> 2) % 8u);
#else
            sum ^= (key + sum) >> (((i >> 2) % 8u) + 1u);
#endif
    }
    return sum;
}

void mu_pet_bux(uint8_t *data, int32_t size)
{
    static const uint8_t code[3] = {0xfc, 0xcf, 0xab};   /* 0x01cf0448 */
    for (int32_t i = 0; i < size; ++i)
        data[i] ^= code[i % 3];
}

int mu_pet_data_load(const uint8_t *file, size_t size, mu_pet_info table[MU_PET_RECORDS])
{
    memset(table, 0, sizeof(mu_pet_info) * MU_PET_RECORDS);   /* memset(this + 4, 0, 0x600) */
    if (!file)
        return 1;   /* "%s - File not exist." */
    uint8_t buffer[MU_PET_RECORDS * MU_PET_RECORD_BYTES];
    uint32_t stored = 0;
    memset(buffer, 0, sizeof buffer);   /* native choice: a short file reads as zero bytes */
    memcpy(buffer, file, size < sizeof buffer ? size : sizeof buffer);
    if (size >= sizeof buffer + 4)
        memcpy(&stored, file + sizeof buffer, 4);
    if (stored != mu_pet_checksum(buffer, sizeof buffer, MU_PET_CHECKSUM_KEY))
        return 2;   /* "%s - File corrupted." */
    for (int32_t i = 0; i < MU_PET_RECORDS; ++i) {
        uint8_t *record = buffer + i * MU_PET_RECORD_BYTES;
        mu_pet_bux(record, MU_PET_RECORD_BYTES);
        memcpy(&table[i], record, MU_PET_RECORD_BYTES);
    }
    return 0;
}

const mu_pet_info *mu_pet_data_find(const mu_pet_info table[MU_PET_RECORDS], int32_t item_code)
{
    /* 0x00eb0c52: records in order until the first item 0; std::map::insert keeps the first of equal keys */
    for (int32_t i = 0; i < MU_PET_RECORDS && table[i].item != 0; ++i)
        if (table[i].item + 0x1a00 == item_code)
            return &table[i];
    return NULL;
}

/* ---------------------------------------------------------------- process */

void mu_pets_init(mu_pets *p, uint32_t rand_seed, mu_pet_owner *owners, int32_t owner_count, const mu_pet_host *host)
{
    memset(p, 0, sizeof *p);
    p->rand_state = rand_seed;
    p->pending_pickup = -1;
    p->owners = owners;
    p->owner_count = owner_count;
    if (host)
        p->host = *host;
}

int32_t mu_pets_rand(mu_pets *p)
{
    p->rand_state = p->rand_state * 214013u + 2531011u;
    ++p->rand_calls;
    return (int32_t)((p->rand_state >> 16) & 0x7fffu);
}

static mu_pet_owner *owner_of(mu_pets *p, int32_t index)
{
    return (index >= 0 && index < p->owner_count) ? &p->owners[index] : NULL;
}

static uint32_t tick(mu_pets *p)
{
    return p->host.tick ? p->host.tick(p->host.context) : 0;
}

static uint32_t now(mu_pets *p)
{
    return p->host.time ? p->host.time(p->host.context) : 0;
}

static int has_model(mu_pets *p, int32_t model)
{
    return p->host.has_model ? p->host.has_model(p->host.context, model) : 1;
}

/* 0x00eac81e(ms, &last): timeGetTime() - last > ms -> last = timeGetTime(), 1 */
static int interval(mu_pets *p, uint32_t ms, uint32_t *last)
{
    if (now(p) - *last > ms) {
        *last = now(p);
        return 1;
    }
    return 0;
}

int mu_pet_create_object(mu_pets *p, mu_pet *pet, int32_t item, int32_t model, const float position[3], int32_t owner,
                         int32_t subtype)
{
    mu_pet_owner *c = owner_of(p, owner);
    if (!c)
        return 0;
    mu_hp_object *o = &pet->object;
    if (o->live == 1)   /* the OBJECT exists already and is live */
        return 0;
    pet->created = tick(p);
    pet->owner = owner;
    pet->item = item;
    o->type = model;
    o->live = 1;              /* SetLive(o, 1) */
    o->visible = 0;
    o->lighting = 1;
    o->flag_0e = 0;
    o->alpha_enable = 0;
    o->flag_0d = 0;
    o->owner = owner;         /* c + 0x3254 */
    o->subtype = subtype;
    o->field_68 = -1;
    o->blend_mesh = -1;
    o->blend_light = 1.0f;
    o->scale = 0.7f;
    o->lifetime = 0x1e;
    o->alpha = 0.0f;
    o->alpha_target = 1.0f;
    o->blend_mesh = pet->info->blend_mesh;   /* 0x00eb0933(info + 0x18) */
    o->scale = pet->info->scale;             /* 0x00eb0953(info + 0x14) */
    o->position[0] = position[0];
    o->position[1] = position[1];
    o->position[2] = position[2];
    o->angle[0] = c->angle[0];
    o->angle[1] = c->angle[1];
    o->angle[2] = c->angle[2];
    o->light[0] = o->light[1] = o->light[2] = 3.0f;
    o->prior_frame = 0.0f;
    o->frame = 0.0f;
    o->velocity = 0.5f;
    if (o->type == MU_PET_MODEL_SKELETON)
        o->position[1] = 60.0f * c->scale + o->position[1];
    return 1;
}

static int32_t pet_key(const mu_pet_owner *c, int32_t item)
{
    return (int32_t)c->key * 10000 + item;
}

static void release(mu_pets *p, mu_pet *pet)
{
    /* 0x00eabf9b: owner, info and the OBJECT (deleted) */
    (void)p;
    pet->owner = -1;
    pet->info = NULL;
}

static void erase(mu_pets *p, int32_t index)
{
    release(p, &p->list[index]);
    memmove(&p->list[index], &p->list[index + 1], sizeof(mu_pet) * (size_t)(p->count - index - 1));
    p->count--;
}

int mu_pets_create(mu_pets *p, int32_t item, int32_t model, const float position[3], int32_t owner, int32_t subtype)
{
    mu_pet_owner *c = owner_of(p, owner);
    if (item < 1 || model < 1 || !c || p->count >= MU_PET_MAX)
        return 0;
    mu_pet fresh;
    memset(&fresh, 0, sizeof fresh);
    fresh.owner = 0;
    fresh.target_item = 0;
    fresh.item = -1;          /* 0x00eabf2b: +0xc -1 */
    fresh.info = mu_pet_data_find(p->table, item);   /* 0x00eb0cdb -> SetInfo */
    mu_hp_object_init(&fresh.object);
    if (!fresh.info)
        return 0;   /* the client dereferences the NULL info in Create (native: refused) */
    if (!mu_pet_create_object(p, &fresh, item, model, position, owner, subtype))
        return 0;
    fresh.key = pet_key(c, item);
    int32_t at = 0;
    while (at < p->count && p->list[at].key < fresh.key)
        ++at;
    if (at < p->count && p->list[at].key == fresh.key)
        return 0;   /* the key exists: the new pet is deleted */
    memmove(&p->list[at + 1], &p->list[at], sizeof(mu_pet) * (size_t)(p->count - at));
    p->list[at] = fresh;
    p->count++;
    return 1;
}

mu_pet *mu_pets_find(mu_pets *p, int32_t owner, int32_t item)
{
    mu_pet_owner *c = owner_of(p, owner);
    if (!c)
        return NULL;
    int32_t key = pet_key(c, item);
    for (int32_t i = 0; i < p->count; ++i)
        if (p->list[i].key == key)
            return &p->list[i];
    return NULL;
}

int mu_pets_delete(mu_pets *p, int32_t owner, int32_t item)
{
    mu_pet_owner *c = owner_of(p, owner);
    if (!c)
        return 0;
    if (item == -1) {
        for (int32_t i = 0; i < p->count; ++i)
            if (p->list[i].object.owner == owner) {   /* 0x00eac609 */
                erase(p, i);
                return 1;
            }
        return 0;   /* the loop ends without a match: the function's last value (static) */
    }
    int32_t key = pet_key(c, item);
    for (int32_t i = 0; i < p->count; ++i) {
        if (p->list[i].key != key)
            continue;
        if (p->list[i].object.owner != owner)   /* 0x00eac609, then 0x00eac62c */
            return 1;
        erase(p, i);
        return 1;
    }
    return 0;
}

/* ---------------------------------------------------------------- update */

static void model_tick(mu_pets *p, mu_pet *pet)
{
    /* 0x00eac84d */
    mu_hp_object *o = &pet->object;
    if (!has_model(p, o->type))
        return;
    if (p->host.animate)
        p->host.animate(p->host.context, o, o->type, o->velocity);
}

void mu_pet_find_target(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in)
{
    mu_pet_owner *c = owner_of(p, pet->object.owner);
    if (!c || pet->has_target == 1 || !in->items)
        return;
    for (int32_t i = 0; i < MU_PET_GROUND_ITEMS; ++i) {
        const mu_pet_ground_item *it = &in->items[i];
        if (!it->live || !it->visible)
            continue;
        float dx = c->position[0] - it->position[0];
        float dy = c->position[1] - it->position[1];
        float dist = csqrt(dx * dx + dy * dy);
#if MU_PET_MUTATION == 5
        if (!(350.0f > dist))
#else
        if (!(300.0f > dist))
#endif
            continue;
        if (it->type != MU_PET_ZEN_TYPE)
            continue;
        if (pet->has_target != 0)
            continue;
        pet->has_target = 1;
        pet->target_item = i;
        pet->target[0] = it->position[0];
        pet->target[1] = it->position[1];
        pet->target[2] = it->position[2];
    }
}

/* AngleMatrix(angle) -> matrix, VectorRotate(direction) and position += the result */
static void step_forward(mu_hp_object *o)
{
    float v[3];
    mu_angle_matrix(o->angle, o->matrix);
    mu_vector_rotate(o->direction, o->matrix, v);
    o->position[0] = o->position[0] + v[0];
    o->position[1] = o->position[1] + v[1];
    o->position[2] = o->position[2] + v[2];
}

static void set_speed(mu_hp_object *o, float speed)
{
    o->direction[0] = 0.0f;
    o->direction[1] = -speed;
    o->direction[2] = 0.0f;
}

static void turn_to(mu_hp_object *o, float x, float y, float step)
{
    float heading = mu_create_angle(o->position[0], o->position[1], x, y);
    o->angle[2] = mu_turn_angle2(o->angle[2], heading, step);
}

/* the collector's walk toward a point (states 0 and 4): returns nothing, sets the direction */
static void collector_follow(mu_pet *pet, const mu_pet_owner *c, float range, float dist_owner)
{
    mu_hp_object *o = &pet->object;
    float speed = 0.0f;
    float t[3];
    if (pet->info->follow == 1) {
        t[0] = c->position[0];
        t[1] = c->position[1];
        t[2] = c->position[2];
        if (dist_owner > range * range)
            speed = clog(dist_owner) * 2.3f;
    } else {
        speed = 50.0f;
        t[0] = csin(pet->angle1) * 50.0f + c->position[0];
        t[1] = ccos(pet->angle1) * 50.0f + c->position[1];
        t[2] = c->position[2];
        if (dist_owner > range)
            speed = clog(dist_owner) * 2.3f;
    }
    float d[3] = {t[0] - o->position[0], t[1] - o->position[1], t[2] - o->position[2]};
    (void)csqrt(d[0] * d[0] + d[1] * d[1]);
    if (80.0f >= range)
        turn_to(o, t[0], t[1], 8.0f);
    step_forward(o);
    set_speed(o, speed);
}

int mu_pet_move(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in, uint32_t elapsed)
{
    mu_hp_object *o = &pet->object;
    mu_pet_owner *c = owner_of(p, o->owner);
    if (!pet->info || !c)
        return 0;
    o->velocity = (pet->state >= 0 && pet->state <= 4) ? pet->info->speed[pet->state] : 0.0f;   /* 0x00eb08c2 */
    if (pet->info->move == 0) {
        float range = pet->info->range;
        o->position[2] = 230.0f * c->scale + c->position[2];
        float dx = c->position[0] - o->position[0];
        float dy = c->position[1] - o->position[1];
        float dist2 = dx * dx + dy * dy;
        if (dist2 >= range * range * range * range) {
            o->position[0] = c->position[0];
            o->position[1] = c->position[1];
            o->position[2] = c->position[2];
            o->position[2] = c->position[2] + 200.0f;
            o->angle[0] = c->angle[0];
            o->angle[1] = c->angle[1];
            o->angle[2] = c->angle[2];
        } else if (dist2 >= range * range) {
            turn_to(o, c->position[0], c->position[1], 10.0f);
        }
        step_forward(o);
        float speed = 0.0f;
        if (dist2 > range * range)
#if MU_PET_MUTATION == 1
            speed = clog(dist2) * 2.3f;
#else
            speed = clog(dist2) * 1.8f;
#endif
        set_speed(o, speed);
        return 1;
    }
    if (pet->info->move != 1)
        return 1;
    /* the collector */
    if (o->owner == in->hero) {
        if (in->helper_type < 0)
            return 0;
        if (in->helper_92 == 1 && in->helper_93 == 1) {
            pet->state = 4;
        } else {
            mu_pet_find_target(p, pet, in);
            if (pet->state == 0 && pet->has_target != 0)
                pet->state = 1;
        }
    } else {
        pet->state = 4;
    }
    float range = pet->info->range;
    pet->angle1 = (float)(elapsed % 4000u) * 0x1.9b90ecp-10f;   /* 0.00157 */
#if MU_PET_MUTATION == 2
    pet->angle2 = (float)(elapsed % 4000u) * 0x1.9b90ecp-9f;
#else
    pet->angle2 = (float)(elapsed % 2000u) * 0x1.9b90ecp-9f;    /* 0.00314 */
#endif
    if (pet->item == MU_PET_UNICORN)
        o->position[2] = 200.0f * c->scale + c->position[2];
    else if (pet->item == MU_PET_SKELETON)
        o->position[2] = 50.0f * c->scale + c->position[2];
    else
        o->position[2] = c->position[2] + 20.0f;
    float d[3] = {o->position[0] - c->position[0], o->position[1] - c->position[1], o->position[2] - c->position[2]};
    float dist = csqrt(d[0] * d[0] + d[1] * d[1]);
    if (dist > 900.0f) {
        o->position[0] = csin(pet->angle1) * 50.0f + c->position[0];
        o->position[1] = ccos(pet->angle1) * 50.0f + c->position[1];
        o->angle[0] = c->angle[0];
        o->angle[1] = c->angle[1];
        o->angle[2] = c->angle[2];
        pet->state = 0;
        pet->has_target = 0;
    }
    switch (pet->state) {
    case 0:
    case 4:
        collector_follow(pet, c, range, dist);
        break;
    case 1: {
        if (pet->has_target == 0) {
            pet->has_target = 0;
            pet->state = 3;
            break;
        }
        float t[3];
        t[0] = csin(pet->angle2) * 50.0f + pet->target[0];
        t[1] = ccos(pet->angle2) * 50.0f + pet->target[1];
        t[2] = pet->target[2];
        float e[3] = {t[0] - o->position[0], t[1] - o->position[1], t[2] - o->position[2]};
        float de = csqrt(e[0] * e[0] + e[1] * e[1]);
        if (de >= range)
            turn_to(o, t[0], t[1], 20.0f);
        step_forward(o);
        float speed = 0.0f;
        if (de > 20.0f)
            speed = clog(de) * 2.5f;
        set_speed(o, speed);
        if (speed == 0.0f || interval(p, 100000u, &pet->wait_tick) == 1) {
            pet->pick_tick = tick(p);
            pet->wait_tick = tick(p);
            pet->state = 2;
        }
        break;
    }
    case 2: {
        int fail = pet->has_target == 0 || dist > 300.0f;
        if (!fail && interval(p, 3000u, &pet->wait_tick) == 1)
            fail = 1;
        if (!fail) {
            int32_t type = in->before_items;   /* target -1 */
            if (pet->target_item >= 0 && pet->target_item < MU_PET_GROUND_ITEMS)
                type = in->items ? in->items[pet->target_item].type : 0;
            if (type != MU_PET_ZEN_TYPE)
                fail = 1;
        }
        if (fail) {
            pet->has_target = 0;
            pet->wait_tick = tick(p);
            pet->state = 3;
            break;
        }
        turn_to(o, pet->target[0], pet->target[1], 10.0f);
        if (interval(p, 1000u, &pet->pick_tick) == 1 && pet->target_item != -1 && o->owner == in->hero) {
            if (p->pending_pickup == -1) {
                p->pending_pickup = pet->target_item;
                if (p->host.pickup)
                    p->host.pickup(p->host.context, pet->target_item);
            }
            pet->target_item = -1;
        }
        break;
    }
    case 3: {
        float t[3];
        t[0] = csin(pet->angle1) * 50.0f + c->position[0];
        t[1] = ccos(pet->angle1) * 50.0f + c->position[1];
        t[2] = c->position[2];
        float e[3] = {t[0] - o->position[0], t[1] - o->position[1], t[2] - o->position[2]};
        float de = csqrt(e[0] * e[0] + e[1] * e[1]);
        if (de >= range)
            turn_to(o, t[0], t[1], 20.0f);
        step_forward(o);
        float speed = 0.0f;
        if (de > range)
            speed = clog(de) * 2.5f;
        set_speed(o, speed);
        if (speed != 0.0f && interval(p, 3000u, &pet->wait_tick) != 1)
            break;
        pet->state = 0;
        break;
    }
    default:
        break;
    }
    return 1;
}

int mu_pet_update(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in)
{
    mu_hp_object *o = &pet->object;
    mu_pet_owner *c = owner_of(p, o->owner);
    if (!c || !o->live)
        return 0;
    if (in->scene == 6 && (!c->live || c->kind != 1)) {
        o->live = 0;   /* SetLive(o, 0) */
        if (p->host.kill)
            p->host.kill(p->host.context, o);
        return 0;
    }
    mu_hp_fade_alpha(o);
    uint32_t elapsed = tick(p) - pet->created;   /* 0x00eb091e */
    model_tick(p, pet);
    mu_pet_move(p, pet, in, elapsed);
    if (pet->state == 2 && p->host.sound)   /* 0x00eaeacf */
        p->host.sound(p->host.context, 0x1f);
    return 1;
}

void mu_pets_update(mu_pets *p, const mu_pet_inputs *in)
{
    for (int32_t i = 0; i < p->count; ++i)
        mu_pet_update(p, &p->list[i], in);
}

/* ---------------------------------------------------------------- render */

static const float zero3[3] = {0.0f, 0.0f, 0.0f};

/* TransformPosition 0x012b6ef1(model, BoneTransform + 0x30 * bone, vector, out, 0) */
static void bone_point(const mu_pet_render_host *r, int32_t model, int32_t bone, const float v[3], float out[3])
{
    const float *m = r->bone_matrix ? r->bone_matrix(r->context, model, bone) : NULL;
    if (m)
        mu_vector_transform(v, m, out);
}

/* 0x012b6d2a(model, out, BoneTransform + 0x30 * bone, position, NULL): BodyScale * translation + position; the
 * skeletons set the model's BodyScale to the object scale just before */
static void bone_origin(const mu_pet_render_host *r, int32_t model, int32_t bone, float scale, const float position[3],
                        float out[3])
{
    const float *m = r->bone_matrix ? r->bone_matrix(r->context, model, bone) : NULL;
    if (!m)
        return;
    out[0] = scale * m[3] + position[0];
    out[1] = scale * m[7] + position[1];
    out[2] = scale * m[11] + position[2];
}

static void sprite(const mu_pet_render_host *r, int32_t bitmap, const float pos[3], float scale, const float light[3],
                   const mu_hp_object *o)
{
    if (r->sprite)
        r->sprite(r->context, bitmap, pos, scale, light, o);
}

static void particle(const mu_pet_render_host *r, int32_t bitmap, const float pos[3], const float angle[3],
                     const float light[3], int32_t subtype, float scale, const mu_hp_object *owner)
{
    if (r->particle)
        r->particle(r->context, bitmap, pos, angle, light, subtype, scale, owner, 0);
}

static void remember(const mu_pet_render_host *r, int32_t kind)
{
    if (r->remember)
        r->remember(r->context, kind);
}

static void pose(const mu_pet_render_host *r, const mu_hp_object *o, int translate)
{
    if (r->pose)
        r->pose(r->context, o, o->type, translate);
}

static void visuals_demon(const mu_pet_render_host *r, mu_pet *pet, uint32_t elapsed)
{
    mu_hp_object *o = &pet->object;
    float k = csin((float)(elapsed % 25000u) * 0x1.4940bcp-10f) + 0.4f;   /* 0.001256 */
    float light[3] = {k * 0.7f, k * 0.5f, k * 0.6f};
    static const float red[3] = {0.7f, 0.3f, 0.3f};
    static const int32_t bones[9] = {8, 0x22, 0x33, 0x3d, 0x38, 0x42, 0x34, 0x3a, 0x2c};
    for (int32_t i = 0; i < 9; ++i) {
        float p[3] = {0.0f, 0.0f, 0.0f};
        bone_point(r, o->type, bones[i], zero3, p);
        switch (i) {
        case 0:
            sprite(r, 0x8099, p, 1.0f, light, o);
            sprite(r, 0x7f78, p, 0.5f, light, o);
            break;
        case 1: case 2: case 3: case 4: case 5:
            particle(r, 0x7ffd, p, o->angle, light, 0xb, 0.5f, NULL);
            remember(r, 0x7ffd);
            break;
        case 6: case 7:
            sprite(r, 0x8099, p, 0.5f, light, o);
            break;
        case 8:
            particle(r, 0x8085, p, o->angle, light, 1, 0.4f, NULL);
            remember(r, 0x8085);
            sprite(r, 0x7f78, p, 1.5f, light, o);
            sprite(r, 0x7f78, p, 0.5f, red, o);
            break;
        default:
            break;
        }
    }
}

static void visuals_spirit(const mu_pet_render_host *r, mu_pet *pet, uint32_t elapsed)
{
    mu_hp_object *o = &pet->object;
    float s1 = (float)(elapsed % 3000u) * 0x1.12609ep-10f;   /* 3.14 / 3000 */
    float s2 = (float)((elapsed + 0x5dcu) % 3000u) * 0x1.12609ep-10f;
    pose(r, o, 1);
    float p[3] = {0.0f, 0.0f, 0.0f};
    float light[3] = {0.7f, 0.2f, 0.6f};
    bone_point(r, o->type, 3, zero3, p);
    sprite(r, 0x8099, p, 1.5f, light, o);
    sprite(r, 0x8099, p, 0.8f, light, o);
    light[0] = 0.3f, light[1] = 0.3f, light[2] = 0.6f;
    bone_point(r, o->type, 5, zero3, p);
    p[2] = p[2] - 25.0f;
    if (r->effect) {
        const int32_t args[10] = {4, 0, -1, 0, 0, 0, (int32_t)0x3e99999a /* 0.3f */, -1, 0, 0};
        r->effect(r->context, 0x460, p, o->angle, light, args);
    }
    remember(r, 0x460);
    static const int32_t bones[11] = {0x2d, 0x2a, 0x30, 0x36, 0x33, 0x39, 0x19, 0x1a, 0x1b, 0x26, 0x20};
    for (int32_t i = 0; i < 11; ++i) {
        bone_point(r, o->type, bones[i], zero3, p);
        if (i <= 5) {
            light[0] = 0.5f, light[1] = 0.5f, light[2] = 0.8f;
            sprite(r, 0x8099, p, 0.3f, light, o);
        } else if (i <= 8) {
            light[0] = 0.6f, light[1] = 0.2f, light[2] = 0.8f;
            sprite(r, 0x7ef7, p, 0.2f, light, o);
        } else {
#if MU_PET_MUTATION == 3
            float f = (i % 2 == 1) ? csin(s1) * 2.0f : csin(s2) * 2.0f;
#else
            float f = (i % 2 == 0) ? csin(s1) * 2.0f : csin(s2) * 2.0f;
#endif
            light[0] = f, light[1] = f, light[2] = f;
            sprite(r, 0x7f78, p, 0.5f, light, o);
        }
    }
}

static void visuals_rudolph(const mu_pet_render_host *r, mu_pet *pet, uint32_t elapsed)
{
    mu_hp_object *o = &pet->object;
    pose(r, o, 1);
    float k = csin((float)(elapsed % 3000u) * 0x1.12609ep-10f) * 0.2f;
    float m = 1.0f;
    float light[3] = {1.0f, 0.8f, 0.2f};
    float p[3] = {o->position[0], o->position[1], o->position[2] + 30.0f};
    particle(r, 0x7f66, p, o->angle, light, 7, 1.0f, NULL);
    if (pet->state == 1 || pet->state == 2) {
        k = 0.8f;
        m = 3.0f;
    } else if (pet->state == 3) {
        if (r->effect) {
            const int32_t args[10] = {0, 0, -1, 0, 0, 0, 0, -1, 0, 0};
            r->effect(r->context, 0x3fa, p, o->angle, light, args);
        }
        remember(r, 0x3fa);
    }
    bone_point(r, o->type, 10, zero3, p);
    light[0] = 1.0f, light[1] = 0.8f, light[2] = 0.2f;
    sprite(r, 0x7fe0, p, 0.5f + k, light, o);
    light[0] = 1.0f, light[1] = 0.1f, light[2] = 0.2f;
    sprite(r, 0x7ef7, p, 2.0f + k, light, o);
    static const int32_t bones[5] = {0x13, 0x20, 0x21, 0x22, 0x23};
    for (int32_t i = 0; i < 5; ++i) {
        bone_point(r, o->type, bones[i], zero3, p);
        light[0] = 0.8f, light[1] = 0.6f, light[2] = 0.2f;
        sprite(r, 0x7ef7, p, 0.6f * m, light, o);
        light[0] = 0.8f, light[1] = 0.8f, light[2] = 0.2f;
        sprite(r, 0x7f67, p, 0.4f * m, light, o);
    }
}

static void visuals_panda(mu_pets *pets, const mu_pet_render_host *r, mu_pet *pet, uint32_t elapsed)
{
    mu_hp_object *o = &pet->object;
    pose(r, o, 1);
    float k = csin((float)(elapsed % 3000u) * 0x1.12609ep-10f) * 0.2f;
    float light[3] = {1.0f, 1.0f, 1.0f};
    float p[3] = {o->position[0], o->position[1], o->position[2]};
    bone_point(r, o->type, 7, zero3, p);
    if (mu_pets_rand(pets) % 3 == 0) {
        light[0] = 0.6f, light[1] = 1.0f, light[2] = 0.4f;
        particle(r, 0x7efa, p, o->angle, light, 1, 1.0f, NULL);
    }
    bone_point(r, o->type, 4, zero3, p);
    light[0] = 0.9f, light[1] = 0.9f, light[2] = 0.0f;
    sprite(r, 0x7ef7, p, 1.5f + k, light, o);
    light[0] = 0.6f, light[1] = 1.0f, light[2] = 0.2f;
    sprite(r, 0x7ef7, p, 2.5f + k, light, o);
}

static void visuals_skeleton(mu_pets *pets, const mu_pet_render_host *r, mu_pet *pet, const mu_pet_inputs *in)
{
    mu_hp_object *o = &pet->object;
    pose(r, o, 0);   /* after BodyScale = the object scale */
    float k = (csin(in->world_time * 0.003f) + 1.0f) * 0.5f + 0.5f;
    float light[3] = {k * 0.0f, 1.0f * k, 0.5f * k};
    float p[3] = {0.0f, 0.0f, 0.0f};
    bone_origin(r, o->type, 12, o->scale, o->position, p);
    sprite(r, 0x7f37, p, 0.05f, light, o);
    bone_origin(r, o->type, 11, o->scale, o->position, p);
    sprite(r, 0x7f37, p, 0.05f, light, o);
    bone_origin(r, o->type, 0x2c, o->scale, o->position, p);
    sprite(r, 0x7ef7, p, 0.3f, light, o);
    bone_origin(r, o->type, 0x2e, o->scale, o->position, p);
    sprite(r, 0x7ef7, p, 0.6f, light, o);
    bone_origin(r, o->type, 0x2d, o->scale, o->position, p);
    sprite(r, 0x7ef7, p, 0.4f, light, o);
#if MU_PET_MUTATION == 6
    bone_origin(r, o->type, 0x3d, o->scale, o->position, p);
#else
    bone_origin(r, o->type, 0x3e, o->scale, o->position, p);
#endif
    sprite(r, 0x7ef7, p, 0.3f, light, o);
    mu_pet_owner *c = owner_of(pets, o->owner);
    uint16_t a = c ? c->action : 0;   /* c + 0x327e */
    int show = (a == 0 || a > 0x31) && (a < 0x133 || a > 0x141) && (a < 0x148 || a > 0x185);
    if (!show)
        return;
    light[0] = 0.0f, light[1] = 1.0f, light[2] = 0.5f;
    bone_origin(r, o->type, 13, o->scale, o->position, p);
    float angle[3] = {o->angle[0] + 35.0f, o->angle[1], o->angle[2]};
    for (int32_t i = 0; i < 2; ++i) {
        if (i == 1 && mu_pets_rand(pets) % 2 == 0)
            continue;
        int32_t pick = mu_pets_rand(pets) % 3;
        if (r->particle) {
            if (pick == 0)
                r->particle(r->context, 0x8086, p, angle, light, 4, o->scale, o, 0);
            else if (pick == 1)
                r->particle(r->context, 0x8087, p, angle, light, 8, o->scale, o, 0);
            else
                r->particle(r->context, 0x8089, p, angle, light, 5, o->scale, o, 0);
        }
    }
    light[0] = 1.0f, light[1] = 1.0f, light[2] = 1.0f;
    float s = (csin(in->world_time * 0.005f) + 1.0f) * 0.1f + 0.1f;
    sprite(r, 0x8003, p, s, light, o);
}

int mu_pet_visuals(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in, const mu_pet_render_host *r, uint32_t elapsed)
{
    mu_hp_object *o = &pet->object;
    switch (pet->item) {
    case MU_PET_DEMON:
        remember(r, -1);
        if (has_model(p, o->type))
            visuals_demon(r, pet, elapsed);
        break;
    case MU_PET_SPIRIT:
        remember(r, -1);
        if (has_model(p, o->type))
            visuals_spirit(r, pet, elapsed);
        break;
    case MU_PET_RUDOLPH:
        remember(r, -1);
        if (has_model(p, o->type))
            visuals_rudolph(r, pet, elapsed);
        break;
    case MU_PET_PANDA:
    case MU_PET_PC_PANDA:
        if (has_model(p, o->type))
            visuals_panda(p, r, pet, elapsed);
        break;
    case MU_PET_SKELETON:
    case MU_PET_PC_SKELETON:
        if (has_model(p, o->type))
            visuals_skeleton(p, r, pet, in);
        break;
    default:
        break;
    }
    return 1;
}

int mu_pet_render(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in, const mu_pet_render_host *r)
{
    mu_hp_object *o = &pet->object;
    mu_pet_owner *c = owner_of(p, pet->owner);
    if (o->live != 1 || !c || c->alt_pet != -1)
        return 1;
    o->visible = (uint8_t)(r->frustum ? r->frustum(r->context, o->position[0] * 0.01f, o->position[1] * 0.01f, -20.0f)
                                      : 1);
    if (o->visible != 1)
        return 1;
    int32_t a3 = 0;
    mu_pet_owner *w = owner_of(p, o->owner);
    if (w && w->buff_12 == 1)
        a3 = 10;
    if (r->draw_object)
        r->draw_object(r->context, o, 0, 0, a3, -1, -1);
    mu_pet_visuals(p, pet, in, r, tick(p) - pet->created);
    return 1;
}

void mu_pets_render(mu_pets *p, const mu_pet_inputs *in, const mu_pet_render_host *r)
{
    for (int32_t i = 0; i < p->count; ++i)
        mu_pet_render(p, &p->list[i], in, r);
}
