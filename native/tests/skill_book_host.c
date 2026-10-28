/* Test host for native/core/mu_skill.c (NATIVE-SKILL-001, NATIVE-SKILL-002).
 *
 *   skill-book-host LANG_DIR GAME_ROOT|- [OP ...]
 *
 * Loads the Lang plaintext (core/mu_lang) and SkillTooltipText.bmd under GAME_ROOT/Data/Local, then runs:
 *   demo CLASS | stats STR AGI VIT ENE CMD MANA AG | feed | select SLOT | cast SKILL | tick MS | tip SKILL
 *   | icon SKILL | stamp | slot N | drop FROM TO | cancel | print
 *   | demofile PATH | learn SKILL | forget SKILL | save | tab N | packet HEX (a server packet)
 *   | tree4 CLASS POINTS (NATIVE-SKILL-003: core/mu_skill_tree4 over LANG_DIR/tree4.tsv, the demo login)
 *   | t4click INDEX (click, confirm, the demo answer) | t4tab TAB | t4state
 * Each op prints one JSON line.  Synthetic data in the tests; no client bytes. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_lang.h"
#include "../core/mu_skill.h"
#include "../core/mu_skill_tree4.h"

static int t4_invokes, t4_boxes;
static char t4_last[4096];
static void t4_invoke(void *u, const char *name, const char *json)
{
    (void)u;
    ++t4_invokes;
    snprintf(t4_last, sizeof t4_last, "%s %s", name, json);
}
static void t4_box(void *u, const char *text) { (void)u; (void)text; ++t4_boxes; }
static void t4_confirm(void *u, int id, const char *text) { (void)u; (void)id; (void)text; ++t4_boxes; }

static int weapon_kind;
static int kind(void *u, int slot, int value) { (void)u; return slot == 0 && value == weapon_kind; }

int main(int argc, char **argv)
{
    mu_skill_demo model = {0};
    if (argc < 3) {
        fprintf(stderr, "usage: %s LANG_DIR GAME_ROOT|- [OP ...]\n", argv[0]);
        return 2;
    }
    mu_lang *lang = mu_lang_load(argv[1]);
    mu_skill_book *b = mu_skill_book_open(lang, argv[1], strcmp(argv[2], "-") ? argv[2] : NULL);
    if (!b) {
        printf("{\"error\": \"open\"}\n");
        return 1;
    }
    mu_skill_tree4 *t4 = NULL;
    mu_skill_stamp stamp;
    mu_skill_book_stamp_open(b, &stamp);
    printf("{\"records\": %zu, \"tooltips\": %zu}\n", mu_skill_book_count(b), mu_skill_book_tooltips(b));
    for (int i = 3; i < argc; i++) {
        const char *op = argv[i];
        int a = i + 1 < argc ? atoi(argv[i + 1]) : 0;
        if (!strcmp(op, "demo")) {
            printf("{\"demo\": %d}\n", mu_skill_book_demo(&model, b, a));
            mu_skill_book_stamp_open(b, &stamp);
            i++;
        } else if (!strcmp(op, "stats") && i + 7 < argc) {
            mu_skill_stats s = {.class_byte = mu_skill_book_hero(b)->class_index};
            s.strength = (uint16_t)atoi(argv[i + 1]);
            s.agility = (uint16_t)atoi(argv[i + 2]);
            s.vitality = (uint16_t)atoi(argv[i + 3]);
            s.energy = (uint16_t)atoi(argv[i + 4]);
            s.command = (uint16_t)atoi(argv[i + 5]);
            s.mana = atoi(argv[i + 6]);
            s.ag = atoi(argv[i + 7]);
            mu_skill_book_set_stats(b, &s);
            i += 7;
        } else if (!strcmp(op, "feed")) {
            char json[8192];
            if (mu_skill_book_feed(b, json, sizeof json))
                printf("{\"feed\": %s}\n", json);
            else
                printf("{\"feed\": null}\n");
        } else if (!strcmp(op, "use") && i + 2 < argc) {
            weapon_kind = atoi(argv[i + 2]);
            mu_skill_use_env env = {.world = a, .transform = 0xffff, .item_kind = kind};
            for (int j = 0; j < 15; j++)
                env.items[j].code = -1;
            mu_skill_book_set_use_state(b, &env);
            i += 2;
        } else if (!strcmp(op, "master")) {
            mu_master_tree *tree = mu_skill_book_master(b);
            printf("{\"tree_nodes\": %d, \"tree_tips\": %d, \"master_points\": %d, \"master_learned\": %d, "
                   "\"level\": %d, \"damage\": %d}\n", tree->nnodes, tree->ntips,
                   mu_skill_book_master_env(b)->points, tree->nlearned, mu_master_level(tree, a),
                   mu_master_skill_damage(tree, mu_skill_book_env(b), a, NULL, NULL));
            i++;
        } else if (!strcmp(op, "masterlearn")) {
            uint8_t p[8];
            mu_master_request(p, sizeof p, a);
            printf("{\"master_answer\": %d}\n", mu_skill_book_demo_master_request(b, p, sizeof p));
            i++;
        } else if (!strcmp(op, "select")) {
            printf("{\"select\": %d, \"selected\": %d}\n", mu_skill_book_select_slot(b, a), (int)mu_skill_book_selected(b));
            i++;
        } else if (!strcmp(op, "cast")) {
            int32_t ev[2][2];
            int n = 0, potion = 0;
            int r = mu_skill_book_cast(b, a, ev, &n, &potion);
            printf("{\"cast\": \"%s\", \"events\": [", mu_skill_cast_name(r));
            for (int k = 0; k < n; k++)
                printf("%s[%d, %d]", k ? ", " : "", ev[k][0], ev[k][1]);
            printf("], \"potion\": %d, \"mana\": %d, \"ag\": %d, \"left\": %.3f}\n", potion,
                   mu_skill_book_hero(b)->mana, mu_skill_book_hero(b)->ag, (double)mu_skill_book_delay_left(b, a));
            i++;
        } else if (!strcmp(op, "tick")) {
            mu_skill_book_tick(b, a);
            i++;
        } else if (!strcmp(op, "tip")) {
            static char title[4096], body[65536];
            int ok = mu_skill_book_tooltip(b, a, title, sizeof title, body, sizeof body);
            mu_skill_tip lines;
            mu_skill_book_tooltip_lines(b, a, &lines);
            printf("{\"tip\": %d, \"lines\": %d, \"title\": \"", ok, ok ? lines.count : 0);
            for (const char *p = ok ? title : ""; *p; p++)
                printf(*p == '"' || *p == '\\' ? "\\%c" : "%c", *p);
            printf("\", \"body\": \"");
            for (const char *p = ok ? body : ""; *p; p++)
                printf(*p == '"' || *p == '\\' ? "\\%c" : *p == '\n' ? "\\n" : "%c", *p);
            printf("\"}\n");
            i++;
        } else if (!strcmp(op, "icon")) {
            mu_skill_icon ic;
            int ok = mu_skill_book_icon(b, a, &ic);
            printf("{\"icon\": %d, \"bitmap\": %d, \"file\": \"%s\", \"u\": %.5f, \"v\": %.5f}\n", ok, ok ? ic.bitmap : 0,
                   ok && mu_skill_icon_file(ic.bitmap) ? mu_skill_icon_file(ic.bitmap) : "", ok ? (double)ic.u : 0.0,
                   ok ? (double)ic.v : 0.0);
            i++;
        } else if (!strcmp(op, "stamp")) {
            mu_skill_book_stamp_open(b, &stamp);
            printf("{\"stamp_pages\": %d}\n", stamp.pages);
        } else if (!strcmp(op, "slot")) {
            printf("{\"slot\": %d, \"skill\": %d}\n", a, (int)mu_skill_book_stamp_skill(b, &stamp, a));
            i++;
        } else if (!strcmp(op, "drop") && i + 2 < argc) {
            printf("{\"drop\": %d}\n", mu_skill_book_stamp_drop(b, &stamp, atoi(argv[i + 1]), atoi(argv[i + 2])));
            i += 2;
        } else if (!strcmp(op, "cancel")) {
            mu_skill_book_stamp_cancel(b, &stamp);
        } else if (!strcmp(op, "demofile") && i + 1 < argc) {
            printf("{\"demofile\": %d}\n", mu_skill_demo_load(&model, argv[i + 1]));
            i++;
        } else if (!strcmp(op, "learn") || !strcmp(op, "forget")) {
            printf("{\"%s\": %d}\n", op, mu_skill_book_demo_learn(b, a, op[0] == 'f'));
            i++;
        } else if (!strcmp(op, "save")) {
            mu_skill_book_stamp_save(b);
        } else if (!strcmp(op, "tab")) {
            printf("{\"tab_pages\": %d}\n", mu_skill_book_stamp_tab(b, &stamp, a));
            i++;
        } else if (!strcmp(op, "packet") && i + 1 < argc) {
            uint8_t pk[512];
            size_t n = 0;
            for (const char *p = argv[i + 1]; p[0] && p[1] && n < sizeof pk; p += 2) {
                unsigned v;
                sscanf(p, "%2x", &v);
                pk[n++] = (uint8_t)v;
            }
            printf("{\"packet\": %d}\n", mu_skill_book_receive(b, pk, n));
            i++;
        } else if (!strcmp(op, "tree4") && i + 2 < argc) {
            if (!t4) {
                t4 = mu_skill_tree4_open(argv[1], b);
                mu_skill_tree4_host host = {NULL, NULL, t4_invoke, t4_box, t4_confirm};
                mu_skill_tree4_set_host(t4, &host);
            }
            mu_skill_tree4_enter(t4, a);
            int r = mu_skill_tree4_demo_login(t4, atoi(argv[i + 2]));
            printf("{\"tree4\": %d, \"records\": %zu, \"invokes\": %d}\n", r, mu_skill_tree4_records(t4), t4_invokes);
            i += 2;
        } else if (!strcmp(op, "t4click") && t4) {
            mu_t4_window *w = mu_skill_tree4_window(t4);
            int boxes = t4_boxes, opened = mu_t4_click(w, mu_skill_tree4_env(t4), a), answered = 0;
            uint8_t group, req[16];
            uint16_t skill, idx;
            if (opened && mu_t4_confirm(w, 0, &group, &skill, &idx))
                answered = mu_skill_tree4_demo_request(t4, req, mu_t4_request(req, sizeof req, group, skill, idx));
            printf("{\"t4click\": %d, \"answered\": %d, \"boxes\": %d}\n", opened, answered, t4_boxes - boxes);
            i++;
        } else if (!strcmp(op, "t4tab") && t4) {
            mu_t4_change_tab(mu_skill_tree4_window(t4), mu_skill_tree4_env(t4), a);
            printf("{\"t4tab\": %d}\n", a);
            i++;
        } else if (!strcmp(op, "t4state") && t4) {
            static char json[1 << 16];
            mu_t4_dump(mu_skill_tree4_window(t4), json, sizeof json);
            printf("{\"t4state\": %s}\n", json);
        } else if (!strcmp(op, "print")) {
            const mu_skill_hero *h = mu_skill_book_hero(b);
            const mu_skill_hotkeys *k = mu_skill_book_hotkeys(b);
            printf("{\"learned\": [");
            for (int j = 0; j < h->count; j++)
                printf("%s%d", j ? ", " : "", h->skills[j]);
            printf("], \"bar\": [");
            for (int j = 0; j < MU_SKILL_SLOTS; j++)
                printf("%s%d", j ? ", " : "", k->slots[j]);
            printf("], \"window\": [");
            for (int j = 0; j < MU_SKILL_SLOTS; j++) {
                mu_skill_stamp view = stamp;
                view.select_page = j / 5;
                printf("%s%d", j ? ", " : "", (int)mu_skill_book_stamp_skill(b, &view, j % 5));
            }
            const mu_skill_stamp_mgr *sm = mu_skill_book_stamp_mgr(b);
            printf("], \"basic\": [");
            for (int j = 0; j < sm->basic.count; j++)
                printf("%s[%d, %d, %d]", j ? ", " : "", sm->basic.items[j]->base, sm->basic.items[j]->learned,
                       sm->basic.items[j]->imprint);
            printf("], \"selected\": %d, \"current\": %d, \"class_index\": %d}\n", k->selected, h->current,
                   h->class_index);
        } else {
            fprintf(stderr, "unknown op %s\n", op);
            return 2;
        }
    }
    mu_skill_tree4_close(t4);
    mu_skill_book_close(b);
    mu_lang_free(lang);
    return 0;
}
