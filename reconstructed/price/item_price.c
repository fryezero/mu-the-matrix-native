/* ItemValue 0x0169320b and ConvertRepairGold 0x016b8d16 (NATIVE-LANG-002); see item_price.h.
 *
 * Arithmetic follows the client's instruction widths: 32-bit imul where the
 * client multiplies in registers (wrapping), the CRT's 64-bit _allmul /
 * _alldiv (0x0191be60 / 0x0191c8b0) where it calls them, and the CRT
 * conversions __ltod3 0x0191c350, __dtol3 0x0191c250, __ltof3 0x0191c420 and
 * __ftol3 0x0191c080 (out-of-range and NaN results 0x8000000000000000).
 * MU_PRICE_MUTATION (build-time) plants the validator's negative controls. */
#include "item_price.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#ifndef MU_PRICE_MUTATION
#define MU_PRICE_MUTATION 0
#endif

/* Item.bmd record fields */
#define R_KIND_A 0x250
#define R_KIND_B 0x251
#define R_TYPE 0x252
#define R_TWO_HANDED 0x253
#define R_LEVEL 0x254
#define R_DURABILITY 0x268
#define R_VALUE 0x288
#define R_ZEN 0x28c
#define R_CAN_REPAIR 0x2ae
#define R_MAX_STACK 0x2af
#define R_PC_ROOM 0x2b0
#define R_EVOLVED_PET 0x2b1

static uint16_t rd16(const uint8_t *p) { return (uint16_t)(p[0] | p[1] << 8); }
static int32_t rd32(const uint8_t *p)
{
    return (int32_t)((uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24);
}

static int32_t mul32(int32_t a, int32_t b) { return (int32_t)((uint32_t)a * (uint32_t)b); }
static int32_t add32(int32_t a, int32_t b) { return (int32_t)((uint32_t)a + (uint32_t)b); }
static int64_t mul64(int64_t a, int64_t b) { return (int64_t)((uint64_t)a * (uint64_t)b); }
static int64_t add64(int64_t a, int64_t b) { return (int64_t)((uint64_t)a + (uint64_t)b); }

/* __dtol3 / __ftol3: truncation, 0x8000000000000000 when out of range. */
static int64_t dtol3(double x)
{
    if (!(x > -9223372036854775808.0) || !(x < 9223372036854775808.0))   /* NaN fails both */
        return INT64_MIN;
    return (int64_t)x;
}
static int64_t ftol3(float x) { return dtol3((double)x); }

/* g += __dtol3(__ltod3(g) * num / den) */
static int64_t add_fraction(int64_t g, double num, double den) { return add64(g, dtol3((double)g * num / den)); }

/* Signed rounding of the tail: >= 1000 to hundreds, >= 100 to tens. */
static int64_t round_gold(int64_t g)
{
    if (g >= 1000)
        return mul64(g / 100, 100);
    if (g >= 100)
        return mul64(g / 10, 10);
    return g;
}

typedef struct ctx {
    const uint8_t *r;
    const mu_price_item *it;
    int in_range;                       /* 0 <= code <= 0x2c00 (the object predicates' guard) */
} ctx;

static int kind_a(const ctx *c, int k) { return c->in_range && c->r[R_KIND_A] == k; }   /* 0x0095fc2e */
static int kind_b(const ctx *c, int k) { return c->in_range && c->r[R_KIND_B] == k; }   /* 0x00987982 */
static int type_is(const ctx *c, int k) { return c->in_range && c->r[R_TYPE] == k; }    /* 0x0095fbeb */
static int opt_set(const ctx *c) { return c->in_range && (c->it->set_bits & 0x33) != 0; }    /* 0x00cd0995(0) */
static int opt_excellent(const ctx *c) { return c->in_range && c->it->excellent == 1; }     /* 0x00cd0995(1) */

static int has_excellent_options(const mu_price_item *it)   /* 0x00cd14a7 */
{
    for (int i = 0; i < 9; i++)
        if (it->excellent_options[i] != 0xff)
            return 1;
    return 0;
}
/* 0x00cd1dfc: kind A 0x2e (0x00cd1ed8), 0x2d (0x00cd1e65), 0x2f/0x30/0x31/0x38 (0x00cd1e85) */
static int kind_2d_group(const ctx *c)
{
    return kind_a(c, 0x2e) || kind_a(c, 0x2d) || kind_a(c, 0x2f) || kind_a(c, 0x30) || kind_a(c, 0x31) ||
           kind_a(c, 0x38);
}
/* 0x00cd1e38: the same without 0x2e */
static int kind_2d_group_no2e(const ctx *c)
{
    return kind_a(c, 0x2d) || kind_a(c, 0x2f) || kind_a(c, 0x30) || kind_a(c, 0x31) || kind_a(c, 0x38);
}
static int type2_kind2(const ctx *c) { return type_is(c, 2) && kind_a(c, 2); }   /* 0x00cd2175 */

/* 0x00cd2326: special-durability codes */
static int special_durability(int32_t code)
{
    switch (code) {
    case 0x1a04: case 0x28f7: return 1;
    case 0x1a05: case 0x28f8: case 0x28f9: case 0x28fa: case 0x2900: return 0;
    default: return -1;
    }
}

/* 0x016be1d9 (NATIVE-DATA-002, verified there) */
static int repair_ban(const ctx *c)
{
    if (kind_b(c, 0x2b))
        return 1;
    if (c->it->period == 1 && c->it->expired == 1)
        return 1;
    return c->r[R_CAN_REPAIR] == 0;
}

static int in_list(int32_t v, const int32_t *list, size_t n)
{
    for (size_t i = 0; i < n; i++)
        if (list[i] == v)
            return 1;
    return 0;
}
#define IN(v, ...) in_list((v), (const int32_t[]){__VA_ARGS__}, sizeof((const int32_t[]){__VA_ARGS__}) / sizeof(int32_t))

/* The excellent-option ladders: the first case of the two 4/8/12/16 ladders
 * and of the 5/10/15/20 ladder is displaced (INFERRED, see the header). */
static int64_t ladder(int64_t g, int32_t v, int32_t step)
{
#if MU_PRICE_MUTATION == 4
    if (v == 2 * step)
        return add_fraction(g, 15.0, 10.0);
#endif
    if (v == step)
        return add_fraction(g, 6.0, 10.0);
    if (v == 2 * step)
        return add_fraction(g, 14.0, 10.0);
    if (v == 3 * step)
        return add_fraction(g, 28.0, 10.0);
    if (v == 4 * step)
        return add_fraction(g, 56.0, 10.0);
    return g;
}

static int32_t item_value(const uint8_t *record, const mu_price_item *it, int gt, const mu_price_state *s, int depth);

/* 0x010a91a7 (this = 0x06fb4518): socket items add gold * sockets * 7 / 10 and the buy price of each
 * seed sphere: code 0x1864 + 6 * (level - 1) + seed - 1, or 0x1937 + 6 * (level - 6) + seed - 1 above
 * level 5, on a new object (0x00ccbaa2 + 0x00ccc51e). */
static int64_t socket_price(const ctx *c, int64_t g, const mu_price_state *s, int depth)
{
    int64_t add = 0;
    if (!type_is(c, 2))
        return 0;
    const mu_price_item *it = c->it;
#if MU_PRICE_MUTATION == 3
    add = add64(add, mul64(g, (int64_t)mul32(it->socket_count, 8)) / 10);
#else
    add = add64(add, mul64(g, (int64_t)mul32(it->socket_count, 7)) / 10);
#endif
    for (int i = 0; i < it->socket_count && i < MU_PRICE_SOCKETS; i++) {
        uint8_t id = it->socket[i];
        if (id == 0xff)
            continue;
        int32_t seed = add32(s && s->socket_seed ? s->socket_seed[id] : 0, -1);
        int32_t base = 0x1864, adjust = 0;
        if (it->socket_level[i] > 5) {
            base = 0x1937;
            adjust = 5;
        }
        int32_t code = add32(add32(mul32(it->socket_level[i] - 1 - adjust, 6), base), seed);
        mu_price_item sphere;
        mu_price_item_init(&sphere);
        sphere.code = code;
        const uint8_t *rec = s && s->record_of ? s->record_of(s->user, code) : NULL;
        if (rec && depth < 4)
            add = add64(add, (int64_t)item_value(rec, &sphere, 0, s, depth + 1));
    }
    return add;
}

/* The per-code chain 0x016933e5..0x01694476.  Returns 1 with *g set when a case matched. */
static int code_chain(const ctx *c, int32_t L, int gt, int32_t world, int64_t *g)
{
    const mu_price_item *it = c->it;
    const int32_t code = it->code, n = it->durability;
    const int world3 = world == 0x5c && gt == 0;   /* the world-0x5c buy price x3 */
    int64_t v = 0;
    switch (code) {
    case 0x807: case 0x80f: {
        static const int32_t T807[4] = {100, 1400, 2200, 3000}, T80F[4] = {70, 1200, 2000, 2800};
        int32_t k = L >= 0 && L < 4 ? (code == 0x807 ? T807 : T80F)[L] : 0;
        if (c->r[R_DURABILITY] > 0)
            v = (int64_t)(mul32(n, k) / (int32_t)c->r[R_DURABILITY]);
        if (world3)
            v = mul64(v, 3);
        *g = v;
        return 1;
    }
    case 0x1c0d: *g = mul32(n, 3000000); return 1;
    case 0x1c0e: *g = mul32(n, 1800000); return 1;
    case 0x180f: *g = mul32(n, 810000); return 1;
    case 0x1c10: *g = mul32(n, 15000000); return 1;
    case 0x1c16: *g = mul32(n, 12000000); return 1;
    case 0x1c8d: *g = 672000; return 1;
    case 0x1c8e: *g = 546000; return 1;
    case 0x1c8f: *g = 471000; return 1;
    case 0x1c90: *g = 363000; return 1;
    case 0x1cce: *g = 5000; return 1;
    case 0x1ccf: case 0x1cd0: *g = 0; return 1;
    case 0x1a0e: *g = L == 0 ? 180000 : L == 1 ? 2400000 : 0; return 1;
    case 0x1a03:
        v = 960000;
        for (int i = 0; i < it->special_count && i < MU_PRICE_SPECIALS; i++)
            if (it->special[i] == 9 || it->special[i] == 10 || it->special[i] == 11)
                v = add64(v, 300000);
        *g = v;
        return 1;
    case 0x1a0f: *g = 9000000; return 1;
    case 0x1a10: case 0x1a11: {
        static const int32_t T[9] = {15000, 10000, 50000, 100000, 300000, 500000, 800000, 1000000, 1200000};
        *g = L >= 0 && L <= 8 ? T[L] : 0;
        return 1;
    }
    case 0x1a12:
        v = (int64_t)add32(mul32(L - 1, 20000), 200000);
        if (L == 1)
            v = 50000;
        *g = mul64(v, 3);
        return 1;
    case 0x1c1c: *g = 210000; return 1;
    case 0x1c1d: case 0x1c6e: *g = mul32(mul32(n, 10000), 3); return 1;
    case 0x1c6f: *g = world3 ? 1800000 : 600000; return 1;
    case 0x1c66: case 0x1c6d: *g = world3 ? 90000 : 30000; return 1;
    case 0x286c: v = mul32(n, 30000); *g = world3 ? mul64(v, 3) : v; return 1;
    case 0x1c65: case 0x1c67: case 0x1c68: case 0x1c69: case 0x1c6a: case 0x1c6b: case 0x1c6c:
        *g = mul32(mul32(n, 10000), 3);
        return 1;
    case 0x1a1d: *g = world3 ? 15000 : 5000; return 1;
    case 0x1c15: *g = L >= 0 && L <= 2 ? 9000 : L == 3 ? mul32(n, 3900) : 0; return 1;
    case 0x1c11: case 0x1c12: case 0x1c13: {
        static const int32_t T[3][8] = {{30000, 10000, 50000, 100000, 300000, 500000, 800000, 1000000},
                                        {30000, 15000, 75000, 150000, 450000, 750000, 1200000, 1500000},
                                        {120000, 60000, 84000, 120000, 180000, 240000, 300000, 180000}};
        int32_t idx = L < 0 ? 0 : L;
        if (idx >= 7)
            idx = 7;
        *g = T[code - 0x1c11][idx];
        return 1;
    }
    case 0x1a31: case 0x1a32: case 0x1a33: {
        static const int32_t T[7] = {9000, 500000, 600000, 800000, 1000000, 1200000, 1400000};
        *g = L >= 1 && L <= 6 ? T[L] : 9000;
        return 1;
    }
    case 0x1c17: case 0x1c18: case 0x1c19: case 0x1c1a: case 0x1c41: case 0x1c42: case 0x1c43: case 0x1c44:
        *g = 9000;
        return 1;
    default:
        break;
    }
    if (code == 0x1c09 && L == 1) { *g = 1000; return 1; }
    switch (code) {
    case 0x1c14: *g = 900; return 1;
    case 0x1c33: case 0x1c3f: *g = 200000; return 1;
    case 0x1c34: *g = 99; return 1;
    case 0x1c0a: *g = world3 ? 2250 : 750; return 1;
    case 0x1c1f: *g = mul32(n, 21000000); return 1;
    case 0x1c07: *g = L == 0 ? mul32(n, 900000) : L == 1 ? mul32(n, 450000) : 0; return 1;
    case 0x1a07:
        v = L == 0 ? 1500000 : L == 1 ? 1200000 : 0;
        *g = world3 ? mul64(v, 3) : v;
        return 1;
    case 0x1a0b: *g = L == 0 ? 100000 : L == 1 ? 2400000 : 0; return 1;
    case 0x1c23: *g = mul64(2000, n); return 1;
    case 0x1c24: *g = mul64(4000, n); return 1;
    case 0x1c25: *g = mul64(6000, n); return 1;
    case 0x1c26: *g = mul64(2500, n); return 1;
    case 0x1c27: *g = mul64(5000, n); return 1;
    case 0x1c28: *g = mul64(7500, n); return 1;
    case 0x1c55: case 0x1c56: case 0x1c57: *g = mul64(300, n); return 1;
    case 0x1a91: *g = mul32(n, 30000); return 1;
    case 0x1a92: *g = 600000; return 1;
    case 0x1a93: case 0x1890: case 0x1892: *g = mul32(n, 300000); return 1;
    case 0x1896: *g = mul32(n, 3000000); return 1;
    case 0x1897: *g = mul32(n, 9000000); return 1;
    case 0x1920: *g = mul64(n, 80000000); return 1;
    case 0x1d22: *g = mul32(n, 3000); return 1;
    case 0x1d35: case 0x1d36: case 0x1d37: case 0x1d38: *g = 1500000; return 1;
    case 0x1d3c: *g = 6000000; return 1;
    case 0x1d40: *g = mul32(n, 3000000); return 1;
    case 0x1d3d: *g = 60000000; return 1;
    case 0x1dd4: *g = mul32(n, 300000); return 1;
    default:
        return 0;
    }
}

/* The general formula 0x0169447b..0x01695261.  Returns 1 when the value branch returned directly
 * (*ret set), else 0 with *g for the tail. */
static int general(const ctx *c, int32_t L, int32_t lvl, int gt, const mu_price_state *s, int depth, int64_t *g,
                   int32_t *ret)
{
    const mu_price_item *it = c->it;
    const uint8_t *r = c->r;
    const int32_t code = it->code, n = it->durability;
    const int32_t world = s ? s->world : 0;
    int64_t v = 0;
    if (r[R_VALUE] > 0) {
        int32_t val = r[R_VALUE];
        v = (int64_t)(mul32(mul32(val, val), 10) / 12);
        if (kind_a(c, 9) && r[R_MAX_STACK] > 0)
            v = mul64(v, n);
        if (code == 0x1c03 || code == 0x1c06)
            v = 1500;
        if (code >= 0x1c00 && code <= 0x1c08) {
            if (world == 0x5c && gt == 0)
                v = mul64(v, 3);
            if (L > 0)
                v = mul64(v, dtol3(pow(2.0, (double)L)));
            v = mul64(v / 10, 10);
            v = mul64(v, n);
            if (gt != 0) {
                v = v / 3;
                v = mul64(v / 10, 10);
            }
            *ret = (int32_t)(uint32_t)(uint64_t)v;
            return 1;
        }
        *g = v;
        return 0;
    }
    if (code == 0x1a14) { *g = L == 0 ? 3000 : 0; return 0; }
    if (code == 0x1a34 || code == 0x1a35) { *g = 3000000; return 0; }
    if (code == 0x1a1f) { *g = L == 0 ? 9000000 : L == 1 ? 4500000 : 0; return 0; }
    if (kind_a(c, 0x19)) {
        int32_t e = add32(mul32(mul32(mul32(rd16(r + R_LEVEL), L + 0x32), mul32(L, 10)), L), 100000);
        *g = dtol3((double)e * ((double)it->socket_count * 0.8));
        return 0;
    }
    if (kind_a(c, 0x1a) || kind_b(c, 0x2c)) {
        int32_t sum = 0;
        for (int i = 0; i < 5; i++)
            if (it->slot_73[i] != 0xff)
                sum += it->slot_73[i] >> 4;
        int32_t x = add32(rd16(r + R_LEVEL), mul32(sum, 5));
        int32_t e = add32(mul32(mul32(add32(x, 40), x), x / 8), 100);
        *g = (int64_t)mul32(it->socket_count * 2, e);
        return 0;
    }
    if (kind_b(c, 0x64) || kind_a(c, 0xb)) { *g = 0; return 0; }
    const int32_t type = code / 512;
    if ((type == 0xc || type == 0xd || type == 0xf) && !kind_a(c, 6)) {
        v = (int64_t)add32(mul32(mul32(lvl, lvl), lvl), 100);
        for (int i = 0; i < it->special_count && i < MU_PRICE_SPECIALS; i++) {
            if (it->special[i] == 6)
                v = add64(mul64(v, it->special_value[i]), v);
            else if (it->special[i] == 0)
                v = add64(mul64(v, it->special_value[i]) / 4, v);
        }
        *g = v;
        return 0;
    }
    static const int32_t LEVEL_ADD[11] = {4, 10, 25, 45, 65, 95, 135, 185, 245, 305, 365};
    if (L >= 5 && L <= 15)
        lvl = add32(lvl, LEVEL_ADD[L - 5]);
    if (kind_a(c, 6) && !kind_b(c, 0x16))
        v = add64((int64_t)mul32(mul32(mul32(add32(lvl, 40), lvl), lvl), 11), 40000000);
    else
        v = (int64_t)add32(mul32(mul32(add32(lvl, 40), lvl), lvl) / 8, 100);
    if (type >= 0 && type <= 6 && r[R_TWO_HANDED] == 0)
        v = mul64(v, 80) / 100;
    if (IN(it->skill, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x38, 0x104, 0x105, 0x10e))
        v = add64(v, (int64_t)(uint32_t)(uint64_t)ftol3((float)v * 1.5f));
    for (int i = 0; i < it->special_count && i < MU_PRICE_SPECIALS; i++) {
        uint16_t sp = it->special[i];
        int32_t value = it->special_value[i];
        switch (sp) {
        case 0: case 1: case 2: case 4: case 6:
            if (kind_a(c, 6)) {
                if (sp == 6)
                    value <<= 2;
                v = ladder(v, value, 4);
            } else if (kind_2d_group(c) && opt_set(c)) {
                /* 0x00cd21f6: unchanged */
            } else if (type2_kind2(c)) {
                if (value >= 1 && value <= 3) {
                    static const double F[3] = {6.0, 14.0, 28.0};
                    v = add_fraction(v, F[value - 1], 10.0);
                }
            } else {
                v = ladder(v, value, 4);
            }
            break;
        case 3: v = ladder(v, value, 5); break;
        case 5: case 10: case 11: v = add_fraction(v, 25.0, 100.0); break;
        case 7: case 8: case 9: case 12: v = add64(v, v); break;
        default: break;
        }
    }
    if (has_excellent_options(it) && !kind_2d_group(c)) {
        for (int i = 0; i < 9; i++)
            if (it->excellent_options[i] != 0xff)
                v = add64(v, kind_a(c, 6) ? dtol3((double)v * 25.0 / 100.0) : v);
    } else if (kind_2d_group(c)) {
        if (opt_excellent(c)) {
            int k = 0;
            for (int i = 0; i < 9; i++)
                k += it->excellent_options[i] != 0xff;
            v = dtol3((double)v * pow(2.0, (double)k));
        } else if (opt_set(c) && kind_2d_group_no2e(c)) {
            int k = 1;
            if (((it->slot_73[3] & 0x38) >> 3) != 7)     /* 0x00cdaf42(item, 0) */
                k++;
            if ((it->slot_73[3] & 7) != 7)               /* 0x00cdaf42(item, 1) */
                k++;
            v = dtol3((double)v * pow(2.0, (double)k));
        }
    }
    if (it->flag_72 == 1)
        v = add_fraction(v, 16.0, 100.0);
    v = add64(v, socket_price(c, v, s, depth));
    v = add64(v, (int64_t)mul32(it->harmony, 50000));
    if (r[R_MAX_STACK] > 0)
        v = mul64(v, n);
    *g = v;
    return 0;
}

static int32_t item_value(const uint8_t *r, const mu_price_item *it, int gt, const mu_price_state *s, int depth)
{
    if (!r || !it)
        return 0;
    if (it->code == -1)
        return 0;
    if (gt == 1 && s && s->sell_flag)
        return 1;
    ctx c = {r, it, it->code >= 0 && it->code <= 0x2c00};
    const int32_t code = it->code, n = it->durability, world = s ? s->world : 0;
    int64_t g = 0;
    int32_t zen = rd32(r + R_ZEN);
    if (zen != 0) {
        g = zen;
        if (gt != 0)
            g = g / 3;
        g = round_gold(g);
        if (r[R_MAX_STACK] != 0)
            g = mul64(g, n);
        return (int32_t)(uint32_t)(uint64_t)g;
    }
    const int32_t L = (it->level & 0xf);
    int32_t lvl = add32(rd16(r + R_LEVEL), mul32(L, 3));
    if (has_excellent_options(it) && !kind_a(&c, 6) && !kind_2d_group(&c)) {
        lvl = add32(lvl, 25);
    } else if (kind_2d_group(&c)) {
        if (opt_excellent(&c))
            lvl = add32(lvl, 25);
        else if (opt_set(&c))
            lvl = add32(lvl, 35);
    }
    if (!code_chain(&c, L, gt, world, &g)) {
        int32_t ret;
        if (general(&c, L, lvl, gt, s, depth, &g, &ret))
            return ret;
    }
    /* tail 0x01695261 */
    if (g >= 3000000000LL)
        g = 3000000000LL;
    if (gt == 2)
        g = round_gold(g);
#if MU_PRICE_MUTATION != 1
    if (gt != 0)
        g = g / 3;
#endif
    switch (code) {
    case 0x1a20: g = mul32(n, 50); break;
    case 0x1a21: g = mul32(n, 100); break;
    case 0x1a22: g = mul32(n, 1000); break;
    case 0x1a23: g = mul32(n, 10000); break;
    case 0x1a24: g = 30000; break;
    case 0x1a25: g = 50000; break;
    default: break;
    }
    if ((code >= 0x1c2d && code <= 0x1c32) || (code >= 0x1db0 && code <= 0x1db7) || IN(code, 0x1ce0, 0x1d07, 0x1d08))
        g = mul32(n, 100);
    if (code >= 0x1c99 && code <= 0x1c9c)
        g = mul32(n, 1000);
    else if (code >= 0x1c9d && code <= 0x1c9f)
        g = 10000;
    if (IN(code, 0x18de, 0x18e8, 0x18f2, 0x18fc, 0x1904))
        g = 1;
    if (code == 0x18db)
        g = 0;
    if (code >= 0x1a47 && code <= 0x1a4b)
        g = 1000000;
    if (special_durability(code) != -1) {
        if (!s || s->pet_status == -1)
            return -1;
        g = (int64_t)s->pet_value;
    }
    if (IN(code, 0x1a70, 0x1a40, 0x1a41, 0x1a4c, 0x1a4d, 0x1a4e, 0x1a50, 0x1a6d, 0x1a6e, 0x1a6f, 0x1a71, 0x1a72,
           0x1a73, 0x1aa6, 0x1c70, 0x1c71, 0x1c79, 0x1c7a, 0x1c7b, 0x1c7c, 0x298d, 0x298e))
        g = 1000;
    else if (IN(code, 0x1a7a, 0x1a7b, 0x1aa3, 0x1aa4, 0x1aa5))
        g = 2000;
    else if (IN(code, 0x1882, 0x1883, 0x1884, 0x1885, 0x1886, 0x1887, 0x189a, 0x18ac, 0x1916))
        g = 80;
    if (type_is(&c, 5) && gt == 1)
        g = 0;
    if ((kind_a(&c, 0xe) || kind_a(&c, 0xf) || kind_a(&c, 0x12) || kind_a(&c, 0x1b) || kind_a(&c, 0x21) ||
         kind_a(&c, 0x37) || kind_2d_group(&c)) &&
        it->period == 1 && it->expired == 1 && gt == 1)
        g = 0;
    if (type2_kind2(&c))
        g = g / 100;
    if (type_is(&c, 4))
        g = 0;
    if (code == 0x1b0c) g = 1000000000;
    if (code == 0x190a) g = 100000000;
    if (code == 0x190b || code == 0x19e0) g = 1000000;
    if (code == 0x1aa9 || code == 0x1aaa) g = 30000;
    if (code >= 0x1cd9 && code <= 0x1cdd) g = 100000;
    if ((code >= 0x1cf5 && code <= 0x1cf7) || code == 0x1cea) g = 1000000;
    if ((code >= 0x1d0d && code <= 0x1d14) || code == 0x1d17 || code == 0x1d18) g = 1000;
    if (code == 0x1d86) g = mul32(n, 1000);
    if (code == 0x18d7) g = 1;
    if (kind_a(&c, 0xc)) {
        if (kind_b(&c, 0))
            g = 200000;
        else if (code == 0x20ef)
            g = gt == 0 ? 900000 : 300000;
        else if (code == 0x20f0)
            g = 1000000;
        else
            g = 0;
    }
    if (code >= 0x1d1a && code <= 0x1d1c) g = 1000000;
    if (code == 0x29) g = 100000;
    if (code == 0x1bfe) g = mul32(n, 100000);
    if (r[R_PC_ROOM]) g = 0;
    if (r[R_EVOLVED_PET]) g = 0;
    if (gt == 1 && IN(code, 0x1b98, 0x1da4, 0x1d73, 0x1d74, 0x1d75, 0x1c45)) g = 0;
    if (gt == 1 && code == 0x1920) g = mul32(n, 1000);
    if (gt == 1 && code == 0x1d59) g = 5000;
    if (IN(code, 0x1dae, 0x1d93, 0x1d94, 0x1d95)) g = mul32(n, 1000);
    if (code == 0x1dbe || code == 0x1dc3) g = 0;
    if (s && s->soul_conversion && s->soul_conversion(s->user, code)) g = 10000;
    switch (code) {
    case 0x1dd2: g = mul32(n, 100000); break;
    case 0x1dd3: g = mul32(n, 200000); break;
    case 0x1dd4: g = mul32(n, 500000); break;
    case 0x1dd5: g = mul32(n, 30000); break;
    case 0x1dd6: g = mul32(n, 900000); break;
    case 0x1dd7: g = mul32(n, 50000); break;
    case 0x1dd8: case 0x1dd9: case 0x1dda: case 0x1ddb: case 0x1ddc: g = 1000000; break;
    case 0x1ddd: g = mul32(n, 500000); break;
    case 0x2915: case 0x2934: g = mul32(n, 1000); break;
    default: break;
    }
    if (kind_a(&c, 0x39)) g = mul32(n, 10000000);
    if (kind_a(&c, 0x3a)) g = mul32(n, 10000000);
    if (kind_a(&c, 0x17)) g = mul32(n, 10000000);
    if (kind_a(&c, 0x18)) g = mul32(n, 1000000);
    if (kind_a(&c, 0x1c)) g = 200000;
    if (kind_b(&c, 0x5c)) g = mul32(n, 50000);
    if (code == 0x285e) g = mul32(n, 10000);
    if ((code == 0x1d9e || code == 0x1db8) && it->period == 1 && it->expired == 1 && gt == 1) g = 0;
    if (code == 0x286d) g = mul32(n, 10000);
    if (code == 0x28a4 || code == 0x28ee || code == 0x28ef) g = mul32(n, 1000);
    if (kind_a(&c, 0x20)) g = 0;
    if (code == 0x289d || code == 0x2610 || code == 0x291f) g = 0;
    if (code == 0x2876) g = 10000;
    if (code == 0x289e) g = mul32(n, 10000);
    if (code == 0x289f || code == 0x28a0) g = 10000;
    if (code == 0x28a1) g = mul32(n, 1000);
    {   /* 0x00cd5de8 on the item-script manager: kind A of the code, 0 when absent */
        const uint8_t *byc = s && s->record_of ? s->record_of(s->user, code) : r;
        if (byc && byc[R_KIND_A] == 0x22)
            g = 50000;
    }
    if (code == 0x181d || code == 0x1a06) g = 0;
    if (gt == 1 && IN(code, 0x1a10, 0x1a11, 0x1a12, 0x1c11, 0x1c12, 0x1c13, 0x1a31, 0x1a32, 0x1a33, 0x1a1d, 0x1c6e,
                      0x1c6f, 0x286c, 0x286d, 0x1dae))
        g = 0;
    if (code >= 0x2984 && code <= 0x2987) g = 0;
    if (repair_ban(&c) != 1 && gt == 1) {
        /* the sell price loses 60 % of the missing durability share */
        float worn = 1.0f - (float)it->durability / (float)it->max_durability;
#if MU_PRICE_MUTATION == 2
        uint32_t cut = (uint32_t)(uint64_t)ftol3((float)g * 0.5f * worn);
#else
        uint32_t cut = (uint32_t)(uint64_t)ftol3((float)g * 0.6f * worn);
#endif
        if (code == 0x1a1f)
            cut = 0;
        g = (int64_t)((uint64_t)g - cut);
    }
    g = round_gold(g);
    return (int32_t)(uint32_t)(uint64_t)g;
}

void mu_price_item_init(mu_price_item *item)
{
    memset(item, 0, sizeof *item);
    item->code = -1;
    memset(item->excellent_options, 0xff, sizeof item->excellent_options);
}

int32_t mu_item_price(const uint8_t *record, const mu_price_item *item, int gold_type, const mu_price_state *state)
{
    return item_value(record, item, gold_type, state, 0);
}

int32_t mu_item_repair_cost(int32_t value, int32_t durability, int32_t max_durability, int16_t code,
                            const mu_repair_state *s)
{
    int32_t gold = value < 400000000 ? value : 400000000;
    float rg = (float)gold;
    float worn = 1.0f - (float)durability / (float)max_durability;
    if (worn > 0.0f) {
        float a = (float)sqrt((double)rg);
        float b = (float)sqrt(sqrt((double)rg));
        rg = 3.0f * a * b;
        rg *= worn;
        rg += 1.0f;
        if (durability <= 0) {
            if (special_durability(code) != -1)   /* 0x00c92e9a: the same code list */
                rg *= 2.0f;
            else
                rg = rg * 0.4f + rg;
        }
    } else {
        rg = 0.0f;
    }
    int shop = s && s->shop_visible, flag = s && s->shop_repair_flag, inventory = s && s->inventory_visible;
    float f = rg;
    if (!(shop && flag) && inventory)
#if MU_PRICE_MUTATION == 5
        f = rg * 1.2f + rg;
#else
        f = rg * 1.1f + rg;
#endif
    /* cvttss2si: 0x80000000 when out of range */
    if (f >= -2147483648.0f && f < 2147483648.0f)
        gold = (int32_t)f;
    else
        gold = INT32_MIN;
    if (gold >= 1000)
        gold = gold / 100 * 100;
    else if (gold >= 100)
        gold = gold / 10 * 10;
    int32_t discount = s ? s->discount_percent : 0;
    gold = add32(gold, -(int32_t)(uint32_t)(uint64_t)(mul64(gold, discount) / 100));
    return gold;
}

int32_t mu_item_repair_price(const uint8_t *record, const mu_price_item *item, const mu_price_state *state,
                             const mu_repair_state *repair, int *shown)
{
    if (shown)
        *shown = 0;
    if (!item || item->durability >= item->max_durability)
        return 0;
    int32_t value = mu_item_price(record, item, MU_PRICE_REPAIR, state);
    if (value == -1)
        return 0;
    if (shown)
        *shown = 1;
    return mu_item_repair_cost(value, item->durability, item->max_durability, (int16_t)item->code, repair);
}

char *mu_price_format(uint32_t value, char *out, size_t cap)
{
    uint32_t lead = value;
    int digits = 0;
    while (lead / 1000 > 0) {
        digits += 3;
        lead /= 1000;
    }
    size_t n = (size_t)snprintf(out, cap, "%d", (int)lead);
    for (; digits > 0 && n < cap; digits -= 3) {
        uint32_t p1 = 1, p2 = 1;
        for (int i = 0; i < digits; i++)
            p1 *= 10;
        for (int i = 0; i < digits - 3; i++)
            p2 *= 10;
        n += (size_t)snprintf(out + n, cap - n, ",%03d", (int)(value % p1 / p2));
    }
    return out;
}
