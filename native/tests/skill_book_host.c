/* Test host for native/core/mu_skill.c (NATIVE-SKILL-001).
 *
 *   skill-book-host LANG_DIR GAME_ROOT|- [OP ...]
 *
 * Loads the Lang plaintext (core/mu_lang) and SkillTooltipText.bmd under GAME_ROOT/Data/Local, then runs:
 *   demo CLASS | stats STR AGI VIT ENE CMD MANA AG | feed | select SLOT | cast SKILL | tick MS | tip SKILL
 *   | icon SKILL | stamp | slot N | drop FROM TO | cancel | print
 * Each op prints one JSON line.  Synthetic data in the tests; no client bytes. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_lang.h"
#include "../core/mu_skill.h"

int main(int argc, char **argv)
{
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
    mu_skill_stamp stamp;
    mu_skill_book_stamp_open(b, &stamp);
    printf("{\"records\": %zu, \"tooltips\": %zu}\n", mu_skill_book_count(b), mu_skill_book_tooltips(b));
    for (int i = 3; i < argc; i++) {
        const char *op = argv[i];
        int a = i + 1 < argc ? atoi(argv[i + 1]) : 0;
        if (!strcmp(op, "demo")) {
            printf("{\"demo\": %d}\n", mu_skill_book_demo(b, a));
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
        } else if (!strcmp(op, "print")) {
            const mu_skill_hero *h = mu_skill_book_hero(b);
            const mu_skill_hotkeys *k = mu_skill_book_hotkeys(b);
            printf("{\"learned\": [");
            for (int j = 0; j < h->count; j++)
                printf("%s%d", j ? ", " : "", h->skills[j]);
            printf("], \"bar\": [");
            for (int j = 0; j < MU_SKILL_SLOTS; j++)
                printf("%s%d", j ? ", " : "", k->slots[j]);
            printf("], \"selected\": %d, \"current\": %d, \"class_index\": %d}\n", k->selected, h->current,
                   h->class_index);
        } else {
            fprintf(stderr, "unknown op %s\n", op);
            return 2;
        }
    }
    mu_skill_book_close(b);
    mu_lang_free(lang);
    return 0;
}
