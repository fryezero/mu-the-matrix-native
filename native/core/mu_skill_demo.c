/* OFFLINE DEMO server for the hero's skills (NATIVE-SKILL-002); see mu_skill.h.
 *
 * The real game's server sends the skill list (opcode 0xA0 sub 0x20) and the saved hotkeys (0xA0 sub 0x03) when the
 * character enters the world, and one skill added / removed (sub 0x20 with 0xFE / 0xFF) when a skill is learned or
 * lost.  This demo stands in for it: it builds those packets from a small table (built in, or a demo file) and the
 * client's own handlers (reconstructed/skill/skill_list.c) take them. */
#include "mu_skill.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/skill/skill_list.h"

#define DEMO_CLASSES 16
#define DEMO_SKILLS 64

typedef struct demo_class {
    int32_t skills[DEMO_SKILLS];
    int count;
    int32_t keys[MU_SKILL_SLOTS];     /* the saved bar: key 1..9, 0 (-1 none) */
    int has_keys;
} demo_class;

static demo_class demo[DEMO_CLASSES];
static int demo_ready;

static void demo_set(int ci, const int32_t *skills, const int32_t *keys)
{
    demo_class *d = &demo[ci];
    d->count = 0;
    for (const int32_t *p = skills; *p && d->count < DEMO_SKILLS; p++)
        d->skills[d->count++] = *p;
    for (int i = 0; i < MU_SKILL_SLOTS; i++)
        d->keys[i] = keys ? keys[i] : (i < d->count ? d->skills[i] : -1);
    d->has_keys = 1;
}

/* Built-in demo lists (skill indices of the classic classes). */
static void demo_defaults(void)
{
    static const int32_t DW[] = {17, 4, 11, 3, 6, 2, 7, 1, 5, 8, 9, 10, 12, 14, 13, 16, 38, 39, 0};
    /* the demo hero (Blade Knight): melee skills, Blood Storm (a master skill with a 5 s delay)
     */
    static const int32_t DK[] = {19, 20, 21, 22, 23, 41, 42, 43, 44, 18, 47, 48, 49, 344, 0};
    static const int32_t DK_KEYS[MU_SKILL_SLOTS] = {19, 41, 22, 344, 42, 43, 18, 20, 21, 23};
    static const int32_t ELF[] = {24, 26, 27, 28, 30, 31, 32, 51, 52, 33, 34, 35, 36, 0};
    static const int32_t ANY[] = {17, 4, 9, 10, 14, 22, 41, 24, 26, 3, 6, 2, 0};
    for (int ci = 0; ci < DEMO_CLASSES; ci++)
        demo_set(ci, ANY, NULL);
    demo_set(0, DW, NULL);
    demo_set(1, DK, DK_KEYS);
    demo_set(2, ELF, NULL);
    demo_ready = 1;
}

/* A demo file: "list CLASS SKILL..." and "keys CLASS K1 K2 .. K9 K0" (-1 none) lines, '#' comments. */
int mu_skill_demo_load(const char *path)
{
    if (!demo_ready)
        demo_defaults();
    FILE *f = path ? fopen(path, "r") : NULL;
    if (!f)
        return -1;
    char line[2048];
    int n = 0;
    while (fgets(line, sizeof line, f)) {
        char word[16];
        int ci, used;
        if (line[0] == '#' || sscanf(line, "%15s %d%n", word, &ci, &used) != 2 || ci < 0 || ci >= DEMO_CLASSES)
            continue;
        const char *p = line + used;
        int32_t v[DEMO_SKILLS + 1];
        int k = 0;
        char *end;
        for (long x = strtol(p, &end, 0); end != p && k < DEMO_SKILLS; x = strtol(p, &end, 0)) {
            v[k++] = (int32_t)x;
            p = end;
        }
        if (!strcmp(word, "list")) {
            v[k] = 0;
            demo_class *d = &demo[ci];
            d->count = 0;
            for (int i = 0; i < k; i++)
                if (v[i] > 0)
                    d->skills[d->count++] = v[i];
            n++;
        } else if (!strcmp(word, "keys")) {
            for (int i = 0; i < MU_SKILL_SLOTS; i++)
                demo[ci].keys[i] = i < k ? v[i] : -1;
            demo[ci].has_keys = 1;
            n++;
        }
    }
    fclose(f);
    return n;
}

int mu_skill_book_demo_login(mu_skill_book *b, int32_t class_byte)
{
    if (!b)
        return 0;
    if (!demo_ready)
        demo_defaults();
    int ci = class_byte & 0xf;
    const demo_class *d = &demo[ci];
    /* DEMO class map: without the records' class maps (skills_class.tsv) the demo's own list says which skills
     * the class has (the stamp manager's tabs are built from the class map) */
    if (!mu_skill_book_has_classes(b))
        for (int i = 0; i < d->count; i++)
            mu_skill_book_allow(b, d->skills[i], ci);
    mu_skill_book_enter(b, class_byte);
    uint8_t p[1024];
    size_t n = mu_skill_list_packet(p, sizeof p, 0, d->skills, d->count);
    if (n)
        mu_skill_book_receive(b, p, n);
    if (d->has_keys) {
        int32_t keys[MU_SKILL_SLOTS];          /* the packet's order: key 0 is the bar's tenth slot */
        for (int i = 0; i < MU_SKILL_SLOTS; i++)
            keys[(i + 1) % MU_SKILL_SLOTS] = d->keys[i];
        n = mu_skill_keys_packet(p, sizeof p, keys);
        if (n)
            mu_skill_book_receive(b, p, n);
    }
    mu_skill_book_demo_master_login(b);
    return mu_skill_book_hero(b)->count;
}

int mu_skill_book_demo(mu_skill_book *b, int32_t class_index)
{
    return mu_skill_book_demo_login(b, class_index);
}

int mu_skill_book_demo_learn(mu_skill_book *b, int32_t skill, int forget)
{
    uint8_t p[16];
    size_t n = mu_skill_list_packet(p, sizeof p, forget ? 0xff : 0xfe, &skill, 1);
    return n ? mu_skill_book_receive(b, p, n) : 0;
}

static void put32(uint8_t *p, uint32_t v)
{
    for (int i = 0; i < 4; i++)
        p[i] = (uint8_t)(v >> (8 * i));
}

static void putf(uint8_t *p, float value)
{
    uint32_t bits;
    memcpy(&bits, &value, 4);
    put32(p, bits);
}

int mu_skill_book_demo_master_login(mu_skill_book *b)
{
    mu_master_tree *tree = mu_skill_book_master(b);
    if (!tree)
        return 0;
    uint8_t packet[12 + 16 * MU_MASTER_NODES] = {0xc2, 0, 0, 0xa0, 0x10};
    int count = 0;
    /* Explicit demo values for the already learned master skills. These are server answers, not formulas. */
    for (int i = 0; i < tree->nnodes; i++) {
        const mu_master_node *node = &tree->nodes[i];
        const mu_skill_hero *hero = mu_skill_book_hero(b);
        if (mu_skill_learned_index(hero, node->skill) < 0)
            continue;
        uint8_t *entry = packet + 12 + 16 * count++;
        entry[0] = node->slot;
        entry[1] = 1;
        putf(entry + 4, 25.0f);
        putf(entry + 8, 30.0f);
        entry[12] = 1;
    }
    size_t size = 12 + 16 * (size_t)count;
    packet[1] = (uint8_t)(size >> 8);
    packet[2] = (uint8_t)size;
    put32(packet + 8, (uint32_t)count);
    return mu_skill_book_receive(b, packet, size);
}

int mu_skill_book_demo_master_request(mu_skill_book *b, const uint8_t *p, size_t size)
{
    if (!b || size != 8 || p[0] != 0xc1 || p[1] != 8 || p[2] != 1 || p[3] != 0x16)
        return 0;
    uint32_t skill = (uint32_t)p[4] | (uint32_t)p[5] << 8 | (uint32_t)p[6] << 16 | (uint32_t)p[7] << 24;
    mu_master_tree *tree = mu_skill_book_master(b);
    mu_master_env *env = mu_skill_book_master_env(b);
    const mu_master_node *node = NULL;
    for (int i = 0; i < tree->nnodes; i++)
        if ((uint32_t)tree->nodes[i].skill == skill)
            node = &tree->nodes[i];
    if (!node)
        return 0;
    uint8_t level = mu_master_level(tree, (int32_t)skill);
    uint8_t answer[0x1d] = {0xc1, 0x1d, 0xa0, 0x14};
    int points = env->points;
    answer[4] = points < node->cost || level >= node->max_level ? 7 : 1;
    if (answer[4] == 1)
        points -= node->cost;
    answer[6] = (uint8_t)points;
    answer[7] = (uint8_t)(points >> 8);
    answer[8] = node->slot;
    put32(answer + 12, skill);
    answer[16] = (uint8_t)(level + 1);
    putf(answer + 20, 25.0f + level * 5.0f);
    putf(answer + 24, 30.0f + level * 5.0f);
    answer[28] = 1;
    return mu_skill_book_receive(b, answer, sizeof answer);
}
