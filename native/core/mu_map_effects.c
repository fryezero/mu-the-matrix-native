/* RENDER-EFFECTS-008: the map-object effect table in the native world; see mu_map_effects.h. */
#include "mu_map_effects.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_objects.h"
#include "mu_particles.h"

enum { COLUMNS = 16 };

static int split(char *line, char **fields, int max)
{
    int n = 0;
    for (char *s = line; n < max; ++n) {
        fields[n] = s;
        char *tab = strchr(s, '\t');
        if (!tab) {
            s[strcspn(s, "\r\n")] = '\0';
            return n + 1;
        }
        *tab = '\0';
        s = tab + 1;
    }
    return n;
}

/* live_lang_to_plain.escape: \\, \t, \n, \r and \xNN */
static size_t unescape(const char *s, char *out)
{
    size_t n = 0;
    for (; *s; ++s) {
        if (*s == '\\' && s[1]) {
            ++s;
            if (*s == 'x' && s[1] && s[2]) {
                char hex[3] = {s[1], s[2], 0};
                out[n++] = (char)strtol(hex, NULL, 16);
                s += 2;
                continue;
            }
            out[n++] = *s == 't' ? '\t' : *s == 'n' ? '\n' : *s == 'r' ? '\r' : *s;
            continue;
        }
        out[n++] = *s;
    }
    out[n++] = '\0';
    return n;
}

void mu_map_effects_free(mu_map_effects *t)
{
    if (!t)
        return;
    free(t->worlds);
    free(t->types);
    free(t->entries);
    free(t->actions);
    free(t->paths);
    free(t);
}

mu_map_effects *mu_map_effects_load(const char *dir)
{
    if (!dir || !*dir)
        return NULL;
    char path[4096];
    snprintf(path, sizeof path, "%s/mapeffects.tsv", dir);
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    const long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *text = size > 0 ? malloc((size_t)size + 1) : NULL;
    mu_map_effects *t = calloc(1, sizeof *t);
    if (!text || !t || fread(text, 1, (size_t)size, f) != (size_t)size) {
        fclose(f);
        free(text);
        free(t);
        return NULL;
    }
    fclose(f);
    text[size] = '\0';
    size_t rows = 0, action_words = 0;
    for (const char *s = text; *s; ++s)
        rows += *s == '\n';
    for (const char *s = text; *s; ++s)
        action_words += *s == ',' || *s == '\t';
    t->worlds = calloc(rows + 1, sizeof *t->worlds);
    t->types = calloc(rows + 1, sizeof *t->types);
    t->entries = calloc(rows + 1, sizeof *t->entries);
    t->actions = calloc(action_words + 1, sizeof *t->actions);
    t->paths = malloc((size_t)size + 1);
    size_t path_used = 0, action_used = 0;
    int ok = t->worlds && t->types && t->entries && t->actions && t->paths;
    int32_t last_world = 0, last_type = 0;
    for (char *line = text, *next; ok && line && *line; line = next) {
        next = strchr(line, '\n');
        if (next)
            *next++ = '\0';
        if (*line == '#' || !*line || *line == '\r')
            continue;
        char *col[COLUMNS];
        if (split(line, col, COLUMNS) != COLUMNS) {
            ok = 0;
            break;
        }
        const int32_t world = (int32_t)strtol(col[0], NULL, 10), type = (int32_t)strtol(col[1], NULL, 10);
        /* rows come in map order: ascending worlds, ascending types inside a world, entries in vector order */
        if (!t->world_count || world != last_world) {
            if (t->world_count && world < last_world) { ok = 0; break; }
            t->worlds[t->world_count++] = (mu_map_effect_world){world, &t->types[t->type_count], 0};
            last_world = world;
            last_type = type - 1;
        }
        mu_map_effect_world *w = &t->worlds[t->world_count - 1];
        if (!w->count || type != last_type) {
            if (w->count && type < last_type) { ok = 0; break; }
            t->types[t->type_count++] = (mu_map_effect_type){type, &t->entries[t->entry_count], 0};
            ++w->count;
            last_type = type;
        }
        mu_map_effect_entry *e = &t->entries[t->entry_count++];
        ++t->types[t->type_count - 1].count;
        e->path = t->paths + path_used;   /* paths is sized for the whole file once: the pointers stay valid */
        path_used += unescape(col[3], t->paths + path_used);
        for (int k = 0; k < 3; ++k) {
            e->position[k] = strtof(col[4 + k], NULL);
            e->rotation[k] = strtof(col[7 + k], NULL);
        }
        e->scale = strtof(col[10], NULL);
        e->bone = (int32_t)strtol(col[11], NULL, 10);
        e->follow = (uint8_t)strtoul(col[12], NULL, 10);
        e->tint = (uint8_t)strtoul(col[13], NULL, 10);
        e->start_bits = (uint32_t)strtoul(col[14], NULL, 16);
        e->actions = t->actions + action_used;
        e->action_count = 0;
        if (strcmp(col[15], "-"))
            for (char *s = col[15]; *s; ) {
                t->actions[action_used++] = (int32_t)strtol(s, &s, 10);
                ++e->action_count;
                if (*s == ',')
                    ++s;
                else
                    break;
            }
    }
    free(text);
    if (!ok || !t->entry_count) {
        mu_map_effects_free(t);
        return NULL;
    }
    t->table.worlds = t->worlds;
    t->table.count = t->world_count;
    return t;
}

mu_map_effects *mu_map_effects_load_default(void)
{
    return mu_map_effects_load(getenv("MU_LANG_DIR"));
}

typedef struct attach_context {
    mu_world_particles *particles;
    mu_map_effects_stats *stats;
} attach_context;

static void op_clear(void *c, int32_t object)
{
    attach_context *a = c;
    mu_world_particles_ein_clear(a->particles, object);
    ++a->stats->cleared;
}

static int32_t op_create(void *c, int32_t object, const mu_map_effect_entry *e, uint16_t type_word)
{
    attach_context *a = c;
    (void)object;
    (void)type_word;   /* the factory's unused word argument */
    float start;
    memcpy(&start, &e->start_bits, sizeof start);
    ++a->stats->requested;
    ++a->particles->ein_requests;
    const int32_t instance = mu_world_particles_ein_create(a->particles, e->path, e->position, e->rotation, e->scale,
                                                           e->tint, e->actions, (uint32_t)e->action_count, start);
    a->stats->invalid += instance < 0;
    a->particles->ein_invalid += instance < 0;
    return instance;
}

static void op_attach(void *c, int32_t object, int32_t handle, int32_t bone, int follow, int timed, float lifetime)
{
    attach_context *a = c;
    mu_world_particles_ein_link(a->particles, object, handle, bone, follow, timed, lifetime);
    ++a->stats->attached;
}

static void op_release(void *c, int32_t handle)
{
    (void)c;
    (void)handle;   /* the scene keeps every instance; the list record holds the attached ones */
}

static void op_prime(void *c, int32_t object)
{
    attach_context *a = c;
    (void)object;
    ++a->stats->primed;
}

void mu_map_effects_attach_world(const mu_map_effects *table, int32_t world, struct mu_objects *objects,
                                 struct mu_world_particles *particles, mu_map_effects_stats *stats)
{
    mu_map_effects_stats local = {0};
    if (!stats)
        stats = &local;
    if (!table || !objects || !particles || !objects->rt.ready)
        return;
    attach_context a = {particles, stats};
    const mu_map_effect_ops ops = {&a, op_clear, op_create, op_attach, op_release, op_prime};
    mu_map_effects_attach(&table->table, world, &objects->rt.world, &ops);
}
