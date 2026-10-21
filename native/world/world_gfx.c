/* The GFx interface over mu-world's 3D view (NATIVE-GFX-002/003); see world_gfx.h. */
#include "world_gfx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_hud.h"
#include "../core/mu_hud_tip.h"
#include "../core/mu_lang.h"
#include "../core/mu_npc.h"
#include "../../reconstructed/hud/tooltip_html.h"
#include "../../reconstructed/npc/npc_dialogue.h"
#include "../../reconstructed/price/item_price.h"
#include "../gfx/mu_gfx_layer.h"
#include "../gfx/mu_gfx_sdl.h"
#include "world_gfx_game.h"

struct world_gfx {
    mu_gfx_layer *layer;
    mu_hud_tip_tables tables;
    const char *root;
    mu_hud_inventory *scratch;
    wg_items *items;            /* item models over the windows and in the hotkey image (NATIVE-GFX-003) */
    double time_ms;
    int skills;
    /* NATIVE-NPC-001: the demo vault contents */
    mu_npc_item npc_storage[MU_NPC_ITEMS];
    int npc_storage_count;
    /* NATIVE-LANG-002: the dialogue manager (NPCDialogue.bmd + QuestWords.bmd) and the open dialogue */
    mu_dlg_tables dlg;
    int have_dlg, dlg_open, hide_contribute;
    int32_t world;                  /* the session's world (ItemValue reads the current world) */
    int32_t dlg_state;
    char dlg_title[96];
};

/* GlobalText for the layer's labels: the tables read from the client
 * (NATIVE-LANG-001, MU_LANG_DIR). */
static const char *lang_text(void *user, int32_t index)
{
    return mu_lang_text(user, index);
}

/* The skill table the game sends to ASData (SkillInfo builder 0x00c5ebaa:
 * Index, Magic_Icon, Name, Delay, SkillUseType, MasteryType; records whose
 * first byte is set are skipped) from the client's Skill(Kor) table. */
static int lang_skills(const mu_lang *lang, mu_gfx_skill *out, int max)
{
    int n = 0;
    for (size_t i = 0; i < mu_lang_skill_count(lang) && n < max; i++) {
        const mu_lang_skill *s = mu_lang_skill_at(lang, i);
        if (s->skip)
            continue;
        mu_gfx_skill *k = &out[n++];
        memset(k, 0, sizeof *k);
        k->index = s->index;
        k->icon = s->icon;
        k->delay = s->delay;
        k->use_type = s->use_type;
        k->mastery = s->mastery;
        mu_lang_ascii(k->name, sizeof k->name, s->name);
    }
    return n;
}

static int64_t client_price(world_gfx *g, int32_t code, int32_t level, int gold_type);

/* The InfoPopup HTML of an item through the tooltip pipeline (core/mu_hud_tip); context (NATIVE-LANG-002):
 * MU_GFX_TIP_SHOP adds the buy line, MU_GFX_TIP_SELL the sell line, as the tooltip builder does at 0x00f0bee3 /
 * 0x00f0bfe2 (static; the condition that picks the buy line sits behind a jump out of the restored image):
 * GlobalText 0x654 "%s(%s)" with the price through 0x016b9103 (plus NpcShop's tax +0xac: 0 offline) and
 * 0x016b8b26, GlobalText 0x3f with the sell price (none when the sell ban 0x016be839 holds). */
static int tooltip_ex(void *user, int32_t code, int32_t level, int context, char *html, size_t cap);
static int tooltip(void *user, int32_t code, int32_t level, char *html, size_t cap)
{
    return tooltip_ex(user, code, level, MU_GFX_TIP_PLAIN, html, cap);
}

static int tooltip_ex(void *user, int32_t code, int32_t level, int context, char *html, size_t cap)
{
    world_gfx *g = user;
    if (!g->tables.have_tooltip || !g->scratch)
        return 1;
    mu_hud_inventory_init(g->scratch);
    int k = mu_hud_inventory_add(g->scratch, g->tables.have_items ? &g->tables.items : NULL, g->root, code, level, 1, 1);
    if (k < 0)
        return 1;
    const mu_gfx_hero *h = mu_gfx_layer_hero(g->layer);
    const int hero[4] = {h->strength, h->agility, h->energy, h->level + h->master_level};
    mu_hud_tip tip;
    mu_hud_tip_build(&g->tables, &g->scratch->items[k], hero, &tip);
    const mu_hud_item *hi = &g->scratch->items[k];
    if ((context == MU_GFX_TIP_SHOP || context == MU_GFX_TIP_SELL) && tip.count + 2 <= MU_HUD_TIP_LINES &&
        (context == MU_GFX_TIP_SHOP || !hi->has_record || hi->record.attributes.can_sell)) {
        char num[32], line[256];
        int64_t price = client_price(g, code, level, context == MU_GFX_TIP_SHOP ? MU_PRICE_BUY : MU_PRICE_SELL);
        mu_price_format((uint32_t)price, num, sizeof num);
        const char *fmt = mu_lang_text(mu_lang_shared(), context == MU_GFX_TIP_SHOP ? 0x654 : 0x3f);
        if (context == MU_GFX_TIP_SHOP)
            snprintf(line, sizeof line, "Purchasing price: %s(%s)", num, num);
        else
            snprintf(line, sizeof line, "Selling Price: %s", num);
        if (fmt) {
            char clean[160];
            mu_lang_ascii(clean, sizeof clean, fmt);
            int conversions = 0;   /* the table's format with the two (buy) or one (sell) %s */
            for (const char *p = clean; *p; p++)
                if (*p == '%')
                    conversions += p[1] == 's' ? 1 : 100, p += p[1] != 0;
            if (conversions == (context == MU_GFX_TIP_SHOP ? 2 : 1)) {
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
#endif
                snprintf(line, sizeof line, clean, num, num);
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
            }
        }
        snprintf(tip.text[tip.count], sizeof tip.text[0], "%s", line);
        tip.color[tip.count++] = 0;
    }
    mu_hud_tip_html(&tip, html, cap);
    return 0;
}

/* NATIVE-LANG-002: the client's ItemValue 0x0169320b (reconstructed/price, verified) for an item object as the
 * native session has it: the code and level, full durability (the item constructor's maximum 0x00ccc5b0), no
 * options, sockets or harmony; world = the session's world; MonsterSoulConversion from MU_LANG_DIR; the other
 * Item.bmd records for seed spheres and kind 0x22.  gold_type: MU_PRICE_BUY / SELL / REPAIR.  Without Item.bmd
 * the item has no record and the price is 0. */
static const uint8_t *record_of(void *user, int32_t code)
{
    world_gfx *g = user;
    mu_item it;
    return g->tables.have_items && code >= 0 && mu_item_find(&g->tables.items, (uint32_t)code, &it) == 0 ? it.record
                                                                                                    : NULL;
}

static int soul_conversion(void *user, int32_t code)
{
    (void)user;
    return mu_lang_soul_conversion(mu_lang_shared(), code);
}

static int64_t client_price(world_gfx *g, int32_t code, int32_t level, int gold_type)
{
    mu_item it;
    if (!g->tables.have_items || code < 0 || mu_item_find(&g->tables.items, (uint32_t)code, &it) != 0)
        return 0;
    mu_price_item item;
    mu_price_item_init(&item);
    item.code = code;
    item.level = level < 0 ? 0 : level > 15 ? 15 : level;
    item.max_durability = mu_item_max_durability_at(&it, item.level, 0, 0);
    item.durability = it.attributes.max_stack ? 1 : item.max_durability;   /* a stack of one */
    mu_price_state st;
    memset(&st, 0, sizeof st);
    st.world = g->world;
    st.record_of = record_of;
    st.soul_conversion = soul_conversion;
    st.user = g;
    st.pet_status = 0;
    int32_t v = mu_item_price(it.record, &item, gold_type, &st);
    return gold_type == MU_PRICE_BUY ? (int64_t)(uint32_t)v : (int64_t)v;   /* the tooltip prints buy unsigned */
}

/* The layer's price callback: the buy price (NpcShop) and the sell price (inventory items while it is open). */
static int64_t item_price(void *user, int32_t code, int32_t level)
{
    return client_price(user, code, level, MU_PRICE_BUY);
}

static int64_t item_price_ex(void *user, int32_t code, int32_t level, int gold_type)
{
    return client_price(user, code, level, gold_type);
}

/* Name and size of an item code from Item.bmd (the inventory's source). */
static void item_info(world_gfx *g, int32_t code, int32_t level, mu_gfx_slot_item *out)
{
    memset(out, 0, sizeof *out);
    out->code = code;
    out->level = level;
    out->width = 1;
    out->height = 2;
    snprintf(out->name, sizeof out->name, "Item %d", (int)code);
    if (g->scratch && g->tables.have_items) {
        mu_hud_inventory_init(g->scratch);
        int k = mu_hud_inventory_add(g->scratch, &g->tables.items, g->root, code, level, 1, 2);
        if (k >= 0) {
            out->width = g->scratch->items[k].grid.width;
            out->height = g->scratch->items[k].grid.height;
            snprintf(out->name, sizeof out->name, "%s", g->scratch->items[k].name);
        }
    }
    out->price = client_price(g, code, level, MU_PRICE_BUY);
}

/* Demo inventory (layer choice): a weapon, armour pieces, potions and a ring;
 * sizes and names from Item.bmd when the game root has it. */
static void demo_items(world_gfx *g)
{
    static const int32_t ITEMS[][2] = {{0 * 512 + 5, 9}, {7 * 512 + 1, 7}, {8 * 512 + 1, 11}, {9 * 512 + 1, 7},
                                       {14 * 512 + 3, 0}, {14 * 512 + 4, 0}, {6 * 512 + 2, 5}, {13 * 512 + 8, 0},
                                       {4 * 512 + 8, 0}};
    for (size_t i = 0; i < sizeof ITEMS / sizeof ITEMS[0]; i++) {
        int32_t code = ITEMS[i][0], level = ITEMS[i][1];
        uint8_t w = 1, h = 2;
        char name[96];
        snprintf(name, sizeof name, "Item %d", (int)code);
        if (g->scratch && g->tables.have_items) {
            mu_hud_inventory_init(g->scratch);
            int k = mu_hud_inventory_add(g->scratch, &g->tables.items, g->root, code, level, 1, 2);
            if (k >= 0) {
                w = g->scratch->items[k].grid.width;
                h = g->scratch->items[k].grid.height;
                snprintf(name, sizeof name, "%s", g->scratch->items[k].name);
            }
        }
        mu_gfx_layer_add_item(g->layer, code, level, w, h, name);
    }
}

/* ---- NATIVE-LANG-002 ---- */

/* The dialogue manager's files (Data\Local\NPCDialogue.bmd, QuestWords.bmd; the client's loaders 0x00fdcbb4 /
 * 0x00fdcdc8) decoded by reconstructed/data. */
static int load_dialogue(world_gfx *g, const char *root)
{
    if (!root || getenv("MU_NO_NPC_DIALOGUE"))
        return 0;
    char path[4096];
    mu_data_table rec, words;
    memset(&rec, 0, sizeof rec);
    memset(&words, 0, sizeof words);
    snprintf(path, sizeof path, "%s/Data/Local/npcdialogue.bmd", root);
    int ok = mu_data_load(path, NULL, &rec) == 0 && rec.result.status == MU_DATA_OK;
    snprintf(path, sizeof path, "%s/Data/Local/questwords.bmd", root);
    ok = ok && mu_data_load(path, NULL, &words) == 0 && words.result.status == MU_DATA_OK;
    if (ok)
        ok = mu_dlg_parse_records(&g->dlg, rec.bytes, rec.size) > 0 &&
             mu_dlg_parse_words(&g->dlg, words.bytes, words.size) > 0;
    mu_data_free(&rec);
    mu_data_free(&words);
    if (!ok)
        mu_dlg_free(&g->dlg);
    return ok;
}

/* npcdialogue's open (0x00be842c -> 0x00be86de(state) -> 0x00be89f7 / 0x00be8a9b): the state's text and its
 * options "%d. text" while present (at most 10; the client also stops at 21 wrapped lines, measured with its
 * font: not reproduced). */
static int dialogue_show(world_gfx *g, int32_t state)
{
    static char text[4096], options[MU_DLG_OPTIONS][96];
    const char *t = mu_dlg_state_text(&g->dlg, state);
    mu_gfx_npc_dialog d;
    memset(&d, 0, sizeof d);
    d.title = g->dlg_title;
    mu_lang_ascii(text, sizeof text, t ? t : "");
    d.text = text;
    int n = mu_dlg_option_count(&g->dlg, state);
    for (int i = 0; i < n; i++) {
        mu_lang_ascii(options[i], sizeof options[i], mu_dlg_option_text(&g->dlg, state, i));
        d.options[d.noptions++] = options[i];
    }
    d.hide_contribute = g->hide_contribute;
    g->dlg_state = state;
    g->dlg_open = 1;
    return mu_gfx_layer_npc_dialog(g->layer, &d);
}

/* onClickSelectBtn(index) -> 0x00be85fd -> 0x00be906d: show the next state, or a server request (901..920:
 * packets C1 F6 / C1 F8 in the client; not played offline, some close the window), or state 999. */
static int dialogue_choice(void *user, int index)
{
    world_gfx *g = user;
    if (!g->have_dlg || !g->dlg_open)
        return 0;
    mu_dlg_choice c = mu_dlg_select(&g->dlg, g->dlg_state, index);
    if (c.kind == MU_DLG_SHOW) {
        dialogue_show(g, c.value);
        return 1;
    }
    if (mu_dlg_action_closes(c.value)) {
        mu_gfx_layer_npc_close(g->layer);
        g->dlg_open = 0;
    }
    char note[96];
    snprintf(note, sizeof note, "dialogue request %d (a server request in the client; not played)", (int)c.value);
    mu_gfx_layer_npc_note(g->layer, note);
    return 1;
}

/* The buff InfoPopup (0x00b8d4de): the lines of 0x01298a54 (core/mu_lang, verified), the name gold
 * (0xffd8bc65) and the others white as the client passes them to its line formatter 0x0096fe90; the HTML
 * around them is the reconstructed InfoPopup assembly's (0x00b8d94b, layer choice: 0x0096fe90 itself is not
 * reconstructed).  No hero buff values offline (the value lines show their plain description). */
static int buff_tooltip(void *user, int32_t buff, char *html, size_t cap)
{
    (void)user;
    char lines[16][256];
    int n = mu_lang_buff_tooltip(mu_lang_shared(), buff, NULL, lines, 16);
    if (n <= 0)
        return 1;
    char clean[16][300];
    mu_tooltip_line tl[16];
    for (int i = 0; i < n; i++) {
        char a[256];
        mu_lang_ascii(a, sizeof a, lines[i]);
        if (!strcmp(lines[i], "\n"))
            snprintf(clean[i], sizeof clean[i], "\n");
        else
            snprintf(clean[i], sizeof clean[i], "<font color='%s'>%s</font><br>", i == 0 ? "#D8BC65" : "#FFFFFF", a);
        tl[i] = (mu_tooltip_line){clean[i], 0, 0, (uint8_t)strcmp(lines[i], "\n") != 0};
    }
    char raw[8192];
    mu_tooltip_html(raw, sizeof raw, tl, n, NULL);
    mu_latin1_to_utf8(html, cap, raw);
    return 0;
}

/* The demo buffs of --gfx-open "buffs=1:2:8" (no server: labelled demo) through the bufflist's addBuff rule. */
static void demo_buffs(world_gfx *g, const char *open)
{
    const char *p = open ? strstr(open, "buffs=") : NULL;
    if (!p || !mu_lang_shared())
        return;
    for (p += 6; *p && *p != ',';) {
        char *end = NULL;
        long v = strtol(p, &end, 0);
        if (end == p)
            break;
        mu_lang_addbuff a;
        if (mu_lang_buff_addbuff(mu_lang_shared(), (int32_t)v, &a)) {
            mu_gfx_buff b = {a.buff, a.is_debuff, a.is_cash, a.has_detail, a.detail};
            mu_gfx_layer_add_buff(g->layer, &b);
        }
        p = *end == ':' ? end + 1 : end;
    }
}

/* The character window rows of a class index ("class=N" in --gfx-open, default 1: the demo hero's
 * Blade Knight) from CharacterInfoSetup (0x00b3dedc's order). */
static void char_rows(world_gfx *g, const char *open)
{
    const char *p = open ? strstr(open, "class=") : NULL;
    int32_t cls = p ? (int32_t)strtol(p + 6, NULL, 0) : 1;
    const mu_lang_charinfo *rows[256];
    int n = mu_lang_charinfo_rows(mu_lang_shared(), cls, rows, 256);
    if (n <= 0)
        return;
    static mu_gfx_char_row out[256];
    for (int i = 0; i < n; i++) {
        mu_gfx_char_row *r = &out[i];
        memset(r, 0, sizeof *r);
        r->type = rows[i]->type;
        r->id = rows[i]->id;
        r->sort = rows[i]->sort;
        r->button = rows[i]->button;
        r->color = rows[i]->color;
        r->value_color = rows[i]->value_color;
        mu_lang_ascii(r->label, sizeof r->label, rows[i]->label);
        /* the hero values the layer has, by row id (labels Class, Level, Pts Remaining, Strength, Agility,
         * Stamina, Energy, Command, * ATK Power; a static reading of the table's labels) */
        switch (rows[i]->id) {
        case 1: r->value_key = MU_GFX_ROW_CLASS; break;
        case 2: r->value_key = MU_GFX_ROW_LEVEL; break;
        case 5: r->value_key = MU_GFX_ROW_POINTS; break;
        case 8: r->value_key = MU_GFX_ROW_STRENGTH; break;
        case 13: r->value_key = MU_GFX_ROW_AGILITY; break;
        case 24: r->value_key = MU_GFX_ROW_VITALITY; break;
        case 29: r->value_key = MU_GFX_ROW_ENERGY; break;
        case 42: r->value_key = MU_GFX_ROW_COMMAND; break;
        case 10: r->value_key = MU_GFX_ROW_DAMAGE; break;
        default: r->value_key = MU_GFX_ROW_NONE; break;
        }
    }
    mu_gfx_layer_set_char_rows(g->layer, out, n);
}

world_gfx *world_gfx_open(const char *movie_dir, const char *game_root, int width, int height, double scale,
                          int shared, const char *open, char *error, size_t error_size)
{
    world_gfx *g = calloc(1, sizeof *g);
    if (!g) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    g->root = game_root;
    g->scratch = malloc(sizeof *g->scratch);
    mu_hud_tip_tables_load(game_root, &g->tables);
    g->items = game_root && !getenv("MU_GFX_NO_ITEM_MODELS") ? wg_items_open(game_root) : NULL;
    mu_gfx_layer_config cfg = {.movie_dir = movie_dir, .width = width, .height = height, .shared = shared, .demo = 1,
                               .tooltip = tooltip, .tooltip_user = g, .scale = scale,
                               .items = g->items ? wg_items_draw : NULL, .icons = g->items && !getenv("MU_GFX_NO_ICON_MODELS") ? wg_items_icons : NULL,
                               .items_user = g->items,
                               .double_buffer = !getenv("MU_GFX_SINGLE_BUFFER"),
                               .text = mu_lang_shared() ? lang_text : NULL, .text_user = (void *)mu_lang_shared(),
                               .price = item_price, .price_ex = item_price_ex, .tooltip_ex = tooltip_ex,
                               .dialog_choice = dialogue_choice, .buff_tooltip = buff_tooltip};
    if (getenv("MU_GFX_LOG"))
        cfg.log = fopen(getenv("MU_GFX_LOG"), "w");
    g->layer = mu_gfx_layer_open(&cfg, error, error_size);
    if (!g->layer) {
        world_gfx_close(g);
        return NULL;
    }
    demo_items(g);
    g->have_dlg = load_dialogue(g, game_root);
    demo_buffs(g, open);
    char_rows(g, open);
    mu_gfx_skill *skills = malloc(1024 * sizeof *skills);
    if (skills) {
        g->skills = mu_lang_skill_count(mu_lang_shared()) ? lang_skills(mu_lang_shared(), skills, 1024)
                                                          : wg_skills_load(game_root, skills, 1024);
        if (g->skills > 0)
            mu_gfx_layer_set_skills(g->layer, skills, g->skills);
        free(skills);
    }
    if (open) {
        if (strstr(open, "inventory"))
            mu_gfx_layer_show(g->layer, MU_GFX_INVENTORY, 1);
        if (strstr(open, "character"))
            mu_gfx_layer_show(g->layer, MU_GFX_CHARACTER, 1);
    }
    return g;
}

void world_gfx_close(world_gfx *g)
{
    if (!g)
        return;
    mu_gfx_layer_close(g->layer);
    wg_items_close(g->items);
    mu_hud_tip_tables_free(&g->tables);
    mu_dlg_free(&g->dlg);
    free(g->scratch);
    free(g);
}

int world_gfx_event(world_gfx *g, const SDL_Event *e, double scale)
{
    return g ? mu_gfx_sdl_event(g->layer, e, scale) : 0;
}

void world_gfx_frame(world_gfx *g, double dt_ms, int draw)
{
    if (!g)
        return;
    g->time_ms += dt_ms;
    wg_items_set_time(g->items, g->time_ms);
    mu_gfx_layer_advance(g->layer, dt_ms);
    if (draw)
        mu_gfx_layer_draw_gl(g->layer);
}

void world_gfx_set_location(world_gfx *g, int world, float x, float y)
{
    if (!g)
        return;
    g->world = world;
    /* The top menu's map name: the map-name function 0x016baaa6 over the
     * GlobalText read from the client (NATIVE-LANG-001); without the tables
     * the data folder's name stands in.  Cells are 100 world units. */
    char name[64];
    const char *map = mu_lang_map_name(mu_lang_shared(), world);
    if (map)
        mu_lang_ascii(name, sizeof name, map);
    else
        snprintf(name, sizeof name, "World %d", world + 1);
    mu_gfx_layer_set_location(g->layer, name, (int)(x / 100.0f), (int)(y / 100.0f));
}

void world_gfx_report(world_gfx *g, char *out, size_t cap)
{
    mu_gfx_layer_stats st;
    mu_gfx_layer_stats_get(g ? g->layer : NULL, &st);
    long renders = 0;
    for (int m = 0; m < MU_GFX_MOVIES; m++)
        renders += st.renders[m];
    long drawn = 0, missing = 0, icons = 0;
    wg_items_counts(g ? g->items : NULL, &drawn, &missing, &icons);
    snprintf(out, cap, "\"gfx\": {\"shared\": %d, \"renders\": %ld, \"callbacks\": %ld, \"invokes\": %ld, "
                       "\"inventory_open\": %d, \"tooltips\": %d, \"base_mode\": %d, \"skills\": %d, "
                       "\"item_models\": %ld, \"item_models_missing\": %ld, \"icon_models\": %ld}",
             st.shared, renders, st.callbacks, st.invokes, mu_gfx_layer_is_open(g ? g->layer : NULL, MU_GFX_INVENTORY),
             g && g->tables.have_tooltip, mu_gfx_layer_base_mode(g ? g->layer : NULL), g ? g->skills : 0, drawn,
             missing, icons);
}

/* NATIVE-NAMES-001: the layer, for the hudPlayerName game side (world_names_gfx.c). */
mu_gfx_layer *world_gfx_layer(world_gfx *g)
{
    return g ? g->layer : NULL;
}

/* ---- NPC windows (NATIVE-NPC-001) ---- */

static void npc_title(const mu_npc_open *o, const char *label, char *out, size_t cap)
{
    /* Npcname(kor): for npcdialogue the dialogue NPC the result names (0x00fdc96c(class) stores its name for
     * SetTitle, static), otherwise the clicked NPC's class */
    int32_t index = o->kind == MU_NPC_WINDOW_DIALOG && o->window.dialogue >= 0 ? o->window.dialogue : o->server_class;
    const mu_lang_npc *npc = mu_lang_npc_get(mu_lang_shared(), index);
    if (npc && npc->name && npc->name[0])
        mu_lang_ascii(out, cap, npc->name);
    else
        snprintf(out, cap, "%s", label && label[0] ? label : "NPC");
}

void world_gfx_npc_open(world_gfx *g, const mu_npc_open *o, const char *label)
{
    if (!g || !o)
        return;
    char title[96];
    npc_title(o, label, title, sizeof title);
    const mu_npc_demo_row *row = o->demo;
    if (o->kind == MU_NPC_WINDOW_DIALOG && g->have_dlg && o->window.dialogue > 0) {
        /* NATIVE-LANG-002: the client's dialogue: 0x00fdc96c(dialogue NPC), then the open shows state 0 */
        mu_dlg_set_npc(&g->dlg, o->window.dialogue);
        snprintf(g->dlg_title, sizeof g->dlg_title, "%s", title);
        g->hide_contribute = o->window.dialogue == 0x248 || o->window.dialogue == 0x2fc ||
                             o->window.dialogue == 0x2fd || o->window.dialogue == 0x3ab || o->window.dialogue == 0x3ac;
        dialogue_show(g, 0);
    } else if (o->kind == MU_NPC_WINDOW_DIALOG) {
        static char text[4096], options[13][96];
        mu_gfx_npc_dialog d;
        memset(&d, 0, sizeof d);
        d.title = title;
        size_t n = 0;
        text[0] = 0;
        for (int i = 0; row && i < row->dialog_count && n < sizeof text; i++) {
            const char *line = mu_lang_dialog(mu_lang_shared(), row->dialog[i]);
            char clean[2048];
            if (line)
                mu_lang_ascii(clean, sizeof clean, line);
            else
                snprintf(clean, sizeof clean, "Dialog %d", (int)row->dialog[i]);
            n += (size_t)snprintf(text + n, sizeof text - n, "%s%s", n ? ";" : "", clean);   /* the client's line separator */
        }
        if (!text[0])
            snprintf(text, sizeof text, "(demo dialogue)");
        d.text = text;
        for (int i = 0; row && i < row->option_count && i < 13; i++) {
            const char *line = mu_lang_dialog(mu_lang_shared(), row->options[i]);
            if (line)
                mu_lang_ascii(options[i], sizeof options[i], line);
            else
                snprintf(options[i], sizeof options[i], "Dialog %d", (int)row->options[i]);
            d.options[d.noptions++] = options[i];
        }
        if (!d.noptions) {
            snprintf(options[0], sizeof options[0], "Close");
            d.options[d.noptions++] = options[0];
        }
        d.hide_contribute = o->window.dialogue == 0x248 || o->window.dialogue == 0x2fc || o->window.dialogue == 0x2fd ||
                       o->window.dialogue == 0x3ab || o->window.dialogue == 0x3ac;
        mu_gfx_layer_npc_dialog(g->layer, &d);
    } else if (o->kind == MU_NPC_WINDOW_SHOP) {
        static mu_gfx_slot_item items[MU_NPC_ITEMS];
        int n = 0;
        for (int i = 0; row && i < row->shop_count && n < MU_NPC_ITEMS; i++)
            item_info(g, row->shop[i].code, row->shop[i].level, &items[n++]);
        mu_gfx_layer_npc_shop(g->layer, title, o->repair, o->shop_tabs, items, n);
    } else if (o->kind == MU_NPC_WINDOW_STORAGE) {
        static mu_gfx_slot_item items[MU_NPC_ITEMS];
        int n = 0;
        for (int i = 0; i < g->npc_storage_count && n < MU_NPC_ITEMS; i++)
            item_info(g, g->npc_storage[i].code, g->npc_storage[i].level, &items[n++]);
        mu_gfx_layer_storage(g->layer, "Vault", items, n);
    }
}

void world_gfx_npc_close_all(world_gfx *g)
{
    if (g)
        mu_gfx_layer_npc_close(g->layer);
}

int world_gfx_npc_window(world_gfx *g)
{
    return g ? mu_gfx_layer_npc_window(g->layer) >= 0 : 0;
}

int world_gfx_npc_action(world_gfx *g, const char *verb, const char *arg)
{
    return g ? mu_gfx_layer_npc_action(g->layer, verb, arg ? atoi(arg) : 0) : 0;
}

const char *world_gfx_npc_last(world_gfx *g)
{
    return g ? mu_gfx_layer_npc_last(g->layer) : "";
}

void world_gfx_npc_storage(world_gfx *g, const mu_npc_item *items, int n)
{
    if (!g)
        return;
    g->npc_storage_count = n > MU_NPC_ITEMS ? MU_NPC_ITEMS : n;
    memcpy(g->npc_storage, items, (size_t)g->npc_storage_count * sizeof *items);
}
