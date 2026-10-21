/* mu-lang: query the Lang.mpr tables read from the client (NATIVE-LANG-001).
 *
 *   mu-lang DIR summary            counts as JSON
 *   mu-lang DIR text N             GlobalText[N]
 *   mu-lang DIR skill N [MASTER]   skill record and GetSkillInformation's mana/distance/AG
 *   mu-lang DIR map WORLD          map name (map-name function 0x016baaa6)
 *   mu-lang DIR enchant CODE [MESH] EnchantEffect colour (0x010ffd7a, or 0x010ffddb with MESH)
 *   mu-lang DIR npc N | gate N | move N | dialog N
 *   mu-lang DIR buff N [VALUE]     BuffEffect record (0x010de66f) and its InfoPopup lines (0x01298a54)
 *   mu-lang DIR charinfo CLASS     the character window rows of a class index (CharacterInfoSetup, 0x00b3dedc)
 *   mu-lang DIR soul CODE          MonsterSoulConversion has the item code (0x01135146): 1 / 0
 *
 * DIR holds the plaintext scripts/live_lang_to_plain.py wrote (local only). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_lang.h"

static void quoted(const char *s)
{
    putchar('"');
    for (; s && *s; ++s) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\')
            printf("\\%c", c);
        else if (c < 0x20 || c >= 0x7f)
            printf("\\u%04x", c);
        else
            putchar(c);
    }
    putchar('"');
}

static int usage(void)
{
    fprintf(stderr, "usage: mu-lang DIR summary|text N|skill N [MASTER]|map WORLD|enchant CODE [MESH]|"
                    "npc N|gate N|move N|dialog N|buff N [VALUE]|charinfo CLASS|soul CODE\n");
    return 2;
}

int main(int argc, char **argv)
{
    if (argc < 3)
        return usage();
    mu_lang *L = mu_lang_load(argv[1]);
    if (!L) {
        fprintf(stderr, "mu-lang: no table in %s\n", argv[1]);
        return 1;
    }
    const char *cmd = argv[2];
    int32_t n = argc > 3 ? (int32_t)strtol(argv[3], NULL, 0) : 0;
    int status = 0;
    if (!strcmp(cmd, "summary")) {
        mu_lang_counts c;
        mu_lang_get_counts(L, &c);
        printf("{\"text\": %zu, \"skills\": %zu, \"gates\": %zu, \"moves\": %zu, \"npcs\": %zu, \"dialog\": %zu, "
               "\"enchant_codes\": %zu, \"enchant_entries\": %zu, \"enchant_default\": %d, \"buffs\": %zu, "
               "\"charinfo\": %zu, \"skillreq\": %zu, \"soulconv\": %zu}\n",
               c.text, c.skills, c.gates, c.moves, c.npcs, c.dialog, c.enchant_codes, c.enchant_entries,
               c.enchant_default, c.buffs, c.charinfo, c.skillreq, c.soulconv);
    } else if (!strcmp(cmd, "buff") && argc > 3) {
        const mu_lang_buff *b = mu_lang_buff_get(L, n);
        if (!b) {
            status = 1;
        } else {
            mu_lang_buff_values v;
            memset(&v, 0, sizeof v);
            v.value2_kind = -1;
            v.hero_value = argc > 4 ? (int32_t)strtol(argv[4], NULL, 0) : 0;
            char lines[16][256];
            int k = mu_lang_buff_tooltip(L, n, &v, lines, 16);
            printf("{\"index\": %d, \"group\": %d, \"item\": [%d, %d], \"type\": %d, \"value_kind\": %d, \"name\": ",
                   b->index, b->group, b->item_group, b->item_index, b->type, b->value_kind);
            quoted(b->name);
            printf(", \"tooltip\": [");
            for (int i = 0; i < k; i++) {
                printf(i ? ", " : "");
                quoted(lines[i]);
            }
            mu_lang_addbuff a;
            if (mu_lang_buff_addbuff(L, n, &a))
                printf("], \"addbuff\": {\"is_debuff\": %d, \"is_cash\": %d, \"has_detail\": %d, \"detail\": %d}}\n",
                       a.is_debuff, a.is_cash, a.has_detail, a.detail);
            else
                printf("], \"addbuff\": null}\n");
        }
    } else if (!strcmp(cmd, "soul") && argc > 3) {
        printf("%d\n", mu_lang_soul_conversion(L, n));
    } else if (!strcmp(cmd, "charinfo") && argc > 3) {
        const mu_lang_charinfo *rows[256];
        int k = mu_lang_charinfo_rows(L, n, rows, 256);
        printf("[");
        for (int i = 0; i < k; i++) {
            printf("%s{\"id\": %d, \"type\": %d, \"sort\": %d, \"button\": %d, \"label\": ", i ? ", " : "",
                   rows[i]->id, rows[i]->type, rows[i]->sort, rows[i]->button);
            quoted(rows[i]->label);
            printf("}");
        }
        printf("]\n");
        status = k == 0;
    } else if (!strcmp(cmd, "text") && argc > 3) {
        const char *s = mu_lang_text(L, n);
        if (s)
            printf("%s\n", s);
        status = !s;
    } else if (!strcmp(cmd, "dialog") && argc > 3) {
        const char *s = mu_lang_dialog(L, n);
        if (s)
            printf("%s\n", s);
        status = !s;
    } else if (!strcmp(cmd, "skill") && argc > 3) {
        int32_t mana = 0, distance = 0, ag = 0;
        int32_t master = argc > 4 ? (int32_t)strtol(argv[4], NULL, 0) : 0;
        const char *name = mu_lang_skill_info(L, n, master, &mana, &distance, &ag);
        const mu_lang_skill *s = mu_lang_skill_get(L, n);
        if (!s) {
            status = 1;
        } else {
            printf("{\"index\": %d, \"name\": ", s->index);
            quoted(name);
            printf(", \"level\": %d, \"damage\": %d, \"mana\": %d, \"ag\": %d, \"distance\": %d, \"delay\": %d, "
                   "\"icon\": %d, \"use_type\": %d, \"mastery\": %d, \"type\": %d, \"skip\": %d}\n",
                   s->level, s->damage, mana, ag, distance, s->delay, s->icon, s->use_type, s->mastery, s->type,
                   s->skip);
        }
    } else if (!strcmp(cmd, "map") && argc > 3) {
        const char *s = mu_lang_map_name(L, n);
        printf("{\"world\": %d, \"globaltext\": %d, \"name\": ", n, mu_lang_map_text_index(n));
        if (s)
            quoted(s);
        else
            printf("null");
        printf("}\n");
    } else if (!strcmp(cmd, "enchant") && argc > 3) {
        float rgb[3];
        int ok = argc > 4 ? mu_lang_enchant_mesh(L, n, (int32_t)strtol(argv[4], NULL, 0), rgb)
                          : mu_lang_enchant_first(L, n, rgb);
        if (ok)
            printf("{\"code\": %d, \"entries\": %zu, \"rgb\": [%.9g, %.9g, %.9g]}\n", n, mu_lang_enchant_entries(L, n),
                   (double)rgb[0], (double)rgb[1], (double)rgb[2]);
        status = !ok;
    } else if (!strcmp(cmd, "npc") && argc > 3) {
        const mu_lang_npc *c = mu_lang_npc_get(L, n);
        if (c) {
            printf("{\"index\": %d, \"name\": ", c->index);
            quoted(c->name);
            printf(", \"x1c\": %d, \"x20\": %d, \"x24\": %d}\n", c->x1c, c->x20, c->x24);
        }
        status = !c;
    } else if (!strcmp(cmd, "gate") && argc > 3) {
        const mu_lang_gate *g = mu_lang_gate_get(L, n);
        if (g)
            printf("{\"index\": %d, \"flag\": %d, \"world\": %d, \"x1\": %d, \"y1\": %d, \"x2\": %d, \"y2\": %d, "
                   "\"target\": %d, \"dir\": %d, \"min_level\": %d, \"max_level\": %d}\n",
                   g->index, g->flag, g->world, g->x1, g->y1, g->x2, g->y2, g->target, g->dir, g->min_level,
                   g->max_level);
        status = !g;
    } else if (!strcmp(cmd, "move") && argc > 3) {
        const mu_lang_move *m = mu_lang_move_get(L, n);
        if (m) {
            const mu_lang_gate *g = mu_lang_gate_get(L, m->gate);
            printf("{\"index\": %d, \"name\": ", m->index);
            quoted(m->name);
            printf(", \"server_name\": ");
            quoted(m->server_name);
            printf(", \"zen\": %d, \"min_level\": %d, \"max_level\": %d, \"gate\": %d, \"world\": %d}\n", m->zen,
                   m->min_level, m->max_level, m->gate, g ? g->world : -1);
        }
        status = !m;
    } else {
        status = usage();
    }
    mu_lang_free(L);
    return status;
}
