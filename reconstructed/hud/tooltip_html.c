/* Reconstructed GFx tooltip assembly (see tooltip_html.h). */
#include "tooltip_html.h"

#include <string.h>

static const char *const COLORS[22] = {
    "#FFFFFF", "#7FB2FF", "#FF3319", "#FFCC19", "#19FF7F", "#A00000", "#FF19FF", "#0000A0", "#A06600", "#00FF00",
    "#666666", "#CC7FCC", "#B266FF", "#E56B0A", "#800080", "#FFFF00", "#00B0F0", "#00B050", "#CCFF00", "#00FFFF",
    "#BCBCBC", "#C1C469"};

const char *mu_tooltip_color_hex(int32_t color)
{
    if (color < 0 || color > 21)                       /* unsigned compare: ja default */
        return "#FFFFFF";
    return COLORS[color];
}

typedef struct sbuf {
    char *out;
    size_t cap, len;
} sbuf;

static void put(sbuf *b, const char *s, size_t n)
{
    for (size_t i = 0; i < n; i++, b->len++)
        if (b->len + 1 < b->cap)
            b->out[b->len] = s[i];
    if (b->cap)
        b->out[b->len < b->cap ? b->len : b->cap - 1] = 0;
}

static void puts_(sbuf *b, const char *s)
{
    put(b, s, strlen(s));
}

static void put_escaped(sbuf *b, const char *text)
{
    for (const char *p = text; *p; p++) {
        if (*p == '<')
            puts_(b, "&lt;");
        else
            put(b, p, 1);
    }
}

size_t mu_tooltip_html_line(char *out, size_t cap, const char *text, int32_t color, int32_t bold)   /* 0x00ab4dc0 */
{
    sbuf b = {out, cap, 0};
    if (cap)
        out[0] = 0;
    if (text[0] == 0 || strcmp(text, "\n") == 0)
        return 0;
    puts_(&b, "<font color='");
    puts_(&b, mu_tooltip_color_hex(color));
    puts_(&b, (bold & 0xff) == 1 ? "'><b>" : "'>");
    put_escaped(&b, text);
    puts_(&b, (bold & 0xff) == 1 ? "</b></font><br>" : "</font><br>");
    return b.len;
}

#define STAR_ON "<img src = 'icon_star01' align = 'center' width = '13' height = '13'>"
#define STAR_OFF "<img src = 'icon_star00' align = 'center' width = '13' height = '13'>"

size_t mu_tooltip_html(char *out, size_t cap, const mu_tooltip_line *lines, int32_t count, int *bad_star)   /* 0x00b8d94b */
{
    sbuf b = {out, cap, 0};
    if (cap)
        out[0] = 0;
    if (bad_star)
        *bad_star = 0;
    for (int32_t i = 0; i < count; i++) {
        const char *t = lines[i].text;
        if (t[0] == 0)
            continue;
        if (t[0] == '\n') {
            puts_(&b, "<BR>");
            continue;
        }
        if (lines[i].raw == 1) {
            puts_(&b, t);
            continue;
        }
        if (strstr(t, "starGrade*")) {
            char last = t[strlen(t) - 1];
            int n = 0;
            if (last >= '0' && last <= '9')
                n = last - '0';
            else if (bad_star)
                *bad_star = 1;
            puts_(&b, " ");
            for (int k = 0; k < n; k++)
                puts_(&b, STAR_ON);
            for (int k = n; k < 5; k++)
                puts_(&b, STAR_OFF);
            puts_(&b, " ");
            puts_(&b, "<br>");
            continue;
        }
        size_t need = mu_tooltip_html_line(NULL, 0, t, lines[i].color, 0);
        char tmp[4096];
        if (need < sizeof tmp) {
            mu_tooltip_html_line(tmp, sizeof tmp, t, lines[i].color, 0);
            puts_(&b, tmp);
        }
    }
    return b.len;
}

void mu_tooltip_popup_rect(float px, float py, const int32_t rect[4], float rate_x, float rate_y, int32_t out[4])
{
    out[0] = (int32_t)(px / rate_x);
    out[1] = (int32_t)(py / rate_y);
    out[2] = (int32_t)((float)(rect[2] - rect[0]) / rate_x);
    out[3] = (int32_t)((float)(rect[3] - rect[1]) / rate_y);
}

size_t mu_latin1_to_utf8(char *out, size_t cap, const char *text)
{
    sbuf b = {out, cap, 0};
    if (cap)
        out[0] = 0;
    for (const unsigned char *p = (const unsigned char *)text; *p; p++) {
        if (*p < 0x80) {
            char c = (char)*p;
            put(&b, &c, 1);
        } else {
            char two[2] = {(char)(0xc0 | (*p >> 6)), (char)(0x80 | (*p & 0x3f))};
            put(&b, two, 2);
        }
    }
    return b.len;
}
