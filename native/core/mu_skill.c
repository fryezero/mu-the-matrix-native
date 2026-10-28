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
    mu_skill_hotkeys hotkeys;         /* the bar's view of the hotkey manager (mu_skill_keys_hotkeys) */
    mu_skill_keys keys;               /* the hotkey manager 0x01d1df5c */
    mu_skill_stamp_mgr stamp;         /* the Skill Imprint manager [0x01d1dbcc] */
    int has_classes;                  /* skills_class.tsv gave the records' class maps (+0x6c) */
    int32_t class_byte;               /* attributes +0x187 */
    mu_skill_bar bar;
    int32_t delays[MU_SKILL_LEARNED]; /* the delay each running timer started with (the window overlay) */
    mu_ui_font font;                  /* the wrap's GetTextExtentPointA (layer choice: GlobalText[0], height 12) */
    int font_open;
    float screen_rate;                /* [0x06fbcd94] */
    mu_skill_use_env use;
    mu_master_tree master;
    mu_master_env menv;
    mu_master_node *nodes;
    mu_master_tip *master_tips;
    int nnodes, nmaster_tips;
    mu_master_formula_fn formula;
    void *formula_user;
    int (*buff)(void *user, int list, int32_t id);
    void *buff_user;
};

static const char *tip_text(void *u, int32_t index);
static float master_value(void *u, int32_t skill, int32_t flag)
{
    mu_skill_book *b = u;
    return mu_master_chain(&b->master, &b->env, skill, flag);
}
static int master_delay(void *u, int32_t skill) { (void)u; return mu_master_is_master(skill); }
static int32_t master_base(void *u, int32_t skill)
{
    mu_skill_book *b = u;
    return mu_skill_master_base(&b->env, skill);
}
static int hero_buff(void *u, int list, int32_t id)
{
    const mu_skill_book *b = u;
    return b->buff ? b->buff(b->buff_user, list, id) : 0;
}
int mu_skill_book_requirement(mu_skill_book *b, int32_t base, int32_t *skill, int32_t *master, int32_t *level)
{
    const mu_lang_skillreq *r = b ? mu_lang_skillreq_get(b->lang, base) : NULL;
    if (!r || !r->skill)
        return 0;
    *skill = r->x10;
    *master = r->x14;
    *level = r->x18;
    return 1;
}
static int default_requirement(void *u, int32_t base, int32_t *skill, int32_t *master, int32_t *level)
{
    return mu_skill_book_requirement(u, base, skill, master, level);
}
static int default_level(void *u, int32_t skill)
{
    mu_skill_book *b = u;
    return mu_master_level(&b->master, skill);
}

/* The existing fixed-table codec checks the checksum before either table reaches the tree. */
static void load_master(mu_skill_book *b, const char *root)
{
    if (!root)
        return;
    const char *names[] = {"masterskilltreedata.bmd", "masterskilltooltip.bmd"};
    for (int kind = 0; kind < 2; kind++) {
        char path[4096];
        snprintf(path, sizeof path, "%s/Data/Local/%s", root, names[kind]);
        mu_data_table data = {0};
        if (mu_data_load(path, mu_data_find(names[kind]), &data) == 0 && data.result.status == MU_DATA_OK) {
            size_t stride = kind ? 808 : 24;
            int count = (int)(data.size / stride);
            if (count > 2048)
                count = 2048;
            if (kind) {
                b->master_tips = calloc((size_t)count, sizeof *b->master_tips);
                if (b->master_tips) {
                    b->nmaster_tips = count;
                    for (int i = 0; i < count; i++)
                        mu_master_tip_decode(data.bytes + (size_t)i * stride, &b->master_tips[i]);
                }
            } else {
                b->nodes = calloc((size_t)count, sizeof *b->nodes);
                if (b->nodes) {
                    b->nnodes = count;
                    for (int i = 0; i < count; i++)
                        mu_master_node_decode(data.bytes + (size_t)i * stride, &b->nodes[i]);
                }
            }
        }
        mu_data_free(&data);
    }
}

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

/* skills_class.tsv (scripts/live_lang_to_plain.py over a langread snapshot taken with nested:0x6d8): index, the
 * class map +0x6c (class index 0..15) and the ranks +0x64 (keys 0x80, 0x40, 0x20). */
static void load_classes(mu_skill_book *b, const char *dir)
{
    if (!dir)
        return;
    char path[4096];
    snprintf(path, sizeof path, "%s/skills_class.tsv", dir);
    FILE *f = fopen(path, "r");
    if (!f)
        return;
    char line[1024];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n')
            continue;
        long v[20];
        int n = 0;
        char *p = line, *end;
        while (n < 20) {
            v[n] = strtol(p, &end, 10);
            if (end == p)
                break;
            n++;
            p = end;
        }
        mu_skill_record *r = n == 20 ? (mu_skill_record *)mu_skill_table_get(&b->table, (int32_t)v[0]) : NULL;
        if (!r)
            continue;
        for (int i = 0; i < 16; i++)
            r->classes[i] = (int32_t)v[1 + i];
        for (int i = 0; i < 3; i++)
            r->rank[i] = (int32_t)v[17 + i];
        b->has_classes = 1;
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
    load_classes(b, lang_dir);
    load_tips(b, game_root);
    load_master(b, game_root);
    b->env.table = &b->table;
    b->env.user = b;
    b->env.master_has_delay = master_delay;
    b->env.base_skill = master_base;
    b->env.master_value = master_value;
    b->env.buff = hero_buff;
    b->menv.skills = &b->env;
    b->menv.user = b;
    b->menv.text = tip_text;
    mu_skill_book_set_use_state(b, NULL);
    b->screen_rate = 1.0f;
    b->env.class_index = 1;
    b->hero.class_index = 1;
    mu_skill_stamp_init(&b->stamp);
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
    free(b->nodes);
    free(b->master_tips);
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

void mu_skill_book_set_use_state(mu_skill_book *b, const mu_skill_use_env *state)
{
    if (!b)
        return;
    if (state)
        b->use = *state;
    else {
        memset(&b->use, 0, sizeof b->use);
        b->use.transform = 0xffff;
        b->use.user = b;
        b->use.skill_require = default_requirement;
        b->use.master_level = default_level;
        for (int i = 0; i < 15; i++)
            b->use.items[i].code = -1;
    }
    b->buff = state && state->skills ? state->skills->buff : NULL;
    b->buff_user = state && state->skills ? state->skills->user : NULL;
    b->use.skills = &b->env;
}

void mu_skill_book_set_elemental(mu_skill_book *b, int32_t elemental)
{
    if (b) {
        b->hero.elemental = elemental;
        mu_skill_stamp_refresh(&b->env, &b->stamp, elemental);
    }
}

const mu_skill_env *mu_skill_book_env(const mu_skill_book *b) { return b ? &b->env : NULL; }
mu_master_tree *mu_skill_book_master(mu_skill_book *b) { return b ? &b->master : NULL; }
mu_master_env *mu_skill_book_master_env(mu_skill_book *b) { return b ? &b->menv : NULL; }

void mu_skill_book_set_formula(mu_skill_book *b, mu_master_formula_fn formula, void *user)
{
    if (b) {
        b->formula = formula;
        b->formula_user = user;
    }
}

double mu_skill_book_formula(mu_skill_book *b, int group, int id, int argument)
{
    return b && b->formula ? b->formula(b->formula_user, group, id, argument) : 0.0;
}

void mu_skill_book_master_build(mu_skill_book *b)
{
    if (!b)
        return;
    mu_master_build(&b->master, &b->menv, b->nodes, b->nnodes, b->master_tips, b->nmaster_tips);
    mu_master_set_text(&b->master, &b->menv, 0x7f);
    if (b->menv.invoke)
        for (int i = 0; i < b->master.nnodes; i++) {
            const mu_master_node *n = &b->master.nodes[i];
            char args[64];
            snprintf(args, sizeof args, "%d %d", n->slot, mu_master_level(&b->master, n->skill));
            b->menv.invoke(b->menv.user, "SetRank", args);
        }
}

/* ---- the server's skill packets ----------------------------------------------------------------------- */

static void sync_keys(mu_skill_book *b)
{
    mu_skill_keys_hotkeys(&b->keys, &b->hotkeys);
}

static int usable_cb(void *user, int32_t skill);

static mu_skill_world world_of(mu_skill_book *b)
{
    mu_skill_world w = {&b->env, &b->hero, &b->stamp, &b->keys, usable_cb, b};
    return w;
}

void mu_skill_book_enter(mu_skill_book *b, int32_t class_byte)
{
    if (!b)
        return;
    b->class_byte = class_byte;
    b->env.class_index = class_byte & 0xf;
    b->hero.class_index = b->env.class_index;
    b->hero.count = 0;
    b->hero.current = 0;
    memset(b->hero.skills, 0, sizeof b->hero.skills);
    memset(b->hero.timers, 0, sizeof b->hero.timers);
    memset(b->delays, 0, sizeof b->delays);
    memset(&b->keys, 0, sizeof b->keys);
    memset(&b->bar, 0, sizeof b->bar);
    b->bar.dirty = 1;
    mu_master_init(&b->master);
    int stage = class_byte & 0x80 ? 5 : class_byte & 0x40 ? 4 : class_byte & 0x20 ? 3 : 0;
    if (stage)
        mu_master_class(&b->master, ((stage - 1) << 4) | (class_byte & 0xf));
    b->menv.points = 0;                   /* supplied by the authoritative hero context */
    mu_skill_book_master_build(b);
    /* Layer choice: the client builds the stamp manager in the window's 0x00c2008b (0x01095c77); the native
     * session builds it when the hero enters the world, before the server's packets arrive. */
    mu_skill_stamp_init(&b->stamp);
    mu_skill_stamp_reset(&b->env, &b->stamp, class_byte);
    sync_keys(b);
}

int mu_skill_book_has_classes(const mu_skill_book *b) { return b && b->has_classes; }

void mu_skill_book_allow(mu_skill_book *b, int32_t skill, int32_t class_index)
{
    mu_skill_record *r = b ? (mu_skill_record *)mu_skill_table_get(&b->table, skill) : NULL;
    if (r && class_index >= 0 && class_index < 16)
        r->classes[class_index] = 1;
}

int mu_skill_book_receive(mu_skill_book *b, const uint8_t *p, size_t n)
{
    if (!b || n < 4)
        return 0;
    size_t head = p[0] == 0xc1 || p[0] == 0xc3 ? 2 : 3;     /* C1/C3: one size byte, C2/C4: two */
    if (n < head + 2 || p[head] != 0xa0)
        return 0;
    mu_skill_world w = world_of(b);
    int r = 0;
    if (p[head + 1] == 0x20)
        r = mu_skill_list_receive(&w, p, n, NULL);         /* 0x0126176e */
    else if (p[head + 1] == 0x03)
        r = mu_skill_keys_receive(&w, p, n, NULL);         /* 0x0126f225 (its skill part) */
    else if (p[head + 1] == 0x10)
        r = mu_master_receive_list(&b->master, &b->menv, p, n);
    else if (p[head + 1] == 0x14)
        r = mu_master_receive_learn(&b->master, &b->menv, &w, p, n, 0, &b->menv.points);
    sync_keys(b);
    return r;
}

const mu_skill_stamp_mgr *mu_skill_book_stamp_mgr(const mu_skill_book *b) { return b ? &b->stamp : NULL; }

const mu_skill_hero *mu_skill_book_hero(const mu_skill_book *b) { return b ? &b->hero : NULL; }
const mu_skill_hotkeys *mu_skill_book_hotkeys(const mu_skill_book *b) { return b ? &b->hotkeys : NULL; }

/* ---- the bar ---------------------------------------------------------------------------------------- */

int mu_skill_book_usable(const mu_skill_book *b, int32_t skill)
{
    return b && skill && mu_skill_can_use(&b->use, &b->hero, skill) && mu_skill_special_ok(&b->env, skill);
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
    /* 0x00c70f4b: the slot's stamp entry (its learned skill) in the learned list, the mounted rule, CurrentSkill;
     * then the hotkeys select it (0x00a079d2) */
    mu_skill_hotkeys tmp = b->hotkeys;
    int r = mu_skill_select(&b->env, &b->hero, &tmp, b->hotkeys.slots[slot]);
    if (r)
        mu_skill_keys_follow(&b->env, &b->keys, &b->hero, NULL);
    sync_keys(b);
    return r;
}

int32_t mu_skill_book_selected(const mu_skill_book *b) { return b ? b->hotkeys.selected : 0; }

const char *mu_skill_cast_name(int result)
{
    static const char *const names[] = {"ok", "no skill", "requirements", "delay", "mana", "AG"};
    return result >= 0 && result <= MU_SKILL_CAST_AG ? names[result] : "?";
}

int mu_skill_book_check_cast(mu_skill_book *b, int32_t skill, int *potion)
{
    if (potion) *potion=0;
    if (!b) return MU_SKILL_CAST_NONE;
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
    return MU_SKILL_CAST_OK;
}

int mu_skill_book_cast(mu_skill_book *b, int32_t skill, int32_t events[2][2], int *nevents, int *potion)
{
    if (nevents)
        *nevents = 0;
    if (potion)
        *potion = 0;
    if (!b)
        return MU_SKILL_CAST_NONE;
    int result=mu_skill_book_check_cast(b,skill,potion);
    if(result!=MU_SKILL_CAST_OK)return result;
    int32_t local[2][2];
    int n = mu_skill_delay_start(&b->env, &b->hero, skill, events ? events : local);
    for (int i = 0; i < b->hero.count; i++)
        if (b->hero.timers[i] > 0 && b->delays[i] <= 0)
            b->delays[i] = b->hero.timers[i];
    if (nevents)
        *nevents = n;
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

static float tip_formula(void *u, int32_t group, int32_t id, int32_t argument)
{
    return (float)mu_skill_book_formula(u, group, id, argument);
}
static int tip_master_has(void *u, int32_t skill)
{
    mu_skill_book *b = u;
    return mu_master_find(&b->master, skill) != NULL;
}
static int tip_master_kind(void *u, int32_t skill)
{
    mu_skill_book *b = u;
    return mu_master_flag(&b->master, skill);
}
static float tip_master_value(void *u, int32_t skill)
{
    mu_skill_book *b = u;
    return mu_master_value(&b->master, skill);
}

int mu_skill_book_master_tooltip(mu_skill_book *b, int slot, char *title, size_t title_cap, char *body,
                                 size_t body_cap)
{
    if (!b)
        return 0;
    mu_skill_tip_env env = {.skills = &b->env, .user = b, .text = tip_text, .measure = tip_measure,
                            .formula = tip_formula, .text_scale = b->screen_rate};
    mu_skill_tip *tip = calloc(1, sizeof *tip);
    char *t = malloc(4096), *h = malloc(65536);
    int ok = tip && t && h && mu_master_tooltip(&b->master, &env, &b->menv, &b->hero, slot, tip, NULL);
    if (ok) {
        mu_skill_tooltip_html(tip, t, 4096, h, 65536);
        mu_latin1_to_utf8(title, title_cap, t);
        mu_latin1_to_utf8(body, body_cap, h);
    }
    free(tip);
    free(t);
    free(h);
    return ok;
}

void mu_skill_book_tip_env(mu_skill_book *b, mu_skill_tip_env *out)
{
    memset(out, 0, sizeof *out);
    if (!b)
        return;
    *out = (mu_skill_tip_env){.skills = &b->env, .user = b, .text = tip_text, .measure = tip_measure,
                              .formula = tip_formula, .text_scale = b->screen_rate};
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
    env.master_is = tip_master_has;
    env.master_kind = tip_master_kind;
    env.master_float = tip_master_value;
    env.formula = tip_formula;
    env.text_scale = b->screen_rate;
    mu_skill_tip_input in;
    memset(&in, 0, sizeof in);
    /* main's onSkillTooltip 0x00c7070d takes the stamp manager's entry of the skill (0x01096aa7) */
    const mu_skill_stamp_entry *e = mu_skill_stamp_find(&b->stamp, skill);
    in.base = e ? e->base : skill;
    in.learned = e ? e->learned : mu_skill_learned_index(&b->hero, skill) >= 0 ? skill : 0;
    in.stamped = e ? e->imprint : 0;
    in.weapon_index = -1;
    in.strength = b->hero.strength;
    in.agility = b->hero.agility;
    in.vitality = b->hero.vitality;
    in.energy = b->hero.energy;
    in.command = b->hero.command;
    in.skill_damage = mu_master_skill_damage(&b->master, &b->env, skill, b->formula, b->formula_user);
    return mu_skill_tooltip_build(&env, &in, out);
}

int mu_skill_book_tooltip(mu_skill_book *b, int32_t skill, char *title, size_t title_cap, char *body, size_t body_cap)
{
    mu_skill_tip tip;
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
    const mu_skill_stamp_entry *e = mu_skill_stamp_find(&b->stamp, skill);
    int32_t learned = e ? e->learned : mu_skill_learned_index(&b->hero, skill) >= 0 ? skill : 0;
    return mu_skill_icon_of(&b->env, e ? e->base : skill, learned, mu_skill_book_usable(b, skill), 20.0f, 28.0f, out);
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
    case 0x7e26: return "Interface/SkillStamp.tga";
    case 0x8313: return "Interface/DamageTypeIcon.tga";
    default: return NULL;
    }
}

/* ---- the Skill Imprint window ----------------------------------------------------------------------- */

static const mu_skill_stamp_tab *stamp_tab(const mu_skill_book *b, const mu_skill_stamp *s)
{
    return s->tab ? &b->stamp.special : &b->stamp.basic;
}

static int tab_pages(const mu_skill_book *b, const mu_skill_stamp *s)
{
    int n = stamp_tab(b, s)->count;            /* 0x00c21b0b: the tab's entries (0x010970d8 / 0x01097104) */
    return n / 15 + (n % 15 != 0);
}

void mu_skill_book_stamp_open(mu_skill_book *b, mu_skill_stamp *s)
{
    memset(s, 0, sizeof *s);
    s->page = 1;                               /* 0x00c2008b: both pages 1 */
    s->drag_from = s->drag_to = -1;
    if (!b)
        return;
    s->pages = tab_pages(b, s);
    memcpy(s->saved, b->hotkeys.slots, sizeof s->saved);
    mu_skill_stamp_refresh(&b->env, &b->stamp, b->hero.elemental);    /* the refresh 0x00c20ee4 */
}

int mu_skill_book_stamp_tab(mu_skill_book *b, mu_skill_stamp *s, int tab)
{
    if (!b || !s)
        return 0;
    s->tab = tab ? 1 : 0;
    s->page = 1;
    s->pages = tab_pages(b, s);
    return s->pages;
}

static mu_skill_stamp_entry *window_entry(const mu_skill_book *b, const mu_skill_stamp *s, int slot)
{
    if (slot < 0 || slot >= 20)
        return NULL;
    if (slot < 5)
        return b->stamp.edit[s->select_page * 5 + slot];
    int i = (s->page - 1) * 15 + slot - 5;    /* 0x00c22588 */
    const mu_skill_stamp_tab *t = stamp_tab(b, s);
    return i >= 0 && i < t->count ? t->items[i] : NULL;      /* 0x010968c6 */
}

int32_t mu_skill_book_stamp_skill(const mu_skill_book *b, const mu_skill_stamp *s, int slot)
{
    if (!b)
        return 0;
    const mu_skill_stamp_entry *e = window_entry(b, s, slot);
    return e ? (e->learned ? e->learned : e->base) : 0;      /* 0x01096a60 */
}

int mu_skill_book_stamp_entry(const mu_skill_book *b, const mu_skill_stamp *s, int slot, int32_t *base,
                              int32_t *learned, int *imprint)
{
    const mu_skill_stamp_entry *e = b ? window_entry(b, s, slot) : NULL;
    if (!e)
        return 0;
    if (base)
        *base = e->base;
    if (learned)
        *learned = e->learned;
    if (imprint)
        *imprint = e->imprint;
    return 1;
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
    if (from < 5) {                           /* two bar slots swap (0x01096e15) */
        int src = from + s->select_page * 5;
        mu_skill_stamp_entry *t = b->stamp.edit[src];
        b->stamp.edit[src] = b->stamp.edit[dst];
        b->stamp.edit[dst] = t;
        return 1;
    }
    mu_skill_stamp_entry *e = window_entry(b, s, from);
    if (!e)
        return 0;
    if (e->learned == 0)
        return -1;                            /* GlobalText 0x12bb */
    for (int i = 0; i < MU_SKILL_SLOTS; i++)  /* 0x01096c42: the entry leaves its old slot */
        if (b->stamp.edit[i] == e) {
            b->stamp.edit[i] = NULL;
            break;
        }
    b->stamp.edit[dst] = e;                   /* 0x01096d10 */
    return 1;
}

void mu_skill_book_stamp_save(mu_skill_book *b)
{
    if (!b)
        return;
    /* 0x00c20db4 Save: 0x01096d2a (the client also sends the slots to the server), 0x01096f37, the bar 0x00a08330 */
    mu_skill_world w = world_of(b);
    mu_skill_stamp_save(&b->stamp);
    mu_skill_stamp_after_save(&w, NULL);
    mu_skill_keys_rebuild(&b->keys, &b->stamp);
    sync_keys(b);
}

void mu_skill_book_stamp_cancel(mu_skill_book *b, const mu_skill_stamp *s)
{
    (void)s;
    if (b)
        mu_skill_stamp_cancel(&b->stamp);     /* 0x01096dd0 */
}
