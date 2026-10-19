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
};

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
