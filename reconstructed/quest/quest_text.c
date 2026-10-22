/* The quest condition and reward texts (0x00fe1a52, 0x00fe1e92) and the HTML line 0x0096fe90
 * (NATIVE-QUEST-001); see quest.h. */
#include "quest_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define COLOR_COMPLETE 0xff67bfdfu        /* 0x00fe1b0f */
#define COLOR_PROGRESS 0xff1e1effu        /* 0x00fe1b1b */

void mu_quest_sprintf(char *out, size_t cap, const char *fmt, const mu_qarg *args, int nargs)
{
    size_t n = 0;
    int k = 0;
    if (!cap)
        return;
    out[0] = 0;
    for (const char *p = fmt ? fmt : ""; *p && n + 1 < cap;) {
        if (*p != '%') {
            out[n++] = *p++;
            continue;
        }
        const char *start = p++;
        if (*p == '%') {
            out[n++] = '%';
            p++;
            continue;
        }
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
        char conv = *p ? *p++ : 0;
        char spec[32];
        size_t sl = (size_t)(p - start);
        if (!conv || sl >= sizeof spec - 2 || !strchr("diuxXcs", conv)) {
            /* not a conversion the model knows: copied as text */
            for (const char *q = start; q < p && n + 1 < cap; q++)
                out[n++] = *q;
            continue;
        }
        /* rebuild the spec without the length letters */
        size_t j = 0;
        for (const char *q = start; q < p - 1; q++)
            if (*q != 'l' && *q != 'h')
                spec[j++] = *q;
        spec[j++] = conv;
        spec[j] = 0;
        char piece[1024];
        const mu_qarg *a = k < nargs ? &args[k] : NULL;
        k++;
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
#endif
        if (conv == 's')
            snprintf(piece, sizeof piece, spec, a && a->is_str && a->s ? a->s : "");
        else if (conv == 'u' || conv == 'x' || conv == 'X')
            snprintf(piece, sizeof piece, spec, (unsigned)(a && !a->is_str ? a->i : 0));
        else
            snprintf(piece, sizeof piece, spec, (int)(a && !a->is_str ? a->i : 0));
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
        for (const char *q = piece; *q && n + 1 < cap; q++)
            out[n++] = *q;
    }
    out[n] = 0;
}

const char *mu_quest_text(const mu_quest_client *c, int32_t index)
{
    const char *t = c && c->host.text ? c->host.text(c->host.user, index) : NULL;
    return t ? t : "";
}

const char *mu_quest_utf8(const mu_quest_client *c, const char *src, char *dst, size_t cap)
{
    if (c && c->host.to_utf8)
        return c->host.to_utf8(c->host.user, src ? src : "", dst, cap);
    snprintf(dst, cap, "%s", src ? src : "");
    return dst;
}

void mu_quest_json(char *out, size_t cap, const char *s)
{
    size_t n = 0;
    if (cap < 3) {
        if (cap)
            out[0] = 0;
        return;
    }
    out[n++] = '"';
    for (const unsigned char *p = (const unsigned char *)(s ? s : ""); *p && n + 8 < cap; p++) {
        if (*p == '"' || *p == '\\') {
            out[n++] = '\\';
            out[n++] = (char)*p;
        } else if (*p < 0x20) {
            n += (size_t)snprintf(out + n, cap - n, "\\u%04x", *p);
        } else {
            out[n++] = (char)*p;
        }
    }
    out[n++] = '"';
    out[n] = 0;
}

static const char *host_npc(const mu_quest_host *h, int32_t npc)
{
    const char *s = h && h->npc_name ? h->npc_name(h->user, npc) : NULL;
    return s ? s : "";
}

static const char *host_map(const mu_quest_host *h, int32_t world)
{
    const char *s = h && h->map_name ? h->map_name(h->user, world) : NULL;
    return s ? s : "";
}

static const char *host_item(const mu_quest_host *h, int32_t code)
{
    const char *s = h && h->item_name ? h->item_name(h->user, code) : NULL;
    return s ? s : "";
}

static const char *host_text(const mu_quest_host *h, int32_t index)
{
    const char *s = h && h->text ? h->text(h->user, index) : NULL;
    return s ? s : "";
}

static void line_empty(const mu_quest_host *h, uint32_t font_default, mu_quest_line *out)
{
    /* 0x00fe4817: {[0x06fc9ca4], 0xff67bfdf, GlobalText 0x551} */
    memset(out, 0, sizeof *out);
    out->font = font_default;
    out->color = COLOR_COMPLETE;
    snprintf(out->text, sizeof out->text, "%s", host_text(h, 0x551));
}

int mu_quest_condition(const mu_quest_host *h, const mu_quest *q, uint32_t font_default, mu_quest_line *out)
{
    line_empty(h, font_default, out);
    if (!q || !q->record)
        return 0;
    const int32_t *g = q->record->goal;
    int32_t group = g[2], index = g[3], cur = q->count, need = g[4];
    out->color = q->state == 2 ? COLOR_COMPLETE : COLOR_PROGRESS;
    char buf[1024];
    buf[0] = 0;
    uint32_t type = (uint32_t)g[1] - 1;
    switch (type) {
    case 0: {                                   /* item: the item's name, GlobalText 0x1244 */
        mu_qarg a[4] = {{1, 0, host_item(h, group * 0x200 + index)}, {1, 0, host_text(h, 0x1244)},
                        {0, cur, NULL}, {0, need, NULL}};
        mu_quest_sprintf(buf, sizeof buf, "%s %s x %d/%d", a, 4);
        break;
    }
    case 1: {                                   /* monster: Npcname of the class, GlobalText 0x1077 */
        mu_qarg a[4] = {{1, 0, host_npc(h, group)}, {1, 0, host_text(h, 0x1077)}, {0, cur, NULL}, {0, need, NULL}};
        mu_quest_sprintf(buf, sizeof buf, "%s %s x %d/%d", a, 4);
        break;
    }
    case 2: {                                   /* level */
        mu_qarg a[2] = {{0, group, NULL}, {1, 0, host_text(h, 0xafc)}};
        mu_quest_sprintf(buf, sizeof buf, "Level: %d %s", a, 2);
        break;
    }
    case 3:
    case 4:
        mu_quest_sprintf(buf, sizeof buf, host_text(h, 0xcb1), NULL, 0);
        break;
    case 5:
        mu_quest_sprintf(buf, sizeof buf, host_text(h, 0x153d), NULL, 0);
        break;
    case 7: {                                   /* hunt in a world */
        mu_qarg a[3] = {{1, 0, host_map(h, g[8])}, {0, cur, NULL}, {0, need, NULL}};
        mu_quest_sprintf(buf, sizeof buf, host_text(h, 0x153c), a, 3);
        break;
    }
    case 6: case 8: case 9: case 10: case 11: case 12: case 13: case 14: case 15: {
        static const int32_t TEXT[16] = {0, 0, 0, 0, 0, 0, 0x153f, 0, 0x153e, 0x1540, 0x1541, 0x1542, 0x1543,
                                         0x1544, 0x1545, 0x1546};
        mu_qarg a[2] = {{0, cur, NULL}, {0, need, NULL}};
        mu_quest_sprintf(buf, sizeof buf, host_text(h, TEXT[type]), a, 2);
        break;
    }
    default:
        out->color = COLOR_COMPLETE;
        snprintf(buf, sizeof buf, "%s", host_text(h, 0x551));
        break;
    }
    snprintf(out->text, sizeof out->text, "%s", buf);
    return 1;
}

static void append(char *dst, size_t cap, const char *s)
{
    size_t n = strlen(dst);
    snprintf(dst + n, cap > n ? cap - n : 0, "%s", s);
}

int mu_quest_reward(const mu_quest_host *h, const mu_quest *q, uint32_t font_default, uint32_t font,
                    mu_quest_line *out)
{
    line_empty(h, font_default, out);
    if (!q || !q->record)
        return 0;
    const int32_t *g = q->record->goal;
    char ss[2048] = "", buf[1024];
    int lines = 0;
    out->font = font;
    out->color = COLOR_COMPLETE;
    if (g[11] > 0) {
        mu_qarg a = {0, MU_QUEST_MUTATION == 2 ? g[12] : g[11], NULL};
        mu_quest_sprintf(buf, sizeof buf, "Exp.: %d", &a, 1);
        append(ss, sizeof ss, buf);
        lines++;
    }
    if (g[12] > 0) {
        if (lines > 0)
            append(ss, sizeof ss, "\n");
        mu_qarg a = {0, g[12], NULL};
        mu_quest_sprintf(buf, sizeof buf, "Zen: %d", &a, 1);
        append(ss, sizeof ss, buf);
        lines++;
    }
    for (int i = 0; i < 3; i++) {
        const int32_t *it = g + 14 + 3 * i;
        if (it[0] < 0 || it[1] < 0)
            continue;
        if (lines > 0)
            append(ss, sizeof ss, "\n");
        int32_t code = it[0] * 0x200 + it[1];
        char name[256];
        snprintf(name, sizeof name, "%s", host_item(h, code));
        int k19 = h && h->item_kind ? h->item_kind(h->user, code, 0x19) : 0;
        int k1a = !k19 && h && h->item_kind ? h->item_kind(h->user, code, 0x1a) : 0;
        int b2c = !k19 && !k1a && h && h->item_byte ? h->item_byte(h->user, code, 0x2c) : 0;
        if (k19 || k1a || b2c) {
            /* an element item: the name with the element of the level (GlobalText 0xe81..0xe85) */
            char named[512];
            if (it[2] >= 1 && it[2] <= 5) {
                mu_qarg a[2] = {{1, 0, name}, {1, 0, host_text(h, 0xe80 + it[2])}};
                mu_quest_sprintf(named, sizeof named, "%s %s", a, 2);
            } else {
                snprintf(named, sizeof named, "%s", name);
            }
            mu_qarg a[3] = {{1, 0, host_text(h, 0x1078)}, {1, 0, named}, {0, it[2], NULL}};
            mu_quest_sprintf(buf, sizeof buf, "%s: %s x %d", a, 3);
        } else {
            int k1 = h && h->item_kind ? h->item_kind(h->user, code, 1) : 0;
            int k3 = !k1 && h && h->item_kind ? h->item_kind(h->user, code, 3) : 0;
            if (k1 || k3) {
                mu_qarg a[3] = {{1, 0, host_text(h, 0x1078)}, {1, 0, name}, {0, it[2], NULL}};
                mu_quest_sprintf(buf, sizeof buf, "%s: %s +%d", a, 3);
            } else {
                /* ItemLevelTooltip in key order: the first record of the code and level names the item */
                int found = 0;
                const mu_quest_data *d = h ? h->data : NULL;
                for (size_t t = 0; d && t < d->nlevel_tips; t++) {
                    const mu_quest_level_tip *lt = &d->level_tips[t];
                    if ((lt->group & 0xffff) * 0x200 + (lt->index & 0xffff) == code && (lt->level & 0xffff) == it[2]) {
                        mu_qarg a[2] = {{1, 0, host_text(h, 0x1078)}, {1, 0, lt->name}};
                        mu_quest_sprintf(buf, sizeof buf, "%s: %s", a, 2);
                        found = 1;
                        break;
                    }
                }
                if (!found) {
                    mu_qarg a[3] = {{1, 0, host_text(h, 0x1078)}, {1, 0, name}, {0, it[2], NULL}};
                    mu_quest_sprintf(buf, sizeof buf, "%s: %s x %d", a, 3);
                }
            }
        }
        append(ss, sizeof ss, buf);
        lines++;
    }
    if (g[13] > 0) {
        if (lines > 0)
            append(ss, sizeof ss, "\n");
        mu_qarg a = {0, g[13], NULL};
        mu_quest_sprintf(buf, sizeof buf, host_text(h, 0xbb2), &a, 1);
        append(ss, sizeof ss, buf);
        lines++;
    }
    snprintf(out->text, sizeof out->text, "%s", ss);
    return 1;
}

void mu_quest_html_line(const char *text, uint32_t color, int bold, int line_break, char *out, size_t cap)
{
    if (!cap)
        return;
    out[0] = 0;
    if (!text || !strcmp(text, "\n") || !*text)
        return;
    /* '<' becomes "&lt;" (0x00970f81 / 0x00971de9 loop) */
    char esc[4096];
    size_t n = 0;
    for (const char *p = text; *p && n + 5 < sizeof esc; p++) {
        if (*p == '<') {
            memcpy(esc + n, "&lt;", 4);
            n += 4;
        } else {
            esc[n++] = *p;
        }
    }
    esc[n] = 0;
    /* ABGR -> RGB, "%06x" */
    uint32_t rgb = ((color & 0xff0000u) >> 16) | (color & 0xff00u) | ((color & 0xffu) << 16);
    char hex[16];
    snprintf(hex, sizeof hex, "%06x", rgb);
    if (bold == 1)
        snprintf(out, cap, "<font color='#%s'><b>%s</b></font>", hex, esc);
    else
        snprintf(out, cap, "<font color='#%s'>%s</font>", hex, esc);
    if (line_break == 1)
        append(out, cap, "<BR>");
}
