/* The GFx interface over mu-world's 3D view (NATIVE-GFX-002/003); see world_gfx.h. */
#include "world_gfx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_hud.h"
#include "../core/mu_hud_tip.h"
#include "../core/mu_lang.h"
#include "../core/mu_npc.h"
#include "../core/mu_quest.h"
#include "../core/mu_map.h"
#include "../core/mu_progress.h"
#include "world_gfx_options.h"
#include "../../reconstructed/charsel/charcreate.h"
#include "../core/mu_walk.h"
#include "../core/mu_ui_font.h"
#include "../../reconstructed/hud/tooltip_html.h"
#include "../../reconstructed/npc/npc_dialogue.h"
#include "../../reconstructed/price/item_price.h"
#include "../../reconstructed/social/item_options.h"
#include "../core/mu_social_item_view.h"
#include "../core/mu_skill.h"
#include "../gfx/mu_gfx_layer.h"
#include "../gfx/mu_gfx_sdl.h"
#include "world_gfx_game.h"
#include "world_gfx_skill.h"
#include "world_gfx_tree.h"
#include "../core/mu_mix.h"
#include "../../reconstructed/mix/item_actions.h"
#include "../../reconstructed/mix/item_services.h"

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
    /* NATIVE-QUEST-001: the quest session (reconstructed/quest with the demo server) */
    mu_quest_session quest;
    int have_quest;
    mu_walk *walk;
    mu_map_session *maps;
    mu_ui_font quest_font;
    int path_started;
    int32_t path_mode, path_target[2], path_quest;
    int32_t dlg_npc;
    char quest_events[8][256];
    int quest_event_count;
    /* NATIVE-SKILL-001: the skill host (bar feed, tooltip, Skill Imprint window) */
    wg_skill *skill;
    wg_tree *tree;
    double scale;
    mu_mix_book *mix;
    mu_social_item_tables *social_options;
    mu_social_item_view *social_view;
    /* NATIVE-PROGRESS-001: the hero's progression (core/mu_progress), when the host binds it; the options
     * window and the system menu */
    struct mu_progress *progress;
    wg_options *options;
};

static int mix_quote(void *user,int group,const mu_mix_item *items,int n,mu_mix_quote *out)
{
    world_gfx *g=user;
    return mu_mix_book_quote(g->mix,group,items,n,out);
}
static int jewel_check(void *user,int jewel,const mu_mix_item *target,int visible)
{
    world_gfx *g=user;
    return mu_mix_book_jewel(g->mix,jewel,target,visible);
}
static void jewel_request(void *user,int source,int target)
{
    world_gfx *g=user;uint8_t packet[6];
    mu_jewel_request(packet,(uint8_t)(source+12),(uint8_t)target,0);
    char note[128];
    snprintf(note,sizeof note,"Jewel request %02x %02x %02x %02x %02x %02x (offline demo)",
              packet[0],packet[1],packet[2],packet[3],packet[4],packet[5]);
    mu_gfx_layer_npc_note(g->layer,note);
}

static int store_check(void *user,const mu_mix_item *it) {
    return mu_mix_book_store(((world_gfx *)user)->mix,it);
}
static int repair_quote(void *user,const mu_mix_item *it,int npc,int32_t *cost,int32_t *maximum) {
    return mu_mix_book_repair(((world_gfx *)user)->mix,it,npc,cost,maximum);
}
static void repair_request(void *user,int cell,int npc) {
    world_gfx *g=user;uint8_t p[5];char note[128];
    mu_repair_request(p,cell<0?255:(uint8_t)(cell+12),(uint8_t)!npc);
    snprintf(note,sizeof note,"Repair request %02x %02x %02x %02x %02x (offline demo)",p[0],p[1],p[2],p[3],p[4]);
    mu_gfx_layer_npc_note(g->layer,note);
}

static void quest_dialog_visible(world_gfx *g, int visible);

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

static int contextual_price_line(world_gfx *g, int32_t code, int32_t level, int context, int can_sell,
                                 char line[256]) {
    if ((context != MU_GFX_TIP_SHOP && context != MU_GFX_TIP_SELL) ||
        (context == MU_GFX_TIP_SELL && !can_sell))
        return 0;
    char num[32];
    int64_t price = client_price(g, code, level, context == MU_GFX_TIP_SHOP ? MU_PRICE_BUY : MU_PRICE_SELL);
    mu_price_format((uint32_t)price, num, sizeof num);
    const char *fmt = mu_lang_text(mu_lang_shared(), context == MU_GFX_TIP_SHOP ? 0x654 : 0x3f);
    if (context == MU_GFX_TIP_SHOP)
        snprintf(line, 256, "Buy %s (%s)", num, num); /* stand-in without GlobalText */
    else
        snprintf(line, 256, "Sell %s", num);
    if (fmt) {
        char clean[160];
        mu_lang_ascii(clean, sizeof clean, fmt);
        int conversions = 0; /* the table's format with the two (buy) or one (sell) %s */
        for (const char *p = clean; *p; p++)
            if (*p == '%')
                conversions += p[1] == 's' ? 1 : 100, p += p[1] != 0;
        if (conversions == (context == MU_GFX_TIP_SHOP ? 2 : 1)) {
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
#endif
            snprintf(line, 256, clean, num, num);
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
        }
    }
    return 1;
}

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

static int tooltip_build(void *user,int32_t code,int32_t level,const mu_mix_item *snapshot,int context,char *html,size_t cap);
static int tooltip_snapshot(void *user,const mu_mix_item *snapshot,int context,char *html,size_t cap) {
    return tooltip_build(user,snapshot->code,snapshot->level,snapshot,context,html,cap);
}
static int tooltip_ex(void *user,int32_t code,int32_t level,int context,char *html,size_t cap) {
    return tooltip_build(user,code,level,NULL,context,html,cap);
}
static int tooltip_build(void *user,int32_t code,int32_t level,const mu_mix_item *snapshot,int context,char *html,size_t cap)
{
    world_gfx *g = user;
    if (!g->tables.have_tooltip || !g->scratch)
        return 1;
    mu_hud_inventory_init(g->scratch);
    int k = mu_hud_inventory_add(g->scratch, g->tables.have_items ? &g->tables.items : NULL, g->root, code, level, 1, 1);
    if (k < 0)
        return 1;
    if(snapshot) {
        g->scratch->items[k].durability=(uint8_t)snapshot->durability;
        g->scratch->items[k].excellent=(uint8_t)snapshot->excellent;
    }
    const mu_gfx_hero *h = mu_gfx_layer_hero(g->layer);
    const int hero[4] = {h->strength, h->agility, h->energy, h->level + h->master_level};
    mu_hud_tip tip;
    if(snapshot) {
        uint8_t maximum=mu_item_max_durability_at(&g->scratch->items[k].record,level,(uint8_t)snapshot->excellent,0);
        mu_hud_tip_build_durability(&g->tables,&g->scratch->items[k],hero,maximum,&tip);
    } else mu_hud_tip_build(&g->tables, &g->scratch->items[k], hero, &tip);
    const mu_hud_item *hi = &g->scratch->items[k];
    if (tip.count < MU_HUD_TIP_LINES &&
        contextual_price_line(g, code, level, context, !hi->has_record || hi->record.attributes.can_sell,
                              tip.text[tip.count]))
        tip.color[tip.count++] = 0;
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

/* Trade uses the same original Item.bmd record as ad357e, including cell
 * dimensions and the record's trade permission. Missing data uses demo bounds. */
static int social_item_info(void *user, int32_t code, mu_gfx_slot_item *out) {
    world_gfx *g = user;
    if (!g->tables.have_items) {
        mu_social_item_wire wire;
        mu_social_item_unpack(out->data, &wire);
        mu_social_item_context context = {.can_trade = 1, .capability = 1};
        out->trade_ban = mu_social_item_trade_banned(&wire, &context);
        return 1;
    }
    mu_item it;
    if (mu_item_find(&g->tables.items, (uint32_t)code, &it) != 0)
        return 0;
    out->width = it.attributes.width;
    out->height = it.attributes.height;
    mu_social_item_context context = {0};
    context.kind_a = it.attributes.kind_a;
    context.kind_b = it.attributes.kind_b;
    context.grade = it.attributes.type;
    context.can_trade = it.attributes.can_trade;
    /* 16b823e returns true for a stable Item.bmd record (its later A8/A19/A1a
     * predicates cannot all hold). Special character permissions are absent
     * from this offline hero, so their trade predicate remains restrictive. */
    context.capability = 1;
    mu_social_item_wire wire;
    mu_social_item_unpack(out->data, &wire);
    out->trade_ban = mu_social_item_trade_banned(&wire, &context);
    if (g->social_view) {
        mu_social_item_hero hero = {0};
        if (mu_social_item_view_build(g->social_options, &g->tables, out->data, &hero, g->social_view)) {
            out->excellent = g->social_view->finalized.excellent;
            out->set_bits = g->social_view->decoded.ancient;
            int a = g->social_view->context.kind_a;
            if (a == 8 || a == 25 || a == 26)
                out->element = g->social_view->decoded.element;
        }
    }
    snprintf(out->name, sizeof out->name, "%s", it.name);
    return out->width > 0 && out->height > 0;
}

static int tooltip_packet(void *user, const uint8_t bytes[15], int context, char *html, size_t cap) {
    world_gfx *g = user;
    const mu_gfx_hero *h = mu_gfx_layer_hero(g->layer);
    if (!g->social_view || !h)
        return 1;
    mu_social_item_hero hero = {.known = 1,
                                .level = h->level + h->master_level,
                                .class_byte = g->walk ? g->walk->hero.class_byte : 0,
                                .hp_known = 1,
                                .max_hp = h->max_hp,
                                .mp_known = 1,
                                .max_mp = h->max_mp,
                                .strength = h->strength,
                                .agility = h->agility,
                                .energy = h->energy};
    if (g->progress) {
        const uint8_t *a = g->progress->attr;
        uint32_t level = (uint32_t)mu_prg_i32(a, MU_PRG_A_LEVEL);
        if (a[MU_PRG_A_CLASS] & 0x20)
            level += (uint32_t)mu_prg_i32(a, MU_PRG_A_MLEVEL);
        hero.level = (int32_t)level;
    }
    if (!mu_social_item_view_build(g->social_options, &g->tables, bytes, &hero, g->social_view))
        return 1;
    mu_social_item_view_html(g->social_view, html, cap);
    mu_item record;
    char price[256];
    int sell = mu_item_find(&g->tables.items, (uint32_t)g->social_view->wire.code, &record) == 0 &&
               record.attributes.can_sell;
    if (cap && contextual_price_line(g, g->social_view->wire.code, g->social_view->decoded.level, context,
                                     sell, price)) {
        char ansi[1024], utf8[2048];
        mu_tooltip_html_line(ansi, sizeof ansi, price, 0, 0);
        mu_latin1_to_utf8(utf8, sizeof utf8, ansi);
        size_t used = strlen(html);
        snprintf(html + used, cap - used, "%s", utf8);
    }
    return 0;
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
    quest_dialog_visible(g, 1);
    return mu_gfx_layer_npc_dialog(g->layer, &d);
}

/* onClickSelectBtn(index) -> 0x00be85fd -> 0x00be906d: show the next state, or a server request (901..920:
 * packets C1 F6 / C1 F8 in the client; not played offline, some close the window), or state 999. */
static int dialogue_choice(void *user, int index)
{
    world_gfx *g = user;
    if (!g->have_dlg || !g->dlg_open)
        return 0;
    if (g->have_quest && g->quest.client.dialog.list_mode) {
        /* NATIVE-QUEST-001: npcdialogue's quest-list mode (0x00be906d's first branch; the choice is 1-based) */
        int leave = 0;
        mu_quest_dialog_choice(&g->quest.client, index + 1, &leave);
        if (leave)
            dialogue_show(g, 0);
        else if (!g->quest.client.dialog.visible)
            g->dlg_open = 0;
        return 1;
    }
    mu_dlg_choice c = mu_dlg_select(&g->dlg, g->dlg_state, index);
    if (c.kind == MU_DLG_SHOW) {
        dialogue_show(g, c.value);
        return 1;
    }
    if (c.value == 901 && g->have_quest) {
        /* case 0: C1 F6 71 with the dialogue NPC (0x00bea599(0x00fdc9a3())): the NPC's quest list; the demo
         * server answers F6 71 (core/mu_quest), whose handler fills the quest list into this window */
        mu_quest_session_npc_list(&g->quest, g->dlg_npc);
        mu_gfx_layer_npc_note(g->layer, "dialogue request 901: the NPC's quest list (demo server)");
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
static void char_rows_class(world_gfx *g, int32_t cls);

static void char_rows(world_gfx *g, const char *open)
{
    const char *p = open ? strstr(open, "class=") : NULL;
    char_rows_class(g, p ? (int32_t)strtol(p + 6, NULL, 0) : 1);
}

static void char_rows_class(world_gfx *g, int32_t cls)
{
    cls &= 0xf;                   /* class= accepts the hero's stage bits as well as a base class index */
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
        /* the hero values the layer has, by row id (class, level, free points, the five stats, attack power: a
         * static reading of the table's labels) */
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
        /* NATIVE-PROGRESS-001: the class formula's rows (static reading of the labels; the window's own value
         * builder 0x00b40661 is not reconstructed) */
        case 11: r->value_key = MU_GFX_ROW_ATK_RATE; break;
        case 12: r->value_key = MU_GFX_ROW_PVP_RATE; break;
        case 20: r->value_key = MU_GFX_ROW_DEFENSE; break;
        case 22: r->value_key = MU_GFX_ROW_DEF_RATE; break;
        case 23: r->value_key = MU_GFX_ROW_PVP_DEFRATE; break;
        case 32: r->value_key = MU_GFX_ROW_MAGIC; break;
        case 33: r->value_key = MU_GFX_ROW_CURSE; break;
        case 26: r->value_key = MU_GFX_ROW_HP; break;
        case 27: r->value_key = MU_GFX_ROW_SD; break;
        case 34: r->value_key = MU_GFX_ROW_MANA; break;
        case 35: r->value_key = MU_GFX_ROW_AG; break;
        case 21: r->value_key = MU_GFX_ROW_ATK_SPEED; break;
        default: r->value_key = MU_GFX_ROW_NONE; break;
        }
    }
    mu_gfx_layer_set_char_rows(g->layer, out, n);
}

/* ---- NATIVE-QUEST-001 ---- */

static const char *quest_text(void *user, int32_t index)
{
    (void)user;
    return mu_lang_text(mu_lang_shared(), index);
}

static const char *quest_npc(void *user, int32_t npc)
{
    (void)user;
    return mu_lang_npc_name(mu_lang_shared(), npc);
}

static const char *quest_map(void *user, int32_t world)
{
    (void)user;
    return mu_lang_map_name(mu_lang_shared(), world);
}

static const char *quest_item(void *user, int32_t code)
{
    world_gfx *g = user;
    static char name[96];
    name[0] = 0;
    if (g->scratch && g->tables.have_items) {
        mu_hud_inventory_init(g->scratch);
        int k = mu_hud_inventory_add(g->scratch, &g->tables.items, g->root, code, 0, 1, 2);
        if (k >= 0)
            snprintf(name, sizeof name, "%s", g->scratch->items[k].name);
    }
    return name;
}

static const char *quest_item_record(void *user, int32_t code)
{
    world_gfx *g = user;
    mu_item item;
    return g->tables.have_items && code >= 0 && mu_item_find(&g->tables.items, (uint32_t)code, &item) == 0
               ? quest_item(user, code) : NULL;
}

static int32_t quest_measure(void *user, const char *text, int32_t n)
{
    world_gfx *g = user;
    mu_ui_gdi font = mu_ui_font_gdi(&g->quest_font);
    int32_t x = 0, y = 0;
    font.extent(font.user, text, n, &x, &y);
    return x;
}

static void quest_path_reset(void *user)
{
    world_gfx *g = user;
    if (g->walk) {
        mu_auto_path_reset(&g->walk->auto_path);
        mu_walk_stop(g->walk);
    }
    g->path_started = 0;
    g->path_mode = 0;
}

static int quest_path_start(void *user, int32_t flag, int32_t sx, int32_t sy, int32_t tx, int32_t ty,
                             int32_t mode, int32_t error_check)
{
    world_gfx *g = user;
    (void)sx;
    (void)sy;
    g->path_started = g->walk && mu_walk_auto_move_ex(g->walk, flag, tx, ty, mode, error_check);
    g->path_mode = mode;
    g->path_target[0] = tx;
    g->path_target[1] = ty;
    mu_quest_tab *tab = mu_quest_info_tab(&g->quest.client, g->quest.client.info.tab);
    g->path_quest = tab ? tab->selected : -1;
    return g->path_started;
}

static int quest_send_move(void *user)
{
    return ((world_gfx *)user)->path_started;
}

static void quest_move_answer(void *user, uint8_t subcode)
{
    world_gfx *g = user;
    if (g->walk)
        mu_walk_auto_resume(g->walk, subcode);
}

static int quest_travel(void *user, int32_t world, int32_t x, int32_t y)
{
    world_gfx *g = user;
    return g->maps && mu_map_travel_to(g->maps, world, x, y);
}

static int quest_classic_item(void *user, int32_t code, int32_t need, int32_t level)
{
    (void)need;
    return mu_gfx_layer_count_item(((world_gfx *)user)->layer, code, level);
}

static void quest_item_level(void *user, int32_t code, int32_t level, char *out, size_t cap)
{
    const char *name = quest_item(user, code);
    if (level > 0)
        snprintf(out, cap, "%s +%d", name, level);
    else
        snprintf(out, cap, "%s", name);
}

static void quest_money(void *user, double zen, char *out, size_t cap)
{
    (void)user;
    mu_price_format((uint32_t)zen, out, cap);
}

/* The dialogue manager's QuestWords text (0x00fdc9c1): the quest list's 0x5dd / 0x5de and the leave 0x3ef. */
static const char *quest_word(void *user, int32_t id)
{
    world_gfx *g = user;
    return g->have_dlg ? mu_dlg_text(&g->dlg, id) : NULL;
}

static const char *quest_utf8(void *user, const char *src, char *dst, size_t cap)
{
    (void)user;
    mu_latin1_to_utf8(dst, cap, src);      /* 0x00a99d93 under a Latin-1 code page */
    return dst;
}

static int quest_movie(const char *w, size_t n)
{
    if (n == 16 && !strncmp(w, "NpcQuestProgress", n))
        return MU_GFX_QUEST_PROGRESS;
    if (n == 11 && !strncmp(w, "MyQuestInfo", n))
        return MU_GFX_MY_QUEST;
    if (n == 11 && !strncmp(w, "npcdialogue", n))
        return MU_GFX_NPC_DIALOG;
    if (n == 12 && !strncmp(w, "QuestSummary", n))
        return MU_GFX_QUEST_SUMMARY;
    if (n == 17 && !strncmp(w, "QuestProgressInfo", n))
        return MU_GFX_QUEST_NOTICE;
    if (n == 17 && !strncmp(w, "NpcJobChangeQuest", n))
        return MU_GFX_JOB_QUEST;
    return -1;
}

/* The client's effects as libquest reports them, executed on the movies in order (an invoke's callbacks reach
 * the client code before it goes on, as in the client). */
static void quest_event(void *user, const char *line)
{
    world_gfx *g = user;
    if (g->quest_event_count < 8)
        snprintf(g->quest_events[g->quest_event_count++], sizeof g->quest_events[0], "%s", line);
    else {
        memmove(g->quest_events[0], g->quest_events[1], 7 * sizeof g->quest_events[0]);
        snprintf(g->quest_events[7], sizeof g->quest_events[0], "%s", line);
    }
    const char *sp = strchr(line, ' ');
    if (!sp)
        return;
    const char *w = sp + 1, *we = strchr(w, ' ');
    size_t wn = we ? (size_t)(we - w) : strlen(w);
    int m = quest_movie(w, wn);
    if (!strncmp(line, "invoke ", 7) || !strncmp(line, "value ", 6)) {
        if (m < 0 || !we)
            return;
        const char *meth = we + 1, *me = strchr(meth, ' ');
        if (!me)
            return;
        char method[64];
        snprintf(method, sizeof method, "%.*s", (int)(me - meth), meth);
        mu_gfx_layer_invoke(g->layer, m, NULL, method, me + 1);
    } else if (!strncmp(line, "call ", 5) && m >= 0 && we) {
        int open = !strcmp(we + 1, "openWindow");
        if (open)
            mu_gfx_layer_show(g->layer, m, 1);
        mu_gfx_layer_invoke(g->layer, m, NULL, we + 1, "[]");
        if (!open && !strcmp(we + 1, "closeWindow"))
            mu_gfx_layer_show(g->layer, m, 0);
    } else if (!strncmp(line, "show ", 5) && m >= 0) {
        mu_gfx_layer_show(g->layer, m, 1);
    } else if (!strncmp(line, "hide ", 5) && m >= 0) {
        mu_gfx_layer_show(g->layer, m, 0);
        if (m == MU_GFX_NPC_DIALOG)
            g->dlg_open = 0;
    } else if (!strncmp(line, "demo ", 5)) {
        mu_gfx_layer_chat(g->layer, 3, "", line + 5);
    } else if (!strcmp(line, "MyQuestInfo refresh")) {
        if (g->quest.client.info.visible && g->quest.client.info.tab == 1)
            mu_classic_tab_refresh(&g->quest.client);
    } else if (!strncmp(line, "notice ", 7) || !strncmp(line, "msgbox ", 7) || !strncmp(line, "msgbox2 ", 8)) {
        /* a system message to the chat (0x0095f4ec); the native client has no message box window: its text
         * goes to the chat too */
        const char *q = strchr(line, '"');
        char raw[1024] = "", utf8[2048];
        size_t n = 0;
        for (const char *p = q ? q + 1 : ""; *p && *p != '"' && n + 1 < sizeof raw; p++)
            raw[n++] = *p == '\\' && p[1] ? *++p : *p;
        raw[n] = 0;
        mu_latin1_to_utf8(utf8, sizeof utf8, raw);
        mu_gfx_layer_chat(g->layer, 3, "", utf8);
        /* The offline demo has no confirmation movie. Like its NPC-quest give-up fallback, explicitly
         * accept the chapter abort box; the level warning (0x2f) remains a message only. */
        if (!strncmp(line, "msgbox2 MyQuestInfo 46 ", 23))
            mu_guide_box(&g->quest.client, 0x2e, 0);
    }
}

static void quest_dialog_visible(world_gfx *g, int visible)
{
    if (g->have_quest)
        g->quest.client.dialog.visible = visible;
}

static double json_number_at(const char *args, int k)
{
    double v[8];
    int n = 0;
    for (const char *p = args; p && *p && n < 8;) {
        if (*p == '"') {
            for (p++; *p && *p != '"'; p++)
                if (*p == '\\' && p[1])
                    p++;
            if (*p)
                p++;
            v[n++] = 0;                   /* strings count as arguments */
            continue;
        }
        if ((*p >= '0' && *p <= '9') || *p == '-') {
            char *end = NULL;
            v[n++] = strtod(p, &end);
            p = end;
            continue;
        }
        p++;
    }
    return k < n ? v[k] : 0;
}

static void json_string_at(const char *args, int k, char *out, size_t cap)
{
    int idx = 0;
    out[0] = 0;
    for (const char *p = args; p && *p;) {
        if (*p == '"') {
            size_t n = 0;
            for (p++; *p && *p != '"'; p++) {
                char c = *p;
                if (c == '\\' && p[1]) {
                    c = *++p;
                    c = c == 'n' ? '\n' : c == 't' ? '\t' : c;
                }
                if (idx == k && n + 1 < cap)
                    out[n++] = c;
            }
            if (idx == k) {
                out[n] = 0;
                return;
            }
            idx++;
            if (*p)
                p++;
            continue;
        }
        if ((*p >= '0' && *p <= '9') || *p == '-') {
            char *end = NULL;
            strtod(p, &end);
            p = end;
            idx++;
            continue;
        }
        p++;
    }
}

/* The movies' callbacks to the client's handlers (0x00beec8c NpcQuestProgress, 0x00be4b89 MyQuestInfo). */
static void quest_call(void *user, int movie, const char *name, const char *args)
{
    world_gfx *g = user;
    if (movie >= MU_GFX_MASTER_TREE && movie <= MU_GFX_TREE5) {
        wg_tree_call(g->tree, movie, name, args);
        return;
    }
    if (!g->have_quest)
        return;
    mu_quest_client *c = &g->quest.client;
    char text[8192];
    json_string_at(args, 1, text, sizeof text);
    if (!strcmp(name, "UIInit")) {   /* the movie loaded: the handler's OnLoad (vtable +8) */
        if (movie == MU_GFX_QUEST_PROGRESS)
            mu_quest_progress_onload(c);
        else if (movie == MU_GFX_MY_QUEST)
            mu_quest_info_onload(c);
        else if (movie == MU_GFX_QUEST_SUMMARY)
            mu_summary_onload(c);
        else if (movie == MU_GFX_QUEST_NOTICE)
            mu_quest_progress_info_onload(c);
        else if (movie == MU_GFX_JOB_QUEST)
            mu_classic_onload(c);
        return;
    }
    if (movie == MU_GFX_QUEST_PROGRESS) {
        if (!strcmp(name, "CloseWindow"))
            mu_quest_progress_close(c);
        else
            mu_quest_progress_callback(c, name, json_number_at(args, 0), text);
    } else if (movie == MU_GFX_MY_QUEST) {
        double v[2] = {json_number_at(args, 0), json_number_at(args, 1)};
        if (!strcmp(name, "onClickbtnQuestGiveUp")) {
            /* the client asks with a message box (id 0x2d); the native client has none: taken as OK */
            mu_quest_info_callback(c, name, v, 2, NULL);
            mu_quest_info_giveup_ok(c);
        } else {
            mu_quest_info_callback(c, name, v, 2, text);
        }
    } else if (movie == MU_GFX_QUEST_SUMMARY) {
        mu_summary_callback(c, name, (int32_t)json_number_at(args, 0), (int32_t)json_number_at(args, 1));
    } else if (movie == MU_GFX_JOB_QUEST) {
        if (!strcmp(name, "CloseWindow"))
            mu_classic_close(c);
        else
            mu_classic_callback(c, name, json_number_at(args, 0));
    } else if (movie == MU_GFX_QUEST_NOTICE && (!strcmp(name, "CloseWindow") || !strcmp(name, "LeaveComplete"))) {
        mu_gfx_layer_show(g->layer, movie, 0);
    }
}

static void window_draw(void *user, int movie, int32_t w, int32_t h)
{
    world_gfx *g = user;
    wg_tree_draw(g->tree, movie, w, h);
}

static void quest_wrapped(void *user, const char *text)
{
    world_gfx *g = user;
    if (g->have_quest)
        mu_quest_dialog_set_text(&g->quest.client, text, 0);
}

static int quest_key(void *user, int vk)
{
    world_gfx *g = user;
    if (!g->have_quest)
        return 0;
    mu_quest_client *c = &g->quest.client;
    if (mu_gfx_layer_is_open(g->layer, MU_GFX_JOB_QUEST) && (vk == 27 || (vk >= '1' && vk <= '3'))) {
        mu_classic_key(c, vk);
        return 1;
    }
    if (vk == 'T') {          /* the quest window (layer choice: the client's key scan is not reconstructed) */
        mu_quest_session_toggle_info(&g->quest);
        return 1;
    }
    if (c->progress.visible && vk >= '1' && vk <= '9') {   /* 0x00bede37: 1..9 choose */
        mu_quest_progress_select(c, vk - '1');
        return 1;
    }
    if (vk == 27 && c->progress.visible) {
        mu_quest_progress_close(c);
        return 1;
    }
    if (vk == 27 && c->info.visible) {
        mu_quest_info_close(c);
        return 1;
    }
    return 0;
}

int world_gfx_quest_setup(world_gfx *g, const char *demo_text)
{
    if (!g || !g->layer)
        return 0;
    if (g->have_quest) {
        mu_quest_session_offers(&g->quest, demo_text);
        return 1;
    }
    mu_quest_host host = {.user = g, .text = quest_text, .npc_name = quest_npc, .map_name = quest_map,
                          .item_name = quest_item, .to_utf8 = quest_utf8, .item_record_name = quest_item_record,
                          .measure = quest_measure, .path_reset = quest_path_reset, .path_start = quest_path_start,
                          .send_move = quest_send_move, .classic_item = quest_classic_item,
                          .item_level_name = quest_item_level, .money_text = quest_money};
    char error[256];
    if (mu_quest_session_open(&g->quest, NULL, demo_text, &host, error, sizeof error)) {
        if (getenv("MU_QUEST_VERBOSE"))
            fprintf(stderr, "quests: %s\n", error);
        return 0;
    }
    g->quest.event = quest_event;
    g->quest.user = g;
    g->quest.travel = quest_travel;
    mu_quest_set_move_answer(&g->quest.client, quest_move_answer);
    g->have_quest = 1;
    mu_quest_session_load_classic(&g->quest, g->root);
    const mu_gfx_hero *h = mu_gfx_layer_hero(g->layer);
    mu_quest_set_hero(&g->quest.client, h ? h->name : "");
    mu_quest_set_dialogue_words(&g->quest.client, quest_word);
    /* movies that loaded before the session: their handlers' OnLoad now */
    if (mu_gfx_layer_path(g->layer, MU_GFX_QUEST_PROGRESS)[0])
        mu_quest_progress_onload(&g->quest.client);
    if (mu_gfx_layer_path(g->layer, MU_GFX_MY_QUEST)[0])
        mu_quest_info_onload(&g->quest.client);
    if (mu_gfx_layer_path(g->layer, MU_GFX_QUEST_SUMMARY)[0]) {
        mu_summary_callback(&g->quest.client, "onLoad", 0, 0);
        /* The separate monster-soul tracker has no demo records. Clear the movie's design placeholders. */
        mu_gfx_layer_invoke(g->layer, MU_GFX_QUEST_SUMMARY, NULL, "SetMonsterSoulList", "[[]]");
    }
    if (mu_gfx_layer_path(g->layer, MU_GFX_QUEST_NOTICE)[0])
        mu_quest_progress_info_onload(&g->quest.client);
    if (mu_gfx_layer_path(g->layer, MU_GFX_JOB_QUEST)[0])
        mu_classic_onload(&g->quest.client);
    return 1;
}

void world_gfx_quest_bind(world_gfx *g, mu_walk *walk, mu_map_session *maps)
{
    if (g) {
        g->walk = walk;
        g->maps = maps;
    }
}

void world_gfx_quest_travel_complete(world_gfx *g, int success)
{
    if (g && g->have_quest) {
        if (!success && g->quest.travel_answer) {
            g->path_mode = 0;
            if (g->walk)
                mu_auto_path_reset(&g->walk->auto_path);
        }
        mu_quest_session_travel_complete(&g->quest, success);
    }
}

void world_gfx_quest_step(world_gfx *g)
{
    if (g && g->have_quest) {
        mu_quest_client *c = &g->quest.client;
        const mu_gfx_hero *h = mu_gfx_layer_hero(g->layer);
        c->time = (float)g->time_ms;
        c->world = g->walk ? g->walk->world : g->world;
        c->hero_level = h ? h->level : 1;
        c->hero_level_total = h ? h->level + h->master_level : 1;
        c->money = h ? (uint32_t)h->zen : 0;
        c->holding_item = mu_gfx_layer_held(g->layer) >= 0;
        if (g->walk) {
            c->hero_class = g->walk->hero.class_byte;
            c->hero_safe = g->walk->hero.safe_zone;
            c->hero_x = g->walk->hero.tile[0];
            c->hero_y = g->walk->hero.tile[1];
        }
        mu_quest_session_step(&g->quest);
        /* A completed walk (or the demo teleport) re-enters the verified arrived branch exactly once. */
        if (g->walk && g->path_mode && !g->walk->hero.movement && g->path_target[0] == c->hero_x &&
            g->path_target[1] == c->hero_y) {
            int32_t mode = g->path_mode, quest = g->path_quest;
            g->path_mode = 0;
            if (mode == 1)
                mu_guide_go(c);
            else if (mode == 3 && quest >= 0)
                mu_quest_move(c, quest);
        }
    }
}

void world_gfx_quest_kill(world_gfx *g, int monster_class)
{
    if (g && g->have_quest)
        mu_quest_session_kill(&g->quest, monster_class, g->world);
}

void world_gfx_quest_report(world_gfx *g, FILE *out)
{
    if (g && g->have_quest)
        mu_quest_session_report(&g->quest, out);
}

/* Scripted quest verbs (mu-world --npc-script): qnext / qno (NpcQuestProgress choice 0 / 1), qok (its
 * confirm), qclose, qwin (T), qtab:N, qsel:QUEST, qgo (MyQuestInfo's move/complete button), qgiveup,
 * qkill:CLASS (a demo kill), qset:QUEST:COUNT (demo progress). */
static int quest_action(world_gfx *g, const char *verb, const char *arg)
{
    if (!g->have_quest || verb[0] != 'q')
        return -1;
    mu_quest_client *c = &g->quest.client;
    if (!strcmp(verb, "qnext"))
        return mu_quest_progress_select(c, 0);
    if (!strcmp(verb, "qno"))
        return mu_quest_progress_select(c, 1);
    if (!strcmp(verb, "qok")) {
        mu_quest_progress_confirm(c);
        return 1;
    }
    if (!strcmp(verb, "qclose")) {
        if (c->progress.visible)
            mu_quest_progress_close(c);
        return 1;
    }
    if (!strcmp(verb, "qwin")) {
        mu_quest_session_toggle_info(&g->quest);
        return 1;
    }
    if (!strcmp(verb, "qtab")) {
        /* a click on a tab: the movie's SelectTab (SetUIType, then its OnSelectTab callback) */
        char a[32];
        snprintf(a, sizeof a, "[%d]", arg ? atoi(arg) : 2);
        mu_gfx_layer_invoke(g->layer, MU_GFX_MY_QUEST, NULL, "SelectTab", a);
        return 1;
    }
    if (!strcmp(verb, "qsel")) {
        /* a click on a quest of the list: the movie's SelectQuest(tab, row) (its OnSelectQuest callback) */
        int32_t quest = arg ? atoi(arg) : 0, row = 0;
        const int32_t *list;
        size_t n = mu_quest_active(&c->qs, c->info.tab, &list);
        for (size_t i = 0; i < n; i++)
            if (list[i] == quest)
                row = (int32_t)i;
        char a[48];
        snprintf(a, sizeof a, "[%d,%d]", c->info.tab, row);
        mu_gfx_layer_invoke(g->layer, MU_GFX_MY_QUEST, NULL, "SelectQuest", a);
        return 1;
    }
    if (!strcmp(verb, "qgo"))
        return mu_quest_info_callback(c, c->info.tab == 0 ? "onClickbtnLeaveGuideQuestImmediately" :
                                                            "onClickbtnLeaveQuestImmediately", NULL, 0, NULL);
    if (!strcmp(verb, "qtrack")) {
        mu_quest_info_callback(c, "ScrollingGuideQuestClick", NULL, 0, NULL);
        mu_summary_guide_refresh(c);
        return 1;
    }
    if (!strcmp(verb, "qclass")) {
        mu_quest_session_classic_talk(&g->quest);
        return 1;
    }
    if (!strcmp(verb, "qcnext")) {
        mu_classic_callback(c, "onClickSelectBtn", arg ? atoi(arg) : 0);
        return 1;
    }
    if (!strcmp(verb, "qcok")) {
        mu_classic_complete(c);
        return 1;
    }
    if (!strcmp(verb, "qgset")) {
        int32_t id = arg ? atoi(arg) : 0, count = 0, state = 1;
        if (arg)
            sscanf(arg, "%d:%d:%d", &id, &count, &state);
        char line[80];
        snprintf(line, sizeof line, "guide %d:%d:%d\n", id, count, state);
        mu_quest_session_demo_state(&g->quest, line);
        return 1;
    }
    if (!strcmp(verb, "qgiveup")) {
        if (c->info.tab == 0)
            mu_quest_info_callback(c, "onClickbtnGuideQuestGiveUp", NULL, 0, NULL);
        else
            mu_quest_info_giveup_ok(c);
        return 1;
    }
    if (!strcmp(verb, "qcheck")) {
        mu_quest_info_callback(c, "OnSelectChapterCheck", NULL, 0, NULL);
        return 1;
    }
    if (!strcmp(verb, "qkill")) {
        mu_quest_session_kill(&g->quest, arg ? atoi(arg) : 0, g->world);
        return 1;
    }
    if (!strcmp(verb, "qset")) {
        const char *colon = arg ? strchr(arg, ':') : NULL;
        mu_quest_session_progress(&g->quest, arg ? atoi(arg) : 0, colon ? atoi(colon + 1) : 0);
        return 1;
    }
    return -1;
}

/* NATIVE-PROGRESS-001: winOption / winSystemMenu */
static void progress_call(void *user, int movie, const char *name, const char *args)
{
    world_gfx *g = user;
    wg_options_call(g->options, movie, name, args);
}

wg_options *world_gfx_options(world_gfx *g)
{
    return g ? g->options : NULL;
}

/* NATIVE-PROGRESS-001: CharacterInfoFrame's "+" buttons go through the client's rule and request */
static int stat_button(void *user, double row)
{
    world_gfx *g = user;
    if (!g->progress)
        return 0;
    mu_progress_button(g->progress, row);
    return 1;
}

static void progress_sync(world_gfx *g)
{
    mu_progress *p = g->progress;
    if (!p || !g->layer)
        return;
    if (p->exp_dirty) {
        mu_gfx_layer_exp_data(g->layer, p->exp_json);
        p->exp_dirty = 0;
    }
    if (!p->hero_dirty)
        return;
    p->hero_dirty = 0;
    mu_progress_view v;
    mu_progress_get_view(p, &v);
    mu_gfx_hero h = *mu_gfx_layer_hero(g->layer);
    h.level = v.level;
    h.master_level = v.master_level;
    h.points = v.points;
    h.exp = v.stage >= 3 ? v.master_exp : v.exp;
    h.exp_max = v.stage >= 3 ? v.master_next : v.next_exp;
    h.strength = v.stats[0] + v.added[0];
    h.agility = v.stats[1] + v.added[1];
    h.vitality = v.stats[2] + v.added[2];
    h.energy = v.stats[3] + v.added[3];
    h.command = v.stats[4] + v.added[4];
    h.max_hp = v.life_max;
    h.max_mp = v.mana_max;
    h.max_sd = v.shield_max;
    h.max_ag = v.ag_max;
    if (h.hp > h.max_hp)
        h.hp = h.max_hp;
    if (h.mp > h.max_mp)
        h.mp = h.max_mp;
    const char *cname = mu_lang_text(mu_lang_shared(), mu_ccr_class_name_text(p->hero[0x12], 1));
    if (cname && *cname)   /* the class name 0x0139cc2e (NATIVE-CHARCREATE-001) */
        mu_lang_ascii(h.class_name, sizeof h.class_name, cname);
    h.has_derived = 1;
    h.dmg_min = v.dmg_min;
    h.dmg_max = v.dmg_max;
    h.atk_rate = v.atk_rate;
    h.pvp_rate = v.pvp_rate;
    h.defense = v.defense;
    h.def_rate = v.def_rate;
    h.pvp_defrate = v.pvp_defrate;
    h.magic_min = v.magic_min;
    h.magic_max = v.magic_max;
    h.curse_min = v.curse_min;
    h.curse_max = v.curse_max;
    snprintf(h.speed_text, sizeof h.speed_text, "%s", v.speed_text);
    for (int i = 0; i < 5; i++)
        h.added[i] = v.added[i];
    mu_gfx_layer_set_hero(g->layer, &h);
}

void world_gfx_progress(world_gfx *g, struct mu_progress *p)
{
    if (!g)
        return;
    g->progress = p;
    if (p) {
        char_rows_class(g, p->attr[MU_PRG_A_CLASS]);
        p->hero_dirty = 1;
        p->exp_dirty = p->exp_json[0] != 0;
        progress_sync(g);
    }
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
    g->mix = mu_mix_book_open(game_root);
    g->scale = scale > 0 ? scale : 1.0;
    const char *face = mu_lang_text(mu_lang_shared(), 0);
    mu_ui_font_open(&g->quest_font, face && *face ? face : "Tahoma", 12, 400);
    g->scratch = malloc(sizeof *g->scratch);
    mu_hud_tip_tables_load(game_root, &g->tables);
    g->social_options = mu_social_item_tables_load(game_root, getenv("MU_LANG_DIR"), &g->tables.items);
    g->social_view = calloc(1, sizeof *g->social_view);
    g->items = game_root && !getenv("MU_GFX_NO_ITEM_MODELS") ? wg_items_open(game_root) : NULL;
    mu_gfx_layer_config cfg = {.movie_dir = movie_dir,
                               .width = width,
                               .height = height,
                               .shared = shared,
                               .demo = 1,
                               .tooltip = tooltip,
                               .tooltip_user = g,
                               .scale = scale,
                               .items = g->items ? wg_items_draw : NULL,
                               .icons = g->items && !getenv("MU_GFX_NO_ICON_MODELS") ? wg_items_icons : NULL,
                               .items_user = g->items,
                               .double_buffer = !getenv("MU_GFX_SINGLE_BUFFER"),
                               .text = mu_lang_shared() ? lang_text : NULL,
                               .text_user = (void *)mu_lang_shared(),
                               .price = item_price,
                               .price_ex = item_price_ex,
                               .tooltip_ex = tooltip_ex,
                               .dialog_choice = dialogue_choice,
                               .buff_tooltip = buff_tooltip,
                               .quest_call = quest_call,
                               .dialog_wrapped = quest_wrapped,
                               .window_key = quest_key,
                               .window_draw = window_draw,
                               .mix_quote = mix_quote,
                               .jewel_check = jewel_check,
                               .jewel_request = jewel_request,
                               .tooltip_snapshot = tooltip_snapshot,
                               .store_check = store_check,
                               .repair_quote = repair_quote,
                               .repair_request = repair_request,
                               .stat_button = stat_button,
                               .progress_call = progress_call,
                               .social_item_info = social_item_info,
                               .tooltip_packet = tooltip_packet};
    if (getenv("MU_GFX_LOG"))
        cfg.log = fopen(getenv("MU_GFX_LOG"), "w");
    g->layer = mu_gfx_layer_open(&cfg, error, error_size);
    if (!g->layer) {
        world_gfx_close(g);
        return NULL;
    }
    demo_items(g);
    g->options = wg_options_open(g->layer, NULL, NULL);   /* NATIVE-PROGRESS-001 */
    /* the movies loaded (and called onLoad) inside mu_gfx_layer_open, before the host existed: replay it */
    wg_options_call(g->options, MU_GFX_OPTION, "channel", "[\"onLoad\",\"_level0.instance1\"]");
    wg_options_call(g->options, MU_GFX_SYSTEM_MENU, "channel", "[\"onLoad\",\"_level0.instance1\"]");
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
    {   /* NATIVE-SKILL-001: the demo hero's class ("class=N" in --gfx-open, default 1) */
        const char *p = open ? strstr(open, "class=") : NULL;
        int32_t cls = p ? (int32_t)strtol(p + 6, NULL, 0) : 0x81;
        if (!getenv("MU_GFX_NO_SKILLS")) {
            g->skill = wg_skill_open(game_root, mu_lang_shared(), getenv("MU_LANG_DIR"), cls);
            wg_skill_attach(g->skill, g->layer);
            g->scale = scale > 0 ? scale : 1.0;
            wg_skill_set_screen(g->skill, (int32_t)(width / g->scale));
            g->tree = wg_tree_open(g->skill, g->layer, mu_lang_shared());
            const mu_master_tree *tree = mu_skill_book_master(wg_skill_book(g->skill));
            const char *class_name = tree && tree->mask ? mu_lang_text(mu_lang_shared(), tree->gt_title) : NULL;
            if (class_name) {
                mu_gfx_hero hero = *mu_gfx_layer_hero(g->layer);
                mu_lang_ascii(hero.class_name, sizeof hero.class_name, class_name);
                mu_gfx_layer_set_hero(g->layer, &hero);
            }
            for (int movie = MU_GFX_MASTER_TREE; movie <= MU_GFX_TREE5; movie++)
                wg_tree_call(g->tree, movie, "UIInit", "[]");
            const char *element = open ? strstr(open, "element=") : NULL;
            if (element)
                mu_skill_book_set_elemental(wg_skill_book(g->skill), (int32_t)strtol(element + 8, NULL, 0));
            const char *buff = open ? strstr(open, "buffs=") : NULL;
            int32_t ids[64];
            int count = 0;
            if (buff) {
                const char *at = buff + 6;
                while (*at && count < 64) {
                    char *end;
                    long id = strtol(at, &end, 0);
                    if (end == at)
                        break;
                    ids[count++] = (int32_t)id;
                    if (*end != ':')
                        break;
                    at = end + 1;
                }
            }
            wg_skill_set_buffs(g->skill, ids, count);
        }
    }
    if (open) {
        if (strstr(open, "inventory"))
            mu_gfx_layer_show(g->layer, MU_GFX_INVENTORY, 1);
        if (strstr(open, "mix"))
            mu_gfx_layer_mix_action(g->layer, "mixopen", 0, 0);
        if (strstr(open, "character"))
            mu_gfx_layer_show(g->layer, MU_GFX_CHARACTER, 1);
        if (strstr(open, "skills"))
            mu_gfx_layer_show(g->layer, MU_GFX_SKILL_STAMP, 1);
        if (strstr(open, "master"))
            mu_gfx_layer_show(g->layer, MU_GFX_MASTER_TREE, 1);
        if (strstr(open, "tree4"))
            mu_gfx_layer_show(g->layer, MU_GFX_TREE4, 1);
        if (strstr(open, "tree5"))
            mu_gfx_layer_show(g->layer, MU_GFX_TREE5, 1);
    }
    return g;
}

int world_gfx_skill_cast(world_gfx *g, int32_t *skill)
{
    return g ? wg_skill_cast(g->skill, skill) : MU_SKILL_CAST_NONE;
}

struct mu_skill_book *world_gfx_skills(world_gfx *g)
{
    return g ? wg_skill_book(g->skill) : NULL;
}

int world_gfx_skill_action(world_gfx *g, const char *verb, int a, int b)
{
    if (g && wg_tree_action(g->tree, verb, a))
        return 1;
    if (g && (!strcmp(verb, "learn") || !strcmp(verb, "forget")))
        return wg_skill_server(g->skill, verb, a);          /* NATIVE-SKILL-002: the demo server's packets */
    return g ? mu_gfx_layer_skill_action(g->layer, verb, a, b) : 0;
}

void world_gfx_close(world_gfx *g)
{
    if (g)
        wg_options_close(g->options);   /* NATIVE-PROGRESS-001 */
    if (!g)
        return;
    mu_quest_session_close(&g->quest);
    mu_mix_book_close(g->mix);
    mu_gfx_layer_close(g->layer);
    wg_tree_close(g->tree);
    wg_skill_close(g->skill);
    mu_ui_font_close(&g->quest_font);
    wg_items_close(g->items);
    mu_social_item_tables_free(g->social_options);
    free(g->social_view);
    mu_hud_tip_tables_free(&g->tables);
    mu_dlg_free(&g->dlg);
    free(g->scratch);
    free(g);
}

void world_gfx_resize(world_gfx *g, int width, int height)
{
    if (!g)
        return;
    mu_gfx_layer_resize(g->layer, width, height);
    wg_skill_set_screen(g->skill, (int32_t)(width / (g->scale > 0 ? g->scale : 1.0)));
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
    wg_skill_tick(g->skill, dt_ms);
    progress_sync(g);   /* NATIVE-PROGRESS-001 */
    wg_options_step(g->options, dt_ms);
    mu_gfx_layer_advance(g->layer, dt_ms);
    if (draw)
        mu_gfx_layer_draw_gl(g->layer);
}

void world_gfx_set_location(world_gfx *g, int world, float x, float y)
{
    if (!g)
        return;
    g->world = world;
    wg_skill_set_world(g->skill, world);
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
    long drawn = 0, missing = 0, icons = 0, casts = 0, refused = 0, skill_icons = 0, skill_tips = 0;
    wg_items_counts(g ? g->items : NULL, &drawn, &missing, &icons);
    wg_skill_counts(g ? g->skill : NULL, &casts, &refused, &skill_icons, &skill_tips);
    const mu_skill_book *book = g ? wg_skill_book(g->skill) : NULL;
    snprintf(out, cap, "\"gfx\": {\"shared\": %d, \"renders\": %ld, \"callbacks\": %ld, \"invokes\": %ld, "
                       "\"inventory_open\": %d, \"tooltips\": %d, \"base_mode\": %d, \"skills\": %d, "
                       "\"item_models\": %ld, \"item_models_missing\": %ld, \"icon_models\": %ld, "
                       "\"skill_book\": {\"records\": %zu, \"tooltip_texts\": %zu, \"learned\": %d, \"selected\": %d, "
                       "\"casts\": %ld, \"refused\": %ld, \"window_icons\": %ld, \"tooltips\": %ld, \"window_open\": %d, "
                       "\"last\": \"%s\"}}",
             st.shared, renders, st.callbacks, st.invokes, mu_gfx_layer_is_open(g ? g->layer : NULL, MU_GFX_INVENTORY),
             g && g->tables.have_tooltip, mu_gfx_layer_base_mode(g ? g->layer : NULL), g ? g->skills : 0, drawn,
             missing, icons, mu_skill_book_count(book), mu_skill_book_tooltips(book),
             book ? mu_skill_book_hero(book)->count : 0, (int)mu_skill_book_selected(book), casts, refused, skill_icons,
             skill_tips, mu_gfx_layer_is_open(g ? g->layer : NULL, MU_GFX_SKILL_STAMP),
             mu_gfx_layer_skill_last(g ? g->layer : NULL));
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
    if (o->kind == MU_NPC_WINDOW_CLASSIC && g->have_quest) {
        g->quest.client.target_class = o->server_class;
        mu_quest_session_classic_talk(&g->quest);
    } else if (o->kind == MU_NPC_WINDOW_DIALOG && g->have_dlg && o->window.dialogue > 0) {
        /* NATIVE-LANG-002: the client's dialogue: 0x00fdc96c(dialogue NPC), then the open shows state 0
         * (NATIVE-QUEST-001: also the NPC dialogue packet F9 01, handler 0x0126d5da, for any dialogue NPC; it
         * does nothing while npcdialogue is open) */
        if (o->dialog_packet && g->dlg_open && mu_gfx_layer_npc_window(g->layer) == MU_GFX_NPC_DIALOG)
            return;
        mu_dlg_set_npc(&g->dlg, o->window.dialogue);
        g->dlg_npc = o->window.dialogue;
        if (g->have_quest)
            g->quest.client.dialog.list_mode = 0;      /* 0x00be842c: +0x1d04 = 0 */
        snprintf(g->dlg_title, sizeof g->dlg_title, "%s", title);
        g->hide_contribute = o->window.dialogue == 0x248 || o->window.dialogue == 0x2fc ||
                             o->window.dialogue == 0x2fd || o->window.dialogue == 0x3ab || o->window.dialogue == 0x3ac;
        if (o->dialog_packet)
            g->hide_contribute = 1;   /* 0x00be88b8: VisibleContribute(0) unless a Gens steward of the hero's Gens */
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
    } else if (o->window.slot == 0xb0) {
        mu_gfx_layer_mix_action(g->layer, "goblin", 0, 0);
    } else if (o->window.slot == 0xa8) {
        mu_gfx_layer_mix_action(g->layer, "mixopen", o->window.mix_type >= 0 ? o->window.mix_type : 0, 0);
    }
}

void world_gfx_npc_close_all(world_gfx *g)
{
    if (!g)
        return;
    mu_gfx_layer_npc_close(g->layer);
    g->dlg_open = 0;
    quest_dialog_visible(g, 0);
    /* NATIVE-QUEST-001: ReceiveTalk's close-all closes every GFx window, the quest windows by their handlers */
    if (g->have_quest && g->quest.client.progress.visible)
        mu_quest_progress_close(&g->quest.client);
    if (g->have_quest && g->quest.client.info.visible)
        mu_quest_info_close(&g->quest.client);
    if (g->have_quest && mu_gfx_layer_is_open(g->layer, MU_GFX_JOB_QUEST))
        mu_classic_close(&g->quest.client);
}

int world_gfx_npc_window(world_gfx *g)
{
    return g ? mu_gfx_layer_npc_window(g->layer) >= 0 || mu_gfx_layer_is_open(g->layer, MU_GFX_JOB_QUEST) : 0;
}

int world_gfx_npc_action(world_gfx *g, const char *verb, const char *arg)
{
    if (!g)
        return 0;
    if (!strncmp(verb,"mix",3) || !strcmp(verb,"goblin") || !strcmp(verb,"jewel")) {
        int a=arg?atoi(arg):0,b=0;
        const char *colon=arg?strchr(arg,':'):NULL;if(colon)b=atoi(colon+1);
        if (!strcmp(verb,"mixadd")) {
            mu_gfx_slot_item it;item_info(g,a,b,&it);
            return mu_gfx_layer_add_item(g->layer,it.code,it.level,it.width,it.height,it.name)>=0;
        }
        return mu_gfx_layer_mix_action(g->layer,verb,a,b);
    }
    if(!strncmp(verb,"store",5) || !strncmp(verb,"repair",6) || !strcmp(verb,"selfrepair") || !strcmp(verb,"damage") || !strcmp(verb,"serviceresult")) {
        int a=arg?atoi(arg):0,b=0;const char *colon=arg?strchr(arg,':'):NULL;if(colon)b=atoi(colon+1);
        return mu_gfx_layer_service_action(g->layer,verb,a,b);
    }
    int q = quest_action(g, verb, arg);
    if (q >= 0)
        return q;
    return mu_gfx_layer_npc_action(g->layer, verb, arg ? atoi(arg) : 0);
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
