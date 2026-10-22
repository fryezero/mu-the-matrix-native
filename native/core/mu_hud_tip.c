/* Item tooltip text, see mu_hud_tip.h (moved from tools/mu_render_hud.c in
 * NATIVE-GFX-002 unchanged, so the GFx layer and mu-render share it). */
#include "mu_hud_tip.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/hud/tooltip_format.h"
#include "../../reconstructed/hud/tooltip_html.h"

void mu_hud_tip_tables_load(const char *root, mu_hud_tip_tables *t)
{
    memset(t, 0, sizeof *t);
    if (!root)
        return;
    char path[4096];
    snprintf(path, sizeof path, "%s/Data/Local/item.bmd", root);
    t->have_items = mu_data_load(path, NULL, &t->items) == 0 && t->items.result.status == 0;
    snprintf(path, sizeof path, "%s/Data/Local/itemtooltip.bmd", root);
    t->have_tooltip = mu_data_load(path, NULL, &t->tooltip) == 0;
    snprintf(path, sizeof path, "%s/Data/Local/itemtooltiptext.bmd", root);
    t->have_text = mu_data_load(path, NULL, &t->text) == 0;
}

void mu_hud_tip_tables_free(mu_hud_tip_tables *t)
{
    if (t->have_items)
        mu_data_free(&t->items);
    if (t->have_tooltip)
        mu_data_free(&t->tooltip);
    if (t->have_text)
        mu_data_free(&t->text);
}

static int16_t s16(const uint8_t *p) { return (int16_t)(p[0] | p[1] << 8); }

static const uint8_t *tooltip_record(const mu_hud_tip_tables *t, int32_t code)
{
    if (!t->have_tooltip)
        return NULL;
    for (size_t i = 0; (i + 1) * 136 <= t->tooltip.size; i++) {
        const uint8_t *r = t->tooltip.bytes + i * 136;
        if (r[4] == 0)
            break;
        if (((int32_t)r[0] << 9) + s16(r + 2) == code)
            return r;
    }
    return NULL;
}

static const uint8_t *tooltip_text(const mu_hud_tip_tables *t, int32_t id)
{
    if (!t->have_text || t->text.size < 4)
        return NULL;
    uint32_t n = (uint32_t)t->text.bytes[0] | (uint32_t)t->text.bytes[1] << 8 | (uint32_t)t->text.bytes[2] << 16 |
                 (uint32_t)t->text.bytes[3] << 24;
    for (uint32_t i = 0; i < n && 4 + (size_t)(i + 1) * 260 <= t->text.size; i++) {
        const uint8_t *r = t->text.bytes + 4 + (size_t)i * 260;
        if ((r[0] | r[1] << 8) == id)
            return r;
    }
    return NULL;
}
const char *mu_hud_tip_text(const mu_hud_tip_tables *t, uint16_t id) {
    const uint8_t *r = t ? tooltip_text(t, id) : NULL;
    return r && memchr(r + 2, 0, 256) ? (const char *)(r + 2) : NULL;
}

static void add_line(mu_hud_tip *tp, const char *text, int32_t color)
{
    if (tp->count >= MU_HUD_TIP_LINES)
        return;
    snprintf(tp->text[tp->count], sizeof tp->text[0], "%s", text);
    tp->color[tp->count++] = color;
}

/* The table-driven part of the builder 0x00f0eb44: name line, then up to 15
 * configured lines through the formatter cases.  Not reconstructed (and not
 * drawn): the runtime-patched header (0x00f0edf1) and GlobalText lines, price,
 * set/socket/excellent/harmony blocks and the full name-colour rules. */
void mu_hud_tip_build(const mu_hud_tip_tables *t, const mu_hud_item *it, const int hero[4], mu_hud_tip *tp)
{
    mu_hud_tip_build_durability(t,it,hero,it->durability,tp);
}
void mu_hud_tip_build_durability(const mu_hud_tip_tables *t,const mu_hud_item *it,const int hero[4],
                                uint8_t maximum,mu_hud_tip *tp)
{
    memset(tp, 0, sizeof *tp);
    mu_ttf_item item = {it->durability, maximum, 0, 0, 0, 0};
    mu_ttf_inputs in;
    memset(&in, 0, sizeof in);
    in.hero_strength = (uint16_t)hero[0];
    in.hero_agility = (uint16_t)hero[1];
    in.hero_energy = (uint16_t)hero[2];
    in.hero_level = hero[3];
    in.manager_1c = -1;
    if (it->has_record) {
        const mu_item_attributes *a = &it->record.attributes;
        item.defense = a->defense;
        item.magic_power = (int32_t)a->magic_power;
        item.attack_speed = a->attack_speed;
        in.req_strength = a->require_strength;           /* base values: the level formula 0x00ccf659 is not reconstructed */
        in.req_agility = a->require_dexterity;
        in.req_energy = a->require_energy;
        in.req_level = a->require_level;
        in.kind_a_3 = a->kind_a == 3;
    }
    const uint8_t *rec = tooltip_record(t, it->code);
    char name[160];
    if (rec && s16(rec + 0x4a) == -1 && it->has_record)
        snprintf(name, sizeof name, "%s", it->record.name);
    else if (rec)
        snprintf(name, sizeof name, "%.64s", (const char *)rec + 4);
    else
        snprintf(name, sizeof name, "%s", it->name);
    if ((!rec || rec[0x48]) && it->level > 0) {
        size_t n = strlen(name);
        snprintf(name + n, sizeof name - n, " +%d", it->level);
    }
    add_line(tp, name, rec ? rec[0x44] : 3);
    if (!rec) {
        static const struct { int32_t type; const char *fmt; } SYN[] = {
            {4, "Dur [%d/%d]"}, {5, "Lv %d"}, {6, "Str %d"}, {202, "(need %d str)"}, {101, "Speed %d"}};
        for (size_t k = 0; k < sizeof SYN / sizeof SYN[0]; k++) {
            char out[0x100];
            int32_t color = 0, tc[MU_HUD_TIP_LINES] = {0};
            if (mu_tooltip_format(out, SYN[k].fmt, SYN[k].type, &item, it->level, &in, tp->count, &color, tc) == 0 &&
                out[0])
                add_line(tp, out, color);
        }
        return;
    }
    tp->from_tables = 1;
    for (int i = 0; i < 15; i++) {
        int32_t id = s16(rec + 0x4c + 4 * i);
        const uint8_t *tr = tooltip_text(t, id);
        if (!tr)
            break;                                      /* the builder stops at the first missing text */
        int32_t color = rec[0x4e + 4 * i], type = s16(tr + 0x102);
        char fmt[257];
        memcpy(fmt, tr + 2, 256);
        fmt[256] = 0;
        if (type == -1) {
            add_line(tp, fmt, color);
            continue;
        }
        char out[0x100];
        int32_t tc[MU_HUD_TIP_LINES + 1];
        for (int k = 0; k < tp->count; k++)
            tc[k] = tp->color[k];
        if (mu_tooltip_format(out, fmt, type, &item, it->level, &in, tp->count, &color, tc) != 0) {
            tp->unsupported++;
            continue;
        }
        for (int k = 0; k < tp->count; k++)
            tp->color[k] = tc[k];
        if (out[0])
            add_line(tp, out, color);
    }
}

size_t mu_hud_tip_html(const mu_hud_tip *tp, char *utf8, size_t cap)
{
    mu_tooltip_line lines[MU_HUD_TIP_LINES];
    for (int i = 0; i < tp->count; i++)
        lines[i] = (mu_tooltip_line){tp->text[i], tp->color[i], 0, 0};
    size_t n = mu_tooltip_html(NULL, 0, lines, tp->count, NULL);
    char *html = malloc(n + 1);
    if (!html) {
        if (cap)
            utf8[0] = 0;
        return 0;
    }
    mu_tooltip_html(html, n + 1, lines, tp->count, NULL);
    size_t r = mu_latin1_to_utf8(utf8, cap, html);
    free(html);
    return r;
}
