/* The skill tooltip (NATIVE-SKILL-001); see skill_tooltip.h. */
#include "skill_tooltip.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../hud/tooltip_html.h"

#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

static int32_t rd32(const uint8_t *p)
{
    return (int32_t)((uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24);
}

static void rdtext(char *out, const uint8_t *p, size_t n)
{
    memcpy(out, p, n);
    out[n - 1] = 0;
}

void mu_skill_tip_text_decode(const uint8_t raw[808], mu_skill_tip_text *out)
{
    memset(out, 0, sizeof *out);
    out->skill = (uint16_t)(raw[0] | raw[1] << 8);
    rdtext(out->name, raw + 0x002, sizeof out->name);
    out->name_color = rd32(raw + 0x104);
    out->condition1 = rd32(raw + 0x108);
    rdtext(out->text1, raw + 0x10c, sizeof out->text1);
    out->color1 = rd32(raw + 0x20c);
    out->condition2 = rd32(raw + 0x210);
    rdtext(out->text2, raw + 0x214, sizeof out->text2);
    out->color2 = rd32(raw + 0x314);
    out->value_a = rd32(raw + 0x318);
    out->value_b = rd32(raw + 0x31c);
    out->value_float = rd32(raw + 0x320);
    out->value_cap = rd32(raw + 0x324);
}

/* ---- formatting ---------------------------------------------------------- */

#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
#endif
size_t mu_skill_format(char *out, size_t cap, const char *fmt, int kind, int32_t ivalue, double fvalue,
                       const char *svalue)
{
    size_t n = 0;
    int used = 0;
#define PUT(c)                         \
    do {                               \
        if (n + 1 < cap)               \
            out[n] = (char)(c);        \
        n++;                           \
    } while (0)
    for (const char *p = fmt ? fmt : ""; *p;) {
        if (*p != '%') {
            PUT(*p++);
            continue;
        }
        const char *start = p++;
        while (*p && strchr("-+ #0", *p))
            p++;
        while (*p >= '0' && *p <= '9')
            p++;
        if (*p == '.') {
            p++;
            while (*p >= '0' && *p <= '9')
                p++;
        }
        while (*p == 'l' || *p == 'h')
            p++;
        char conv = *p;
        if (!conv)
            break;              /* a lone '%' at the end prints nothing */
        p++;
        char spec[32], piece[512];
        size_t len = (size_t)(p - start);
        if (conv == '%') {
            PUT('%');
            continue;
        }
        if (len >= sizeof spec - 2)
            continue;
        /* the spec without length modifiers */
        size_t k = 0;
        for (const char *q = start; q < p; q++)
            if (*q != 'l' && *q != 'h')
                spec[k++] = *q;
        spec[k] = 0;
        int first = !used;
        used = 1;
        piece[0] = 0;
        switch (conv) {
        case 'd': case 'i': case 'u': case 'x': case 'X': case 'o': case 'c': {
            int32_t v = first && kind == 'i' ? ivalue : 0;
            if (conv == 'u' || conv == 'x' || conv == 'X' || conv == 'o')
                snprintf(piece, sizeof piece, spec, (unsigned)v);
            else
                snprintf(piece, sizeof piece, spec, (int)v);
            break;
        }
        case 'f': case 'F': case 'e': case 'E': case 'g': case 'G':
            snprintf(piece, sizeof piece, spec, first && kind == 'f' ? fvalue : 0.0);
            break;
        case 's':
            snprintf(piece, sizeof piece, spec, first && kind == 's' && svalue ? svalue : "");
            break;
        default:
            break;
        }
        for (const char *q = piece; *q; q++)
            PUT(*q);
    }
    if (cap)
        out[n < cap ? n : cap - 1] = 0;
#undef PUT
    return n;
}
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic pop
#endif

static const char *gtext(const mu_skill_tip_env *env, int32_t index)
{
    const char *t = env->text ? env->text(env->user, index) : NULL;
    return t ? t : "";
}

static void set_line(mu_skill_tip *tip, int line, const char *text)
{
    if (line < 0 || line >= MU_SKILL_TIP_LINES)
        return;
    snprintf(tip->lines[line], MU_SKILL_TIP_WIDTH, "%s", text);
}

static void set_color(mu_skill_tip *tip, int line, int32_t color)
{
    if (line < 0 || line >= MU_SKILL_TIP_LINES)
        return;
    tip->color[line] = color;
    tip->set[line] |= 1;
}

static void set_bold(mu_skill_tip *tip, int line, int32_t bold)
{
    if (line < 0 || line >= MU_SKILL_TIP_LINES)
        return;
    tip->bold[line] = bold;
    tip->set[line] |= 2;
}

/* ---- text wrap ----------------------------------------------------------- */

/* 0x01193941(text, out, width, max_lines, stride, 0). */
static int wrap_piece(const mu_skill_tip_env *env, const char *text, char *out, int32_t width, int max_lines,
                      int stride)
{
    if (!text)
        return 0;
    const char *p = text;
    int32_t total = (int32_t)strlen(text) + 1, cut = 0, wpx = (int32_t)((float)width * env->text_scale);
    int done = 0, line;
    for (line = 0; line < max_lines; line++) {
        int32_t n = 0, w = 0, k = 0;
        while (n < stride) {
            k = 1;                          /* _mbclen (single-byte text) */
            n += k;
            cut += k;
            w = env->measure ? env->measure(env->user, p, n) : n * 6;
            if (cut >= total) {
                done = 1;
                break;
            }
#if MU_SKILL_MUTATION == 8
            if (w > wpx)                             /* planted */
#else
            if (w >= wpx)
#endif
                break;
        }
        n -= k;
        cut -= k;
        memcpy(out, p, (size_t)n);
        out[n] = 0;
        if (done)
            break;
        p += n;
        out += stride;
    }
    return line + 1;
}

int mu_skill_wrap(const mu_skill_tip_env *env, const char *text, int32_t width, char *out, int max_lines, int stride)
{
    if (!out || max_lines <= 0 || stride <= 0 || !text || width < 0x10)
        return 0;
    size_t length = strlen(text);
    if (!length)
        return 0;
    char *buf = malloc(length + 1);
    if (!buf)
        return 0;
    memcpy(buf, text, length + 1);
    int count = 0;
    char *save = NULL;
    for (char *token = strtok_r(buf, "#", &save); token && count < max_lines; token = strtok_r(NULL, "#", &save)) {
        char piece[0x600];
        snprintf(piece, sizeof piece, " %s", token);
        count += wrap_piece(env, piece, out + (size_t)count * (size_t)stride, width, max_lines - count, stride);
    }
    free(buf);
    return count;
}

/* 0x011ffb3a(text, mode, line, color, bold, flag 1): the wrapped lines from `line` on; returns the next line. */
static int put_wrapped(const mu_skill_tip_env *env, mu_skill_tip *tip, const char *text, int line, int32_t color)
{
    if (!text)
        return line;
    /* 10 lines of 0x100 bytes, plus the line a full wrap reports beyond them (zero here) */
    static char lines[11][0x100];
    memset(lines, 0, sizeof lines);
    int count = mu_skill_wrap(env, text, 0x96, &lines[0][0], 10, 0x100);
    for (int i = 0; i < count && i < 11; i++) {
        set_color(tip, line, color);
        set_bold(tip, line, 0);
        /* every '%' is doubled before sprintf(TextList[line], s): the line keeps its text */
        set_line(tip, line, lines[i]);
        line++;
    }
    return line;
}

/* ---- builder ------------------------------------------------------------- */

static int show(int32_t condition, int learned)
{
    switch (condition) {
    case 0: return 1;
    case 1: return learned;
    case 2: return !learned;
    default: return 0;
    }
}

static float master_float(const mu_skill_tip_env *env, int32_t skill)
{
    return env->master_float ? env->master_float(env->user, skill) : 0.0f;
}

static int formula_skill(int32_t skill)
{
    return skill == 0x389 || skill == 0x38a || skill == 0x82a;
}

/* 0x0117eab5(skill, base, text, buf) */
static void value_text(const mu_skill_tip_env *env, const mu_skill_tip_input *in, int32_t skill,
                       const mu_skill_tip_text *t, char *buf, size_t cap)
{
    int32_t stat = (int32_t)in->vitality + (int32_t)in->stat_19c;
    if (t->value_float == 1) {
        float f = 0.0f;
        if (formula_skill(skill) && env->formula)
            f = env->formula(env->user, t->value_a / 10000, t->value_a % 10000, stat);
        if (t->value_b == 0)
            f = master_float(env, skill) + f;
        float v = f;
        if (t->value_cap != -1)
            v = (float)t->value_cap > f ? f : (float)t->value_cap;
        mu_skill_format(buf, cap, t->text1, 'f', 0, (double)v, NULL);
    } else {
        int32_t i = 0;
        if (formula_skill(skill) && env->formula)
            i = (int32_t)env->formula(env->user, t->value_a / 10000, t->value_a % 10000, stat);
        if (t->value_b == 0)
            i = (int32_t)((float)i + master_float(env, skill));
        if (t->value_cap != -1)
            i = i < t->value_cap ? i : t->value_cap;
        mu_skill_format(buf, cap, t->text1, 'i', i, 0.0, NULL);
    }
}

/* The cooldown the tooltip shows (0x0117e16f..0x0117e377). */
static int32_t shown_delay(const mu_skill_tip_env *env, int32_t skill, const mu_skill_record *r)
{
    const mu_skill_env *s = env->skills;
    int32_t delay = r->delay;
    int32_t key = skill;
    if (s && s->tree_map) {
        int32_t mapped = s->tree_map(s->user, s->class_index, skill);
        if (mapped != -1)
            key = mapped;
    }
    if (s && s->tree_node && s->tree_node(s->user, key)) {
        if (s->tree_value && s->tree_value(s->user, key, 0x3fb) == 1)
            delay = 0;
        else {
            int32_t v = s->tree_value ? s->tree_value(s->user, key, 0x3fa) : 0;
            delay = v > delay ? 0 : delay - v;
        }
        return delay;
    }
    if (env->master_is && env->master_is(env->user, skill) && r->type == 1) {
        if (env->master_kind && env->master_kind(env->user, skill) == 2)
            delay -= (int32_t)(master_float(env, skill) * 1000.0f);
        /* else: 0x00bb1f4a(skill, a, b) gets two zero words by value and the loop then reads those same
         * zero locals, so the related skills never subtract anything */
    }
    return delay;
}

int mu_skill_tooltip_build(const mu_skill_tip_env *env, const mu_skill_tip_input *in, mu_skill_tip *out)
{
    memset(out, 0, sizeof *out);
    int32_t skill = in->base;
    int learned = 0;
    if (in->learned) {
        skill = in->learned;
        learned = 1;
    }
    const mu_skill_tip_text *t = env->tip ? env->tip(env->user, (uint16_t)skill) : NULL;
    if (!t)
        return 0;
    const mu_skill_env *s = env->skills;
    const mu_skill_record *r1 = mu_skill_record_of(s, (int16_t)t->skill);
    if (r1->index == 0)
        return 0;
    int32_t base = s && s->base_skill ? s->base_skill(s->user, skill) : skill;
    const mu_skill_record *r2 = mu_skill_record_of(s, base);
    char a[512], b[512], line[1024];
    int n = 0;
    set_color(out, 0, t->name_color);
    if (in->learned == 0x3c && in->weapon_index != -1 && in->weapon_word == 0x42)
        set_line(out, n, gtext(env, 0x4b0));
    else
        set_line(out, n, t->name);
    set_bold(out, n, 1);
    n++;
    int32_t mana = 0, distance = 0, ag = 0;
    if (env->info)
        env->info(env->user, skill, &mana, &distance, &ag);

    /* requirements: "Strength %d / Agility %d / Energy %d / Health %d / Command %d" */
    static const struct { int32_t text; size_t field; } reqs[5] = {
        {0x18c1, offsetof(mu_skill_record, req_strength)}, {0x18c2, offsetof(mu_skill_record, req_dexterity)},
        {0x18c4, offsetof(mu_skill_record, req_energy)},   {0x18c3, offsetof(mu_skill_record, req_vitality)},
        {0x18c5, offsetof(mu_skill_record, req_command)},
    };
    char req[1024] = "";
    int any = 0;
    const char *sep = gtext(env, 0x18c6);
    for (int i = 0; i < 5; i++) {
        int32_t value;
        memcpy(&value, (const char *)r2 + reqs[i].field, sizeof value);
        if (!value)
            continue;
        any = 1;
        mu_skill_format(a, sizeof a, gtext(env, reqs[i].text), 'i', value, 0.0, NULL);
        strncat(req, a, sizeof req - strlen(req) - 1);
        strncat(req, sep, sizeof req - strlen(req) - 1);
    }
    if (any) {
        size_t seplen = strlen(sep);
        if (seplen) {       /* erase the last separator (rfind) */
            for (size_t i = strlen(req) + 1; i-- > 0;)
                if (i + seplen <= strlen(req) && !memcmp(req + i, sep, seplen)) {
                    memmove(req + i, req + i + seplen, strlen(req + i + seplen) + 1);
                    break;
                }
        }
        set_line(out, n, req);
        set_color(out, n, 1);
        if ((int32_t)in->strength < r2->req_strength || (int32_t)in->agility < r2->req_dexterity ||
            (int32_t)in->energy < r2->req_energy || (int32_t)in->vitality < r2->req_vitality ||
            (int32_t)in->command < r2->req_command)
            set_color(out, n, 2);
        n++;
        set_line(out, n, "  ");
        n++;
    }

    /* mana / AG */
    if (!(mana == 0 && r1->ag == 0)) {
        if (mana)
            mu_skill_format(a, sizeof a, gtext(env, 0x12b0), 'i', mana, 0.0, NULL);
        else
            a[0] = 0;
        if (ag)
            mu_skill_format(b, sizeof b, gtext(env, 0x12b1), 'i', ag, 0.0, NULL);
        else
            b[0] = 0;
        snprintf(line, sizeof line, mana == 0 || ag == 0 ? "%s%s" : "%s / %s", a, b);
        set_line(out, n, line);
        set_color(out, n, 1);
        n++;
    }

    /* range / cooldown */
    if (distance)
        mu_skill_format(a, sizeof a, gtext(env, 0x12b2), 'i', distance, 0.0, NULL);
    else
        a[0] = 0;
    int32_t delay = shown_delay(env, skill, r1);
    if (delay)
        mu_skill_format(b, sizeof b, gtext(env, 0x12b3), 'f', 0, (double)((float)delay / 1000.0f), NULL);
    else
        b[0] = 0;
    snprintf(line, sizeof line, distance == 0 || delay == 0 ? "%s%s" : "%s / %s", a, b);
    set_line(out, n, line);
    set_color(out, n, 1);
    n++;

    /* damage and the elemental imprint bonus */
    if (r1->type == 0 || r1->type == 7) {
        int32_t damage = in->skill_damage;
        damage = (int32_t)((float)damage + in->option_13);
        damage = (int32_t)((float)damage + in->option_7e);
        damage += in->damage_bonus;
        mu_skill_format(a, sizeof a, gtext(env, 0x12b4), 'i', damage, 0.0, NULL);
        if (r1->mastery == 0)
            b[0] = 0;
        else if (in->stamped == 1 && in->imprint_level > 0) {
            float x = (float)in->imprint_level * ((float)r1->imprint / 100.0f);
            int32_t v = (int32_t)(float)floor((double)x);
            mu_skill_format(b, sizeof b, gtext(env, 0x12b5), 'i', v, 0.0, NULL);
        } else
            mu_skill_format(b, sizeof b, gtext(env, 0x12b6), 'i', r1->imprint, 0.0, NULL);
        snprintf(line, sizeof line, "%s %s", a, b);
        set_line(out, n, line);
        set_color(out, n, 1);
        n++;
    }

    /* element */
    static const int32_t imprinted[7] = {0x12b7, 0x12a2, 0x12a3, 0x12a4, 0x12a5, 0x12a6, 0x170a};
    static const int32_t plain[7] = {0x12b7, 0xe99, 0xe9a, 0xe9b, 0xe9c, 0xe9d, 0x1709};
    if (r1->mastery >= 0 && r1->mastery <= 6) {
        mu_skill_format(a, sizeof a, gtext(env, in->stamped == 1 ? imprinted[r1->mastery] : plain[r1->mastery]), 0, 0,
                        0.0, NULL);
        set_line(out, n, a);
    }
    set_color(out, n, 1);
    n++;

    /* description and the third text */
    char buf[0x200];
    if (show(t->condition1, learned)) {
        set_line(out, n, "\n");
        n++;
        if (t->value_a == -1 && t->value_b == -1)
            snprintf(buf, sizeof buf, "%s", t->text1);
        else
            value_text(env, in, skill, t, buf, sizeof buf);
        n = put_wrapped(env, out, buf, n, t->color1);
    }
    if (show(t->condition2, learned)) {
        set_line(out, n, "\n");
        n++;
        snprintf(buf, sizeof buf, "%s", t->text2);
        n = put_wrapped(env, out, buf, n, t->color2);
    }
#if MU_SKILL_MUTATION == 5
    if (n > 2)
        n--;                                /* planted: the last line is lost */
#endif
    out->count = n;
    out->mastery = (int32_t)(uint8_t)r1->mastery;
    return 1;
}

void mu_skill_tooltip_html(const mu_skill_tip *tip, char *title, size_t title_cap, char *body, size_t body_cap)
{
    size_t n = 0;
    if (body_cap)
        body[0] = 0;
    for (int i = 1; i < tip->count && i < MU_SKILL_TIP_LINES; i++) {
        const char *text = tip->lines[i];
        if (!text[0])
            continue;
        char piece[2048];
        if (text[0] == '\n')
#if MU_SKILL_MUTATION == 10
            snprintf(piece, sizeof piece, "<br>");   /* planted */
#else
            snprintf(piece, sizeof piece, "<BR>");
#endif
        else
            mu_tooltip_html_line(piece, sizeof piece, text, tip->color[i], 0);
        size_t k = strlen(piece);
        if (n + k + 1 < body_cap) {
            memcpy(body + n, piece, k + 1);
            n += k;
        }
    }
    if (title_cap)
        mu_tooltip_html_line(title, title_cap, tip->count > 0 ? tip->lines[0] : "", tip->color[0], 0);
}
