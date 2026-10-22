/* The hero's skills in the native client (NATIVE-SKILL-001); see mu_skill.h. */
#include "mu_skill.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/hud/tooltip_html.h"
#include "mu_data.h"
#include "mu_lang.h"
#include "mu_ui_font.h"

struct mu_skill_book {
    const mu_lang *lang;
    mu_skill_table table;
    mu_skill_tip_text *tips;          /* SkillTooltipText records by skill (the first of a key) */
    size_t ntips;
    mu_skill_env env;
    mu_skill_hero hero;
    mu_skill_hotkeys hotkeys;
    mu_skill_bar bar;
    int32_t delays[MU_SKILL_LEARNED]; /* the delay each running timer started with (the window overlay) */
    mu_ui_font font;                  /* the wrap's GetTextExtentPointA (layer choice: GlobalText[0], height 12) */
    int font_open;
    float screen_rate;                /* [0x06fbcd94] */
};

/* ---- loading ---------------------------------------------------------------------------------------- */

static void from_lang(const mu_lang_skill *s, mu_skill_record *r)
{
    memset(r, 0, sizeof *r);
    r->skip = s->skip;
    r->index = s->index;
    snprintf(r->name, sizeof r->name, "%s", s->name ? s->name : "");
    r->level = s->level;
    r->damage = s->damage;
    r->mana = s->mana;
    r->ag = s->ag;
    r->distance = s->distance;
    r->delay = s->delay;
    r->req_strength = s->req[0];      /* +0x3c */
    r->req_dexterity = s->req[1];     /* +0x40 */
    r->req_energy = s->req[2];        /* +0x44 */
    r->req_command = s->req[3];       /* +0x48 */
    r->req_vitality = s->req[4];      /* +0x4c */
    r->mastery = s->mastery;
    r->use_type = s->use_type;
    r->brand = s->brand;
    r->master_factor = s->master_bonus;
    r->icon = s->icon;
    r->type = s->type;
}

/* skills_ext.tsv (scripts/live_lang_to_plain.py): index then the columns the record has besides skills.tsv. */
static void load_ext(mu_skill_book *b, const char *dir)
{
    if (!dir)
        return;
    char path[4096];
    snprintf(path, sizeof path, "%s/skills_ext.tsv", dir);
    FILE *f = fopen(path, "r");
    if (!f)
        return;
    char line[1024];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n')
            continue;
        long v[21];
        int n = 0;
        char *p = line, *end;
        while (n < 21) {
            v[n] = strtol(p, &end, 10);
            if (end == p)
                break;
            n++;
            p = end;
        }
        if (n != 21)
            continue;
        mu_skill_record *r = (mu_skill_record *)mu_skill_table_get(&b->table, (int32_t)v[0]);
        if (!r)
            continue;
        r->x54 = (int32_t)v[1];
        r->x60 = (int32_t)v[2];
        r->x74 = (int32_t)v[3];
        r->x78 = (int32_t)v[4];
        r->master_factor = (int32_t)v[5];
        r->x80 = (int32_t)v[6];
        r->x84 = (int32_t)v[7];
        r->x88 = (int32_t)v[8];
        r->x94 = (uint8_t)v[9];
        r->x98 = (int32_t)v[10];
        r->x9c = (int32_t)v[11];
        r->xa0 = (int32_t)v[12];
        r->xa4 = (int32_t)v[13];
        r->xa8 = (int32_t)v[14];
        r->xac = (int32_t)v[15];
        r->xb0 = (int32_t)v[16];
        r->weapon = (int32_t)v[17];
        r->imprint = (int32_t)v[18];
        r->xc8 = (uint8_t)v[19];
        r->damage_type = (int32_t)v[20];
    }
    fclose(f);
}

static int tip_cmp(const void *a, const void *b)
{
    const mu_skill_tip_text *x = a, *y = b;
    return (int)x->skill - (int)y->skill;
}

/* SkillTooltipText.bmd through the loader 0x0117d758's map insert (the first record of a skill stays). */
static void load_tips(mu_skill_book *b, const char *game_root)
{
    if (!game_root)
        return;
    static const char *const names[] = {"Data/Local/skilltooltiptext.bmd", "Data/Local/SkillTooltipText.bmd"};
    mu_data_table t;
    memset(&t, 0, sizeof t);
    int ok = 0;
    for (size_t i = 0; i < sizeof names / sizeof names[0] && !ok; i++) {
        char path[4096];
        snprintf(path, sizeof path, "%s/%s", game_root, names[i]);
        ok = mu_data_load(path, mu_data_find("skilltooltiptext.bmd"), &t) == 0 && t.result.status == MU_DATA_OK;
        if (!ok)
            mu_data_free(&t);
    }
    if (!ok || t.size < 4)
        return;
    uint32_t count = (uint32_t)t.bytes[0] | (uint32_t)t.bytes[1] << 8 | (uint32_t)t.bytes[2] << 16 |
                     (uint32_t)t.bytes[3] << 24;
    if ((size_t)count * 808 + 4 > t.size)
        count = (uint32_t)((t.size - 4) / 808);
    b->tips = calloc(count ? count : 1, sizeof *b->tips);
    for (uint32_t i = 0; b->tips && i < count; i++) {
        mu_skill_tip_text rec;
        mu_skill_tip_text_decode(t.bytes + 4 + (size_t)i * 808, &rec);
        int dup = 0;
        for (size_t k = 0; k < b->ntips && !dup; k++)
            dup = b->tips[k].skill == rec.skill;
        if (!dup)
            b->tips[b->ntips++] = rec;
    }
    qsort(b->tips, b->ntips, sizeof *b->tips, tip_cmp);
    mu_data_free(&t);
}

mu_skill_book *mu_skill_book_open(const mu_lang *lang, const char *lang_dir, const char *game_root)
{
    mu_skill_book *b = calloc(1, sizeof *b);
    if (!b)
        return NULL;
    b->lang = lang;
    for (size_t i = 0; lang && i < mu_lang_skill_count(lang); i++) {
        mu_skill_record r;
        from_lang(mu_lang_skill_at(lang, i), &r);
        mu_skill_table_add(&b->table, &r);
    }
    load_ext(b, lang_dir);
    load_tips(b, game_root);
    b->env.table = &b->table;
    b->screen_rate = 1.0f;
    b->env.class_index = 1;
    b->hero.class_index = 1;
    const char *face = lang ? mu_lang_text(lang, 0) : NULL;
    b->font_open = mu_ui_font_open(&b->font, face && face[0] ? face : "Arial", 12, 400) == 0;
    return b;
}

void mu_skill_book_close(mu_skill_book *b)
{
    if (!b)
        return;
    mu_skill_table_free(&b->table);
    free(b->tips);
    if (b->font_open)
        mu_ui_font_close(&b->font);
    free(b);
}

size_t mu_skill_book_count(const mu_skill_book *b) { return b ? b->table.count : 0; }
size_t mu_skill_book_tooltips(const mu_skill_book *b) { return b ? b->ntips : 0; }

const mu_skill_record *mu_skill_book_record(const mu_skill_book *b, int32_t skill)
{
    return b ? mu_skill_table_get(&b->table, skill) : NULL;
}

void mu_skill_book_set_stats(mu_skill_book *b, const mu_skill_stats *s)
{
    if (!b || !s)
        return;
    b->env.class_index = s->class_byte & 0xf;     /* 0x0095f5cc */
    b->hero.class_index = b->env.class_index;
    b->hero.strength = s->strength;
    b->hero.agility = s->agility;
    b->hero.vitality = s->vitality;
    b->hero.energy = s->energy;
    b->hero.command = s->command;
    b->hero.mana = s->mana;
    b->hero.ag = s->ag;
}

/* ---- the learned list (DEMO) ------------------------------------------------------------------------ */

int mu_skill_book_learn(mu_skill_book *b, int32_t skill)
{
    if (!b || b->hero.count >= MU_SKILL_LEARNED || !mu_skill_table_get(&b->table, skill))
        return 0;
    for (int i = 0; i < b->hero.count; i++)
        if (b->hero.skills[i] == skill)
            return 0;
    b->hero.skills[b->hero.count] = (uint16_t)skill;
    b->hero.timers[b->hero.count] = 0;
    b->hero.count++;
    return 1;
}

/* DEMO lists (skill indices of the classic classes; the server sends the real list). */
static const int32_t DEMO_DW[] = {17, 4, 11, 3, 6, 2, 7, 1, 5, 8, 9, 10, 12, 14, 13, 16, 38, 39, 0};
static const int32_t DEMO_DK[] = {19, 20, 21, 22, 23, 41, 42, 43, 44, 18, 47, 48, 49, 344, 0};
/* the demo hero's bar (Blade Knight): melee skills, Blood Storm (a master skill with a 5 s delay), and wizard
 * skills the combat demo draws, one of them above the hero's energy (Inferno: disabled on the bar) */
static const int32_t DEMO_DK_BAR[MU_SKILL_SLOTS] = {19, 41, 22, 344, 42, 43, 9, 14, 10, 18};
static const int32_t DEMO_ELF[] = {24, 26, 27, 28, 30, 31, 32, 51, 52, 33, 34, 35, 36, 0};
static const int32_t DEMO_ANY[] = {17, 4, 9, 10, 14, 22, 41, 24, 26, 3, 6, 2, 0};

int mu_skill_book_demo(mu_skill_book *b, int32_t class_index)
{
    if (!b)
        return 0;
    b->hero.count = 0;
    memset(&b->hotkeys, 0, sizeof b->hotkeys);
    memset(&b->bar, 0, sizeof b->bar);
    b->bar.dirty = 1;
    const int32_t *list = class_index == 0 ? DEMO_DW : class_index == 1 ? DEMO_DK : class_index == 2 ? DEMO_ELF
                                                                                                  : DEMO_ANY;
    for (const int32_t *p = list; *p; p++)
        mu_skill_book_learn(b, *p);
    if (class_index == 1)       /* the demo hero's bar also gets the wizard skills the combat demo draws */
        for (const int32_t *p = DEMO_ANY; *p; p++)
            mu_skill_book_learn(b, *p);
    int slot = 0;
    if (class_index == 1)
        for (; slot < MU_SKILL_SLOTS; slot++)
            b->hotkeys.slots[slot] = mu_skill_learned_index(&b->hero, DEMO_DK_BAR[slot]) >= 0 ? DEMO_DK_BAR[slot] : 0;
    for (int i = 0; i < b->hero.count && slot < MU_SKILL_SLOTS; i++)
        b->hotkeys.slots[slot++] = b->hero.skills[i];
    b->hero.current = 0;
    b->hotkeys.selected = b->hero.count ? b->hero.skills[0] : 0;
    return b->hero.count;
}

const mu_skill_hero *mu_skill_book_hero(const mu_skill_book *b) { return b ? &b->hero : NULL; }
const mu_skill_hotkeys *mu_skill_book_hotkeys(const mu_skill_book *b) { return b ? &b->hotkeys : NULL; }

/* ---- the bar ---------------------------------------------------------------------------------------- */

int mu_skill_book_usable(const mu_skill_book *b, int32_t skill)
{
    return b && skill && mu_skill_stats_ok(&b->env, &b->hero, skill) && mu_skill_special_ok(&b->env, skill);
}

static int usable_cb(void *user, int32_t skill)
{
    return mu_skill_book_usable(user, skill);
}

int mu_skill_book_feed(mu_skill_book *b, char *json, size_t cap)
{
    if (!b)
        return 0;
    return mu_skill_bar_feed(&b->env, &b->bar, &b->hero, &b->hotkeys, usable_cb, b, json, cap);
}

int mu_skill_book_select_slot(mu_skill_book *b, int slot)
{
    if (!b || slot < 0 || slot >= MU_SKILL_SLOTS)
        return 0;
    return mu_skill_select(&b->env, &b->hero, &b->hotkeys, b->hotkeys.slots[slot]);
}

int32_t mu_skill_book_selected(const mu_skill_book *b) { return b ? b->hotkeys.selected : 0; }

const char *mu_skill_cast_name(int result)
{
    static const char *const names[] = {"ok", "no skill", "requirements", "delay", "mana", "AG"};
    return result >= 0 && result <= MU_SKILL_CAST_AG ? names[result] : "?";
}

int mu_skill_book_cast(mu_skill_book *b, int32_t skill, int32_t events[2][2], int *nevents, int *potion)
{
    if (nevents)
        *nevents = 0;
    if (potion)
        *potion = 0;
    if (!b)
        return MU_SKILL_CAST_NONE;
    int index = mu_skill_learned_index(&b->hero, skill);
    if (index < 0)
        return MU_SKILL_CAST_NONE;
    if (!mu_skill_book_usable(b, skill))
        return MU_SKILL_CAST_UNUSABLE;
    if (!mu_skill_ready(&b->env, &b->hero, index))
        return MU_SKILL_CAST_DELAY;
    int32_t mana = 0, distance = 0, ag = 0;
    if (b->lang)
        mu_lang_skill_info(b->lang, mu_skill_info_skill(skill), 0, &mana, &distance, &ag);
    int short_mana = 0;
    if (!mu_skill_mana_ok(&b->env, &b->hero, skill, skill, mana, ag, &short_mana)) {
        if (potion)
            *potion = short_mana;
        return short_mana ? MU_SKILL_CAST_MANA : MU_SKILL_CAST_AG;
    }
    int32_t local[2][2];
    int n = mu_skill_delay_start(&b->env, &b->hero, skill, events ? events : local);
    for (int i = 0; i < b->hero.count; i++)
        if (b->hero.timers[i] > 0 && b->delays[i] <= 0)
            b->delays[i] = b->hero.timers[i];
    if (nevents)
        *nevents = n;
    /* DEMO: the server takes the mana and AG */
    b->hero.mana -= mana;
    b->hero.ag -= skill == 0x28 || skill == 0x188 ? 0 : ag;
    return MU_SKILL_CAST_OK;
}

void mu_skill_book_tick(mu_skill_book *b, int32_t dt)
{
    if (!b)
        return;
    mu_skill_delay_tick(&b->hero, dt);
    for (int i = 0; i < b->hero.count; i++)
        if (b->hero.timers[i] <= 0)
            b->delays[i] = 0;
}

float mu_skill_book_delay_left(const mu_skill_book *b, int32_t skill)
{
    if (!b)
        return 0.0f;
    int i = mu_skill_learned_index(&b->hero, skill);
    if (i < 0 || b->hero.timers[i] <= 0 || b->delays[i] <= 0)
        return 0.0f;
    return (float)b->hero.timers[i] / (float)b->delays[i];
}

/* ---- tooltip ---------------------------------------------------------------------------------------- */

static const char *tip_text(void *u, int32_t index)
{
    mu_skill_book *b = u;
    return b->lang ? mu_lang_text(b->lang, index) : NULL;
}

static const mu_skill_tip_text *tip_find(void *u, uint16_t skill)
{
    mu_skill_book *b = u;
    mu_skill_tip_text key;
    key.skill = skill;
    return b->ntips ? bsearch(&key, b->tips, b->ntips, sizeof *b->tips, tip_cmp) : NULL;
}

static void tip_info(void *u, int32_t skill, int32_t *mana, int32_t *distance, int32_t *ag)
{
    mu_skill_book *b = u;
    *mana = *distance = *ag = 0;
    if (b->lang)
        mu_lang_skill_info(b->lang, skill, 0, mana, distance, ag);
}

static int32_t tip_measure(void *u, const char *text, int32_t n)
{
    mu_skill_book *b = u;
    if (b->font_open) {
        mu_ui_gdi gdi = mu_ui_font_gdi(&b->font);
        int32_t cx = 0, cy = 0;
        gdi.extent(gdi.user, text, n, &cx, &cy);
        return cx;
    }
    return n * 6;
}

void mu_skill_book_set_screen(mu_skill_book *b, int32_t width)
{
    if (b && width > 0)
        b->screen_rate = (float)width / 640.0f;
}

int mu_skill_book_tooltip_lines(mu_skill_book *b, int32_t skill, mu_skill_tip *out)
{
    if (!b || !out)
        return 0;
    mu_skill_tip_env env;
    memset(&env, 0, sizeof env);
    env.skills = &b->env;
    env.user = b;
    env.text = tip_text;
    env.tip = tip_find;
    env.info = tip_info;
    env.measure = tip_measure;
    env.text_scale = b->screen_rate;
    mu_skill_tip_input in;
    memset(&in, 0, sizeof in);
    in.base = skill;
    in.learned = mu_skill_learned_index(&b->hero, skill) >= 0 ? skill : 0;
    in.weapon_index = -1;
    in.strength = b->hero.strength;
    in.agility = b->hero.agility;
    in.vitality = b->hero.vitality;
    in.energy = b->hero.energy;
    in.command = b->hero.command;
    const mu_skill_record *r = mu_skill_table_get(&b->table, skill);
    in.skill_damage = r ? r->damage : 0;      /* DEMO: the character machine's skill damage 0x00a01692 */
    return mu_skill_tooltip_build(&env, &in, out);
}

int mu_skill_book_tooltip(mu_skill_book *b, int32_t skill, char *title, size_t title_cap, char *body, size_t body_cap)
{
    static mu_skill_tip tip;
    if (!mu_skill_book_tooltip_lines(b, skill, &tip))
        return 0;
    char *t = malloc(4096), *h = malloc(65536);
    if (!t || !h) {
        free(t);
        free(h);
        return 0;
    }
    mu_skill_tooltip_html(&tip, t, 4096, h, 65536);
    mu_latin1_to_utf8(title, title_cap, t);   /* 0x00a99d93 (CP_ACP taken as Latin-1) */
    mu_latin1_to_utf8(body, body_cap, h);
    free(t);
    free(h);
    return 1;
}

/* ---- icons ------------------------------------------------------------------------------------------ */

int mu_skill_book_icon(const mu_skill_book *b, int32_t skill, mu_skill_icon *out)
{
    if (!b || !skill)
        return 0;
    int learned = mu_skill_learned_index(&b->hero, skill) >= 0;
    return mu_skill_icon_of(&b->env, skill, learned ? skill : 0, mu_skill_book_usable(b, skill), 20.0f, 28.0f, out);
}

const char *mu_skill_icon_file(int32_t bitmap)
{
    switch (bitmap) {      /* the bitmap loads 0x00ed3751 / 0x01820c4f.. (static) */
    case 0x7c40: return "Interface/newui_skill00.jpg";
    case 0x7c43: return "Interface/newui_non_skill00.jpg";
    case 0x7e18: return "Interface/new_Master_Icon.jpg";
    case 0x7e19: return "Interface/new_Master_Icon01.jpg";
    case 0x7e1a: return "Interface/new_Master_Non_Icon.jpg";
    case 0x7e1b: return "Interface/new_Master_Non_Icon01.jpg";
    case 0x7e1c: return "Interface/4th_Skill_Icon.jpg";
    case 0x7e1d: return "Interface/4th_Skill_Non_Icon.jpg";
    default: return NULL;
    }
}

/* ---- the Skill Imprint window ----------------------------------------------------------------------- */

static int learned_pages(const mu_skill_book *b)
{
    int n = b->hero.count;
    return n / 15 + (n % 15 != 0);       /* 0x00c21b0b */
}

void mu_skill_book_stamp_open(mu_skill_book *b, mu_skill_stamp *s)
{
    memset(s, 0, sizeof *s);
    s->page = 1;
    s->pages = b ? learned_pages(b) : 0;
    s->drag_from = s->drag_to = -1;
    if (b)
        memcpy(s->saved, b->hotkeys.slots, sizeof s->saved);
}

int32_t mu_skill_book_stamp_skill(const mu_skill_book *b, const mu_skill_stamp *s, int slot)
{
    if (!b || slot < 0 || slot >= 20)
        return 0;
    if (slot < 5)
        return b->hotkeys.slots[s->select_page * 5 + slot];
    int i = (s->page - 1) * 15 + slot - 5;    /* 0x00c22588 */
    return i >= 0 && i < b->hero.count ? b->hero.skills[i] : 0;
}

int mu_skill_book_stamp_drop(mu_skill_book *b, mu_skill_stamp *s, int from, int to)
{
    if (!b || from < 0 || to < 0 || to >= 10)
        return 0;
    s->drag_from = from;
    s->drag_to = to;
    if (to >= 5)
        return 0;
    int dst = to + s->select_page * 5;
    if (from < 5) {                           /* swap two bar slots (0x01096e15) */
        int src = from + s->select_page * 5;
        int32_t t = b->hotkeys.slots[src];
        b->hotkeys.slots[src] = b->hotkeys.slots[dst];
        b->hotkeys.slots[dst] = t;
        return 1;
    }
    int32_t skill = mu_skill_book_stamp_skill(b, s, from);
    if (!skill)
        return 0;
    if (mu_skill_learned_index(&b->hero, skill) < 0)
        return -1;
    for (int i = 0; i < MU_SKILL_SLOTS; i++)  /* 0x01096c42: the skill leaves its old slot */
        if (b->hotkeys.slots[i] == skill)
            b->hotkeys.slots[i] = 0;
    b->hotkeys.slots[dst] = skill;            /* 0x01096d10 */
    if (b->hotkeys.selected && mu_skill_learned_index(&b->hero, b->hotkeys.selected) < 0)
        b->hotkeys.selected = 0;
    return 1;
}

void mu_skill_book_stamp_cancel(mu_skill_book *b, const mu_skill_stamp *s)
{
    if (b && s)
        memcpy(b->hotkeys.slots, s->saved, sizeof s->saved);   /* 0x01096dd0 */
}
