/* Experience and the server's progression answers (NATIVE-PROGRESS-001).  See progress.h.
 *
 * Lines (env->emit), besides the GFx invokes:
 *   call 00a00386                     SetLevel's refresh (only when the window 0x0095c5da exists:
 *                                     then "call 00c8d968 LEVEL")
 *   call 00c71772                     the main frame (getter 0x0095c50b) refreshes HP/MP
 *   call 00b45719 / 00b458f2 / 00b45a48 / 00b45c36   the character window (GFx manager +0x21c)
 *   call 01219a39 "TEXT"              the chat window [0x01d22c6c] adds a system line
 *   call 0095f547 "TEXT"              the chat window's other line (master experience)
 *   call 00a00f4a / 00a00fb7          the hero's level experience / the stat machine's recalculation
 *   call 00c349cb                     GFx manager +0x298
 *   call 0153b02c TYPE P1 P2 P3 SUB OWNER SCALE A B C D E F     CreateJoint (pointers as o+OFF)
 *   call 013c0eaa TYPE P1 P2 P3 SUB OWNER A B C D SCALE E F G   CreateEffect
 *   call 00a6ac96 SOUND A B           PlayBuffer
 *   call 00c51256                     the experience bar (main frame +0xf0)
 * Floats are printed as their bit patterns. */
#include <inttypes.h>
#include <string.h>

#include "progress_internal.h"

static uint32_t fbits(float f)
{
    uint32_t u;
    memcpy(&u, &f, sizeof u);
    return u;
}

static uint16_t rd16le(const uint8_t *p, int off)
{
    return (uint16_t)(p[off] | p[off + 1] << 8);
}

static int window(const mu_prg_env *e, uint32_t getter)
{
    return e->window ? e->window(e->user, getter) : 0;
}

static const char *gtext(const mu_prg_env *e, int32_t index)
{
    const char *t = e->global_text ? e->global_text(e->user, index) : NULL;
    return t ? t : "";
}

/* the client's formatter over one "%lld"-style argument (GlobalText formats; other conversions are
 * copied as they are) */
static void format_i64(char *out, size_t cap, const char *fmt, int64_t value)
{
    size_t n = 0;
    for (const char *p = fmt; *p && n + 1 < cap; p++) {
        if (p[0] == '%' && (!strncmp(p + 1, "lld", 3) || !strncmp(p + 1, "I64d", 4))) {
            n += (size_t)snprintf(out + n, cap - n, "%" PRId64, value);
            p += p[1] == 'l' ? 3 : 4;
            if (n >= cap)
                n = cap - 1;
        } else if (p[0] == '%' && p[1] == 'd') {
            n += (size_t)snprintf(out + n, cap - n, "%d", (int32_t)value);
            p += 1;
            if (n >= cap)
                n = cap - 1;
        } else if (p[0] == '%' && p[1] == '%') {
            out[n++] = '%';
            p += 1;
        } else {
            out[n++] = *p;
        }
    }
    out[n] = 0;
}

static void chat(const mu_prg_env *e, const char *fn, const char *text)
{
    char q[1100];
    mu_prg_json(q, sizeof q, text);
    mu_prg_emitf(e, "call %s %s", fn, q);
}

/* ---- the experience table ---------------------------------------------------------------------- */

int64_t mu_prg_exp_table(int64_t level)
{
    uint64_t n = (uint64_t)level - 1u;
    int64_t r = 0;
    if ((int64_t)n > 0) {
        r = (int64_t)(((n + 9u) * n * n) * (MU_PROGRESS_MUTATION == 4 ? 9u : 10u));
        if ((int64_t)n > 0xff) {
            uint32_t m = (uint32_t)n - 0xffu;
            int32_t t = (int32_t)((m + 9u) * m * m);
            r = (int64_t)((uint64_t)r + (uint64_t)((int64_t)t * 1000));
        }
    }
    return r < 0 ? 0 : r;
}

void mu_prg_level_exp(uint8_t *a)
{
    mu_prg_set64(a, MU_PRG_A_EXP, 0);
    int64_t level = mu_prg_i32(a, MU_PRG_A_LEVEL);
    int64_t lo = mu_prg_exp_table(level), hi = mu_prg_exp_table(level + 1);
    mu_prg_set64(a, MU_PRG_A_NEXT_EXP, (uint64_t)hi - (uint64_t)lo);
}

/* ---- level up ---------------------------------------------------------------------------------- */

static void set_level(const mu_prg_env *e, int32_t v)
{
    mu_prg_set32(e->attr, MU_PRG_A_LEVEL, (uint32_t)(v >= 0x190 ? 0x190 : v));
    if (window(e, 0x0095c5da))
        mu_prg_emitf(e, "call 00c8d968 %x", (uint32_t)mu_prg_effective_level(e->attr));
}

static void at_least(uint8_t *a, size_t off, int32_t value, int32_t floor)
{
    mu_prg_set32(a, off, (uint32_t)value);
    if (mu_prg_i32(a, off) < floor)
        mu_prg_set32(a, off, (uint32_t)floor);
}

static void character_window(const mu_prg_env *e, int all)
{
    mu_prg_emitf(e, "call 00b45719");
    mu_prg_emitf(e, "call 00b458f2");
    mu_prg_emitf(e, "call 00b45a48");
    if (all)
        mu_prg_emitf(e, "call 00b45c36");
}

static void joint(const mu_prg_env *e, int32_t sub, float scale)
{
    mu_prg_emitf(e, "call 0153b02c 7f78 o+158 o+158 o+164 %x o %08x 2 0 0 ffffffff 0 ffffffff 0", (uint32_t)sub,
                 fbits(scale));
}

static void third_class_effects(const mu_prg_env *e)
{
    joint(e, 0x2d, 80.0f);
    for (int i = 0; i < 0x13; i++)
        joint(e, 0x2e, 80.0f);
}

void mu_prg_recv_levelup(const mu_prg_env *e, const uint8_t *p)
{
    uint8_t *a = e->attr;
    set_level(e, rd16le(p, 4));
    mu_prg_set16(a, MU_PRG_A_POINTS, rd16le(p, 6));
    at_least(a, MU_PRG_A_LIFE_MAX, rd16le(p, 8), 1);
    at_least(a, MU_PRG_A_MANA_MAX, rd16le(p, 0xa), 1);
    at_least(a, MU_PRG_A_LIFE, rd16le(p, 8), 0);
    at_least(a, MU_PRG_A_MANA, rd16le(p, 0xa), 0);
    at_least(a, MU_PRG_A_SHIELD_MAX, rd16le(p, 0xc), 1);
    at_least(a, MU_PRG_A_AG_MAX, rd16le(p, 0xe), MU_PROGRESS_MUTATION == 5 ? 0 : 1);
    if (window(e, 0x0095c50b))
        mu_prg_emitf(e, "call 00c71772");
    for (int i = 0; i < 4; i++)
        mu_prg_set16(a, MU_PRG_A_ADD_POINT + 2 * (size_t)i, rd16le(p, 0x10 + 2 * i));
    character_window(e, 1);
    char text[512];
    uint64_t rest = mu_prg_u64(a, MU_PRG_A_NEXT_EXP) - mu_prg_u64(a, MU_PRG_A_EXP);
    format_i64(text, sizeof text, gtext(e, 0x1e6), (int64_t)rest);
    chat(e, "01219a39", text);
    mu_prg_emitf(e, "call 00a00f4a");
    mu_prg_emitf(e, "call 00a00fb7");
    mu_prg_emitf(e, "call 00c349cb");
    if ((e->hero_class >> 5 & 1) == 1) {
        third_class_effects(e);
    } else {
        for (int i = 0; i < 0xf; i++)
            joint(e, 0, 40.0f);
        mu_prg_emitf(e, "call 013c0eaa 7f84 o+158 o+164 o+ec 0 o ffffffff 0 0 0 00000000 ffffffff 0 0");
    }
    mu_prg_emitf(e, "call 00a6ac96 98 0 0");
}

/* ---- the stat point answer --------------------------------------------------------------------- */

void mu_prg_recv_point(const mu_prg_env *e, const uint8_t *p)
{
    uint8_t *a = e->attr;
    if (p[4] >> 4) {
        mu_prg_set16(a, MU_PRG_A_POINTS, (uint32_t)mu_prg_u16(a, MU_PRG_A_POINTS) - 1u);
        int stat = p[4] & 0xf;
        if (stat == 2)
            at_least(a, MU_PRG_A_LIFE_MAX, rd16le(p, 6), 1);
        else if (stat == (MU_PROGRESS_MUTATION == 6 ? 4 : 3))
            at_least(a, MU_PRG_A_MANA_MAX, rd16le(p, 6), 1);
        at_least(a, MU_PRG_A_AG_MAX, rd16le(p, 0xa), 1);
        at_least(a, MU_PRG_A_SHIELD_MAX, rd16le(p, 8), 1);
        if (window(e, 0x0095c50b))
            mu_prg_emitf(e, "call 00c71772");
    }
    mu_prg_emitf(e, "call 00b458f2");
}

/* ---- the experience of a kill ------------------------------------------------------------------ */

int mu_prg_recv_kill_exp(const mu_prg_env *e, const uint8_t *p, int encrypted, uint8_t report[5])
{
    if (!encrypted) {
        static const uint8_t R[5] = {0xc1, 0x4d, 0x02, 0x00, 0x16};
        if (report)
            memcpy(report, R, sizeof R);
        mu_prg_emitf(e, "call 00d51d4f 1 0");
        return 0;
    }
    int32_t key = p[3] << 8 | p[4];
    uint32_t exp = (uint32_t)(p[5] << 8 | p[6]);
    int32_t dmg = p[7] << 8 | p[8];
    int died = key >> 15;
    key &= 0x7fff;
    int32_t index = 0;
    uint8_t *o = e->character ? e->character(e->user, key, &index) : NULL;
    if (o) {
        if (died) {
            mu_prg_emitf(e, "call 01393a61 o");
        } else if (e->hero) {
            e->hero[0x20] = 2;
            mu_prg_set16(e->hero, 0x148, (uint32_t)dmg);
            mu_prg_set16(e->hero, 0x40, (uint32_t)index);
        }
        if (dmg && !(e->world_hides_damage && e->world_hides_damage(e->user)))
            mu_prg_emitf(e, "call 016912ae o+158 %x %08x %08x %08x %08x 1 0 00000000 0", (uint32_t)dmg, fbits(1.0f),
                         fbits(0.6f), fbits(0.0f), fbits(15.0f));
        o[0x23] = 1;
        o[0x38] = 0;
    }
    uint8_t *a = e->attr;
    int third = (e->hero_class >> 5 & 1) == 1;
    if (third)
        mu_prg_set64(a, MU_PRG_A_MEXP, mu_prg_u64(a, MU_PRG_A_MEXP) + exp);
    else
        mu_prg_set64(a, MU_PRG_A_EXP, mu_prg_u64(a, MU_PRG_A_EXP) + exp);
    if (exp) {
        /* the client passes the 32-bit experience to a %lld format: the high half is the stack word
         * above the arguments (0 in the validator's cleared stack) */
        char text[512];
        format_i64(text, sizeof text, gtext(e, third ? 0x6d6 : 0x1e6), (int64_t)exp);
        chat(e, "01219a39", text);
    }
    if (window(e, 0x0095c50b))
        mu_prg_emitf(e, "call 00c51256");
    if (window(e, 0x00aae6f9))
        mu_prg_emitf(e, "call 00c42e9e");
    return 1;
}

/* ---- master level ------------------------------------------------------------------------------ */

static int16_t rd16s(const uint8_t *p, int off)
{
    return (int16_t)rd16le(p, off);
}

void mu_prg_recv_master_levelup(const mu_prg_env *e, const uint8_t *p)
{
    uint8_t *a = e->attr;
    mu_prg_set32(a, MU_PRG_A_MLEVEL, (uint32_t)(int32_t)rd16s(p, 4));
    if (window(e, 0x0095c5da))
        mu_prg_emitf(e, "call 00c8d968 %x", (uint32_t)mu_prg_effective_level(a));
    mu_prg_set32(a, MU_PRG_A_MPOINTS, (uint32_t)(int32_t)rd16s(p, 6));
    mu_prg_set32(a, MU_PRG_A_M34, (uint32_t)(int32_t)rd16s(p, 8));
    mu_prg_set32(a, MU_PRG_A_M3C, (uint32_t)(int32_t)rd16s(p, 0xa));
    char text[512];
    uint64_t rest = mu_prg_u64(a, MU_PRG_A_MNEXT_EXP) - mu_prg_u64(a, MU_PRG_A_MEXP);
    format_i64(text, sizeof text, gtext(e, 0x6d6), (int64_t)rest);
    chat(e, "0095f547", text);
    character_window(e, 0);
    if ((e->hero_class >> 5 & 1) == 1)
        third_class_effects(e);
    if ((e->hero_class >> 6 & 1) == 1) {
        mu_prg_emitf(e, "call 00c239c2");
        mu_prg_emitf(e, "call 00c23c52");
    }
    mu_prg_emitf(e, "call 00bb0803 e");
    if (window(e, 0x00aae6f9))
        mu_prg_emitf(e, "call 00c42e9e");
    mu_prg_emitf(e, "call 00c349cb");
}

static uint64_t be64(const uint8_t *p)
{
    uint64_t v = 0;
    for (int i = 0; i < 8; i++)
        v = v << 8 | p[i];
    return v;
}

void mu_prg_recv_master_exp(const mu_prg_env *e, const uint8_t *p)
{
    uint8_t *a = e->attr;
    int32_t ml = rd16s(p, 4);
    if (mu_prg_master_level(a) != ml) {
        mu_prg_set32(a, MU_PRG_A_MLEVEL, (uint32_t)ml);
        if (window(e, 0x0095c5da))
            mu_prg_emitf(e, "call 00c8d968 %x", (uint32_t)mu_prg_effective_level(a));
        if (window(e, 0x009a19ae))
            mu_prg_emitf(e, "call 00c84990");
        mu_prg_emitf(e, "call 00c349cb");
    }
    mu_prg_set64(a, MU_PRG_A_MEXP, be64(p + 6));
    mu_prg_set64(a, MU_PRG_A_MNEXT_EXP, be64(p + 0xe));
    mu_prg_set32(a, MU_PRG_A_M34, (uint32_t)(int32_t)rd16s(p, 0x16));
    if ((e->hero_class >> 6 & 1) == 1) {
        mu_prg_emitf(e, "call 00c239c2");
        mu_prg_emitf(e, "call 00c23c52");
    }
    mu_prg_emitf(e, "call 00bb0803 e");
    if (window(e, 0x0095c50b))
        mu_prg_emitf(e, "call 00c51256");
    if (window(e, 0x00aae6f9))
        mu_prg_emitf(e, "call 00c42e9e");
}

/* ---- the character window's stat values (0x00b3ee5e) -------------------------------------------- */

int mu_prg_recv_stats(const mu_prg_env *e, mu_prg_stat_window *w, const uint8_t *p)
{
    static const size_t BASE[5] = {MU_PRG_A_STRENGTH, MU_PRG_A_DEXTERITY, MU_PRG_A_VITALITY, MU_PRG_A_ENERGY,
                                   MU_PRG_A_COMMAND};
    static const size_t ADD[5] = {MU_PRG_A_ADD_STR, MU_PRG_A_ADD_DEX, MU_PRG_A_ADD_VIT, MU_PRG_A_ADD_ENE,
                                  MU_PRG_A_ADD_CMD};
    static const int ROW[5] = {8, 0xd, 0x18, 0x1d, 0x2a};
    uint8_t *a = e->attr;
    for (int i = 0; i < 5; i++) {
        uint16_t base = rd16le(p, 4 + 4 * i), add = rd16le(p, 6 + 4 * i);
        if (mu_prg_u16(a, BASE[i]) == base && mu_prg_u16(a, ADD[i]) == add && w->shown[2 * i] == base &&
            w->shown[2 * i + 1] == add)
            continue;
        mu_prg_emitf(e, "call 00b3e773 %x %x", (uint32_t)ROW[i], (uint32_t)(int32_t)(int16_t)base);
        mu_prg_emitf(e, "call 00b3e935 %x %x", (uint32_t)ROW[i], (uint32_t)(int32_t)(int16_t)add);
        mu_prg_emitf(e, "call 00b3e2ed %x", (uint32_t)ROW[i]);
        mu_prg_set16(a, BASE[i], base);
        mu_prg_set16(a, ADD[i], add);
        w->total[i] = (uint16_t)(mu_prg_u16(a, BASE[i]) + mu_prg_u16(a, ADD[i]));
    }
    float rate;
    memcpy(&rate, p + 0x18, sizeof rate);
    if (!(w->rate == rate)) {
        mu_prg_emitf(e, "call 00b3e3d5 39 %08x", fbits(rate));
        mu_prg_emitf(e, "call 00b3e2a4 39");
    }
    mu_prg_emitf(e, "call 00a00fb7");
    mu_prg_emitf(e, "invoke UpdateScorllList [3]");
    w->dirty = 1;
    return 1;
}
