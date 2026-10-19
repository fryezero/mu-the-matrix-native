#include "ground_items.h"

#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "../record-math/record_math.h"

/* ------------------------------------------------------------------ helpers */

static float mu_gi_f32(uint32_t bits)
{
    float f;
    memcpy(&f, &bits, sizeof f);
    return f;
}

static int code_ok(int32_t code)
{
    return code >= 0 && code <= 0x2c00;     /* the item predicates' range check */
}

static const mu_gi_record *host_record(const mu_gi_host *host, int32_t code)
{
    return host && host->record ? host->record(host->context, code) : NULL;
}

/* 0x0095fc2e / 0x00987982 / 0x0095fbeb on an ITEM: code in range and the record's field equals k. */
static int item_kind_a(const mu_gi_host *host, const mu_gi_item_data *it, int32_t k)
{
    const mu_gi_record *r = code_ok(it->code) ? host_record(host, it->code) : NULL;
    return r && r->present && r->kind_a == (uint8_t)k;
}

static int item_kind_b(const mu_gi_host *host, const mu_gi_item_data *it, int32_t k)
{
    const mu_gi_record *r = code_ok(it->code) ? host_record(host, it->code) : NULL;
    return r && r->present && r->kind_b == (uint8_t)k;
}

static int item_type(const mu_gi_host *host, const mu_gi_item_data *it, int32_t k)
{
    const mu_gi_record *r = code_ok(it->code) ? host_record(host, it->code) : NULL;
    return r && r->present && r->type == (uint8_t)k;
}

/* 0x00cd0995(k): (0) ancient bits & 0x33, (1) +0x98 == 1, (2) +0x92 == 1; code in range. */
static int item_option(const mu_gi_item_data *it, int32_t k)
{
    if (!code_ok(it->code))
        return 0;
    if (k == 0)
        return (it->ancient & 0x33) != 0;
    if (k == 1)
        return it->flag_98 == 1;
    if (k == 2)
        return it->flag_92 == 1;
    return 0;
}

/* ------------------------------------------------------------------ packet 0x20 */

int32_t mu_gi_item_code(const uint8_t *b)
{
    return (int32_t)((uint32_t)b[0] | ((uint32_t)(b[3] & 0x80) << 1) | ((uint32_t)(b[5] & 0xf0) << 5) |
                     ((uint32_t)(b[5] & 1) << 13));
}

int32_t mu_gi_viewport_parse(const uint8_t *packet, mu_gi_viewport_entry *out, int32_t capacity)
{
    int32_t count = packet[4] < MU_GI_VIEWPORT_MAX ? packet[4] : MU_GI_VIEWPORT_MAX;
    int32_t offset = 5, n = 0;
    for (int32_t i = 0; i < count; ++i) {
        const uint8_t *e = packet + offset;
        int32_t key = ((int32_t)e[0] << 8) + e[1];
        int32_t drop = key >> 15;
        key &= 0x7fff;
        if (key >= MU_GI_ITEMS)
            key = 0;
        if (n < capacity) {
            out[n].index = key;
            out[n].drop = drop;
            out[n].x = ((float)e[2] + 0.5f) * 100.0f;
            out[n].y = ((float)e[3] + 0.5f) * 100.0f;
            out[n].item = e + 4;
            ++n;
        }
        offset += MU_GI_ENTRY_BYTES;        /* both branches of the zen test add 0x13 */
    }
    return n;
}

/* ------------------------------------------------------------------ sounds */

static int is_jewel(int32_t code)
{
    return code == 0x1c0d || code == 0x1c0e || code == 0x1c10 || code == 0x180f || code == 0x1c16 ||
           code == 0x1c1f;
}

int32_t mu_gi_drop_sound(int32_t code, int32_t drop)
{
    if (!drop)
        return -1;
    if (code == MU_GI_CODE_ZEN)
        return 0x1f;
    if (is_jewel(code))
        return 0x45;
    if (code == 0x1c29)
        return 0x2d3;
    if (code == 0x1cfe || (code >= 0x1d00 && code <= 0x1d06))
        return 0x5a;
    if (code >= 0x1d09 && code <= 0x1d0c)
        return 0x5a;
    return 0x1e;
}

int32_t mu_gi_pickup_sound(int32_t code)
{
    if (is_jewel(code))
        return 0x45;
    if (code == 0x1c29)
        return 0x2d3;
    return 0x1d;
}

/* ------------------------------------------------------------------ ItemObjectAttribute 0x016da00b */

static float wave(const mu_gi_host *h, float factor, float amplitude, float base)
{
    float s = h->sin(h->context, h->world_time * factor);
    return s * amplitude + base;
}

static float rand_tenth(const mu_gi_host *h, int32_t modulo)
{
    return (float)(h->rand(h->context) % modulo) * 0.1f;
}

void mu_gi_object_attribute(mu_gi_object *o, const mu_gi_host *h)
{
    for (int k = 0; k < 3; ++k)
        o->light[k] = 0.3f;
    o->light_enable = 1;
    o->field_0c = 0;
    o->field_04 = 0;
    o->field_bc = 0.0f;
    o->field_c0 = 50.0f;
    o->prior_frame = 0.0f;
    o->frame = 0.0f;
    o->prior_action = 0;
    o->action = 0;
    o->hidden_mesh = -1;
    o->gravity = 0.0f;
    o->alpha = 1.0f;
    o->blend_mesh = -1;
    o->blend_light = 1.0f;
    o->blend_u = 0.0f;
    o->blend_v = 0.0f;
    o->hidden_mesh = -1;
    o->scale = 0.8f;
    /* 0x01295f18(o + 0x358): sub-object reset, not modelled */
    if (o->type >= 0x10e6 && o->type <= 0x14f3)
        o->scale = 0.7f;
    const float f4 = 0.004f;
    switch (o->type) {
    case 0xa99: case 0xa9a: case 0xa9b: case 0xa9c: case 0xa9d: case 0xa9e: case 0xa9f: case 0xaa0: case 0xaa1:
        o->scale = 1.0f;
        break;
    case 0xaeb: case 0xaf3:
        o->blend_mesh = 1;
        break;
    case 0xaf0: case 0x10e6: case 0xeec: case 0x16f1: case 0x16f2: case 0x16f3: case 0x1702:
        o->blend_mesh = 1;
        o->blend_light = wave(h, f4, 0.3f, 0.7f);
        break;
    case 0xaf4: case 0xb0d:
        o->blend_mesh = 1;
        o->blend_u = rand_tenth(h, 10);
        o->blend_light = wave(h, f4, 0.3f, 0.7f);
        break;
    case 0xb05: case 0xeed: case 0xf0b: case 0x1711: case 0x16f6:
        o->hidden_mesh = 2;
        break;
    case 0xeea:
        o->blend_mesh = 1;
        o->blend_light = wave(h, f4, 0.2f, 0.8f);
        break;
    case 0xeeb:
        o->blend_mesh = 0;
        break;
    case 0x10ef: {
        int32_t t = (int32_t)h->world_time;          /* cvttss2si */
        o->blend_v = -(float)(t % 2000) * 0.0005f;
        break;
    }
    case 0x10f0:
        o->hidden_mesh = 1;
        break;
    case 0x12ec: case 0x12f3: case 0x12f4: case 0x14ec:
        o->blend_mesh = -2;
        o->blend_light = wave(h, f4, 0.3f, 0.7f);
        break;
    case 0x12f6: case 0x14ee: case 0x1516:
        o->blend_mesh = -2;
        o->blend_light = wave(h, f4, 0.2f, 0.9f);
        break;
    case 0x14e6:
        o->blend_mesh = 2;
        break;
    case 0x14eb: case 0x150c: case 0x1513:
        o->blend_mesh = 2;
        o->blend_u = rand_tenth(h, 10);
        o->blend_v = rand_tenth(h, 10);
        break;
    case 0x14ed:
        o->blend_mesh = 1;
        o->blend_light = rand_tenth(h, 11);
        break;
    case 0x14ef: case 0x24e6:
        o->blend_mesh = 1;
        break;
    case 0x14f1:
        o->blend_mesh = 2;
        o->blend_light = wave(h, f4, 0.3f, 0.7f);
        break;
    case 0x16f4: case 0x1701: case 0x170b:
        o->blend_mesh = 1;
        o->blend_u = rand_tenth(h, 10);
        o->blend_v = rand_tenth(h, 10);
        break;
    case 0x18fe: case 0x1cfe:
        o->blend_light = wave(h, 0.001f, 0.4f, 0.6f);
        break;
    case 0x248e: case 0x22e9:
        o->scale = 0.5f;
        o->blend_mesh = 0;
        break;
    case 0x22e6: case 0x236a:
        o->blend_mesh = 0;
        break;
    case 0x26e7:
        o->scale = 1.0f;
        break;
    case 0x26fb:
        o->scale = 0.5f;
        break;
    case 0x28e6:
        o->scale = 0.7f;
        break;
    default:
        break;
    }
}

/* ------------------------------------------------------------------ ItemAngle 0x01802a66 (lifted) */

/* 0x00cd5fac / 0x00cd6017 (index, k): a temporary item of code index; the
 * record's kind A / kind B equals k, with the code range check. */
static int mu_gi_kind_a(const mu_gi_record *r, int32_t index, int32_t k)
{
    return code_ok(index) && r->present && r->kind_a == (uint8_t)k;
}

static int mu_gi_kind_b(const mu_gi_record *r, int32_t index, int32_t k)
{
    return code_ok(index) && r->present && r->kind_b == (uint8_t)k;
}

/* 0x0095c61f(value, low, high): low <= value <= high. */
static int mu_gi_in_range(int32_t value, int32_t low, int32_t high)
{
    if (value < low)
        return 0;
    return value <= high;
}

#include "item_angle_table.h"

int32_t mu_gi_item_angle(mu_gi_object *o, const mu_gi_angle_env *env)
{
    return mu_gi_item_angle_body(o, env);
}

/* ------------------------------------------------------------------ the name builder 0x017ea422 (lifted) */

typedef struct mu_gi_name_arg {
    int is_string;
    const char *s;
    int32_t d;
} mu_gi_name_arg;

#define MU_GI_ARG_S(x) (mu_gi_name_arg){1, (x), 0}
#define MU_GI_ARG_D(x) (mu_gi_name_arg){0, NULL, (x)}

static void sink_log(mu_gi_name_sink *s, int32_t kind, const char *text)
{
    if (!s || s->count >= MU_GI_NAME_LOG)
        return;
    mu_gi_name_call *c = &s->calls[s->count++];
    c->kind = kind;
    snprintf(c->text, sizeof c->text, "%s", text ? text : "");
}

/* The client's sprintf on its own destination: the output is formatted from
 * the arguments as they are when the call starts (a %s of the destination
 * itself reads the old text). Supports the formats the builder uses: %s, %d
 * and literal text (GlobalText strings used as formats). */
static void mu_gi_name_sprintf(mu_gi_name_sink *s, char *dst, const char *fmt, int n, ...)
{
    mu_gi_name_arg args[4];
    char copies[4][MU_GI_NAME_BYTES + 64];
    va_list ap;
    va_start(ap, n);
    for (int i = 0; i < n && i < 4; ++i) {
        args[i] = va_arg(ap, mu_gi_name_arg);
        if (args[i].is_string) {
            snprintf(copies[i], sizeof copies[i], "%s", args[i].s ? args[i].s : "");
            args[i].s = copies[i];
        }
    }
    va_end(ap);
    char out[256];
    size_t w = 0;
    int next = 0;
    for (const char *p = fmt ? fmt : ""; *p && w + 1 < sizeof out; ++p) {
        if (*p == '%' && p[1] == 's' && next < n) {
            for (const char *q = args[next++].s; *q && w + 1 < sizeof out; ++q)
                out[w++] = *q;
            ++p;
        } else if (*p == '%' && p[1] == 'd' && next < n) {
            char num[16];
            snprintf(num, sizeof num, "%d", (int)args[next++].d);
            for (const char *q = num; *q && w + 1 < sizeof out; ++q)
                out[w++] = *q;
            ++p;
        } else if (*p == '%' && p[1] == '%') {
            out[w++] = '%';
            ++p;
        } else {
            out[w++] = *p;
        }
    }
    out[w] = 0;
    /* the destination is the 0x53-byte label field; the client writes past it
     * into +0x55c for longer names (not reproduced: truncated) */
    snprintf(dst, MU_GI_NAME_BYTES, "%s", out);
    sink_log(s, 1, out);
}

static void mu_gi_name_strcat(mu_gi_name_sink *s, char *dst, const char *src)
{
    size_t cap = dst == NULL ? 0 : MU_GI_NAME_BYTES;
    size_t len = strlen(dst);
    snprintf(dst + len, cap > len ? cap - len : 0, "%s", src ? src : "");
    sink_log(s, 2, dst);
}

static void mu_gi_name_strcpy(mu_gi_name_sink *s, char *dst, const char *src)
{
    snprintf(dst, 0x40, "%s", src ? src : "");
    sink_log(s, 3, dst);
}

static void mu_gi_name_strncpy(mu_gi_name_sink *s, char *dst, const char *src, size_t n)
{
    strncpy(dst, src ? src : "", n);
    (void)s;
}

static void mu_gi_name_memset(mu_gi_name_sink *s, char *dst, int value, size_t n)
{
    memset(dst, value, n);
    (void)s;
}

static void mu_gi_name_gl_color(mu_gi_name_sink *s, float r, float g, float b)
{
    if (!s)
        return;
    s->gl_color[0] = r;
    s->gl_color[1] = g;
    s->gl_color[2] = b;
    sink_log(s, 6, "");
}

static void mu_gi_name_label_add(mu_gi_name_sink *s, mu_gi_item *it)
{
    if (!s)
        return;
    s->label_add = 1;
    sink_log(s, 7, it->name);
}

static const mu_gi_record *name_record(const mu_gi_name_env *env, int32_t code)
{
    return env->record ? env->record(env->context, code) : NULL;
}

static const char *mu_gi_record_name(const mu_gi_name_env *env, const mu_gi_item *it)
{
    const mu_gi_record *r = name_record(env, it->data.code);
    return r && r->present && r->name ? r->name : "";
}

static int32_t mu_gi_record_pc_room(const mu_gi_name_env *env, const mu_gi_item *it)
{
    const mu_gi_record *r = name_record(env, it->data.code);
    return r && r->present ? r->pc_room : 0;
}

static int mu_gi_item_kind_a(const mu_gi_name_env *env, const mu_gi_item *it, int32_t k)
{
    const mu_gi_record *r = code_ok(it->data.code) ? name_record(env, it->data.code) : NULL;
    return r && r->present && r->kind_a == (uint8_t)k;
}

static int mu_gi_item_kind_b(const mu_gi_name_env *env, const mu_gi_item *it, int32_t k)
{
    const mu_gi_record *r = code_ok(it->data.code) ? name_record(env, it->data.code) : NULL;
    return r && r->present && r->kind_b == (uint8_t)k;
}

static int mu_gi_item_type(const mu_gi_name_env *env, const mu_gi_item *it, int32_t k)
{
    const mu_gi_record *r = code_ok(it->data.code) ? name_record(env, it->data.code) : NULL;
    return r && r->present && r->type == (uint8_t)k;
}

static int mu_gi_item_option(const mu_gi_name_env *env, const mu_gi_item *it, int32_t k)
{
    (void)env;
    return item_option(&it->data, k);
}

/* 0x00cd2175: type 2 and kind A 2. */
static int mu_gi_item_type2_kind2(const mu_gi_name_env *env, const mu_gi_item *it)
{
    return mu_gi_item_type(env, it, 2) && mu_gi_item_kind_a(env, it, 2);
}

static int mu_gi_script_kind_a(const mu_gi_name_env *env, int32_t index, int32_t k)
{
    const mu_gi_record *r = code_ok(index) ? name_record(env, index) : NULL;
    return r && r->present && r->kind_a == (uint8_t)k;
}

static const char *mu_gi_text(const mu_gi_name_env *env, int32_t id)
{
    const char *t = env->text ? env->text(env->context, id) : NULL;
    return t ? t : "";
}

static const char *mu_gi_name_prefix(const mu_gi_name_env *env, const mu_gi_item *it)
{
    const char *t = env->prefix ? env->prefix(env->context, &it->data) : NULL;
    return t ? t : "";
}

static int32_t mu_gi_set_tier(const mu_gi_name_env *env, int32_t code)
{
    return env->set_tier ? env->set_tier(env->context, code) : 0;
}

static const char *mu_gi_table_1e(const mu_gi_name_env *env, int32_t key)
{
    const char *t = env->table_1e ? env->table_1e(env->context, key) : NULL;
    return t ? t : "";
}

static const char *mu_gi_text_string(const mu_gi_name_env *env, int32_t id)
{
    const char *t = env->text_string ? env->text_string(env->context, id) : NULL;
    return t ? t : "";
}

static int32_t mu_gi_level_key(const mu_gi_name_env *env, int32_t level)
{
    return env->level_key ? env->level_key(env->context, level) : 0;
}

static const char *mu_gi_level_table_text(const mu_gi_name_env *env, int32_t key)
{
    const char *t = env->level_table_text ? env->level_table_text(env->context, key) : NULL;
    return t ? t : "";
}

static int mu_gi_label_window(const mu_gi_name_env *env)
{
    return env->label_window;
}

#include "item_name_table.h"

void mu_gi_name_build(mu_gi_item *it, const mu_gi_name_env *env, mu_gi_name_sink *sink)
{
    mu_gi_name_body(it, env, sink);
}

/* ------------------------------------------------------------------ CreateItem 0x016daa27 */

static void default_reset(void *c, mu_gi_item_data *it)
{
    (void)c;
    /* the ITEM constructor-like reset 0x00ccc144: the fields this library models */
    memset(it, 0, sizeof *it);
    it->code = -1;
}

static void default_live(void *c, mu_gi_object *o, int32_t live)
{
    (void)c;
    o->live = (uint8_t)live;
}

static void default_attribute(void *c, mu_gi_object *o)
{
    mu_gi_object_attribute(o, (const mu_gi_host *)c);
}

static void default_angle(void *c, mu_gi_object *o)
{
    const mu_gi_host *h = c;
    mu_gi_angle_env env;
    memset(&env, 0, sizeof env);
    const mu_gi_record *r = host_record(h, o->type - MU_GI_MODEL_ITEM);
    if (r)
        env.record = *r;
    mu_gi_item_angle(o, &env);
}

void mu_gi_default_hooks(mu_gi_create_hooks *hooks, const mu_gi_host *host)
{
    memset(hooks, 0, sizeof *hooks);
    hooks->context = (void *)host;
    hooks->reset = default_reset;
    hooks->set_live = default_live;
    hooks->object_attribute = default_attribute;
    hooks->item_angle = default_angle;
}

static int32_t box_model(int32_t level_shift)
{
    /* the jump table 0x016db5af on (level >> 3) - 1 for code 0x1c0b; 0 keeps the type */
    switch (level_shift) {
    case 1: return 0x3894;
    case 2: return 0x3895;
    case 3: return 0x3896;
    case 5: return 0x3898;
    case 6: return 0x3899;
    case 8: case 9: case 10: case 11: case 12: return 0x389a;
    case 13: case 14: case 15: return 0x3895;   /* 13 stores 0x3896 then 0x3895 */
    default: return 0;
    }
}

int32_t mu_gi_create(mu_gi_item *rec, const uint8_t b[15], const float position[3], int32_t drop,
                     const mu_gi_host *host, const mu_gi_create_hooks *hooks)
{
    mu_gi_item_data *it = &rec->data;
    mu_gi_object *o = &rec->object;
    int32_t code = mu_gi_item_code(b);
    hooks->reset(hooks->context, it);
    it->code = code;
    const mu_gi_record *attr = host_record(host, it->code);
    if (!attr || !attr->present)
        return MU_GI_CREATE_NO_RECORD;          /* 0x016daa8d: no record, nothing else runs */
    if (code == MU_GI_CODE_ZEN) {
        it->level = (int32_t)(((uint32_t)b[6] << 24) + ((uint32_t)b[1] << 16) + ((uint32_t)b[2] << 8) + b[4]);
        it->durability = 0;
        it->excellent = 0;
        if (drop && host->play_sound)
            host->play_sound(host->context, 0x1f);
    } else {
        it->level = b[1];
        it->durability = b[2];
        it->excellent = (uint8_t)(b[3] & 0x7f);
        it->ancient = b[4];
        it->flag_72 = 0;
        it->flag_72 = (b[5] & 8) ? 1 : 0;
        if (item_kind_a(host, it, 8) || item_kind_a(host, it, 0x19) || item_kind_a(host, it, 0x1a)) {
            it->element = b[6] & 0xf;
            o->field_14 = it->element;
            if (o->field_14 > -1 && o->field_14 < 6 && hooks->pentagram) {
                int32_t f18 = o->field_18, f1c = o->field_1c;
                if (hooks->pentagram(hooks->context, it, &f18, &f1c)) {
                    o->field_18 = f18;
                    o->field_1c = f1c;
                }
            }
            if (item_kind_b(host, it, 0x2b))
                for (int i = 0; i < 5; ++i)
                    it->sockets[i] = b[7 + i];
        }
        if (item_type(host, it, 2))
            for (int i = 0; i < 5; ++i)
                it->sockets[i] = b[7 + i];
        if (host->socket_like && host->socket_like(host->context, it)) {   /* 0x00cd1534 (runtime-patched) */
            if (b[3] & 0x3f)
                it->flag_98 = 1;
            if (!(item_type(host, it, 2) && item_kind_a(host, it, 2)))     /* 0x00cd2175 */
                for (int i = 0; i < 3; ++i)
                    if (b[7 + i] != 0xff) {
                        it->flag_98 = 1;
                        break;
                    }
        }
        if (drop && host->play_sound)
            host->play_sound(host->context, mu_gi_drop_sound(code, drop));
    }
    hooks->set_live(hooks->context, o, 1);
    o->type = code + MU_GI_MODEL_ITEM;
    o->sparkle = 1;
    int32_t level_shift = it->level >> 3;
    if (code == 0x1c0b) {
        int32_t m = box_model(level_shift);
        if (m)
            o->type = m;
    }
    if (code >= 0x1c2e && code <= 0x1c30)
        o->type = code + MU_GI_MODEL_ITEM;
    if (code >= 0x1c20 && code <= 0x1c22) {
        if (level_shift == 1)
            o->type = code - 0x1c20 + 0x38a5;
    } else if (code == 0x1c15) {
        if (level_shift == 1 || level_shift == 2)
            o->type = 0x389b;
    } else if (code == 0x1a13) {
        if (level_shift == 0) {
            o->type = 0x14f0;
            it->level = 0;
        } else if (level_shift == 1) {
            o->type = 0xaf9;
            it->level = 0;
        } else if (level_shift == 2) {
            o->type = 0x12f8;
            it->level = 0;
        }
    } else if (code == 0x1c17) {
        if (level_shift == 1)
            o->type = 0x389c;
    } else if (code == 0x1c18) {
        if (level_shift == 1)
            o->type = 0x389d;
    } else if (code == 0x1a14) {
        if (level_shift == 0)
            o->type = 0x389f;
        else if (level_shift >= 1 && level_shift <= 3)
            o->type = 0x389e;
    } else if (code == 0x1c09) {
        if (level_shift == 1)
            o->type = 0x3897;
    } else if (code == 0x1a0e && level_shift == 1) {
        o->type = 0x38a0;
    } else if (code == 0x1a0b && level_shift == 1) {
        o->type = 0x38a2;
    } else if (code == 0x1c29) {
        o->type = 0x270f;
    } else if (code == 0x1c2a) {
        o->type = 0x2710;
    } else if (code == 0x1c2b) {
        o->type = 0x2711;
    } else if (code == 0x1c2c) {
        o->type = 0x2712;
    }
    hooks->object_attribute(hooks->context, o);
    for (int k = 0; k < 3; ++k) {
        o->bbox_min[k] = -30.0f;
        o->bbox_max[k] = 30.0f;
    }
    for (int k = 0; k < 3; ++k)
        o->position[k] = position[k];
    if (drop) {
        if (o->type == 0x3898 || o->type == 0x3899) {
            float p[3] = {position[0], position[1], 0.0f};
            p[2] = host->terrain_height(host->context, position[0], position[1]) + 3.0f;
            if (hooks->create_effect) {
                hooks->create_effect(hooks->context, 0x467, p, o, 0x37);
                hooks->create_effect(hooks->context, 0x465, p, o, 0x37);
            }
            o->position[2] = host->terrain_height(host->context, o->position[0], o->position[1]) + 3.0f;
            o->gravity = 50.0f;
        } else {
            o->position[2] = host->terrain_height(host->context, o->position[0], o->position[1]) + 180.0f;
            o->gravity = 20.0f;
        }
    } else {
        o->position[2] = host->terrain_height(host->context, o->position[0], o->position[1]);
    }
    hooks->item_angle(hooks->context, o);
    if (hooks->name_build)
        hooks->name_build(hooks->context, rec);
    return MU_GI_CREATE_OK;
}

/* ------------------------------------------------------------------ MoveItems 0x017ea1aa */

int32_t mu_gi_move_item(mu_gi_object *o, const mu_gi_host *host, const mu_gi_move_hooks *hooks)
{
    if (!o->live)
        return -1;
    int32_t landed = 0;
    o->position[2] = o->position[2] + o->gravity;
    o->gravity = o->gravity - 6.0f;
    float floor = host->terrain_height(host->context, o->position[0], o->position[1]) + 30.0f;
    if (o->type >= 0xae6 && o->type < 0x16e6)
        floor = floor + 40.0f;
    if (!(floor < o->position[2]) && !(floor != floor) && !(o->position[2] != o->position[2])) {
        o->position[2] = floor;
        if (hooks && hooks->item_angle)
            hooks->item_angle(hooks->context, o);
        landed = 1;
    } else if (o->type >= 0x16e6 && o->type < 0x18e6) {
        o->angle[1] = -o->gravity * 10.0f;
    } else {
        o->angle[0] = -o->gravity * 10.0f;
    }
    /* 0x017f7290: the sparkle */
    int32_t phase = o->sparkle % 48;
    o->sparkle = o->sparkle + 1;
    if (phase == 0) {
        float m[3][4];
        mu_angle_matrix(o->angle, m);
        float v[3];
        v[0] = (float)(host->rand(host->context) % 32 + 16);
        v[1] = 0.0f;
        v[2] = (float)(host->rand(host->context) % 32 + 16);
        float r[3];
        mu_vector_rotate(v, m, r);
        float p[3];
        for (int k = 0; k < 3; ++k)
            p[k] = o->position[k] + r[k];
        static const float white[3] = {1.0f, 1.0f, 1.0f};
        if (hooks && hooks->create_particle) {
            hooks->create_particle(hooks->context, 0x7f66, p, o->angle, white, 0, 1.0f);
            hooks->create_particle(hooks->context, 0x7f66, p, o->angle, white, 1, 1.0f);
        }
    }
    return landed;
}

/* ------------------------------------------------------------------ RenderItems 0x017e9495 */

int32_t mu_gi_zen_coins(int32_t amount, const mu_gi_host *host)
{
    float root = host->sqrt(host->context, (float)amount);
    int32_t n = (int32_t)root / 2;
    if (n < 3)
        n = 3;
    if (n > 80)
        n = 80;
    return n;
}

static int is_white_light_type(int32_t t)
{
    static const int32_t list[] = {0x230e, 0x23ec, 0x23fd, 0x23f3, 0x23f4, 0x2493, 0x249b, 0x2498, 0x23fc, 0x2402,
                                   0x2488, 0x24a0, 0x248b, 0x24a3, 0x2380, 0x2381, 0x2382, 0x2383, 0x2384, 0x2385,
                                   0x2386, 0x2387, 0x2392, 0x2393, 0x2394, 0x2395, 0x2396, 0x2397, 0x2398, 0x2399,
                                   0x239e, 0x23a0, 0x23a1, 0x23a5, 0x23a7, 0x34e6, 0x34e7, 0x34e8, 0x34e9, 0x34ea,
                                   0x34eb};
    if (t == 0x2318 || t == 0x249a)
        return 1;
    for (size_t i = 0; i < sizeof list / sizeof list[0]; ++i)
        if (list[i] == t)
            return 1;
    return 0;
}

static void push_call(mu_gi_render_plan_t *plan, const mu_gi_item *it, const mu_gi_object *o,
                      const float position[3], const float light[3], int32_t a12, int32_t a13)
{
    if (plan->call_count >= MU_GI_RENDER_CALLS)
        return;
    mu_gi_render_call *c = &plan->calls[plan->call_count++];
    c->type = o->type;
    for (int k = 0; k < 3; ++k) {
        c->position[k] = position[k];
        c->light[k] = light[k];
    }
    c->alpha = o->alpha;
    c->item_level = it->data.level;
    c->option = it->data.excellent != 0;
    c->ext = it->data.ancient;
    c->a12 = a12;
    c->a13 = a13;
}

void mu_gi_render_plan(const mu_gi_item *it, int32_t index, const mu_gi_host *host, const mu_gi_render_env *env,
                       mu_gi_render_plan_t *plan)
{
    const mu_gi_object *o = &it->object;
    memset(plan, 0, sizeof *plan);
    plan->visible = env->visible;
    if (!o->live || !env->visible)
        return;
    int32_t pose = o->type;
    if (o->type >= 0x18e6 && o->type < 0x22e6) {
        pose = 0xa91;                            /* armour parts animate on the Player skeleton */
    } else if (o->type == 0x26f2) {
        int32_t v = (it->data.level >> 3) & 0xf;
        if (v == 0)
            pose = 0x3890;
        else if (v == 2)
            pose = 0x3891;
    }
    plan->pose_model = pose;
    if (!env->pose_model_exists) {
        plan->abort = 1;
        return;
    }
    if (o->type >= 0x18e6 && o->type < 0x1ae6)
        plan->pose_head_offset = -160.0f;
    else if (o->type >= 0x1ae6 && o->type < 0x1ce6)
        plan->pose_head_offset = -100.0f;
    else if (o->type >= 0x1ee6 && o->type < 0x20e6)
        plan->pose_head_offset = -70.0f;
    else if (o->type >= 0x1ce6 && o->type < 0x1ee6)
        plan->pose_head_offset = -50.0f;
    else
        plan->pose_head_offset = 0.0f;
    int32_t render = pose;
    if (o->type >= 0x18e6 && o->type < 0x22e6)
        render = o->type;
    plan->render_model = render;
    if (!env->render_model_exists) {
        plan->abort = 1;
        return;
    }
    float light[3];
    host->terrain_light(host->context, o->position[0], o->position[1], light);
    for (int k = 0; k < 3; ++k)
        light[k] = light[k] + o->light[k];
    mu_gi_object work = *o;
    if (o->type == 0x26f5) {
        float saved[3] = {o->position[0], o->position[1], o->position[2]};
        int32_t count = mu_gi_zen_coins(it->data.level, host);
        for (int32_t j = 1; j < count; ++j) {
            float angle[3] = {0.0f, 0.0f, 0.0f};
            angle[2] = (float)(env->random_table[(index * 20 + j) % 100] % 360);
            float p[3] = {0.0f, 0.0f, 0.0f};
            p[0] = (float)(env->random_table[(index + j) % 100] % (count + 20));
            float m[3][4], r[3];
            mu_angle_matrix(angle, m);
            mu_vector_rotate(p, m, r);
            for (int k = 0; k < 3; ++k)
                work.position[k] = saved[k] + r[k];
            push_call(plan, it, &work, work.position, light, -1, -1);
        }
        for (int k = 0; k < 3; ++k)
            work.position[k] = saved[k];
    } else if (is_white_light_type(o->type)) {
        light[0] = light[1] = light[2] = 1.0f;
    }
    float saved[3] = {work.position[0], work.position[1], work.position[2]};
    if (host->world == 10 || host->world == 0x84 || (host->world == 0x27 && env->world_39_state)) {
        float s = host->sin(host->context, ((float)(index * 1237) + host->world_time) * 0.002f);
        work.position[2] = s * 10.0f + work.position[2];
    } else if (env->world_float) {
        work.position[2] = env->special_height + 180.0f;
    }
    if (env->kind_option)
        push_call(plan, it, &work, work.position, light, o->field_18, o->field_1c);
    else
        push_call(plan, it, &work, work.position, light, -1, -1);
    for (int k = 0; k < 3; ++k)
        work.position[k] = saved[k];
    float top[3] = {work.position[0], work.position[1], work.position[2] + 30.0f};
    int32_t sx = 0, sy = 0;
    if (env->project)
        env->project(env->context, top, &sx, &sy);
    plan->screen_x = (int16_t)sx;
    plan->screen_y = (int16_t)sy;
}

/* ------------------------------------------------------------------ TestFrustrum 0x016ccc14 */

int32_t mu_gi_test_frustum(const float normal[5][3], const float distance[5], const float position[3], float range)
{
    for (int i = 0; i < 5; ++i) {
        volatile float d = position[0] * normal[i][0];
        volatile float t = position[1] * normal[i][1];
        d = d + t;
        t = position[2] * normal[i][2];
        d = d + t;
        d = d + distance[i];
        if (-range > d)
            return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------ SelectItem 0x016b4fc0 */

int32_t mu_gi_select(mu_gi_item *items, int32_t count, mu_gi_ray_test hit, void *context)
{
    for (int32_t i = 0; i < count; ++i) {
        mu_gi_object *o = &items[i].object;
        if (o->live && o->visible) {
            o->light_enable = 1;
            o->light[0] = o->light[1] = o->light[2] = 0.2f;
        }
    }
    for (int32_t i = 0; i < count; ++i) {
        mu_gi_object *o = &items[i].object;
        if (o->live && o->visible && hit(context, i)) {
            o->light_enable = 0;
            o->light[0] = o->light[1] = o->light[2] = 1.5f;
            return i;
        }
    }
    return -1;
}

/* ------------------------------------------------------------------ labels */

const char *mu_gi_label_color(int32_t c)
{
    /* the jump table 0x00c84fd4 over classes 0..0x15; others white */
    static const char *const table[22] = {
        "#FFFFFF", "#7FB2FF", "#FF3319", "#FFCC19", "#19FF7F", "#A00000", "#FF19FF", "#0000A0",
        "#A06600", "#00FF00", "#B2B2B2", "#CC7FCC", "#B266FF", "#E56B0A", "#800080", "#FFFF00",
        "#00B0F0", "#00B050", "#CCFF00", "#00FFFF", "#BCBCBC", "#C1C469"};
    if (c < 0 || c > 0x15)
        return "#FFFFFF";
    return table[c];
}

void mu_gi_label_anchor(const mu_gi_item *it, int32_t index, const mu_gi_label_env *env, float *x, float *y)
{
    if (index == env->selected) {
        *x = (float)env->mouse_x * env->scale_x;
        *y = (float)(env->mouse_y - MU_GI_LABEL_MOUSE_DY) * env->scale_y;
        return;
    }
    float p[3] = {it->object.position[0], it->object.position[1],
                  (float)MU_GI_LABEL_HEIGHT + it->object.position[2]};
    env->project(env->context, p, x, y);
}

void mu_gi_label_layout(float text_width, float text_height, mu_gi_label_box *b)
{
    b->text_w = text_width + 6.0f;
    b->text_h = text_height + 4.0f;
    b->text_x = -floorf(b->text_w / 2.0f);
    b->text_y = -floorf(b->text_h + 14.0f);
    b->bg_x = b->text_x - 3.0f;
    b->bg_y = b->text_y - 2.0f;
    b->bg_w = b->text_w + 6.0f;
    b->bg_h = b->text_h + 4.0f;
}
