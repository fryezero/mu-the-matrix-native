/* Lang.mpr tables from local plaintext files (NATIVE-LANG-001); see mu_lang.h. */
#include "mu_lang.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_lang_maps.h"

typedef struct text_entry {
    int32_t index;
    char *text;
} text_entry;

typedef struct enchant_entry {
    int32_t code, mesh;
    float rgb[3];
} enchant_entry;

typedef struct enchant_code {
    int32_t code;
    size_t first, count;              /* range in the entry array, in file (vector) order */
} enchant_code;

struct mu_lang {
    text_entry *text, *dialog;
    size_t ntext, ndialog;
    mu_lang_skill *skills;
    size_t nskills;
    mu_lang_gate *gates;
    size_t ngates;
    mu_lang_move *moves;
    size_t nmoves;
    mu_lang_npc *npcs;
    size_t nnpcs;
    enchant_entry *enchant;
    size_t nenchant;
    enchant_code *codes;
    size_t ncodes;
    int has_enchant, has_enchant_default;
    float enchant_default[3];
    /* NATIVE-FIDELITY-001 */
    struct int_row *pentagram, *invenanim, *legendary;
    size_t npentagram, ninvenanim, nlegendary;
    int32_t pentagram_default, legendary_default[4];
    int has_pentagram, has_legendary;
    mu_lang_cash_set *cash_sets;
    mu_lang_cash_item *cash_items;
    size_t ncash_sets, ncash_items;
    /* NATIVE-LANG-002 */
    mu_lang_buff *buffs, buff_default;
    size_t nbuffs;
    int has_buffs;
    mu_lang_charinfo *charinfo, charinfo_default;
    size_t ncharinfo;
    int has_charinfo;
    mu_lang_skillreq *skillreq;
    size_t nskillreq;
    struct int_row *soulconv;
    size_t nsoulconv;
};

typedef struct int_row {
    int32_t key;
    int32_t v[4];
} int_row;

/* ---- reading --------------------------------------------------------- */

static char *read_file(const char *dir, const char *name, size_t *len)
{
    char path[4096];
    snprintf(path, sizeof path, "%s/%s", dir, name);
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    char *buf = NULL;
    size_t cap = 0, n = 0;
    for (;;) {
        if (n + 65536 + 1 > cap) {
            size_t ncap = cap ? cap * 2 : 1u << 20;
            char *nb = realloc(buf, ncap);
            if (!nb) {
                free(buf);
                fclose(f);
                return NULL;
            }
            buf = nb;
            cap = ncap;
        }
        size_t got = fread(buf + n, 1, 65536, f);
        n += got;
        if (got < 65536)
            break;
    }
    fclose(f);
    buf[n] = 0;
    *len = n;
    return buf;
}

/* Splits the next line (without its LF) off *cursor. */
static char *next_line(char **cursor)
{
    char *s = *cursor;
    if (!s || !*s)
        return NULL;
    char *nl = strchr(s, '\n');
    if (nl) {
        *nl = 0;
        *cursor = nl + 1;
    } else {
        *cursor = s + strlen(s);
    }
    size_t l = strlen(s);
    if (l && s[l - 1] == '\r')
        s[l - 1] = 0;
    return s;
}

/* Splits a line into TAB fields in place. */
static int split(char *line, char **fields, int max)
{
    int n = 0;
    fields[n++] = line;
    for (char *p = line; *p && n < max; ++p)
        if (*p == '\t') {
            *p = 0;
            fields[n++] = p + 1;
        }
    return n;
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    if (c >= 'A' && c <= 'F')
        return c - 'A' + 10;
    return -1;
}

/* The converter's escapes: \t \n \r \\ and \xHH. */
static char *unescape(const char *s)
{
    size_t l = strlen(s);
    char *out = malloc(l + 1), *o = out;
    if (!out)
        return NULL;
    for (size_t i = 0; i < l; ++i) {
        if (s[i] == '\\' && i + 1 < l) {
            char c = s[++i];
            if (c == 'x' && i + 2 < l + 1 && hexval(s[i + 1]) >= 0 && hexval(s[i + 2]) >= 0) {
                *o++ = (char)(hexval(s[i + 1]) * 16 + hexval(s[i + 2]));
                i += 2;
            } else {
                *o++ = c == 't' ? '\t' : c == 'n' ? '\n' : c == 'r' ? '\r' : c;
            }
        } else {
            *o++ = s[i];
        }
    }
    *o = 0;
    return out;
}

static int to_int(const char *s, int32_t *out)
{
    char *end = NULL;
    errno = 0;
    long v = strtol(s, &end, 10);
    if (errno || end == s || *end)
        return -1;
    *out = (int32_t)v;
    return 0;
}

static void *grow(void *array, size_t n, size_t *cap, size_t size)
{
    if (n < *cap)
        return array;
    size_t ncap = *cap ? *cap * 2 : 256;
    void *na = realloc(array, ncap * size);
    if (na)
        *cap = ncap;
    return na;
}

static int cmp_text(const void *a, const void *b)
{
    int32_t x = ((const text_entry *)a)->index, y = ((const text_entry *)b)->index;
    return (x > y) - (x < y);
}

#define DEFINE_CMP(name, type)                                                   \
    static int name(const void *a, const void *b)                                \
    {                                                                            \
        int32_t x = ((const type *)a)->index, y = ((const type *)b)->index;      \
        return (x > y) - (x < y);                                                \
    }
DEFINE_CMP(cmp_skill, mu_lang_skill)
DEFINE_CMP(cmp_gate, mu_lang_gate)
DEFINE_CMP(cmp_move, mu_lang_move)
DEFINE_CMP(cmp_npc, mu_lang_npc)

static int cmp_code(const void *a, const void *b)
{
    int32_t x = ((const enchant_code *)a)->code, y = ((const enchant_code *)b)->code;
    return (x > y) - (x < y);
}

static int load_text(const char *dir, const char *name, text_entry **out, size_t *count)
{
    size_t len = 0;
    char *buf = read_file(dir, name, &len);
    if (!buf)
        return 0;
    size_t cap = 0, n = 0;
    text_entry *t = NULL;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[2];
        int32_t index;
        if (split(line, f, 2) != 2 || to_int(f[0], &index))
            continue;
        text_entry *nt = grow(t, n, &cap, sizeof *t);
        if (!nt)
            break;
        t = nt;
        t[n].index = index;
        t[n].text = unescape(f[1]);
        if (t[n].text)
            ++n;
    }
    free(buf);
    qsort(t, n, sizeof *t, cmp_text);
    *out = t;
    *count = n;
    return n > 0;
}

static int load_skills(mu_lang *L, const char *dir)
{
    size_t len = 0;
    char *buf = read_file(dir, "skills.tsv", &len);
    if (!buf)
        return 0;
    size_t cap = 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[20];
        if (split(line, f, 20) != 20)
            continue;
        mu_lang_skill s;
        memset(&s, 0, sizeof s);
        int32_t v[18];
        int bad = to_int(f[0], &s.index);
        for (int k = 0; k < 18; ++k)
            bad |= to_int(f[2 + k], &v[k]);
        if (bad)
            continue;
        s.level = v[0];
        s.damage = v[1];
        s.mana = v[2];
        s.ag = v[3];
        s.distance = v[4];
        s.delay = v[5];
        for (int k = 0; k < 5; ++k)
            s.req[k] = v[6 + k];
        s.mastery = v[11];
        s.use_type = v[12];
        s.brand = v[13];
        s.master_bonus = (uint8_t)v[14];
        s.icon = v[15];
        s.type = v[16];
        s.skip = (uint8_t)v[17];
        s.name = unescape(f[1]);
        mu_lang_skill *ns = grow(L->skills, L->nskills, &cap, sizeof *ns);
        if (!ns || !s.name) {
            free((char *)s.name);
            break;
        }
        L->skills = ns;
        L->skills[L->nskills++] = s;
    }
    free(buf);
    qsort(L->skills, L->nskills, sizeof *L->skills, cmp_skill);
    return L->nskills > 0;
}

static int load_gates(mu_lang *L, const char *dir)
{
    size_t len = 0;
    char *buf = read_file(dir, "gates.tsv", &len);
    if (!buf)
        return 0;
    size_t cap = 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[11];
        if (split(line, f, 11) != 11)
            continue;
        int32_t v[11];
        int bad = 0;
        for (int k = 0; k < 11; ++k)
            bad |= to_int(f[k], &v[k]);
        if (bad)
            continue;
        mu_lang_gate g = {v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8], v[9], v[10]};
        mu_lang_gate *ng = grow(L->gates, L->ngates, &cap, sizeof *ng);
        if (!ng)
            break;
        L->gates = ng;
        L->gates[L->ngates++] = g;
    }
    free(buf);
    qsort(L->gates, L->ngates, sizeof *L->gates, cmp_gate);
    return L->ngates > 0;
}

static int load_moves(mu_lang *L, const char *dir)
{
    size_t len = 0;
    char *buf = read_file(dir, "moves.tsv", &len);
    if (!buf)
        return 0;
    size_t cap = 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[11];
        if (split(line, f, 11) != 11)
            continue;
        mu_lang_move m;
        memset(&m, 0, sizeof m);
        int32_t v[8];
        int bad = to_int(f[0], &m.index);
        for (int k = 0; k < 8; ++k)
            bad |= to_int(f[3 + k], &v[k]);
        if (bad)
            continue;
        m.id = v[0];
        m.zen = v[1];
        m.min_level = v[2];
        m.max_level = v[3];
        m.gate = v[4];
        m.x44 = v[5];
        m.x48 = v[6];
        m.x4c = v[7];
        m.name = unescape(f[1]);
        m.server_name = unescape(f[2]);
        mu_lang_move *nm = grow(L->moves, L->nmoves, &cap, sizeof *nm);
        if (!nm || !m.name || !m.server_name) {
            free((char *)m.name);
            free((char *)m.server_name);
            break;
        }
        L->moves = nm;
        L->moves[L->nmoves++] = m;
    }
    free(buf);
    qsort(L->moves, L->nmoves, sizeof *L->moves, cmp_move);
    return L->nmoves > 0;
}

static int load_npcs(mu_lang *L, const char *dir)
{
    size_t len = 0;
    char *buf = read_file(dir, "npcnames.tsv", &len);
    if (!buf)
        return 0;
    size_t cap = 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[5];
        if (split(line, f, 5) != 5)
            continue;
        mu_lang_npc c;
        memset(&c, 0, sizeof c);
        int32_t x24 = 0;
        if (to_int(f[0], &c.index) || to_int(f[2], &c.x1c) || to_int(f[3], &c.x20) || to_int(f[4], &x24))
            continue;
        c.x24 = (uint8_t)x24;
        c.name = unescape(f[1]);
        mu_lang_npc *nn = grow(L->npcs, L->nnpcs, &cap, sizeof *nn);
        if (!nn || !c.name) {
            free((char *)c.name);
            break;
        }
        L->npcs = nn;
        L->npcs[L->nnpcs++] = c;
    }
    free(buf);
    qsort(L->npcs, L->nnpcs, sizeof *L->npcs, cmp_npc);
    return L->nnpcs > 0;
}

static int load_enchant(mu_lang *L, const char *dir)
{
    size_t len = 0;
    char *buf = read_file(dir, "enchant.tsv", &len);
    if (!buf)
        return 0;
    size_t cap = 0, ccap = 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[5];
        if (split(line, f, 5) != 5)
            continue;
        float rgb[3];
        int bad = 0;
        for (int k = 0; k < 3; ++k) {
            char *end = NULL;
            rgb[k] = strtof(f[2 + k], &end);
            bad |= end == f[2 + k] || *end;
        }
        if (bad)
            continue;
        if (!strcmp(f[0], "default")) {
            memcpy(L->enchant_default, rgb, sizeof rgb);
            L->has_enchant_default = 1;
            continue;
        }
        int32_t code, mesh = 0;
        if (to_int(f[0], &code))
            continue;
        int empty = !strcmp(f[1], "empty");
        if (!empty && to_int(f[1], &mesh))
            continue;
        /* codes arrive grouped (one map node each); a new code opens a range */
        if (!L->ncodes || L->codes[L->ncodes - 1].code != code) {
            enchant_code *nc = grow(L->codes, L->ncodes, &ccap, sizeof *nc);
            if (!nc)
                break;
            L->codes = nc;
            L->codes[L->ncodes++] = (enchant_code){code, L->nenchant, 0};
        }
        if (empty)
            continue;
        enchant_entry *ne = grow(L->enchant, L->nenchant, &cap, sizeof *ne);
        if (!ne)
            break;
        L->enchant = ne;
        L->enchant[L->nenchant] = (enchant_entry){code, mesh, {rgb[0], rgb[1], rgb[2]}};
        ++L->nenchant;
        ++L->codes[L->ncodes - 1].count;
    }
    free(buf);
    qsort(L->codes, L->ncodes, sizeof *L->codes, cmp_code);
    L->has_enchant = L->ncodes > 0 || L->has_enchant_default;
    return L->has_enchant;
}

static int cmp_row(const void *a, const void *b)
{
    int32_t x = ((const int_row *)a)->key, y = ((const int_row *)b)->key;
    return x < y ? -1 : x > y;
}

/* key<TAB>v0..v(n-1) rows; a "default" row fills *def. Returns the row count, -1 when the file is absent. */
static long load_rows(const char *dir, const char *name, int nv, int_row **out, size_t *count, int32_t *def)
{
    size_t len = 0, cap = 0;
    char *buf = read_file(dir, name, &len);
    if (!buf)
        return -1;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[6];
        if (split(line, f, 6) != nv + 1)
            continue;
        int_row r;
        memset(&r, 0, sizeof r);
        int bad = 0;
        for (int k = 0; k < nv; ++k)
            bad |= to_int(f[1 + k], &r.v[k]);
        if (bad)
            continue;
        if (!strcmp(f[0], "default")) {
            if (def)
                memcpy(def, r.v, sizeof(int32_t) * (size_t)nv);
            continue;
        }
        if (to_int(f[0], &r.key))
            continue;
        int_row *nr = grow(*out, *count, &cap, sizeof *nr);
        if (!nr)
            break;
        *out = nr;
        (*out)[(*count)++] = r;
    }
    free(buf);
    qsort(*out, *count, sizeof **out, cmp_row);
    return (long)*count;
}

static int load_cash(mu_lang *L, const char *dir)
{
    size_t len = 0, scap = 0, icap = 0;
    char *buf = read_file(dir, "cashsets.tsv", &len);
    if (!buf)
        return 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[5];
        int n = split(line, f, 5);
        if (n == 4 && !strcmp(f[0], "set")) {
            mu_lang_cash_set *ns = grow(L->cash_sets, L->ncash_sets, &scap, sizeof *ns);
            if (!ns)
                break;
            L->cash_sets = ns;
            L->cash_sets[L->ncash_sets].name = unescape(f[2]);
            L->cash_sets[L->ncash_sets].name2 = unescape(f[3]);
            ++L->ncash_sets;
        } else if (n == 4 && !strcmp(f[0], "item")) {
            mu_lang_cash_item it;
            if (to_int(f[1], &it.group) || to_int(f[2], &it.index) || to_int(f[3], &it.set))
                continue;
            mu_lang_cash_item *ni = grow(L->cash_items, L->ncash_items, &icap, sizeof *ni);
            if (!ni)
                break;
            L->cash_items = ni;
            L->cash_items[L->ncash_items++] = it;
        }
    }
    free(buf);
    return L->ncash_sets > 0;
}

/* ---- NATIVE-LANG-002 loaders ---- */

static void free_buff(mu_lang_buff *b)
{
    free((char *)b->name);
    for (int i = 0; i < b->nlines; i++)
        free((char *)b->lines[i]);
}

static int parse_buff(char **f, int n, mu_lang_buff *b)
{
    memset(b, 0, sizeof *b);
    if (n < 9)
        return -1;
    int32_t *ints[8] = {&b->index, &b->group, &b->item_group, &b->item_index, &b->type, &b->x2c, &b->x30,
                        &b->value_kind};
    for (int i = 1; i < 8; i++)
        if (to_int(f[i], ints[i]))
            return -1;
    if (strcmp(f[0], "default") && to_int(f[0], &b->index))
        return -1;
    b->name = unescape(f[8]);
    for (int i = 9; i < n && b->nlines < MU_LANG_BUFF_LINES; i++)
        b->lines[b->nlines++] = unescape(f[i]);
    return b->name ? 0 : -1;
}

DEFINE_CMP(cmp_buff, mu_lang_buff)

static int load_buffs(mu_lang *L, const char *dir)
{
    size_t len = 0, cap = 0;
    char *buf = read_file(dir, "buffs.tsv", &len);
    if (!buf)
        return 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[9 + MU_LANG_BUFF_LINES];
        int n = split(line, f, 9 + MU_LANG_BUFF_LINES);
        mu_lang_buff b;
        if (parse_buff(f, n, &b)) {
            free_buff(&b);
            continue;
        }
        if (!strcmp(f[0], "default")) {
            free_buff(&L->buff_default);
            L->buff_default = b;
            L->has_buffs = 1;
            continue;
        }
        mu_lang_buff *nb = grow(L->buffs, L->nbuffs, &cap, sizeof *nb);
        if (!nb) {
            free_buff(&b);
            break;
        }
        L->buffs = nb;
        L->buffs[L->nbuffs++] = b;
    }
    free(buf);
    qsort(L->buffs, L->nbuffs, sizeof *L->buffs, cmp_buff);
    if (L->nbuffs && !L->has_buffs) {   /* a file without the default line: the client's default record */
        L->buff_default.item_group = L->buff_default.item_index = -1;
        L->buff_default.type = L->buff_default.x2c = L->buff_default.x30 = -1;
        L->buff_default.name = unescape("null");
    }
    L->has_buffs = L->has_buffs || L->nbuffs > 0;
    return L->nbuffs > 0;
}

static int parse_charinfo(char **f, int n, mu_lang_charinfo *c)
{
    memset(c, 0, sizeof *c);
    if (n < 9)
        return -1;
    int32_t *ints[7] = {&c->id, &c->color, &c->group, &c->type, &c->sort, &c->value_color, &c->button};
    for (int i = 1; i < 7; i++)
        if (to_int(f[i], ints[i]))
            return -1;
    if (strcmp(f[0], "default") && to_int(f[0], &c->id))
        return -1;
    if (strcmp(f[7], "-"))
        for (const char *p = f[7]; *p && c->nclasses < 16; p++)
            c->classes[c->nclasses++] = (uint8_t)(*p != '0');
    c->label = unescape(f[8]);
    c->prefix = unescape(n > 9 ? f[9] : "");
    c->suffix = unescape(n > 10 ? f[10] : "");
    return c->label && c->prefix && c->suffix ? 0 : -1;
}

static void free_charinfo(mu_lang_charinfo *c)
{
    free((char *)c->label);
    free((char *)c->prefix);
    free((char *)c->suffix);
}

static int cmp_charinfo(const void *a, const void *b)
{
    int32_t x = ((const mu_lang_charinfo *)a)->id, y = ((const mu_lang_charinfo *)b)->id;
    return (x > y) - (x < y);
}

static int load_charinfo(mu_lang *L, const char *dir)
{
    size_t len = 0, cap = 0;
    char *buf = read_file(dir, "charinfo.tsv", &len);
    if (!buf)
        return 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[12];
        int n = split(line, f, 12);
        mu_lang_charinfo c;
        if (parse_charinfo(f, n, &c)) {
            free_charinfo(&c);
            continue;
        }
        if (!strcmp(f[0], "default")) {
            free_charinfo(&L->charinfo_default);
            L->charinfo_default = c;
            L->has_charinfo = 1;
            continue;
        }
        mu_lang_charinfo *nc = grow(L->charinfo, L->ncharinfo, &cap, sizeof *nc);
        if (!nc) {
            free_charinfo(&c);
            break;
        }
        L->charinfo = nc;
        L->charinfo[L->ncharinfo++] = c;
    }
    free(buf);
    qsort(L->charinfo, L->ncharinfo, sizeof *L->charinfo, cmp_charinfo);
    if (L->ncharinfo && !L->has_charinfo) {
        L->charinfo_default.label = unescape("null");
        L->charinfo_default.prefix = unescape("null");
        L->charinfo_default.suffix = unescape("null");
    }
    L->has_charinfo = L->has_charinfo || L->ncharinfo > 0;
    return L->ncharinfo > 0;
}

static int cmp_skillreq(const void *a, const void *b)
{
    int32_t x = ((const mu_lang_skillreq *)a)->key, y = ((const mu_lang_skillreq *)b)->key;
    return (x > y) - (x < y);
}

static int load_skillreq(mu_lang *L, const char *dir)
{
    size_t len = 0, cap = 0;
    char *buf = read_file(dir, "skillreq.tsv", &len);
    if (!buf)
        return 0;
    char *cursor = buf, *line;
    while ((line = next_line(&cursor))) {
        if (!*line || *line == '#')
            continue;
        char *f[8];
        if (split(line, f, 8) != 8)
            continue;
        mu_lang_skillreq r;
        int32_t *v[8] = {&r.key, &r.x00, &r.skill, &r.item_group, &r.item_index, &r.x10, &r.x14, &r.x18};
        int bad = 0;
        for (int i = 0; i < 8; i++)
            bad |= to_int(f[i], v[i]);
        if (bad)
            continue;
        mu_lang_skillreq *nr = grow(L->skillreq, L->nskillreq, &cap, sizeof *nr);
        if (!nr)
            break;
        L->skillreq = nr;
        L->skillreq[L->nskillreq++] = r;
    }
    free(buf);
    qsort(L->skillreq, L->nskillreq, sizeof *L->skillreq, cmp_skillreq);
    return L->nskillreq > 0;
}

mu_lang *mu_lang_load(const char *dir)
{
    if (!dir || !*dir)
        return NULL;
    mu_lang *L = calloc(1, sizeof *L);
    if (!L)
        return NULL;
    int any = 0;
    any |= load_text(dir, "globaltext.txt", &L->text, &L->ntext);
    any |= load_text(dir, "dialog.tsv", &L->dialog, &L->ndialog);
    any |= load_skills(L, dir);
    any |= load_gates(L, dir);
    any |= load_moves(L, dir);
    any |= load_npcs(L, dir);
    any |= load_enchant(L, dir);
    L->has_pentagram = load_rows(dir, "pentagram.tsv", 1, &L->pentagram, &L->npentagram, &L->pentagram_default) >= 0;
    any |= L->has_pentagram;
    any |= load_rows(dir, "invenanim.tsv", 4, &L->invenanim, &L->ninvenanim, NULL) > 0;
    L->legendary_default[0] = L->legendary_default[1] = L->legendary_default[2] = L->legendary_default[3] = -1;
    L->has_legendary = load_rows(dir, "legendary.tsv", 4, &L->legendary, &L->nlegendary, L->legendary_default) >= 0;
    any |= L->has_legendary;
    any |= load_cash(L, dir);
    any |= load_buffs(L, dir);
    any |= load_charinfo(L, dir);
    any |= load_skillreq(L, dir);
    any |= load_rows(dir, "soulconv.tsv", 3, &L->soulconv, &L->nsoulconv, NULL) > 0;
    if (!any) {
        mu_lang_free(L);
        return NULL;
    }
    return L;
}

mu_lang *mu_lang_load_default(void)
{
    return mu_lang_load(getenv("MU_LANG_DIR"));
}

const mu_lang *mu_lang_shared(void)
{
    static int loaded;
    static mu_lang *shared;
    if (!loaded) {
        loaded = 1;
        shared = mu_lang_load_default();
    }
    return shared;
}

void mu_lang_free(mu_lang *L)
{
    if (!L)
        return;
    for (size_t i = 0; i < L->ntext; ++i)
        free(L->text[i].text);
    for (size_t i = 0; i < L->ndialog; ++i)
        free(L->dialog[i].text);
    for (size_t i = 0; i < L->nskills; ++i)
        free((char *)L->skills[i].name);
    for (size_t i = 0; i < L->nmoves; ++i) {
        free((char *)L->moves[i].name);
        free((char *)L->moves[i].server_name);
    }
    for (size_t i = 0; i < L->nnpcs; ++i)
        free((char *)L->npcs[i].name);
    free(L->text);
    free(L->dialog);
    free(L->skills);
    free(L->gates);
    free(L->moves);
    free(L->npcs);
    free(L->enchant);
    free(L->codes);
    free(L->pentagram);
    free(L->invenanim);
    free(L->legendary);
    for (size_t i = 0; i < L->ncash_sets; ++i) {
        free((char *)L->cash_sets[i].name);
        free((char *)L->cash_sets[i].name2);
    }
    free(L->cash_sets);
    free(L->cash_items);
    for (size_t i = 0; i < L->nbuffs; ++i)
        free_buff(&L->buffs[i]);
    free_buff(&L->buff_default);
    free(L->buffs);
    for (size_t i = 0; i < L->ncharinfo; ++i)
        free_charinfo(&L->charinfo[i]);
    free_charinfo(&L->charinfo_default);
    free(L->charinfo);
    free(L->skillreq);
    free(L->soulconv);
    free(L);
}

void mu_lang_get_counts(const mu_lang *L, mu_lang_counts *out)
{
    memset(out, 0, sizeof *out);
    if (!L)
        return;
    out->text = L->ntext;
    out->skills = L->nskills;
    out->gates = L->ngates;
    out->moves = L->nmoves;
    out->npcs = L->nnpcs;
    out->dialog = L->ndialog;
    out->enchant_codes = L->ncodes;
    out->enchant_entries = L->nenchant;
    out->enchant_default = L->has_enchant_default;
    out->buffs = L->nbuffs;
    out->charinfo = L->ncharinfo;
    out->skillreq = L->nskillreq;
    out->soulconv = L->nsoulconv;
}

/* ---- lookups --------------------------------------------------------- */

static const text_entry *find_text(const text_entry *t, size_t n, int32_t index)
{
    text_entry key = {index, NULL};
    return t ? bsearch(&key, t, n, sizeof *t, cmp_text) : NULL;
}

const char *mu_lang_text(const mu_lang *L, int32_t index)
{
    const text_entry *e = L ? find_text(L->text, L->ntext, index) : NULL;
    return e ? e->text : NULL;
}

const char *mu_lang_text_or(const mu_lang *L, int32_t index, const char *fallback)
{
    const char *s = mu_lang_text(L, index);
    return s ? s : fallback;
}

const char *mu_lang_dialog(const mu_lang *L, int32_t index)
{
    const text_entry *e = L ? find_text(L->dialog, L->ndialog, index) : NULL;
    return e ? e->text : NULL;
}

const mu_lang_skill *mu_lang_skill_get(const mu_lang *L, int32_t index)
{
    mu_lang_skill key;
    key.index = index;
    return L && L->skills ? bsearch(&key, L->skills, L->nskills, sizeof key, cmp_skill) : NULL;
}

size_t mu_lang_skill_count(const mu_lang *L)
{
    return L ? L->nskills : 0;
}

const mu_lang_skill *mu_lang_skill_at(const mu_lang *L, size_t i)
{
    return L && i < L->nskills ? &L->skills[i] : NULL;
}

/* 0x00d01e8c: round half away from zero through float. */
static float client_round(float x)
{
    return x > 0.0f ? (float)(int32_t)(x + 0.5f) : (float)(int32_t)(x - 0.5f);
}

/* (float)value * (float)(level * 0.005 + 1.0), rounded (0x016964e3..0x0169651c). */
static int32_t master_scaled(int32_t value, uint8_t level)
{
    float factor = (float)((double)level * 0.005 + 1.0);
    return (int32_t)client_round((float)value * factor);
}

const char *mu_lang_skill_info(const mu_lang *L, int32_t skill, int32_t master_level, int32_t *mana,
                               int32_t *distance, int32_t *ag)
{
    const mu_lang_skill *s = mu_lang_skill_get(L, skill);
    if (!s)
        return NULL;
    int master = skill >= 300 && skill <= 929;
    uint8_t m = (uint8_t)master_level;
    if (mana) {
        if (!master)
            *mana = s->mana;
        else
            *mana = master_scaled(s->mana, (s->brand == 0 && m == 0) ? s->master_bonus : m);
    }
    if (distance)
        *distance = s->distance;
    if (ag) {
        if (!master || (s->use_type == 4 && s->brand == 0))
            *ag = s->ag;
        else
            *ag = master_scaled(s->ag, m);
    }
    return s->name;
}

const mu_lang_gate *mu_lang_gate_get(const mu_lang *L, int32_t index)
{
    mu_lang_gate key;
    key.index = index;
    return L && L->gates ? bsearch(&key, L->gates, L->ngates, sizeof key, cmp_gate) : NULL;
}

const mu_lang_move *mu_lang_move_get(const mu_lang *L, int32_t index)
{
    mu_lang_move key;
    key.index = index;
    return L && L->moves ? bsearch(&key, L->moves, L->nmoves, sizeof key, cmp_move) : NULL;
}

size_t mu_lang_move_count(const mu_lang *L)
{
    return L ? L->nmoves : 0;
}

const mu_lang_move *mu_lang_move_at(const mu_lang *L, size_t i)
{
    return L && i < L->nmoves ? &L->moves[i] : NULL;
}

const mu_lang_npc *mu_lang_npc_get(const mu_lang *L, int32_t index)
{
    mu_lang_npc key;
    key.index = index;
    return L && L->npcs ? bsearch(&key, L->npcs, L->nnpcs, sizeof key, cmp_npc) : NULL;
}

const char *mu_lang_npc_name(const mu_lang *L, int32_t index)
{
    const mu_lang_npc *n = mu_lang_npc_get(L, index);
    return n ? n->name : NULL;
}

int32_t mu_lang_map_text_index(int32_t world)
{
    for (size_t i = 0; i < sizeof MU_LANG_MAPS / sizeof MU_LANG_MAPS[0]; ++i)
        if (MU_LANG_MAPS[i].world == world)
            return MU_LANG_MAPS[i].kind == 0 ? MU_LANG_MAPS[i].text : -1;
    return world >= 0 ? 30 + world : -1;
}

const char *mu_lang_map_name(const mu_lang *L, int32_t world)
{
    int32_t index = mu_lang_map_text_index(world);
    return index < 0 ? NULL : mu_lang_text(L, index);
}

static const enchant_code *find_code(const mu_lang *L, int32_t code)
{
    enchant_code key = {code, 0, 0};
    return L->codes ? bsearch(&key, L->codes, L->ncodes, sizeof key, cmp_code) : NULL;
}

static void put_default(const mu_lang *L, float out[3])
{
    for (int k = 0; k < 3; ++k)
        out[k] = L->has_enchant_default ? L->enchant_default[k] : 1.0f;
}

int mu_lang_enchant_first(const mu_lang *L, int32_t code, float out[3])
{
    if (!L || !L->has_enchant)
        return 0;
    const enchant_code *c = find_code(L, code);
    if (!c || !c->count) {   /* the client reads past an empty vector; never seen in the table */
        put_default(L, out);
        return 1;
    }
    memcpy(out, L->enchant[c->first].rgb, sizeof(float) * 3);
    return 1;
}

int mu_lang_enchant_mesh(const mu_lang *L, int32_t code, int32_t mesh, float out[3])
{
    if (!L || !L->has_enchant)
        return 0;
    const enchant_code *c = find_code(L, code);
    if (c)
        for (size_t i = 0; i < c->count; ++i) {
            const enchant_entry *e = &L->enchant[c->first + i];
            if (e->mesh == mesh || e->mesh == -1) {
                memcpy(out, e->rgb, sizeof(float) * 3);
                return 1;
            }
        }
    put_default(L, out);
    return 1;
}

size_t mu_lang_enchant_entries(const mu_lang *L, int32_t code)
{
    const enchant_code *c = L ? find_code(L, code) : NULL;
    return c ? c->count : 0;
}

char *mu_lang_ascii(char *dst, size_t cap, const char *src)
{
    if (!cap)
        return dst;
    size_t n = 0;
    for (; src && *src && n + 1 < cap; ++src)
        dst[n++] = (*src >= 0x20 && *src < 0x7f) ? *src : '?';
    dst[n] = 0;
    return dst;
}

/* ---- NATIVE-FIDELITY-001 lookups ---- */

static const int_row *find_row(const int_row *rows, size_t n, int32_t key)
{
    int_row k;
    memset(&k, 0, sizeof k);
    k.key = key;
    return rows ? bsearch(&k, rows, n, sizeof *rows, cmp_row) : NULL;
}

int mu_lang_pentagram_tier(const mu_lang *L, int32_t code, int32_t *tier)
{
    if (!L || !L->has_pentagram)
        return 0;
    const int_row *r = find_row(L->pentagram, L->npentagram, code);
    *tier = r ? r->v[0] : L->pentagram_default;
    return 1;
}

int mu_lang_inven_anim(const mu_lang *L, int32_t code, uint16_t *action, float *speed)
{
    const int_row *r = L ? find_row(L->invenanim, L->ninvenanim, code) : NULL;
    if (!r)
        return 0;
    *action = (uint16_t)r->v[2];
    uint32_t bits = (uint32_t)r->v[3];
    memcpy(speed, &bits, sizeof *speed);
    return 1;
}

int mu_lang_legendary(const mu_lang *L, int32_t type, int32_t codes[4])
{
    if (!L || !L->has_legendary)
        return 0;
    const int_row *r = find_row(L->legendary, L->nlegendary, type);
    memcpy(codes, r ? r->v : L->legendary_default, sizeof(int32_t) * 4);
    return 1;
}

size_t mu_lang_cash_sets(const mu_lang *L, const mu_lang_cash_set **sets)
{
    *sets = L ? L->cash_sets : NULL;
    return L ? L->ncash_sets : 0;
}

size_t mu_lang_cash_items(const mu_lang *L, const mu_lang_cash_item **items)
{
    *items = L ? L->cash_items : NULL;
    return L ? L->ncash_items : 0;
}

/* ---- NATIVE-LANG-002 lookups ---- */

const mu_lang_buff *mu_lang_buff_get(const mu_lang *L, int32_t buff)
{
    if (!L || !L->has_buffs)
        return NULL;
    if (buff >= 0x1cb)                /* 0x010de678: cmp [ebp+8], 0x1cb; jl */
        return &L->buff_default;
    mu_lang_buff key;
    key.index = buff;
    const mu_lang_buff *b = bsearch(&key, L->buffs, L->nbuffs, sizeof *L->buffs, cmp_buff);
    return b ? b : &L->buff_default;
}

const mu_lang_buff *mu_lang_buff_by_item(const mu_lang *L, int32_t code)
{
    if (!L || !L->has_buffs)
        return NULL;
    for (size_t i = 0; i < L->nbuffs; i++)   /* 0x010de6d3: the map in key order, (group << 9) + index */
        if ((int32_t)((uint32_t)L->buffs[i].item_group << 9) + L->buffs[i].item_index == code)
            return &L->buffs[i];
    return &L->buff_default;
}

size_t mu_lang_buff_count(const mu_lang *L)
{
    return L ? L->nbuffs : 0;
}

const mu_lang_buff *mu_lang_buff_at(const mu_lang *L, size_t i)
{
    return L && i < L->nbuffs ? &L->buffs[i] : NULL;
}

/* printf of a table format with one numeric argument: the single conversion is substituted, everything else
 * copied (the client hands the format to its sprintf 0x0098d0a9; the tables hold one %d or %.Nf at most). */
static void format_one(char *out, size_t cap, const char *fmt, int is_float, int32_t iv, double fv)
{
    size_t n = 0;
    int used = 0;
    for (const char *p = fmt; *p && n + 1 < cap;) {
        if (*p != '%') {
            out[n++] = *p++;
            continue;
        }
        if (p[1] == '%') {
            out[n++] = '%';
            p += 2;
            continue;
        }
        const char *q = p + 1;
        while (*q && strchr("-+ #0", *q))
            q++;
        while (*q >= '0' && *q <= '9')
            q++;
        if (*q == '.') {
            q++;
            while (*q >= '0' && *q <= '9')
                q++;
        }
        if (used || !*q || !strchr("diuxXfFgGeE", *q) || q - p > 12) {
            out[n++] = *p++;
            continue;
        }
        char spec[16];
        size_t sl = (size_t)(q - p) + 1;
        memcpy(spec, p, sl);
        spec[sl] = 0;
        int floaty = strchr("fFgGeE", *q) != NULL;
        char tmp[128];
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
#endif
        if (floaty)
            snprintf(tmp, sizeof tmp, spec, is_float ? fv : (double)iv);
        else
            snprintf(tmp, sizeof tmp, spec, is_float ? (int)fv : (int)iv);
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
        for (const char *t = tmp; *t && n + 1 < cap; t++)
            out[n++] = *t;
        used = 1;
        p = q + 1;
    }
    out[n] = 0;
}

int mu_lang_buff_tooltip(const mu_lang *L, int32_t buff, const mu_lang_buff_values *vals, char (*out)[256], int max)
{
    const mu_lang_buff *b = mu_lang_buff_get(L, buff);
    if (!b || max < 2)
        return 0;
    mu_lang_buff_values none;
    memset(&none, 0, sizeof none);
    none.value2_kind = -1;
    if (!vals)
        vals = &none;
    int n = 0;
    snprintf(out[n++], 256, "%s", b->name ? b->name : "");
    snprintf(out[n++], 256, "\n");                 /* 0x01298ac7: the string "\n" */
    char joined[1024];                              /* 0x01299f67: the description lines appended */
    size_t jl = 0;
    joined[0] = 0;
    for (int i = 0; i < b->nlines; i++)
        jl += (size_t)snprintf(joined + jl, jl < sizeof joined ? sizeof joined - jl : 0, "%s", b->lines[i]);
    if (vals->hero_value != 0 && b->value_kind == 1) {
        if (n < max)
            format_one(out[n++], 256, joined, 0, vals->hero_value, 0.0);
        return n;
    }
    if (b->value_kind == 2) {
        if (vals->value2_hidden)
            return n;
        if (n < max) {
            if (vals->value2_kind == 0)
                format_one(out[n++], 256, joined, 0, vals->value2_int, 0.0);
            else if (vals->value2_kind == 1)
                format_one(out[n++], 256, joined, 1, 0, (double)vals->value2_float);
            else
                out[n++][0] = 0;            /* the 0x100-byte buffer stays zeroed (0x01298af1) */
        }
        return n;
    }
    for (int i = 0; i < b->nlines && n < max; i++)
        snprintf(out[n++], 256, "%s", b->lines[i]);
    return n;
}

int mu_lang_buff_addbuff(const mu_lang *L, int32_t buff, mu_lang_addbuff *out)
{
    static const int32_t HIDDEN[] = {0x53, 0x54, 0x55, 0x78, 0x19b, 0x19c, 0x19d, 0x19e, 0x19f, 0x1be};
    if (!L || !L->has_buffs || buff <= 0 || buff >= 0x1cb)
        return 0;
    for (size_t i = 0; i < sizeof HIDDEN / sizeof HIDDEN[0]; i++)
        if (buff == HIDDEN[i])
            return 0;
    const mu_lang_buff *b = mu_lang_buff_get(L, buff);
    memset(out, 0, sizeof *out);
    out->buff = buff;
    out->is_debuff = b->type == 1;
    out->is_cash = b->type == 2;
    out->has_detail = !out->is_debuff;
    out->detail = b->group == 0xf7 ? 1 : b->group == 0xf6 ? 2 : 0;
    return 1;
}

const mu_lang_charinfo *mu_lang_charinfo_get(const mu_lang *L, int32_t id)
{
    if (!L || !L->has_charinfo)
        return NULL;
    mu_lang_charinfo key;
    key.id = id;
    const mu_lang_charinfo *c = bsearch(&key, L->charinfo, L->ncharinfo, sizeof *L->charinfo, cmp_charinfo);
    return c ? c : &L->charinfo_default;
}

size_t mu_lang_charinfo_count(const mu_lang *L)
{
    return L ? L->ncharinfo : 0;
}

const mu_lang_charinfo *mu_lang_charinfo_at(const mu_lang *L, size_t i)
{
    return L && i < L->ncharinfo ? &L->charinfo[i] : NULL;
}

/* MSVC's std::sort (introsort: median-of-three / ninther partition with the "fat" pivot range, insertion sort
 * at 32 elements and below) with the row builder's comparator 0x00b46e30 (a->sort < b->sort).  Rows with equal
 * sorts keep the order this algorithm gives them, which the character window shows. */
typedef const mu_lang_charinfo *row_ptr;
static int row_lt(row_ptr a, row_ptr b)
{
    return a->sort < b->sort;
}

static void row_swap(row_ptr *a, row_ptr *b)
{
    row_ptr t = *a;
    *a = *b;
    *b = t;
}

static void row_med3(row_ptr *first, row_ptr *mid, row_ptr *last)
{
    if (row_lt(*mid, *first))
        row_swap(mid, first);
    if (row_lt(*last, *mid)) {
        row_swap(last, mid);
        if (row_lt(*mid, *first))
            row_swap(mid, first);
    }
}

static void row_guess_median(row_ptr *first, row_ptr *mid, row_ptr *last)
{
    ptrdiff_t count = last - first;
    if (40 < count) {
        ptrdiff_t step = (count + 1) >> 3, two = step << 1;
        row_med3(first, first + step, first + two);
        row_med3(mid - step, mid, mid + step);
        row_med3(last - two, last - step, last);
        row_med3(first + step, mid, last - step);
    } else {
        row_med3(first, mid, last);
    }
}

static void row_partition(row_ptr *first, row_ptr *last, row_ptr **out_first, row_ptr **out_last)
{
    row_ptr *mid = first + ((last - first) >> 1);
    row_guess_median(first, mid, last - 1);
    row_ptr *pfirst = mid, *plast = pfirst + 1;
    while (first < pfirst && !row_lt(*(pfirst - 1), *pfirst) && !row_lt(*pfirst, *(pfirst - 1)))
        --pfirst;
    while (plast < last && !row_lt(*plast, *pfirst) && !row_lt(*pfirst, *plast))
        ++plast;
    row_ptr *gfirst = plast, *glast = pfirst;
    for (;;) {
        for (; gfirst < last; ++gfirst) {
            if (row_lt(*pfirst, *gfirst))
                ;
            else if (row_lt(*gfirst, *pfirst))
                break;
            else if (plast != gfirst)
                row_swap(plast++, gfirst);
            else
                ++plast;
        }
        for (; first < glast; --glast) {
            if (row_lt(*(glast - 1), *pfirst))
                ;
            else if (row_lt(*pfirst, *(glast - 1)))
                break;
            else if (--pfirst != glast - 1)
                row_swap(pfirst, glast - 1);
        }
        if (glast == first && gfirst == last) {
            *out_first = pfirst;
            *out_last = plast;
            return;
        }
        if (glast == first) {
            if (plast != gfirst)
                row_swap(pfirst, plast);
            ++plast;
            row_swap(pfirst, gfirst);
            ++pfirst;
            ++gfirst;
        } else if (gfirst == last) {
            if (--glast != --pfirst)
                row_swap(glast, pfirst);
            row_swap(pfirst, --plast);
        } else {
            row_swap(gfirst++, --glast);
        }
    }
}

static void row_sift_down(row_ptr *first, ptrdiff_t hole, ptrdiff_t bottom, row_ptr val)
{
    ptrdiff_t top = hole, idx = hole, max_seq = (bottom - 1) >> 1;
    while (idx < max_seq) {
        idx = 2 * idx + 2;
        if (row_lt(first[idx], first[idx - 1]))
            --idx;
        first[hole] = first[idx];
        hole = idx;
    }
    if (idx == max_seq && bottom % 2 == 0) {
        first[hole] = first[bottom - 1];
        hole = bottom - 1;
    }
    for (idx = (hole - 1) >> 1; top < hole && row_lt(first[idx], val); idx = (hole - 1) >> 1) {
        first[hole] = first[idx];
        hole = idx;
    }
    first[hole] = val;
}

static void row_heap_sort(row_ptr *first, row_ptr *last)
{
    ptrdiff_t bottom = last - first;
    for (ptrdiff_t hole = bottom >> 1; 0 < hole;) {
        --hole;
        row_sift_down(first, hole, bottom, first[hole]);
    }
    for (; 2 <= last - first; --last) {
        row_ptr val = *(last - 1);
        *(last - 1) = *first;
        row_sift_down(first, 0, last - 1 - first, val);
    }
}

static void row_insertion_sort(row_ptr *first, row_ptr *last)
{
    if (first == last)
        return;
    for (row_ptr *next = first; ++next != last;) {
        row_ptr *next1 = next, val = *next;
        if (row_lt(val, *first)) {
            memmove(first + 1, first, (size_t)(next - first) * sizeof *first);
            *first = val;
        } else {
            for (row_ptr *first1 = next1; row_lt(val, *--first1); next1 = first1)
                *next1 = *first1;
            *next1 = val;
        }
    }
}

static void row_sort(row_ptr *first, row_ptr *last, ptrdiff_t ideal)
{
    ptrdiff_t count;
    while (32 < (count = last - first) && 0 < ideal) {
        row_ptr *mfirst, *mlast;
        row_partition(first, last, &mfirst, &mlast);
        ideal = (ideal >> 1) + (ideal >> 2);
        if (mfirst - first < last - mlast) {
            row_sort(first, mfirst, ideal);
            first = mlast;
        } else {
            row_sort(mlast, last, ideal);
            last = mfirst;
        }
    }
    if (32 < count)
        row_heap_sort(first, last);
    else if (2 <= count)
        row_insertion_sort(first, last);
}

int mu_lang_charinfo_rows(const mu_lang *L, int32_t class_index, const mu_lang_charinfo **out, int max)
{
    if (!L || class_index < 0 || class_index >= 16)
        return 0;
    int n = 0, nsorted = 0;
    row_ptr sorted[256];
    for (size_t i = 0; i < L->ncharinfo; i++) {
        const mu_lang_charinfo *c = &L->charinfo[i];
        if (class_index >= c->nclasses || !c->classes[class_index])
            continue;
        if (c->type == 2 || c->type == 3 || c->type == 5) {
            if (nsorted < 256)
                sorted[nsorted++] = c;
        } else if (n < max) {
            out[n++] = c;
        }
    }
    row_sort(sorted, sorted + nsorted, nsorted);
    for (int i = 0; i < nsorted && n < max; i++)
        out[n++] = sorted[i];
    return n;
}

const mu_lang_skillreq *mu_lang_skillreq_item(const mu_lang *L, int32_t group, int32_t index)
{
    if (!L)
        return NULL;
    for (size_t i = 0; i < L->nskillreq; i++)   /* 0x00abf829: the map in key order */
        if (L->skillreq[i].item_group == group && L->skillreq[i].item_index == index)
            return &L->skillreq[i];
    return NULL;
}

int mu_lang_soul_conversion(const mu_lang *L, int32_t code)
{
    return L && find_row(L->soulconv, L->nsoulconv, code) != NULL;
}
