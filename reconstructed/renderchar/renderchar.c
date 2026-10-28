/* Item render decisions of the client's world path. See renderchar.h.
 * Build with -ffp-contract=off: float products and sums follow the client's
 * binary32 SSE order. Explicit double casts retain its binary64 blend pulse. */
#include "renderchar.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

#include "special_types.h"
#include "item_glow.h"
#include "skin_glow.h"
#include "item_bodies.h"
#include "skin_bodies.h"
#include "item_links.h"

/* sin wrapper 0x009681bd: the CRT sin of a binary32 argument rounded to
 * binary32 (same rule as the mesh-draw port, client-meshdraw-exec.md). */
static float client_sin(float x)
{
    return (float)sin((double)x);
}

/* 0x0185bdc4(-4,0). Callers add their own body-light or blend-light offset. */
static float armour_wave(float time)
{
    int32_t tick = !(time >= -2147483648.0f && time < 2147483648.0f) ? INT32_MIN : (int32_t)time;
    float x = (float)(tick % -1570) * 0.001f * -4.0f;
    float w = (float)cos((double)x);
    if (3.1415927f > x)
        w = -w;
    return (w + 1.0f) * 0.5f;
}

static float armour_pulse(float time)
{
    return armour_wave(time) + 0.2f;
}

typedef struct sink {
    mu_rc_draw *out;
    int32_t capacity, count;
    const mu_rc_item *item;
    mu_rc_model *model;
    int parameters;
} sink;

static void emit(sink *s, int32_t entry, int32_t mesh, uint32_t flags, float alpha, int32_t hidden, int32_t texture)
{
    if (s->count < s->capacity) {
        mu_rc_draw *d = &s->out[s->count];
        const mu_rc_item *it = s->item;
        d->entry = entry;
        d->mesh = mesh;
        d->flags = flags;
        d->alpha = alpha;
        d->blend_mesh = it->blend_mesh;
        d->blend_light = it->blend_light;
        d->u = it->u;
        d->v = it->v;
        d->hidden = hidden;
        d->texture = texture;
        for (int k = 0; k < 3; ++k) {
            d->body_light[k] = s->model->body_light[k];
            d->shade[k] = s->model->shade[k];
        }
        d->level_field = s->model->level_field;
        d->flag_ca = s->model->flag_ca;
    }
    s->count++;
}

static int body_type(int32_t type)
{
    size_t low = 0, high = sizeof mu_rc_body_types / sizeof mu_rc_body_types[0];
    while (low < high) {
        size_t mid = low + (high - low) / 2;
        if (mu_rc_body_types[mid].type < type)
            low = mid + 1;
        else if (mu_rc_body_types[mid].type > type)
            high = mid;
        else
            return (int)mid;
    }
    return -1;
}

static void apply_recipe(sink *s, const mu_rc_body_recipe *recipe, const uint32_t *input,
                         const mu_rc_draw *base)
{
    uint32_t words[16];
    for (int i = 0; i < recipe->count; ++i) {
        for (int k = 0; k < 16; ++k) {
            int source = recipe->draw[i].source[k];
            words[k] = source ? input[source - 1] : recipe->draw[i].value[k];
        }
        mu_rc_draw d = *base;
        d.entry = recipe->draw[i].entry;
        if (d.entry == MU_RC_ENTRY_BODY) {
            d.flags = words[0];
            memcpy(&d.alpha, &words[1], 4);
            d.blend_mesh = (int32_t)words[2];
            memcpy(&d.blend_light, &words[3], 4);
            memcpy(&d.u, &words[4], 4);
            memcpy(&d.v, &words[5], 4);
            d.hidden = (int32_t)words[6];
        } else {
            d.mesh = (int32_t)words[0];
            d.flags = words[1];
            memcpy(&d.alpha, &words[2], 4);
            d.blend_mesh = (int32_t)words[3];
            memcpy(&d.blend_light, &words[4], 4);
            memcpy(&d.u, &words[5], 4);
            memcpy(&d.v, &words[6], 4);
        }
        d.texture = (int32_t)words[7];
        memcpy(d.body_light, &words[8], 12);
        d.level_field = (int32_t)words[11];
        memcpy(d.shade, &words[12], 12);
        d.flag_ca = (uint8_t)words[15];
        if (s->count < s->capacity)
            s->out[s->count] = d;
        ++s->count;
    }
}

/* Apply a shared mesh/body recipe to one generic helper call. Selectors refer
 * to the actual draw arguments and current model fields, never saved pixels.
 * Phases: base, colour2, colour, excellent, ancient, base with flag 0x40000. */
static void emit_parameter_body(sink *s, int phase, uint32_t flags, float alpha, int32_t hidden, int32_t texture)
{
    int type = body_type(s->item->type);
    if (type < 0 || !s->parameters) {
        emit(s, MU_RC_ENTRY_BODY, 0, flags, alpha, hidden, texture);
        return;
    }
    mu_rc_draw base;
    sink one = {&base, 1, 0, s->item, s->model, 0};
    emit(&one, MU_RC_ENTRY_BODY, 0, flags, alpha, hidden, texture);
    uint32_t input[21];
    input[0] = base.flags;
    memcpy(&input[1], &base.alpha, 4);
    input[2] = (uint32_t)base.blend_mesh;
    memcpy(&input[3], &base.blend_light, 4);
    memcpy(&input[4], &base.u, 4);
    memcpy(&input[5], &base.v, 4);
    input[6] = (uint32_t)base.hidden;
    input[7] = (uint32_t)base.texture;
    memcpy(&input[8], base.body_light, 12);
    input[11] = (uint32_t)base.level_field;
    memcpy(&input[12], base.shade, 12);
    input[15] = base.flag_ca;
    memcpy(&input[16], &s->item->object_alpha, 4);
    float pulse = mu_rc_body_types[type].pulse ? armour_pulse(s->item->time) : 0.0f;
    for (int k = 0; k < 3; ++k) {
        float light = base.body_light[k] * pulse;
        memcpy(&input[17 + k], &light, 4);
    }
    float blend = mu_rc_body_types[type].blend_pulse ?
        (float)((double)armour_wave(s->item->time) * 0.7 + (double)0.3f) : 0.0f;
    if (blend > 1.0f) blend = 1.0f;
    memcpy(&input[20], &blend, 4);
    apply_recipe(s, &mu_rc_body_recipes[mu_rc_body_types[type].recipe[phase]], input, &base);
}

/* Item-table predicates 0x00cd6017 (kind B, +0x251), 0x00cd5fac (kind A,
 * +0x250): false without a record or with an index above 0x2c00. */
static int kind_b(const mu_rc_item *it, uint8_t kind)
{
    uint32_t index = (uint32_t)(it->type - 0xae6);
    return it->has_record && index <= 0x2c00u && it->kind_b == kind;
}

static int kind_a(const mu_rc_item *it, uint8_t kind)
{
    return it->has_record && (uint32_t)(it->type - 0xae6) <= 0x2c00u && it->kind_a == kind;
}

int32_t mu_rc_item_glow_level(const mu_rc_item *it)
{
    int32_t level = (it->item_level >> 3) & 0xf;          /* 0x0176cf4a sar 3, and 0xf */
    if (it->render_type & 0x400u)                          /* 0x0176cf65 */
        level = 0;
    /* Closed type switch 0x0176d160..0x0176dc26, before kind and quality. */
    for (size_t i = 0; i < sizeof mu_rc_glow_rows / sizeof mu_rc_glow_rows[0]; ++i)
        if (it->type == mu_rc_glow_rows[i].type) {
            level = mu_rc_glow_rows[i].levels[level];
            break;
        }
    for (size_t i = 0; i < sizeof mu_rc_skin_glow_rows / sizeof mu_rc_skin_glow_rows[0]; ++i)
        if (it->type == mu_rc_skin_glow_rows[i].type) {
            level = mu_rc_skin_glow_rows[i].levels[level];
            break;
        }
    if (kind_b(it, 0x26) || kind_b(it, 0x5b))              /* 0x0176dc26 / 0x0176dc50 */
        level = 9;
    if (it->quality <= 4) {                                /* 0x0176dc78: cap 2q+5 */
        int32_t cap = it->quality * 2 + 5;
        if (level >= cap)
            level = cap;
    }
    return level;
}

static float client_fabs(float x)                         /* 0x0184f8ff */
{
    return 0.0f > x ? -x : x;
}

/* RenderPartObjectBody 0x016e036c, generic tail 0x017020e2 / 0x0176cad9;
 * the +15 attachment models class15_* (0xa99..0xaa1, 0x016fc881..0x016fca83). */
static void part_body(sink *s, float alpha, uint32_t flags, int32_t a6, int32_t a7)
{
    const mu_rc_item *it = s->item;
    if (s->parameters && body_type(it->type) >= 0) {
        emit_parameter_body(s, flags & 0x40000u ? 5 : 0, flags, alpha, -1, -1);
        return;
    }
    /* 0x016f5894..0x016f5a26, without buffs 6/0x8f: no mesh overrides. */
    if (it->type == 0x12ed || it->type == 0x12f5) {
        emit(s, MU_RC_ENTRY_BODY, 0, flags, alpha, -1, -1);
        return;
    }
    if (it->type >= 0xa99 && it->type <= 0xaa1) {
        mu_rc_item copy = *it;
        float k = 0.8f - client_fabs(client_sin(it->time * 0.0018f) * 0.5f);
        float g = client_fabs(client_sin(it->time * 0.0005f));
        copy.blend_mesh = 0;
        s->item = &copy;
        copy.blend_light = k - 0.1f;
        emit(s, MU_RC_ENTRY_MESH, 0, 0x42, it->object_alpha, 0, -1);
        copy.blend_light = k - 0.3f;
        copy.u = g;
        emit(s, MU_RC_ENTRY_MESH, 0, 0x42, it->object_alpha, 0, 0x80d4);
        copy.blend_light = it->blend_light;
        copy.u = it->u;
        emit(s, MU_RC_ENTRY_MESH, 0, 0x1002, it->object_alpha, 0, -1);
        s->item = it;
        return;
    }
    if (a6 != -1 && a7 != -1) {
        emit(s, MU_RC_ENTRY_BODY, 0, flags, alpha, a6, -1);
        emit(s, MU_RC_ENTRY_MESH, a6, flags, it->object_alpha, 0, a7);
    } else {
        emit(s, MU_RC_ENTRY_BODY, 0, flags, alpha, -1, -1);
    }
}

void mu_rc_part_object_color(const mu_rc_item *it, float alpha, float bright, float out[3])
{
    volatile float f = bright * alpha;                     /* 0x016db606: a3 * a2 */
    for (int k = 0; k < 3; ++k)
        out[k] = f * it->enchant[k];                        /* 0x016db951 */
    if (kind_b(it, 0x26)) {                                /* 0x016db998 */
        out[0] = f;
        out[1] = f * 0.5f;
        out[2] = 0.0f;
    } else if (kind_b(it, 0x5b)) {
        out[0] = 0.0f;
        out[1] = f * 0.5f;
        out[2] = f;
    }
}

static int group_of(int32_t type)
{
    int32_t i = type - 0xae6;
    return (i + ((i >> 31) & 0x1ff)) >> 9;                 /* signed division by 512 */
}

static int32_t index_of(int32_t type)
{
    int32_t i = (int32_t)((uint32_t)(type - 0xae6) & 0x800001ffu);
    if (i < 0)
        i = (int32_t)(((uint32_t)i - 1u) | 0xfffffe00u) + 1;
    return i;
}

/* PartObjectColor2 0x016dba54: scales the current body light. */
static void part_object_color2(const mu_rc_item *it, float alpha, float bright, float c[3])
{
    int32_t t = it->type, g = group_of(t);
    volatile float f = bright * alpha;
    float m0 = 1.0f, m1 = 1.0f, m2 = 1.0f;
    if (g > 6 && g < 12) {
        int32_t i = index_of(t);
        switch (i) {
        case 0x12: case 0x2b:                                        /* 0x016dbfc4 */
            m0 = 0.0f; m1 = 0.5f; break;
        case 4: case 0xe: case 0xf: case 0x11: case 0x27: case 0x28: case 0x29: case 0x2a:
        case 0x50: case 0x52: case 0x84: case 0x86: case 0x88:      /* 0x016dbf46 */
            m1 = 0.5f; m2 = 0.0f; break;
        case 0x15: case 0x2c:                                        /* 0x016dc042 */
            c[0] = c[1] = c[2] = 1.0f;
            return;
        default: break;
        }
    } else {
        switch (t) {
        case 0xaf4: case 0xb0d: case 0x1301: case 0x12eb: case 0x14eb: case 0x12f3: case 0x150c: case 0x1513:
            m0 = 0.0f; m1 = 0.5f; break;
        default: break;
        }
    }
    float s0 = f * m0, s1 = f * m1, s2 = f * m2;
    c[0] = s0 * c[0];
    c[1] = s1 * c[1];
    c[2] = s2 * c[2];
}

/* Ancient colour 0x01806042: armour groups 7..11 only. */
static void ancient_color(int32_t type, float c[3])
{
    int32_t g = group_of(type);
    if (!(g > 6 && g < 12))
        return;
    int32_t i = index_of(type);
    static const float blue[3] = {0.1f, 0.6f, 1.0f}, gold[3] = {1.0f, 0.7f, 0.2f}, dark[3] = {0.05f, 0.1f, 0.3f};
    const float *v = blue;
    if (i == 3 || i == 9 || i == 0x11 || i == 0x4f || i == 0x83 || i == 0x187 || i == 0x197)
        v = gold;
    else if ((i >= 0x13e && i <= 0x14e) || i == 0x15e || i == 0x194)
        v = dark;
    for (int k = 0; k < 3; ++k)
        c[k] = v[k];
}

/* RenderPartObjectBodyColor2 0x016dc148, generic path (a8 = -1). */
static void body_color2(sink *s, float alpha, uint32_t flags, float bright, int32_t a7)
{
    float *bl = s->model->body_light;
    if (flags & 0x10u) {
        bl[0] = bl[1] = bl[2] = 1.0f;
    } else {
        mu_rc_part_object_color(s->item, alpha, bright, bl);
    }
    emit_parameter_body(s, 1, flags, alpha, -1, a7);
}

/* RenderPartObjectBodyColor 0x016dec15, generic path. */
static void body_color(sink *s, float alpha, uint32_t flags, float bright, int32_t a6)
{
    float *bl = s->model->body_light;
    int type = body_type(s->item->type);
    if (s->parameters && type >= 0 && mu_rc_body_types[type].dim)
        return; /* This family omits the ordinary high-level colour passes. */
    if (flags & 0x10u) {
        bl[0] = bl[1] = bl[2] = 1.0f;
    } else if (flags & 0x800u) {
        ancient_color(s->item->type, bl);
    } else {
        part_object_color2(s->item, alpha, bright, bl);
    }
    emit_parameter_body(s, flags & 0x800u ? 4 : 2, flags, alpha, -1, a6);
}

static void scale_light(float out[3], const float light[3], float factor)
{
    for (int k = 0; k < 3; ++k)
        out[k] = light[k] * factor;
}

int mu_rc_item_special(int32_t type)
{
    if (body_type(type) >= 0 || type == 0x3895 || type == 0x3896 ||
        (type >= 0x389b && type <= 0x389e))
        return 0;
    /* RENDER-ITEMS-002b: complete body streams, not the link-effect switch. */
    if (type == 0x12ed || type == 0x12f5 || (type >= 0x22e6 && type <= 0x22eb) ||
        type == 0x22f1 || type == 0x248c || type == 0x248d)
        return 0;
    if (type >= 0xa99 && type <= 0xaa1)          /* +15 attachment models, own rule in part_body */
        return 0;
    return mu_rc_special_type(type);
}

static int item_draws_impl(const mu_rc_item *, mu_rc_model *, mu_rc_draw *, int32_t, int32_t *, int);

int mu_rc_item_draws(const mu_rc_item *it, mu_rc_model *model, mu_rc_draw *out, int32_t capacity, int32_t *count)
{
    *count = 0;
    if (mu_rc_item_special(it->type))
        return MU_RC_SPECIAL;
    if ((body_type(it->type) >= 0 || (it->type >= 0x3890 && it->type <= 0x38a2)) &&
        (it->a10 != -1 || it->a11 != -1))
        return MU_RC_UNSUPPORTED;
    /* 0x01770e41..0x01770ef8: wing blend-light writes survive every pass. */
    if (it->type == 0x22ea || it->type == 0x248c || it->type == 0x22eb || it->type == 0x248d) {
        mu_rc_item copy = *it;
        float pulse = client_sin(it->time * 0.001f);
        copy.blend_light = (it->type == 0x22eb || it->type == 0x248d) ?
            (pulse + 1.0f) / 4.0f : pulse + 1.1f;
        return item_draws_impl(&copy, model, out, capacity, count, 1);
    }
    if (it->type == 0x389d) {
        mu_rc_item copy = *it;
        float clock = -it->time;
        int32_t tick = !(clock >= -2147483648.0f && clock < 2147483648.0f) ? INT32_MIN : (int32_t)clock;
        copy.v = (float)(tick % 4000) * 0.00025f;
        return item_draws_impl(&copy, model, out, capacity, count, 1);
    }
    return item_draws_impl(it, model, out, capacity, count, 1);
}

int mu_rc_item_draws_generic(const mu_rc_item *it, mu_rc_model *model, mu_rc_draw *out, int32_t capacity,
                             int32_t *count)
{
    return item_draws_impl(it, model, out, capacity, count, 0);
}

static int item_draws_impl(const mu_rc_item *it, mu_rc_model *model, mu_rc_draw *out, int32_t capacity,
                             int32_t *count, int parameters)
{
    sink s = {out, capacity, 0, it, model, parameters};
    *count = 0;
    if (it->select != 0 || it->object_shadow == 1 || it->a13 == 1)
        return MU_RC_UNSUPPORTED;
    /* Items whose record type (+0x252) is 4 take their own chain inside
     * RenderPartObjectBody (0x016fd6a2..0x016fe2e1); not reconstructed. */
    if (it->has_record && it->item_kind == 4)
        return MU_RC_UNSUPPORTED;
    /* The +15 attachments are drawn by 0x016d53a4 with level, option and ext 0 only. */
    if (it->type >= 0xa99 && it->type <= 0xaa1 && (((it->item_level >> 3) & 0xf) != 0 || it->option1 != 0 || it->ext_option != 0))
        return MU_RC_UNSUPPORTED;
    /* Record kinds that select further branches (found by the executed kind
     * sweep, scripts/validate_renderchar.py): not reconstructed. */
    if (it->has_record && ((it->kind_a == 0x1f || (it->kind_a >= 0x22 && it->kind_a <= 0x2b && it->kind_a != 0x23)) ||
                           it->kind_b == 0x27 || it->kind_b == 0x4b || it->kind_b == 0x72 || it->item_kind == 8 || it->item_kind == 0xb))
        return MU_RC_UNSUPPORTED;
    int32_t level = mu_rc_item_glow_level(it);
    int type_row = body_type(it->type);
    if (parameters && type_row >= 0 && mu_rc_body_types[type_row].plain)
        level = 0;
    if (parameters) {
        for (size_t i = 0; i < sizeof mu_rc_skin_bodies / sizeof mu_rc_skin_bodies[0]; ++i) {
            int32_t tested = mu_rc_skin_bodies[i].effective ? level : (it->item_level >> 3) & 15;
            if (it->type != mu_rc_skin_bodies[i].type ||
                (mu_rc_skin_bodies[i].level >= 0 && tested != mu_rc_skin_bodies[i].level))
                continue;
            mu_rc_draw base;
            sink one = {&base, 1, 0, it, model, 0};
            emit(&one, MU_RC_ENTRY_BODY, 0, it->render_type, it->alpha, 0, -1);
            uint32_t input[17];
            input[0] = base.flags;
            memcpy(&input[1], &base.alpha, 4);
            input[2] = (uint32_t)base.blend_mesh;
            memcpy(&input[3], &base.blend_light, 4);
            memcpy(&input[4], &base.u, 4);
            memcpy(&input[5], &base.v, 4);
            input[6] = (uint32_t)base.hidden;
            input[7] = (uint32_t)base.texture;
            memcpy(&input[8], base.body_light, 12);
            input[11] = (uint32_t)base.level_field;
            memcpy(&input[12], base.shade, 12);
            input[15] = base.flag_ca;
            memcpy(&input[16], &it->object_alpha, 4);
            apply_recipe(&s, &mu_rc_skin_bodies[i].recipe, input, &base);
            *count = s.count;
            return s.count > capacity ? MU_RC_FULL : MU_RC_OK;
        }
    }
    const float *L = it->light;
    uint32_t rt = it->render_type;
    uint32_t keep = rt & 0x100u;

    if (level < 3) {                                       /* default 0x017e161d..0x017e16fa */
        model->level_field = 0;
        for (int k = 0; k < 3; ++k) {
            model->shade[k] = L[k];
            model->body_light[k] = L[k];
        }
        part_body(&s, it->alpha, rt, it->a10, it->a11);
    } else if (level < 7) {                                /* 0x017e16ff / 0x017e191c */
        model->level_field = 0;
        for (int k = 0; k < 3; ++k)
            model->shade[k] = L[k];
        float p = client_sin(it->time * 0.004f) * 0.15f + 0.6f;
        float v[3];
        if (level < 5) {
            v[0] = p; v[1] = p * 0.6f; v[2] = p * 0.6f;
        } else {
            v[0] = p * 0.5f; v[1] = p * 0.7f; v[2] = p;
        }
        for (int k = 0; k < 3; ++k)
            model->body_light[k] = v[k] * L[k];             /* 0x00cfcc4a component product */
        uint8_t saved = model->flag_ca;
        model->flag_ca = 1;
        part_body(&s, it->alpha, rt, it->a10, it->a11);
        model->flag_ca = saved;
    } else if (it->quality < 1) {                          /* 0x017e1b39 */
        for (int k = 0; k < 3; ++k)
            model->body_light[k] = L[k];
        part_body(&s, it->alpha, rt, it->a10, it->a11);
    } else {
        model->level_field = 0;
        for (int k = 0; k < 3; ++k)
            model->shade[k] = L[k];
        int32_t q = it->quality;
        if (level < 9 && q > 0) {                          /* levels 7, 8 */
            scale_light(model->body_light, L, 0.8f);
            part_body(&s, it->alpha, rt, it->a10, it->a11);
            model->level_field = level;
            body_color2(&s, it->alpha, 0x44, 1.0f, -1);
        } else if (level < 11 && q > 1) {                  /* levels 9, 10 */
            scale_light(model->body_light, L, 0.9f);
            part_body(&s, it->alpha, rt, it->a10, it->a11);
            model->level_field = level;
            body_color2(&s, it->alpha, keep | 0x44, 1.0f, -1);
            body_color2(&s, it->alpha, keep | 0x48, 1.0f, -1);
        } else if (level < 16 && q > (level < 13 ? 2 : 3)) {  /* levels 11..15 */
            scale_light(model->body_light, L, 0.9f);
            part_body(&s, it->alpha, rt, it->a10, it->a11);
            model->level_field = level;
            body_color(&s, 1.0f, keep | 0x240, 1.0f, -1);
            if (level >= 13)
                body_color(&s, 1.0f, keep | 0x1040, 1.0f, -1);
            body_color2(&s, it->alpha, keep | 0x48, 1.0f, -1);
            body_color2(&s, it->alpha, keep | 0x44, 1.0f, -1);
        } else {
            for (int k = 0; k < 3; ++k)
                model->body_light[k] = L[k];
            part_body(&s, it->alpha, rt, it->a10, it->a11);
        }
    }

    /* Tail 0x017e2c87: excellent, then ancient. */
    if (it->quality == 0 || it->buff_39 || it->buff_12 || it->buff_41)
        goto done;
    if (it->option1 == 1 && (it->type > 0xae5 || it->type == 0xace || it->type == 0xacf || it->type == 0xad0)) {
        if (!kind_a(it, 6)) {
            float p = client_sin(it->time * 0.002f) * 0.5f + 0.5f;
            model->body_light[0] = p;
            model->body_light[1] = p * 0.3f;
            model->body_light[2] = 1.0f - p;
            emit_parameter_body(&s, 3, 0x42, 1.0f, -1, -1);
            goto done;
        }
    }
    {
        int32_t e = it->ext_option;
        int tier = (e & 1) ? 1 : (e & 2) ? 2 : (e & 0x10) ? 3 : (e & 0x20) ? 4 : 0;   /* 0x009e072d */
        if (tier == 0 || !it->has_record || it->item_kind == 4)
            goto done;
        if (parameters && type_row >= 0 && mu_rc_body_types[type_row].dim) {
            /* 0x017e5e19..0x017e61bd: three cumulative colour passes. */
            float a = client_sin(it->time * 0.004f) * 0.5f + 0.4f;
            s.parameters = 0;
            for (int i = 0; i < 3; ++i)
                body_color(&s, a, 0x240, 1.0f, -1);
        } else {
            float a = client_sin(it->time * 0.001f) * 0.5f + 0.4f;
            body_color(&s, a, 0x840, 1.0f, -1);
        }
    }
done:
    *count = s.count;
    return s.count > capacity ? MU_RC_FULL : MU_RC_OK;
}

/* RenderObjDraw 0x0176ffe0..0x01770591. Transform without scale, then add OBJECT position. */
int mu_rc_skin_effect(int32_t type, float time, mu_rc_link_effect *out)
{
    if (type != 0x389c && type != 0x389d)
        return 0;
    float pulse = client_sin(time * 0.002f) * 0.35f + 0.65f;
    *out = (mu_rc_link_effect){0};
    out->sprite = (mu_rc_link_sprite){0, 0x7f26, pulse * 0.8f + (type == 0x389c ? 2.0f : 2.5f),
        {pulse * 0.32f, pulse * 0.32f, pulse * 2.0f}, 0, 0, 4};
    out->offset[1] = type == 0x389c ? 0 : -5.0f;
    out->offset[2] = type == 0x389c ? 15.0f : -15.0f;
    if (type == 0x389d) {
        out->sprite.light[0] = pulse * 2.0f;
        out->sprite.light[2] = pulse * 0.32f;
    }
    return 1;
}

int mu_rc_link_supported(int32_t type)
{
    for (size_t i = 0; i < sizeof mu_rc_link_chains / sizeof mu_rc_link_chains[0]; ++i)
        if (type == mu_rc_link_chains[i].type)
            return 1;
    return type == 0x12ea || type == 0x12eb || type == 0x12ec || type == 0x12f7 ||
           type == 0x1301 || type == 0x1303 || type == 0x14f0 || type == 0x12fb ||
           type == 0x0ef4 || type == 0x0afc || type == 0x0afd || type == 0x0afe;
}

static float link_intensity(int32_t random_value)
{
    return (float)(random_value % 30 + 70) * 0.005f;
}

/* RenderLinkItem 0x012c6aa1 and 0x012c70e7..0x012c7415. */
int mu_rc_link_sprites(int32_t type, int32_t random_value, mu_rc_link_sprite *out,
                        int32_t capacity, int32_t *count)
{
    *count = 0;
    if (type != 0x12ea && type != 0x12eb && type != 0x12ec && type != 0x12f7 && type != 0x1301 && type != 0x1303)
        return MU_RC_SPECIAL;
    float intensity = link_intensity(random_value);
    int many = type == 0x12ec || type == 0x12f7 || type == 0x1303;
    int extra = type == 0x12f7 || type == 0x1303;
    int n = many ? (extra ? 10 : 6) : 2;
    for (int i = 0; i < n; ++i) {
        if (i >= capacity)
            continue;
        mu_rc_link_sprite *s = &out[i];
        s->bone = many ? (i < 6 ? 13 + i : 5 + i - 6) : (i == 0 ? 2 : 6);
        s->bitmap = 0x7f67;
        s->scale = 1.0f;
        s->light[0] = intensity * (extra ? 0.5f : type == 0x12ec ? 0.6f : 1.0f);
        s->light[1] = intensity * (extra ? 0.5f : type == 0x12ec ? 1.0f : 0.6f);
        s->light[2] = intensity * (many ? 0.8f : 0.2f);
        s->rotation = 0.0f;
        s->blend = 0;
        s->axes = 4;  /* 0x0150e746 */
    }
    *count = n;
    return n > capacity ? MU_RC_FULL : MU_RC_OK;
}

/* 0x012c741a..0x012c7a40. Offsets precede TransformPosition. */
int mu_rc_link_effects(int32_t type, mu_rc_random_fn random, void *context,
                        mu_rc_link_effect *out, int32_t capacity, int32_t *count)
{
    return mu_rc_link_effects_time(type, 0.0f, random, context, out, capacity, count);
}

int mu_rc_link_effects_time(int32_t type, float time, mu_rc_random_fn random, void *context,
                           mu_rc_link_effect *out, int32_t capacity, int32_t *count)
{
    *count = 0;
    int chain_index = -1;
    for (size_t i = 0; i < sizeof mu_rc_link_chains / sizeof mu_rc_link_chains[0]; ++i)
        if (type == mu_rc_link_chains[i].type)
            chain_index = (int)i;
    if (chain_index < 0 && type != 0x14f0 && type != 0x12fb && type != 0x0ef4 && type != 0x0afc && type != 0x0afd && type != 0x0afe)
        return MU_RC_SPECIAL;
    float intensity = link_intensity(random(context));
    mu_rc_link_effect effects[20] = {0};
    int n = 0;
    if (chain_index >= 0) {
        /* 0x012cb556 / 0x012cb7ab: shared bone chains, original random order. */
        const mu_rc_link_chain *chain = &mu_rc_link_chains[chain_index];
        for (int i = 0; i < chain->count; ++i) {
            int bone = chain->first + i;
            if (chain->flash && random(context) % 3 == 0) {
                mu_rc_link_effect *e = &effects[n++];
                e->sprite = (mu_rc_link_sprite){bone, 0x7f67, 0.6f, {0.4f, 0.4f, 0.4f},
                                               (float)(random(context) % 360), 0, 4};
                e->offset[2] = chain->z;
            }
            float light[3];
            for (int k = 0; k < 3; ++k)
                light[k] = intensity * chain->rgb[k];
            if (!chain->flash) {
                mu_rc_link_effect *e = &effects[n++];
                e->sprite = (mu_rc_link_sprite){bone, 0x7f67, 1.0f, {light[0], light[1], light[2]}, 0, 0, 4};
                e->offset[2] = chain->z;
            }
            if (chain->white && i == chain->count - 1)
                light[0] = light[1] = light[2] = 1.0f;
            mu_rc_link_effect *e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){bone, 0x7ef7, 2.0f, {light[0], light[1], light[2]}, 0, 0, 4};
            e->offset[2] = chain->z;
        }
    } else if (type == 0x14f0) {
        for (int i = 0; i < 10; ++i) {
            float x = (float)i * 30.0f - 180.0f;
            if (random(context) % 3 == 0) {
                mu_rc_link_effect *e = &effects[n++];
                e->sprite = (mu_rc_link_sprite){0, 0x7f67, 0.6f, {0.4f, 0.4f, 0.4f},
                                                (float)(random(context) % 360), 0, 4};
                e->offset[0] = x;
                e->offset[1] = -40.0f;
            }
            mu_rc_link_effect *e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){0, 0x7ef7, 2.0f,
                                            {intensity, intensity * 0.3f, intensity * 0.1f}, 0, 0, 4};
            e->offset[0] = x;
            e->offset[1] = -40.0f;
        }
    } else if (type == 0x0ef4) { /* 0x012c7a45..0x012c7e63 */
        float jitter = (float)(random(context) % 60) / 20.0f - 1.5f;
        float scale = (float)(random(context) % 10) / 20.0f + 1.4f;
        for (int i = 0; i < 2; ++i) {
            mu_rc_link_effect *e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){0, 0x7f67, i ? scale - 0.3f : scale,
                                            {1.0f, 0.3f, 0}, i ? 20.0f : 0.0f, 0, 4};
            e->offset[1] = -100.0f + jitter;
            e->offset[2] = jitter;
        }
        jitter = (float)(random(context) % 60) / 20.0f - 1.5f;
        scale = (float)(random(context) % 10) / 20.0f + 1.0f;
        mu_rc_link_effect *e = &effects[n++];
        e->sprite = (mu_rc_link_sprite){0, 0x7ef7, scale + 0.3f, {1.0f, 0.3f, 0}, 0, 0, 4};
        e->offset[1] = -100.0f + jitter;
        e->offset[2] = jitter;
        jitter = (float)(random(context) % 40) / 20.0f - 1.0f;
        scale = (float)(random(context) % 8) / 20.0f + 0.4f;
        for (int i = 0; i < 2; ++i) {
            e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){0, 0x7f67, i ? scale - 0.2f : scale,
                                            {1.0f, 0.3f, 0}, i ? 90.0f : 0.0f, 0, 4};
            e->offset[1] = 100.0f + jitter;
            e->offset[2] = jitter;
        }
    } else if (type == 0x0afc) { /* 0x012c7e68..0x012c8078 */
        float pulse = client_sin(time * 0.4f) * 0.25f + 0.7f;
        for (int i = 0; i < 2; ++i) {
            mu_rc_link_effect *e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){0, 0x7ef8, 0.75f, {pulse, pulse - 0.5f, pulse - 0.5f}, 0, 0, 4};
            e->offset[0] = i ? -5.0f : 5.0f;
            e->offset[1] = -22.0f;
            e->offset[2] = -10.0f;
        }
    } else if (type == 0x0afd) { /* 0x012c807d..0x012c856c */
        float jitter = (float)(random(context) % 60) / 20.0f - 1.5f;
        float scale = (float)(random(context) % 30) / 20.0f + 1.5f;
        float pulse = client_sin(time * 0.7f) * 0.2f + 0.5f;
        float rotation = time * 0.0006f * 360.0f;
        for (int i = 0; i < 7; ++i) {
            mu_rc_link_effect *e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){i < 4 ? 4 : i + 2,
                i < 2 ? 0x7f67 : 0x7ef7,
                i == 0 ? scale : i == 1 ? scale - 0.4f : i == 2 ? 2.3f : i == 6 ? 1.0f : 2.0f,
                {0.2f, 0.2f, pulse}, i < 2 ? rotation + (i ? 90.0f : 0.0f) : 0.0f, 0, 4};
            if (i < 3) e->offset[1] = e->offset[2] = jitter;
            if (i == 3) e->offset[0] = 30.0f;
        }
    } else if (type == 0x0afe) { /* 0x012c8d7b..0x012c91f9 */
        for (int i = 0; i < 5; ++i) {
            mu_rc_link_effect *e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){2, i < 2 ? 0x7ef8 : i < 4 ? 0x7f67 : 0x7ef7,
                i < 2 ? 0.45f : i == 2 ? 0.7f : i == 3 ? (float)(random(context) % 100) / 180.0f + 0.5f : 3.0f,
                {0.6f, 0.6f, 0.6f}, i == 3 ? time * 0.0006f * 360.0f : 0.0f, 0, 4};
            if (i < 2) e->offset[2] = i ? -3.0f : 3.0f;
            if (i == 4) {
                float pulse = client_sin(time * 0.4f) * 0.25f + 0.6f;
                e->sprite.light[0] = e->sprite.light[1] = e->sprite.light[2] = pulse;
            }
        }
    } else {
        if (random(context) % 2 == 1) {
            for (int i = 0; i < 2; ++i) {
                mu_rc_link_effect *e = &effects[n++];
                e->sprite = (mu_rc_link_sprite){i == 0 ? 4 : 12, 0x7f26, 0.8f,
                                                {0.8f, 0.8f, 0.2f}, 0, 0, 4};
                e->particle = 11;
            }
        }
        for (int i = 0; i < 2; ++i) {
            mu_rc_link_effect *e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){i == 0 ? 7 : 15, 0x7ef7, 2.0f,
                                            {0.5f, 0.5f, 0.1f}, 0, 0, 4};
        }
        static const float scales[3] = {0.8f, 1.3f, 2.0f};
        for (int i = 0; i < 3; ++i) {
            mu_rc_link_effect *e = &effects[n++];
            e->sprite = (mu_rc_link_sprite){0, 0x7ef7, scales[i], {1, 1, 0.4f}, 0, 0, 4};
            e->offset[0] = 20.0f;
        }
    }
    for (int i = 0; i < n && i < capacity; ++i)
        out[i] = effects[i];
    *count = n;
    return n > capacity ? MU_RC_FULL : MU_RC_OK;
}

/* ---- back carry ---- */

#include "back_matrices.h"
#include "../record-math/record_math.h"

int mu_rc_back_local(int32_t type, int32_t kind_b, int32_t right_hand, uint32_t out[12])
{
    /* Kinds the link chain tests (0x012bdc0b..0x012c2ac3); other kinds behave as none. */
    static const int32_t kinds[] = {0x0b, 0x4b, 0x54, 0x59, 0x5a, 0x72, 0x73, 0x7b};
    int32_t kind = 0;
    for (size_t i = 0; i < sizeof kinds / sizeof kinds[0]; ++i)
        if (kind_b == kinds[i])
            kind = kind_b;
    int32_t right = right_hand ? 1 : 0;
    for (size_t i = 0; i < sizeof mu_rc_back_rows / sizeof mu_rc_back_rows[0]; ++i) {
        const int32_t *row = mu_rc_back_rows[i];
        if (type >= row[0] && type <= row[1] && kind == row[2] && right == row[3]) {
            if (row[4] < 0)
                return 0;
            memcpy(out, &mu_rc_back_matrices[row[4]][1], 48);
            return mu_rc_back_matrices[row[4]][0] ? 2 : 1;
        }
    }
    return 0;
}

int mu_rc_back_root(const uint32_t bone[12], int32_t type, int32_t kind_b, int32_t right_hand, uint32_t out[12])
{
    uint32_t local[12];
    int mode = mu_rc_back_local(type, kind_b, right_hand, local);
    if (mode == 0)
        return 0;
    if (mode == 2)
        memcpy(out, local, 48);           /* absolute: the owner bone is not used */
    else
        mu_pose_concat(bone, local, out); /* 0x012c29e4 */
    return 1;
}

/* ---- RenderCharacter call plan ---- */

static int slot_kind(const mu_rc_slot *s, uint8_t kind)
{
    uint32_t index = (uint32_t)(s->type - 0xae6);
    return s->has_record && index <= 0x2c00u && s->kind_b == kind;
}

typedef struct plan {
    mu_rc_call *out;
    int32_t capacity, count;
} plan;

static mu_rc_call *push(plan *p)
{
    static mu_rc_call scratch;
    mu_rc_call *call = p->count < p->capacity ? &p->out[p->count] : &scratch;
    p->count++;
    memset(call, 0, sizeof *call);
    return call;
}

static void link_call(plan *p, const mu_rc_character *c, int32_t slot, const mu_rc_slot *s, int32_t type, float x, float y,
                      float z, int32_t link, int32_t right, int32_t bone)
{
    mu_rc_call *call = push(p);
    call->kind = MU_RC_CALL_LINK;
    call->slot = slot;
    call->type = type;
    call->item_level = s->level;
    call->option = s->option;
    call->translate = c->translate;
    call->xyz[0] = x;
    call->xyz[1] = y;
    call->xyz[2] = z;
    call->link = link;
    call->right_hand = right;
    call->link_bone = bone;
    call->part_action = s->action;
    call->part_speed = s->speed;
    call->part_frame = s->frame;
    call->part_prior_frame = s->prior_frame;
}

/* Hand-weapon animation 0x0136b4b7..0x0136c33f: part action and play speed. */
static void weapon_animation(const mu_rc_character *c, mu_rc_slot *s)
{
    const float *pa = c->player_speed;
    int32_t t = s->type;
    uint16_t a = c->action;
    if (a == 0x7e || a == 0x7f || a == 0x80 || a == 0x81 || a == 0x107) {
        static const int32_t cross[] = {0x12fd, 0x1302, 0x1305, 0x130a, 0x130c, 0x130e, 0x131e, 0x1320, 0x1323,
                                        0x1326, 0x1329, 0x132c, 0x132f};
        s->action = 0;
        for (size_t i = 0; i < sizeof cross / sizeof cross[0]; ++i)
            if (t == cross[i])
                s->action = 1;
        s->speed = pa[0x7e];
        return;
    }
    if (t == 0xee8) {
        if (a < 0x71 || a > 0x72) { s->action = 1; s->speed = pa[1]; }
        else { s->action = 2; s->speed = pa[0x71]; }
        return;
    }
    if (t == 0xeeb) { s->action = 0; s->speed = pa[1] * 2.0f; return; }
    if (t == 0x14ec) { s->action = 0; s->speed = pa[1] * 15.0f; return; }
    if (t == 0xb09) {
        if (s->frame < 2.0f) { s->action = 0; s->speed = pa[4] * 1.5f; }
        else s->frame = 2.0f;
        return;
    }
    if (t == 0xb55) { s->action = 0; s->speed = 0.6f; return; }
    if (t >= 0xae6 && t <= 0xce5) { s->action = 0; s->speed = pa[1]; return; }
    static const struct { int32_t type; int8_t action; int8_t source; float value; } table[] = {
        /* source 1: value * Player action speed index (stored in value as integer); 0: constant */
        {0x12fd, 0, 1, 1}, {0x1302, 0, 1, 1}, {0x12ff, 1, 1, 1}, {0xef6, 0, 1, 1}, {0xef7, 0, 1, 1}, {0xf04, 0, 1, 1},
        {0xf06, 0, 2, 1}, {0xefc, 0, 2, 1}, {0xeff, 0, 1, 1}, {0x1517, 0, 1, 1}, {0xf08, 0, 1, 1},
        {0x1315, 0, 0, 0.05f}, {0x1508, 0, 1, 1}, {0x1509, 0, 1, 1}, {0x150b, 0, 1, 1}, {0x150a, 0, 1, 3},
        {0x10f7, 0, 0, 0.1f}, {0x10f6, 0, 0, 0.25f}, {0x10f9, 0, 0, 0.15f}, {0x1519, 0, 0, 0.3f}, {0x10fe, 0, 0, 0.15f},
        {0xf00, 0, 0, 0.1f}, {0xf01, 0, 0, 0.1f}, {0x151b, 0, 0, 0.1f}, {0x1100, 0, 0, 0.2f}, {0x151e, 0, 0, 0.2f},
        {0xf0a, 0, 0, 0.2f}, {0x1102, 0, 0, 0.1f}, {0xf0c, 0, 0, 0.3f}, {0xf0d, 0, 0, 0.3f}, {0xf03, 0, 0, 0.2f},
        {0xf05, -1, 0, 0.08f}, {0x130e, 0, 0, 0.2f}, {0x1523, 0, 0, 0.1f}, {0xf0e, 0, 0, 0.2f}, {0x1103, 0, 0, 0.2f},
        {0xf10, 0, 0, 0.1f}, {0x1104, 0, 0, 0.1f}, {0x131e, 0, 0, 0.1f}, {0x1526, 0, 0, 0.1f}, {0x1717, 0, 0, 0.2f},
        {0x1731, 0, 0, 0.2f}, {0x1751, 0, 0, 0.2f}, {0x1314, 0, 0, 0.2f}, {0x1320, 0, 0, 0.1f}, {0xf12, 0, 0, 0.1f},
        {0x1105, 0, 0, 0.1f}, {0xf14, 0, 0, 0.1f}, {0x1106, 0, 0, 0.1f}, {0x1549, 0, 0, 0.1f}, {0x1323, 0, 0, 0.1f},
        {0x1326, 0, 0, 0.1f}, {0x1329, 0, 0, 0.1f}, {0x132c, 0, 0, 0.1f}, {0x157e, 0, 0, 0.3f}, {0xf1a, 0, 0, 0.3f},
        {0x132f, 0, 0, 0.1f}, {0x1587, 0, 0, 0.3f}, {0xf2f, 0, 0, 0.3f}, {0xf30, 0, 0, 0.03f},
    };
    for (size_t i = 0; i < sizeof table / sizeof table[0]; ++i) {
        if (table[i].type != t)
            continue;
        if (table[i].action >= 0)
            s->action = (uint8_t)table[i].action;
        if (table[i].source == 0)
            s->speed = table[i].value;
        else if (table[i].source == 1)
            s->speed = pa[(int)table[i].value];
        else
            s->speed = pa[1] * 0.5f;
        return;
    }
    if (slot_kind(s, 0x59)) {
        if (a < 0x6f || a > 0x132) { s->action = 1; s->speed = 0.25f; }
        else { s->action = 2; s->speed = 0.4f; }
    } else if (slot_kind(s, 0x5a)) {
        s->action = 0;
        s->speed = t == 0x154d ? 0.07f : t == 0x1552 ? 0.2f : 0.1f;
    } else if (slot_kind(s, 0x72)) {
        s->action = 0;
        s->speed = 0.1f;
    } else {
        s->action = 0;
        s->speed = 0.0f;
        s->frame = 0.0f;
        s->prior_frame = 0.0f;
    }
}

/* Wing speed 0x0139fd02 for the normal (non-flying) actions. */
static void wing_animation(const mu_rc_character *c, mu_rc_slot *w)
{
    int32_t t = w->type;
    uint16_t a = c->action;
    if (a > 0x185)
        return;
    if (a >= 0x59 && a <= 0x5f) {
        w->speed = 1.0f;    /* default of the flying branch (0x0139ffef); listed types differ */
        return;
    }
    if (t == 0x239a) w->speed = 0.25f;
    else if (t == 0x2301 || t == 0x2302) w->speed = 0.375f;
    else if (t == 0x2386 || t == 0x2387) w->speed = 0.185f;
    else if (t == 0x23a8 || t == 0x23a9 || t == 0x23aa || t == 0x23ab || t == 0x23ac) w->speed = 0.3f;
    else if (t == 0x23ee || t == 0x23ff || t == 0x2404) w->speed = 0.7f;
    else if (t == 0x23f1 || t == 0x2401 || t == 0x24c6) w->speed = 0.23f;
    else w->speed = 0.25f;
}

/* BackCarry 0x0139db9a: weapons on the back. Returns its zone flag [ebp-0xd]
 * (0x0139f2d9), which suppresses the hand loop even when nothing was carried. */
static int back_carry(const mu_rc_character *c, mu_rc_slot weapons[2], plan *p)
{
    int zone = c->safe_zone == 1 && weapons[0].type != 0xb0f;          /* 0x0095fb27 */
    if (c->action > 0x147 && c->action < 0x168)
        zone = 1;
    int carried = 0;
    for (int i = 0; i < 2; ++i) {
        mu_rc_slot *s = &weapons[i];
        int32_t t = s->type;
        if (t < 0)
            continue;
        /* 0x0139f31e: weapons 0xae6..0x18e5 without kind B 0x0e, or 0x0139d8f8 (bow kinds 8/9 of slot 0). */
        int bow = slot_kind(&weapons[0], 8) || slot_kind(&weapons[0], 9);
        if (bow || (t >= 0xae6 && t < 0x18e6 && !slot_kind(s, 0x0e)))
            carried = 1;
        if (t == 0x12ed || t == 0x12f5 || slot_kind(s, 0x4b)) {
            carried = 1;
        } else if (!slot_kind(s, 0x54)) {
            if (!slot_kind(s, 0x7b)) {
                if (!zone)
                    carried = 0;
            } else if (!zone) {
                carried = 0;
            } else if (c->action != 9 || c->frame < 3.0f || c->frame > 44.0f) {
                if (c->safe_zone != 1) { zone = 0; carried = 0; }
            } else {
                zone = 0;
                carried = 0;
            }
        } else if (!zone) {
            carried = 0;
        } else if (c->action != 0x1f || c->frame < 3.0f || c->frame > 24.0f) {
            if (c->safe_zone != 1) { zone = 0; carried = 0; }
        } else {
            zone = 0;
            carried = 0;
        }
        if (!carried)
            continue;
        mu_rc_slot saved = *s;
        static const int32_t action1[] = {0x12ff, 0x1305, 0x130a, 0x130c, 0x130e, 0x131e, 0x1320, 0x1323, 0x1326,
                                          0x1329, 0x132c, 0x132f};
        int listed1 = 0;
        for (size_t k = 0; k < sizeof action1 / sizeof action1[0]; ++k)
            listed1 |= t == action1[k];
        if (t == 0x12fd || t == 0x1302 || listed1 || t == 0x1100 || t == 0x151e || t == 0xf30) {
            s->action = (uint8_t)((t == 0x12fd || t == 0x1302) ? 2 : listed1 ? 1 : 0);
            s->speed = t == 0xf30 ? 0.03f : 0.25f;
            link_call(p, c, i, s, t, 0.0f, 0.0f, 15.0f, 1, 1, 47);
            s->speed = s->speed;   /* action/speed stay (only the link bone is restored) */
            continue;
        }
        if (slot_kind(s, 0x59)) {
            s->action = c->safe_zone == 1 ? 0 : 1;   /* 0x0106b9f7 (mount manager) taken as false */
            s->speed = c->safe_zone == 1 ? 0.25f : 0.2f;
            link_call(p, c, i, s, t, 26.0f, 20.0f, 25.0f, 1, 1, 0x11);
            continue;
        }
        if (slot_kind(s, 0x5a) || slot_kind(s, 0x72)) {
            s->action = 0;
            s->speed = 0.1f;
            link_call(p, c, i, s, t, 26.0f, 20.0f, 25.0f, 1, 1, slot_kind(s, 0x5a) ? 0x21 : 0x2a);
            continue;
        }
        int right = 0;
        if (slot_kind(s, 0x4b))
            right = weapons[0].type - 0xae6 > 0 && slot_kind(&weapons[0], 8);
        else if (slot_kind(s, 10))
            right = 1;
        else if (slot_kind(s, 8))
            right = 0;
        else
            right = i == 0;
        if (t > 0xae5 && t < 0x18e6) {
            s->action = 0;
            s->frame = 0.0f;
            s->speed = 0.0f;
            s->prior_frame = 0.0f;
        }
        link_call(p, c, i, s, t, 0.0f, 0.0f, 15.0f, 1, right, 47);
        *s = saved;                                                  /* 0x0139e4a3: part state restored */
    }
    return zone;
}

int mu_rc_character_plan(const mu_rc_character *c, mu_rc_call *out, int32_t capacity, int32_t *count)
{
    plan p = {out, capacity, 0};
    int32_t nibble = c->class_byte & 0xf;
    *count = 0;
    if (nibble == 4 || nibble == 5 || nibble == 6 || nibble == 13)
        return MU_RC_UNSUPPORTED;
    /* Wings with their own branches in BackCarry (0x0139e85a..) and the skill action 0x8f. */
    if ((c->wing.type != -1 && (c->wing.type < 0x22e6 || c->wing.type > 0x22ec)) || c->action == 0x8f)
        return MU_RC_UNSUPPORTED;
    /* Shadow pass 0x01363a62..0x01363e9f (Player): object +4 = 1 around the call. */
    if (c->alpha >= 0.5f) {
        mu_rc_call *call = push(&p);
        call->kind = MU_RC_CALL_SHADOW;
        call->slot = -1;
        call->type = 0xa92;
        call->translate = c->translate;
        call->render_type = 2;
    }
    /* Body parts 0x0136a374: slots 5..0. */
    for (int slot = 5; slot >= 0; --slot) {
        const mu_rc_slot *s = &c->parts[slot];
        if (s->type == -1)
            continue;
        mu_rc_call *call = push(&p);
        call->kind = MU_RC_CALL_PART;
        call->slot = slot;
        call->type = s->type;
        call->item_level = (int32_t)s->level << 3;
        call->option = s->option != 0;
        call->ext = s->ext;
        call->translate = c->translate;
        call->select = c->select;
        call->render_type = 2;
    }
    /* +15 armour attachments 0x016d53a4 (models class15_*, 0xa99..0xaa1). */
    static const int32_t attach[6][2][2] = {
        {{-1, -1}, {-1, -1}},
        {{20, 0xa9f}, {-1, -1}},           /* helm */
        {{35, 0xa9b}, {26, 0xa9c}},        /* armor */
        {{3, 0xaa0}, {10, 0xaa1}},         /* pants */
        {{36, 0xa99}, {27, 0xa9a}},        /* gloves */
        {{4, 0xa9d}, {11, 0xa9e}},         /* boots */
    };
    for (int slot = 0; slot < 6; ++slot) {
        const mu_rc_slot *s = &c->parts[slot];
        if (slot == 0 || s->level != 15 || s->type == -1)
            continue;
        for (int k = 0; k < 2; ++k) {
            if (attach[slot][k][1] == -1)
                continue;
            mu_rc_slot part = *s;
            link_call(&p, c, slot, &part, attach[slot][k][1], 0.0f, 0.0f, 0.0f, 1, 1, attach[slot][k][0]);
            p.out[p.count - 1 < p.capacity ? p.count - 1 : 0].item_level = 0;
            p.out[p.count - 1 < p.capacity ? p.count - 1 : 0].option = 0;
        }
    }
    mu_rc_slot weapons[2] = {c->weapons[0], c->weapons[1]};
    mu_rc_slot wing = c->wing;
    int carried = back_carry(c, weapons, &p);
    if (wing.type != -1) {                                           /* 0x0139e85a */
        wing_animation(c, &wing);
        link_call(&p, c, 8, &wing, wing.type, 0.0f, 0.0f, 15.0f, 0, 1, 47);
    }
    if (!carried) {
        for (int i = 0; i < 2; ++i) {                                /* 0x0136b4b7 */
            mu_rc_slot *s = &weapons[i];
            int32_t t = s->type;
            if (i == 0 && c->action == 0x8f && c->frame <= 4.0f)
                continue;
            if (t == -1 || t == 0x12ed || t == 0x12f5 || t == 0x24eb || slot_kind(s, 0x4b))
                continue;
            weapon_animation(c, s);
            link_call(&p, c, i, s, t, 0.0f, 0.0f, 0.0f, 0, 1, s == &weapons[0] ? 33 : 42);
        }
    }
    *count = p.count;
    return p.count > capacity ? MU_RC_FULL : MU_RC_OK;
}

/* ---- the character light: RenderCharacter 0x01367530..0x01367d85 ---- */

int mu_rc_light_glow_class(int32_t index)
{
    static const int32_t list[] = {0x211, 0x212, 0x213, 0x214, 0x215,                      /* 0x0139bcdc */
                                   0x216, 0x217, 0x218, 0x219, 0x21a, 0x21b, 0x349, 0x34a,  /* 0x0139bd24 */
                                   0x34b, 0x34c, 0x371, 0x372, 0x373, 0x3c1, 0x3d5};
    for (size_t i = 0; i < sizeof list / sizeof list[0]; ++i)
        if (index == list[i])
            return 1;
    return 0;
}

int mu_rc_character_light(const mu_rc_light_in *in, float out[3])
{
    float base[3];
    for (int k = 0; k < 3; ++k)
        base[k] = in->scene_state == 5 ? 0.4f : in->terrain_light[k];        /* 0x0136753a */
    for (int k = 0; k < 3; ++k)
        out[k] = base[k] + in->object_light[k];                              /* 0x013675bc */
    if (in->model_type == 0x7dc) {                                           /* 0x0136768a */
        out[0] = out[1] = out[2] = 0.6f;
    } else if (mu_rc_light_glow_class(in->class_index)) {                    /* 0x013676f7 */
        return MU_RC_UNSUPPORTED;
    }
    if (in->is_hero) {                                                       /* 0x013679ce */
        float L[3] = {1.0f, 1.0f, 1.0f};
        static const float tint[4][3] = {{0.9f, 0.5f, 0.5f}, {0.5f, 0.9f, 0.5f}, {0.9f, 0.5f, 0.5f},
                                         {0.9f, 0.5f, 0.5f}};
        for (int b = 0; b < 4; ++b)
            if (in->ability & (1u << b))
                for (int k = 0; k < 3; ++k)
                    L[k] = L[k] * tint[b][k];
        if (in->scene_state == 5) {                                          /* 0x01367c18 */
            for (int k = 0; k < 3; ++k)
                out[k] = 0.5f + in->object_light[k];
        } else {
            for (int k = 0; k < 3; ++k)
                out[k] = L[k];
        }
    }
    return MU_RC_OK;
}
