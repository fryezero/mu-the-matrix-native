/* The Muun effect table's consumers and the attached effects' update (RENDER-EFFECTS-018); see muun_effects.h. */
#include "muun_effects.h"

#include <math.h>
#include <string.h>

/* 0x00aed702: equal_range on the ascending keys (std::less<int>) */
static int32_t lower_bound(const mu_muun_effect_table *t, int32_t code, int upper)
{
    int32_t lo = 0, hi = t->count;
    while (lo < hi) {
        const int32_t mid = lo + (hi - lo) / 2;
        if (upper ? !(code < t->entries[mid].code) : t->entries[mid].code < code)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo;
}

int32_t mu_muun_effects_attach(const mu_muun_effect_table *table, int32_t object, int32_t code,
                               const mu_muun_effect_ops *ops)
{
    if (!table)
        return 0;
    const int32_t first = lower_bound(table, code, 0), last = lower_bound(table, code, 1);
    for (int32_t k = first; k < last; ++k) {
        const mu_muun_effect_entry *e = &table->entries[k];
        const int32_t handle = ops->create(ops->context, object, e);
        if (handle >= 0)
            ops->attach(ops->context, object, handle, e->bone, e->follow, 0, 0.0f);
        ops->release(ops->context, handle);
    }
    return last - first;
}

int mu_muun_slot_attach(const mu_muun_slot *s, const mu_muun_effect_table *table, const mu_muun_effect_ops *ops)
{
    if (s->object < 0 || !s->has_owner || !s->has_info)
        return 0;
    if (!s->active || s->key != s->owner_key)
        return 0;
    mu_muun_effects_attach(table, s->object, s->code, ops);
    return 1;
}

int mu_muun_slot_clear(const mu_muun_slot *s, const mu_muun_effect_ops *ops)
{
    if (s->object < 0 || !s->has_owner)
        return 0;
    ops->clear(ops->context, s->object);
    return 1;
}

/* 0x0129f12c: the OBJECT's own bone (model present, +0x318 set, 0 <= bone < the model's count; no model is a count
 * of -1), otherwise the shared pose buffer's (0x06fce398 + 0x30 bone). */
static const float *bone_source(const mu_effect_object *o, int32_t bone)
{
    if (o->bones && bone >= 0 && bone < o->model_bones)
        return o->bones + 12 * bone;
    return o->shared + 12 * bone;
}

/* 0x00cf2679(position, rotation in radians, scale): the rotation's 3x3 times scale, the position in 12..14
 * (cos 0x009fa223, sin 0x009681bd, binary32). */
static void rotation_matrix(float m[16], const float position[3], const float r[3], float s)
{
    const float cx = (float)cos((double)r[0]), sx = (float)sin((double)r[0]);
    const float cy = (float)cos((double)r[1]), sy = (float)sin((double)r[1]);
    const float cz = (float)cos((double)r[2]), sz = (float)sin((double)r[2]);
    m[0] = cy * cz * s;
    m[4] = -(cy * sz) * s;
    m[8] = sy * s;
    m[12] = position[0];
    m[1] = (sx * sy * cz + cx * sz) * s;
    m[5] = (-(sx * sy * sz) + cx * cz) * s;
    m[9] = -(sx * cy) * s;
    m[13] = position[1];
    m[2] = (-(cx * sy * cz) + sx * sz) * s;
    m[6] = (cx * sy * sz + sx * cz) * s;
    m[10] = cx * cy * s;
    m[14] = position[2];
    m[3] = m[7] = m[11] = 0.0f;
    m[15] = 1.0f;
}

void mu_object_bone_matrix(float out[16], const mu_effect_object *o, int32_t bone)
{
    const float *b = bone_source(o, bone);
    float m[16];
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 4; ++c)
            m[4 * c + r] = b[4 * r + c];
    m[3] = m[7] = m[11] = 0.0f;
    m[15] = 1.0f;
    if (!o->in_sector) {
        const float zero[3] = {0.0f, 0.0f, 0.0f};
        float place[16], product[16];
        rotation_matrix(place, o->position, zero, o->scale);
        for (int r = 0; r < 4; ++r)          /* 0x00cf0db8: place x bone, column-major */
            for (int c = 0; c < 4; ++c)
                product[r + 4 * c] = place[r] * m[4 * c] + place[r + 4] * m[1 + 4 * c] +
                                     place[r + 8] * m[2 + 4 * c] + place[r + 12] * m[3 + 4 * c];
        memcpy(m, product, sizeof m);
    }
    memcpy(out, m, sizeof m);
}

void mu_object_bone_position(float out[3], const mu_effect_object *o, int32_t bone)
{
    const float *b = bone_source(o, bone);
    out[0] = b[3];
    out[1] = b[7];
    out[2] = b[11];
    if (!o->in_sector)
        for (int k = 0; k < 3; ++k)
            out[k] = out[k] + o->position[k];
}

/* 0x0129faee: the OBJECT's world matrix (angle in degrees x 0.017453292, 0x00a8c87e), as 0x00cf2679 builds it */
static void world_matrix(float out[16], const mu_effect_object *o)
{
    const float to_rad = 0.017453292f;
    const float r[3] = {o->angle[0] * to_rad, o->angle[1] * to_rad, o->angle[2] * to_rad};
    rotation_matrix(out, o->position, r, o->scale);
}

int mu_object_effect_matrix(float out[16], const mu_object_effect_record *rec, const mu_effect_object *o)
{
    if (rec->follow) {
        if (rec->bone == -1)
            world_matrix(out, o);
        else if (rec->bone >= 0)
            mu_object_bone_matrix(out, o, rec->bone);
        else
            return 0;
        return 1;
    }
    memset(out, 0, 16 * sizeof(float));      /* 0x00cef956: the scale's diagonal */
    out[0] = out[5] = out[10] = o->scale;
    out[15] = 1.0f;
    if (rec->bone == -1) {
        out[12] = o->position[0];
        out[13] = o->position[1];
        out[14] = o->position[2];
    } else if (rec->bone >= 0) {
        mu_object_bone_position(out + 12, o, rec->bone);
    }
    return 1;
}

int32_t mu_object_effects_update(mu_object_effect_record *records, int32_t count, const mu_effect_object *o, float dt,
                                 const mu_object_effect_ops *ops)
{
    int32_t kept = 0;
    for (int32_t k = 0; k < count; ++k) {
        mu_object_effect_record rec = records[k];
        if (rec.timed) {
            rec.lifetime = rec.lifetime - dt;
            if (0.0f >= rec.lifetime) {
                ops->expire(ops->context, rec.handle);
                continue;
            }
        }
        records[kept++] = rec;
        ops->scale(ops->context, rec.handle, rec.template_scale * o->scale);
        float m[16];
        if (mu_object_effect_matrix(m, &rec, o))
            ops->update(ops->context, rec.handle, dt, m);
    }
    return kept;
}
