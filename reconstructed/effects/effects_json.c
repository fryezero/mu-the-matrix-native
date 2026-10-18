/* .ein loader: a small JSON reader with the value conversions of the client's
 * JsonCpp-style reader (0x0093f7e8 parse, 0x0093e3aa member lookup,
 * 0x0093d773 asFloat, 0x0093d1ed asInt, 0x0093d361 asUInt, 0x0093d917 asBool)
 * and the effect load routines (base 0x00a760b2, particle system 0x00a88fda,
 * billboard 0x00a6f3e1 and the component loaders). Missing keys read as null:
 * 0, false, empty arrays. Real numbers are decoded with strtod, as the client's
 * decodeDouble decodes them with sscanf("%lf"). */
#include "effects.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { J_NULL, J_BOOL, J_INT, J_UINT, J_REAL, J_STRING, J_ARRAY, J_OBJECT };

typedef struct jvalue jvalue;
typedef struct jmember { char *key; jvalue *value; } jmember;
struct jvalue {
    int type;
    int boolean;
    int64_t integer;
    uint64_t uinteger;
    double real;
    char *string;
    jvalue **items;
    jmember *members;
    size_t count, capacity;
};

typedef struct jparser {
    const char *p, *end;
    int failed;
} jparser;

static const jvalue NULL_VALUE = {J_NULL, 0, 0, 0, 0.0, NULL, NULL, NULL, 0, 0};

static void jfree(jvalue *v)
{
    if (!v)
        return;
    free(v->string);
    for (size_t i = 0; v->type == J_ARRAY && i < v->count; ++i)
        jfree(v->items[i]);
    for (size_t i = 0; v->type == J_OBJECT && i < v->count; ++i) {
        free(v->members[i].key);
        jfree(v->members[i].value);
    }
    free(v->items);
    free(v->members);
    free(v);
}

static void skip_space(jparser *j)
{
    for (;;) {
        while (j->p < j->end && (*j->p == ' ' || *j->p == '\t' || *j->p == '\r' || *j->p == '\n'))
            j->p++;
        if (j->p + 1 < j->end && j->p[0] == '/' && j->p[1] == '/') {
            while (j->p < j->end && *j->p != '\n')
                j->p++;
            continue;
        }
        if (j->p + 1 < j->end && j->p[0] == '/' && j->p[1] == '*') {
            j->p += 2;
            while (j->p + 1 < j->end && !(j->p[0] == '*' && j->p[1] == '/'))
                j->p++;
            j->p = j->p + 1 < j->end ? j->p + 2 : j->end;
            continue;
        }
        return;
    }
}

static jvalue *jnew(int type)
{
    jvalue *v = calloc(1, sizeof *v);
    if (v)
        v->type = type;
    return v;
}

static char *parse_string_raw(jparser *j)
{
    if (j->p >= j->end || *j->p != '"') {
        j->failed = 1;
        return NULL;
    }
    j->p++;
    size_t cap = 32, n = 0;
    char *out = malloc(cap);
    if (!out) {
        j->failed = 1;
        return NULL;
    }
    while (j->p < j->end && *j->p != '"') {
        char c = *j->p++;
        if (c == '\\' && j->p < j->end) {
            char e = *j->p++;
            switch (e) {
            case 'b': c = '\b'; break;
            case 'f': c = '\f'; break;
            case 'n': c = '\n'; break;
            case 'r': c = '\r'; break;
            case 't': c = '\t'; break;
            case 'u': {
                unsigned code = 0;
                for (int k = 0; k < 4 && j->p < j->end; ++k) {
                    char h = *j->p++;
                    code <<= 4;
                    if (h >= '0' && h <= '9') code |= (unsigned)(h - '0');
                    else if (h >= 'a' && h <= 'f') code |= (unsigned)(h - 'a' + 10);
                    else if (h >= 'A' && h <= 'F') code |= (unsigned)(h - 'A' + 10);
                }
                c = code < 0x80 ? (char)code : '?';
                break;
            }
            default: c = e; break;
            }
        }
        if (n + 2 > cap) {
            cap *= 2;
            char *grown = realloc(out, cap);
            if (!grown) {
                free(out);
                j->failed = 1;
                return NULL;
            }
            out = grown;
        }
        out[n++] = c;
    }
    out[n] = 0;
    if (j->p >= j->end) {
        free(out);
        j->failed = 1;
        return NULL;
    }
    j->p++;
    return out;
}

static jvalue *parse_value(jparser *j, int depth);

static jvalue *parse_number(jparser *j)
{
    const char *start = j->p;
    while (j->p < j->end && strchr("0123456789+-.eE", *j->p))
        j->p++;
    size_t n = (size_t)(j->p - start);
    char buffer[64];
    if (n == 0 || n >= sizeof buffer) {
        j->failed = 1;
        return NULL;
    }
    memcpy(buffer, start, n);
    buffer[n] = 0;
    int is_double = 0;
    for (size_t i = 0; i < n; ++i)
        if (buffer[i] == '.' || buffer[i] == 'e' || buffer[i] == 'E' || buffer[i] == '+' ||
            (buffer[i] == '-' && i != 0))
            is_double = 1;
    if (!is_double) {
        int negative = buffer[0] == '-';
        uint64_t limit = negative ? (uint64_t)INT64_MAX + 1u : UINT64_MAX;
        uint64_t value = 0;
        int overflow = 0;
        for (size_t i = negative ? 1 : 0; i < n; ++i) {
            unsigned digit = (unsigned)(buffer[i] - '0');
            if (digit > 9) {
                j->failed = 1;
                return NULL;
            }
            if (value > (limit - digit) / 10u) {
                overflow = 1;
                break;
            }
            value = value * 10u + digit;
        }
        if (!overflow) {
            jvalue *v = jnew(negative ? J_INT : (value <= (uint64_t)INT64_MAX ? J_INT : J_UINT));
            if (!v)
                return NULL;
            if (negative)
                v->integer = value == (uint64_t)INT64_MAX + 1u ? INT64_MIN : -(int64_t)value;
            else if (v->type == J_INT)
                v->integer = (int64_t)value;
            else
                v->uinteger = value;
            return v;
        }
    }
    char *stop = NULL;
    double d = strtod(buffer, &stop);
    if (stop == buffer) {
        j->failed = 1;
        return NULL;
    }
    jvalue *v = jnew(J_REAL);
    if (v)
        v->real = d;
    return v;
}

static jvalue *parse_value(jparser *j, int depth)
{
    if (depth > 64) {
        j->failed = 1;
        return NULL;
    }
    skip_space(j);
    if (j->p >= j->end) {
        j->failed = 1;
        return NULL;
    }
    char c = *j->p;
    if (c == '{') {
        j->p++;
        jvalue *v = jnew(J_OBJECT);
        if (!v)
            return NULL;
        skip_space(j);
        if (j->p < j->end && *j->p == '}') {
            j->p++;
            return v;
        }
        for (;;) {
            skip_space(j);
            char *key = parse_string_raw(j);
            if (!key)
                break;
            skip_space(j);
            if (j->p >= j->end || *j->p != ':') {
                free(key);
                j->failed = 1;
                break;
            }
            j->p++;
            jvalue *item = parse_value(j, depth + 1);
            if (!item) {
                free(key);
                break;
            }
            if (v->count == v->capacity) {
                size_t cap = v->capacity ? v->capacity * 2 : 8;
                jmember *grown = realloc(v->members, cap * sizeof *grown);
                if (!grown) {
                    free(key);
                    jfree(item);
                    j->failed = 1;
                    break;
                }
                v->members = grown;
                v->capacity = cap;
            }
            v->members[v->count].key = key;
            v->members[v->count].value = item;
            v->count++;
            skip_space(j);
            if (j->p < j->end && *j->p == ',') {
                j->p++;
                continue;
            }
            if (j->p < j->end && *j->p == '}') {
                j->p++;
                return v;
            }
            j->failed = 1;
            break;
        }
        jfree(v);
        return NULL;
    }
    if (c == '[') {
        j->p++;
        jvalue *v = jnew(J_ARRAY);
        if (!v)
            return NULL;
        skip_space(j);
        if (j->p < j->end && *j->p == ']') {
            j->p++;
            return v;
        }
        for (;;) {
            jvalue *item = parse_value(j, depth + 1);
            if (!item)
                break;
            if (v->count == v->capacity) {
                size_t cap = v->capacity ? v->capacity * 2 : 8;
                jvalue **grown = realloc(v->items, cap * sizeof *grown);
                if (!grown) {
                    jfree(item);
                    j->failed = 1;
                    break;
                }
                v->items = grown;
                v->capacity = cap;
            }
            v->items[v->count++] = item;
            skip_space(j);
            if (j->p < j->end && *j->p == ',') {
                j->p++;
                continue;
            }
            if (j->p < j->end && *j->p == ']') {
                j->p++;
                return v;
            }
            j->failed = 1;
            break;
        }
        jfree(v);
        return NULL;
    }
    if (c == '"') {
        jvalue *v = jnew(J_STRING);
        if (!v)
            return NULL;
        v->string = parse_string_raw(j);
        if (!v->string) {
            jfree(v);
            return NULL;
        }
        return v;
    }
    if ((size_t)(j->end - j->p) >= 4 && !strncmp(j->p, "true", 4)) {
        j->p += 4;
        jvalue *v = jnew(J_BOOL);
        if (v)
            v->boolean = 1;
        return v;
    }
    if ((size_t)(j->end - j->p) >= 5 && !strncmp(j->p, "false", 5)) {
        j->p += 5;
        return jnew(J_BOOL);
    }
    if ((size_t)(j->end - j->p) >= 4 && !strncmp(j->p, "null", 4)) {
        j->p += 4;
        return jnew(J_NULL);
    }
    return parse_number(j);
}

/* ---- conversions ---- */

static const jvalue *member(const jvalue *v, const char *key)
{
    if (!v || v->type != J_OBJECT)
        return &NULL_VALUE;
    const jvalue *found = &NULL_VALUE;
    for (size_t i = 0; i < v->count; ++i)
        if (!strcmp(v->members[i].key, key))
            found = v->members[i].value;   /* map semantics: the last duplicate wins */
    return found;
}

static const jvalue *item(const jvalue *v, size_t index)
{
    if (!v || v->type != J_ARRAY || index >= v->count)
        return &NULL_VALUE;
    return v->items[index];
}

static size_t jsize(const jvalue *v)
{
    return v && (v->type == J_ARRAY || v->type == J_OBJECT) ? v->count : 0;
}

static float as_float(const jvalue *v)
{
    switch (v->type) {
    case J_INT: return (float)v->integer;
    case J_UINT: return (float)v->uinteger;
    case J_REAL: return (float)v->real;
    case J_BOOL: return v->boolean ? 1.0f : 0.0f;
    default: return 0.0f;
    }
}

static int32_t as_int(const jvalue *v)
{
    switch (v->type) {
    case J_INT: return (int32_t)v->integer;
    case J_UINT: return (int32_t)v->uinteger;
    case J_REAL: return (int32_t)v->real;
    case J_BOOL: return v->boolean;
    default: return 0;
    }
}

static uint32_t as_uint(const jvalue *v)
{
    switch (v->type) {
    case J_INT: return (uint32_t)v->integer;
    case J_UINT: return (uint32_t)v->uinteger;
    case J_REAL: return (uint32_t)v->real;
    case J_BOOL: return (uint32_t)v->boolean;
    default: return 0;
    }
}

static uint8_t as_bool(const jvalue *v)
{
    switch (v->type) {
    case J_BOOL: return (uint8_t)v->boolean;
    case J_INT: return v->integer != 0;
    case J_UINT: return v->uinteger != 0;
    case J_REAL: return v->real != 0.0;
    default: return 0;
    }
}

static float array_float(const jvalue *v, const char *key, size_t index)
{
    return as_float(item(member(v, key), index));
}

/* ---- keyed data (0x00ce9d70 curves, 0x00ce8c54 / 0x00ce8e91 gradients) ---- */

static int load_curve(mu_fx_curve *c, const jvalue *v)
{
    free(c->keys);
    c->keys = NULL;
    c->count = 0;
    size_t n = jsize(v);
    if (v->type != J_ARRAY || n == 0)
        return 1;
    c->keys = calloc(n, sizeof *c->keys);
    if (!c->keys)
        return 0;
    for (size_t i = 0; i < n; ++i) {
        const jvalue *k = item(v, i);
        c->keys[i].time = as_float(member(k, "Time"));
        c->keys[i].value = as_float(member(k, "Value"));
        c->keys[i].tangent = as_float(member(k, "Tangent"));
    }
    c->count = (uint32_t)n;
    return 1;
}

static int load_grad1(mu_fx_grad1 *g, const jvalue *v)
{
    free(g->keys);
    g->keys = NULL;
    g->count = 0;
    size_t n = jsize(v);
    if (v->type != J_ARRAY || n == 0)
        return 1;
    g->keys = calloc(n, sizeof *g->keys);
    if (!g->keys)
        return 0;
    for (size_t i = 0; i < n; ++i) {
        const jvalue *k = item(v, i);
        g->keys[i].time = as_float(member(k, "Time"));
        g->keys[i].value = as_float(member(k, "Value"));
    }
    g->count = (uint32_t)n;
    return 1;
}

static int load_grad3(mu_fx_grad3 *g, const jvalue *v)
{
    free(g->keys);
    g->keys = NULL;
    g->count = 0;
    size_t n = jsize(v);
    if (v->type != J_ARRAY || n == 0)
        return 1;
    g->keys = calloc(n, sizeof *g->keys);
    if (!g->keys)
        return 0;
    for (size_t i = 0; i < n; ++i) {
        const jvalue *k = item(v, i);
        g->keys[i].time = as_float(member(k, "Time"));
        for (size_t c = 0; c < 3; ++c)
            g->keys[i].rgb[c] = array_float(k, "Value", c);
    }
    g->count = (uint32_t)n;
    return 1;
}

/* ---- components ---- */

static void free_curve(mu_fx_curve *c) { free(c->keys); c->keys = NULL; c->count = 0; }
static void free_grad1(mu_fx_grad1 *g) { free(g->keys); g->keys = NULL; g->count = 0; }
static void free_grad3(mu_fx_grad3 *g) { free(g->keys); g->keys = NULL; g->count = 0; }

/* Each component is created anew (slot[Type] = new component) before its load. */
static void clear_start_color(mu_fx_start_color *c)
{
    free_grad3(&c->color);
    free_grad1(&c->alpha);
    free_grad1(&c->brightness);
    memset(c, 0, sizeof *c);
}
static void clear_range(mu_fx_range *r) { free_curve(&r->curve); memset(r, 0, sizeof *r); }
static void clear_emitter(mu_fx_emitter *m)
{
    free_curve(&m->count_curve);
    free(m->bursts);
    clear_start_color(&m->color);
    clear_range(&m->lifetime);
    clear_range(&m->rotation);
    clear_range(&m->size);
    clear_range(&m->speed);
    memset(m, 0, sizeof *m);
}
static void clear_color_lifetime(mu_fx_color_lifetime *c)
{
    free_grad3(&c->color);
    free_grad1(&c->alpha);
    memset(c, 0, sizeof *c);
}
static void clear_force(mu_fx_force_lifetime *f)
{
    for (int k = 0; k < 3; ++k)
        free_curve(&f->curve[k]);
    memset(f, 0, sizeof *f);
}
static void clear_rotation(mu_fx_rotation_lifetime *r) { free_curve(&r->curve); memset(r, 0, sizeof *r); }
static void clear_curve_component(mu_fx_curve_component *c) { free_curve(&c->curve); memset(c, 0, sizeof *c); }
static void clear_texcoord(mu_fx_texcoord_animation *t) { free_curve(&t->tiles); memset(t, 0, sizeof *t); }

static int load_shape(mu_fx_shape *s, const jvalue *v)
{
    s->present = 1;
    s->shape = as_int(member(v, "Shape"));
    switch (s->shape) {
    case MU_FX_SHAPE_BOX:
        for (size_t k = 0; k < 3; ++k)
            s->size[k] = array_float(v, "Size", k);
        break;
    case MU_FX_SHAPE_CONE:
        s->tangent = as_float(member(v, "Tangent"));
        s->radius = as_float(member(v, "Radius"));
        s->height = as_float(member(v, "Height"));
        s->cylinder = as_bool(member(v, "Cylinder"));
        break;
    case MU_FX_SHAPE_HEMISPHERE:
    case MU_FX_SHAPE_SPHERE:
        s->radius = as_float(member(v, "Radius"));
        break;
    default:
        break;
    }
    if (s->shape != MU_FX_SHAPE_POINT) {
        s->emit_from_shell = as_bool(member(v, "EmitFromShell"));
        s->random_direction = as_bool(member(v, "RandomDirection"));
    }
    return 1;
}

static int load_range(mu_fx_range *r, const jvalue *v, int curve)
{
    r->present = 1;
    r->min = as_float(member(v, "Min"));
    r->max = as_float(member(v, "Max"));
    return curve ? load_curve(&r->curve, member(v, "Curve")) : 1;
}

static int load_emitter(mu_fx_emitter *m, const jvalue *v)
{
    m->present = 1;
    m->delay = as_float(member(v, "Delay"));
    m->delay_left = m->delay;
    m->frequency = as_uint(member(v, "Frequency"));
    m->min_count = (int32_t)as_uint(member(v, "MinEmissionCount"));
    m->max_count = (int32_t)as_uint(member(v, "MaxEmissionCount"));
    if (!load_curve(&m->count_curve, member(v, "CurveEmissionCount")))
        return 0;
    free(m->bursts);
    m->bursts = NULL;
    m->burst_count = 0;
    const jvalue *bursts = member(v, "Bursts");
    size_t nb = jsize(bursts);
    if (nb && bursts->type == J_ARRAY) {
        m->bursts = calloc(nb, sizeof *m->bursts);
        if (!m->bursts)
            return 0;
        for (size_t i = 0; i < nb; ++i) {
            m->bursts[i].time = as_float(member(item(bursts, i), "Time"));
            m->bursts[i].count = (int32_t)as_uint(member(item(bursts, i), "Count"));
        }
        m->burst_count = (uint32_t)nb;
    }
    const jvalue *components = member(v, "Components");
    for (size_t i = 0; i < jsize(components); ++i) {
        const jvalue *c = item(components, i);
        int ok = 1;
        switch (as_int(member(c, "Type"))) {
        case 0: memset(&m->shape, 0, sizeof m->shape); ok = load_shape(&m->shape, c); break;
        case 1:
            clear_start_color(&m->color);
            m->color.present = 1;
            for (size_t k = 0; k < 4; ++k) {
                m->color.min_color[k] = array_float(c, "MinColor", k);
                m->color.max_color[k] = array_float(c, "MaxColor", k);
            }
            ok = load_grad3(&m->color.color, member(c, "ColorGradation")) &&
                 load_grad1(&m->color.alpha, member(c, "AlphaGradation"));
            m->color.min_brightness = as_float(member(c, "MinBrightness"));
            m->color.max_brightness = as_float(member(c, "MaxBrightness"));
            ok = ok && load_grad1(&m->color.brightness, member(c, "BrightnessGradation"));
            break;
        case 2: clear_range(&m->lifetime); ok = load_range(&m->lifetime, c, 1); break;
        case 3: clear_range(&m->rotation); ok = load_range(&m->rotation, c, 0); break;
        case 4: clear_range(&m->size); ok = load_range(&m->size, c, 1); break;
        case 5: clear_range(&m->speed); ok = load_range(&m->speed, c, 1); break;
        default: break;
        }
        if (!ok)
            return 0;
    }
    return 1;
}

static int load_force(mu_fx_force_lifetime *f, const jvalue *v)
{
    f->present = 1;
    for (size_t k = 0; k < 3; ++k)
        f->constant[k] = array_float(v, "Constant", k);
    return load_curve(&f->curve[0], member(v, "CurveX")) && load_curve(&f->curve[1], member(v, "CurveY")) &&
           load_curve(&f->curve[2], member(v, "CurveZ"));
}

static int load_particle_system(mu_fx_effect *e, const jvalue *root)
{
    e->space_is_local = as_bool(member(root, "SpaceIsLocal"));
    e->looping = as_bool(member(root, "Looping"));
    e->duration = as_float(member(root, "Duration"));
    uint32_t capacity = as_uint(member(root, "MaxParticle"));
    free(e->particles);
    e->particles = capacity ? calloc(capacity, sizeof *e->particles) : NULL;
    if (capacity && !e->particles)
        return 0;
    e->capacity = capacity;
    e->blending = as_int(member(root, "Blending"));
    e->billboarding = as_int(member(root, "Billboarding"));
    e->length_scale = as_float(member(root, "LengthScale"));
    e->speed_scale = as_float(member(root, "SpeedScale"));
    const jvalue *components = member(root, "Components");
    for (size_t i = 0; i < jsize(components); ++i) {
        const jvalue *c = item(components, i);
        int ok = 1;
        switch (as_int(member(c, "Type"))) {
        case 0: clear_emitter(&e->emitter); ok = load_emitter(&e->emitter, c); break;
        case 1:
            clear_color_lifetime(&e->color_lifetime);
            e->color_lifetime.present = 1;
            ok = load_grad3(&e->color_lifetime.color, member(c, "ColorGradation")) &&
                 load_grad1(&e->color_lifetime.alpha, member(c, "AlphaGradation"));
            break;
        case 2: clear_force(&e->force_lifetime); ok = load_force(&e->force_lifetime, c); break;
        case 3:
            clear_rotation(&e->rotation_lifetime);
            e->rotation_lifetime.present = 1;
            e->rotation_lifetime.min = as_float(member(c, "Min"));
            e->rotation_lifetime.max = as_float(member(c, "Max"));
            ok = load_curve(&e->rotation_lifetime.curve, member(c, "Curve"));
            break;
        case 4: clear_curve_component(&e->size_lifetime); e->size_lifetime.present = 1; ok = load_curve(&e->size_lifetime.curve, member(c, "Curve")); break;
        case 5: clear_curve_component(&e->speed_lifetime); e->speed_lifetime.present = 1; ok = load_curve(&e->speed_lifetime.curve, member(c, "Curve")); break;
        case 6:
            clear_texcoord(&e->texcoord);
            e->texcoord.present = 1;
            e->texcoord.horizontal = as_uint(member(c, "HorizentalTiles"));
            e->texcoord.vertical = as_uint(member(c, "VerticalTiles"));
            e->texcoord.min_tile = as_int(member(c, "MinTileIndex"));
            e->texcoord.max_tile = as_int(member(c, "MaxTileIndex"));
            ok = load_curve(&e->texcoord.tiles, member(c, "TileIndices"));
            break;
        case 7: e->collider.present = 1; e->collider.bounding = as_float(member(c, "Bounding")); break;
        default: break;
        }
        if (!ok)
            return 0;
    }
    return 1;
}

static int load_billboard(mu_fx_effect *e, const jvalue *root)
{
    e->looping = as_bool(member(root, "Looping"));
    e->duration = as_float(member(root, "Duration"));
    for (size_t k = 0; k < 4; ++k)
        e->base_color[k] = array_float(root, "Color", k);
    e->base_width = as_float(member(root, "Width"));
    e->base_height = as_float(member(root, "Height"));
    e->base_angle = as_float(member(root, "RotationAngle"));
    e->uv0[0] = array_float(root, "TexCoord", 0);
    e->uv0[1] = array_float(root, "TexCoord", 1);
    e->uv1[0] = array_float(root, "TexCoord", 2);
    e->uv1[1] = array_float(root, "TexCoord", 3);
    e->blending = as_int(member(root, "Blending"));
    e->billboarding = as_int(member(root, "Billboarding"));
    e->brightness = as_float(member(root, "Brightness"));
    const jvalue *components = member(root, "Components");
    for (size_t i = 0; i < jsize(components); ++i) {
        const jvalue *c = item(components, i);
        int ok = 1;
        switch (as_int(member(c, "Type"))) {
        case 0:
            clear_color_lifetime(&e->bb_color);
            e->bb_color.present = 1;
            ok = load_grad3(&e->bb_color.color, member(c, "ColorGradation")) &&
                 load_grad1(&e->bb_color.alpha, member(c, "AlphaGradation"));
            break;
        case 1:
            clear_rotation(&e->bb_rotation);
            e->bb_rotation.present = 1;
            e->bb_rotation.constant = as_float(member(c, "Constant"));
            ok = load_curve(&e->bb_rotation.curve, member(c, "Curve"));
            break;
        case 2: clear_curve_component(&e->bb_size); e->bb_size.present = 1; ok = load_curve(&e->bb_size.curve, member(c, "Curve")); break;
        case 3:
            clear_texcoord(&e->bb_texcoord);
            e->bb_texcoord.present = 1;
            e->bb_texcoord.horizontal = as_uint(member(c, "HorizentalTiles"));
            e->bb_texcoord.vertical = as_uint(member(c, "VerticalTiles"));
            ok = load_curve(&e->bb_texcoord.tiles, member(c, "TileIndices"));
            break;
        case 4: clear_force(&e->bb_force); ok = load_force(&e->bb_force, c); break;
        default: break;
        }
        if (!ok)
            return 0;
    }
    return 1;
}

/* Constructor defaults (factory 0x00a797a0 and the child construction in
 * 0x00a760b2 pass the same values), then the base load 0x00a760b2: the node's
 * keys, the type load, the restart and the children. Returns 0 when out of
 * memory. */
static int load_node(mu_fx_effect *e, const jvalue *root)
{
    e->playing = 1;
    e->scale = 1.0f;
    const jvalue *name = member(root, "Name");
    if (name->type == J_STRING)
        snprintf(e->name, sizeof e->name, "%s", name->string);
    for (size_t k = 0; k < 3; ++k) {
        e->position[k] = array_float(root, "Position", k);
        e->rotation[k] = array_float(root, "Rotation", k);
    }
    e->scale = as_float(member(root, "Scale"));
    const jvalue *texture = member(root, "Texture");
    if (texture->type == J_STRING)
        snprintf(e->texture, sizeof e->texture, "%s", texture->string);
    e->min_duration = as_float(member(root, "minduration"));
    e->max_duration = as_float(member(root, "maxduration"));
    e->random_duration = as_bool(member(root, "randomduration"));
    e->parent_duration = as_bool(member(root, "parentduration"));
    int ok = e->type == MU_FX_PARTICLE_SYSTEM ? load_particle_system(e, root) : load_billboard(e, root);
    if (!ok)
        return 0;
    mu_fx_update_transform(e);
    mu_fx_restart(e);
    const jvalue *children = member(root, "Children");
    size_t n = jsize(children);
    for (size_t i = 0; i < n; ++i) {
        const jvalue *c = item(children, i);
        int type = as_int(member(c, "Type"));
        if (type != MU_FX_PARTICLE_SYSTEM && type != MU_FX_BILLBOARD)
            continue;   /* the client constructs nothing and skips the entry */
        mu_fx_effect *child = calloc(1, sizeof *child);
        if (!child)
            return 0;
        child->type = type;
        child->managed = e->managed;   /* constructed with the parent's manager (+0x28) */
        if (e->child_count == e->child_capacity) {
            uint32_t capacity = e->child_capacity ? 2u * e->child_capacity : 4u;
            mu_fx_effect **grown = realloc(e->children, capacity * sizeof *grown);
            if (!grown) {
                free(child);
                return 0;
            }
            e->children = grown;
            e->child_capacity = capacity;
        }
        e->children[e->child_count++] = child;   /* 0x00a75542: parent link, push_back */
        child->parent = e;
        if (!load_node(child, c))
            return 0;
    }
    return 1;
}

int mu_fx_load_json(mu_fx_effect *e, const char *text, size_t length, char *error, size_t error_size)
{
    memset(e, 0, sizeof *e);
    jparser j = {text, text + length, 0};
    jvalue *root = parse_value(&j, 0);
    if (!root || j.failed) {
        jfree(root);
        if (error && error_size)
            snprintf(error, error_size, "JSON parse error at byte %ld", (long)(j.p - text));
        return MU_FX_ERROR_PARSE;
    }
    e->type = as_int(member(root, "Type"));
    if (e->type != MU_FX_PARTICLE_SYSTEM && e->type != MU_FX_BILLBOARD) {
        if (error && error_size)
            snprintf(error, error_size, "effect type %d is not reconstructed", e->type);
        jfree(root);
        return MU_FX_ERROR_TYPE;
    }
    int ok = load_node(e, root);
    jfree(root);
    if (!ok) {
        mu_fx_free(e);
        if (error && error_size)
            snprintf(error, error_size, "out of memory");
        return MU_FX_ERROR_MEMORY;
    }
    return MU_FX_OK;
}

void mu_fx_free(mu_fx_effect *e)
{
    for (uint32_t i = 0; i < e->child_count; ++i) {
        mu_fx_free(e->children[i]);
        free(e->children[i]);
    }
    free(e->children);
    e->children = NULL;
    e->child_count = e->child_capacity = 0;
    free(e->actions);
    e->actions = NULL;
    e->action_count = 0;
    free(e->particles);
    e->particles = NULL;
    free_curve(&e->emitter.count_curve);
    free(e->emitter.bursts);
    e->emitter.bursts = NULL;
    free_grad3(&e->emitter.color.color);
    free_grad1(&e->emitter.color.alpha);
    free_grad1(&e->emitter.color.brightness);
    free_curve(&e->emitter.lifetime.curve);
    free_curve(&e->emitter.rotation.curve);
    free_curve(&e->emitter.size.curve);
    free_curve(&e->emitter.speed.curve);
    free_grad3(&e->color_lifetime.color);
    free_grad1(&e->color_lifetime.alpha);
    for (int k = 0; k < 3; ++k) {
        free_curve(&e->force_lifetime.curve[k]);
        free_curve(&e->bb_force.curve[k]);
    }
    free_curve(&e->rotation_lifetime.curve);
    free_curve(&e->size_lifetime.curve);
    free_curve(&e->speed_lifetime.curve);
    free_curve(&e->texcoord.tiles);
    free_grad3(&e->bb_color.color);
    free_grad1(&e->bb_color.alpha);
    free_curve(&e->bb_rotation.curve);
    free_curve(&e->bb_size.curve);
    free_curve(&e->bb_texcoord.tiles);
}
