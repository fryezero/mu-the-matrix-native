/* RENDER-EFFECTS-018: the Muun effect table in the native port; see mu_muun_effects.h. */
#include "mu_muun_effects.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_effect_scene.h"

enum { COLUMNS = 11 };

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

void mu_muun_effects_free(mu_muun_effects *t)
{
    if (!t)
        return;
    free(t->entries);
    free(t->paths);
    free(t);
}

mu_muun_effects *mu_muun_effects_load(const char *dir)
{
    if (!dir || !*dir)
        return NULL;
    char path[4096];
    snprintf(path, sizeof path, "%s/muuneffects.tsv", dir);
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    const long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *text = size > 0 ? malloc((size_t)size + 1) : NULL;
    mu_muun_effects *t = calloc(1, sizeof *t);
    if (!text || !t || fread(text, 1, (size_t)size, f) != (size_t)size) {
        fclose(f);
        free(text);
        free(t);
        return NULL;
    }
    fclose(f);
    text[size] = '\0';
    size_t rows = 0;
    for (const char *s = text; *s; ++s)
        rows += *s == '\n';
    t->entries = calloc(rows + 1, sizeof *t->entries);
    t->paths = malloc((size_t)size + 1);
    size_t path_used = 0;
    int ok = t->entries && t->paths;
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
        mu_muun_effect_entry *e = &t->entries[t->count];
        e->code = (int32_t)strtol(col[0], NULL, 10);
        if (t->count && e->code < t->entries[t->count - 1].code) {   /* the multimap's order */
            ok = 0;
            break;
        }
        e->path = t->paths + path_used;   /* paths is sized for the whole file once: the pointers stay valid */
        path_used += unescape(col[1], t->paths + path_used);
        for (int k = 0; k < 3; ++k) {
            e->position[k] = strtof(col[2 + k], NULL);
            e->rotation[k] = strtof(col[5 + k], NULL);
        }
        e->scale = strtof(col[8], NULL);
        e->bone = (int32_t)strtol(col[9], NULL, 10);
        e->follow = (uint8_t)strtoul(col[10], NULL, 10);
        ++t->count;
    }
    free(text);
    if (!ok || !t->count) {
        mu_muun_effects_free(t);
        return NULL;
    }
    t->table.entries = t->entries;
    t->table.count = t->count;
    return t;
}

mu_muun_effects *mu_muun_effects_load_default(void)
{
    return mu_muun_effects_load(getenv("MU_LANG_DIR"));
}

static int32_t op_create(void *c, int32_t object, const mu_muun_effect_entry *e)
{
    mu_muun_owner *o = c;
    (void)object;
    ++o->requested;
    if (!o->scene)
        return o->next_handle++;
    char error[256];
    /* the factory's call: template transform 0, type word 0, tint 0, no actions, start frame 0.0 */
    const int instance = mu_effect_scene_create(o->scene, e->path, e->position, e->rotation, e->scale, 0, 0, NULL, 0,
                                                0.0f, error, sizeof error);
    o->invalid += instance < 0;
    return instance;
}

static void op_attach(void *c, int32_t object, int32_t handle, int32_t bone, int follow, int timed, float lifetime)
{
    mu_muun_owner *o = c;
    (void)object;
    if (o->count >= MU_MUUN_RECORDS) {
        ++o->overflow;
        return;
    }
    mu_object_effect_record *r = &o->records[o->count++];
    r->handle = handle;
    /* 0x0129f9c6 keeps the effect's own scale (0x00a74ca5): the factory's scale argument */
    r->template_scale = o->scene ? o->scene->instances[handle].fx.scale : 0.0f;
    r->bone = bone;
    r->follow = (uint8_t)follow;
    r->timed = (uint8_t)timed;
    r->lifetime = lifetime;
    ++o->attached;
}

static void op_release(void *c, int32_t handle)
{
    (void)c;
    (void)handle;   /* the scene keeps every instance; the list record holds the attached ones */
}

static void hide(mu_muun_owner *o, int32_t handle)
{
    if (o->scene && handle >= 0 && (uint32_t)handle < o->scene->instance_count)
        o->scene->instances[handle].owner.visible = 0;
}

static void op_clear(void *c, int32_t object)
{
    mu_muun_owner *o = c;
    (void)object;
    for (int32_t k = 0; k < o->count; ++k)
        hide(o, o->records[k].handle);
    o->count = 0;
    ++o->cleared;
}

int mu_muun_owner_refresh(mu_muun_owner *owner, const mu_muun_effects *table, const mu_muun_slot *slot)
{
    if (!owner || !slot)
        return 0;
    const mu_muun_effect_ops ops = {owner, op_create, op_attach, op_release, op_clear};
    mu_muun_slot_clear(slot, &ops);
    return mu_muun_slot_attach(slot, table ? &table->table : NULL, &ops);
}

static void up_expire(void *c, int32_t handle)
{
    mu_muun_owner *o = c;
    hide(o, handle);
    ++o->expired;
}

static void up_scale(void *c, int32_t handle, float scale)
{
    mu_muun_owner *o = c;
    if (o->scene && (uint32_t)handle < o->scene->instance_count)
        o->scene->instances[handle].fx.scale = scale;
    ++o->scaled;
}

static void up_update(void *c, int32_t handle, float dt, const float matrix[16])
{
    mu_muun_owner *o = c;
    if (o->scene && (uint32_t)handle < o->scene->instance_count) {
        mu_effect_scene_attach(o->scene, (uint32_t)handle, matrix);
        mu_effect_scene_update_one(o->scene, (uint32_t)handle, dt);
    }
    ++o->updates;
}

void mu_muun_owner_update(mu_muun_owner *owner, const mu_effect_object *object, float dt)
{
    if (!owner || !object)
        return;
    const mu_object_effect_ops ops = {owner, up_expire, up_scale, up_update};
    owner->count = mu_object_effects_update(owner->records, owner->count, object, dt, &ops);
}
