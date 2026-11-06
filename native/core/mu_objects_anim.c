/* RENDER-WORLDS-AFTER5: the object action registry in the native world (docs/research/client-worlds-after5.md).
 *
 * The rows are the client's MapObjectAnimationInfo tables (Data\Lang.mpr, decoded game data):
 * scripts/live_anim_table_to_plain.py writes them from a langread snapshot as mapanim.tsv in the local lang
 * directory (MU_LANG_DIR); it is never committed. Without the file the runtime keeps CreateObject's speeds, as
 * before. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_objects.h"

#define COLUMNS 7

static int split(char *line, char **col, int max)
{
    int n = 0;
    for (char *s = line; n < max; ) {
        col[n++] = s;
        char *tab = strchr(s, '\t');
        if (!tab)
            break;
        *tab = '\0';
        s = tab + 1;
    }
    char *end = col[n - 1] + strcspn(col[n - 1], "\r\n");
    *end = '\0';
    return n;
}

int32_t mu_objects_anim_load(mu_objects *o, const char *dir)
{
    mu_objects_runtime *rt = &o->rt;
    rt->anim_count = 0;
    if (!dir || !*dir)
        return 0;
    char path[1024];
    if (snprintf(path, sizeof path, "%s/mapanim.tsv", dir) >= (int)sizeof path)
        return 0;
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    char line[1024];
    int32_t extra_used = 0, ok = 1;
    while (ok && fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r')
            continue;
        char *col[COLUMNS];
        if (split(line, col, COLUMNS) != COLUMNS) {
            ok = 0;
            break;
        }
        if ((int32_t)strtol(col[0], NULL, 10) != o->world)
            continue;
        if (rt->anim_count >= MU_OBJECT_ANIM_ENTRIES) {
            ok = 0;
            break;
        }
        mu_anim_entry *e = &rt->anim[rt->anim_count];
        e->type = (int32_t)strtol(col[1], NULL, 10);
        e->action = (int32_t)strtol(col[2], NULL, 10);
        e->speed = strtof(col[3], NULL);
        e->handler = (int32_t)strtol(col[4], NULL, 10);
        e->param = (int32_t)strtol(col[5], NULL, 10);
        e->extra = &rt->anim_extra[extra_used];
        e->extra_count = 0;
        if (strcmp(col[6], "-"))
            for (char *s = col[6]; *s; ) {
                if (extra_used >= MU_OBJECT_ANIM_EXTRA) {
                    ok = 0;
                    break;
                }
                rt->anim_extra[extra_used++] = (int32_t)strtol(s, &s, 10);
                ++e->extra_count;
                if (*s != ',')
                    break;
                ++s;
            }
        ++rt->anim_count;
    }
    fclose(f);
    if (!ok)
        rt->anim_count = 0;   /* a malformed file changes nothing */
    return rt->anim_count;
}

/* GetModel for the registry: the loaded model's action count, and the action record's key count and lock byte */
typedef struct anim_context {
    mu_objects *o;
    mu_obj_rand_fn rand_fn;
    void *rand_context;
} anim_context;

static int anim_model(void *context, int32_t type, int32_t action, int32_t *count, int16_t *keys, uint8_t *lock)
{
    const mu_objects *o = ((const anim_context *)context)->o;
    const mu_object_model *m = type >= 0 && type < MU_OBJECT_TYPES ? o->models[type] : NULL;
    if (!m || !m->loaded)
        return 0;
    *count = m->bmd.action_count;
    if (action >= 0 && action < m->bmd.action_count) {
        *keys = (int16_t)m->bmd.actions[action].keys;
        *lock = m->bmd.actions[action].lock_positions;
    }
    return 1;
}

static int32_t anim_rand(void *context)
{
    const anim_context *a = context;
    return a->rand_fn(a->rand_context);
}

static int active(const mu_objects *o, int32_t index)
{
    return o->rt.anim_count > 0 && mu_anim_class_world(o->world) && index >= 0 && index < o->count;
}

static mu_anim_inputs inputs(anim_context *c)
{
    mu_anim_inputs in;
    memset(&in, 0, sizeof in);
    in.entries = c->o->rt.anim;
    in.count = c->o->rt.anim_count;
    in.model = anim_model;
    in.rand_fn = anim_rand;
    in.context = c;
    return in;
}

void mu_objects_anim_create(mu_objects *o, int32_t index, mu_obj_rand_fn rand_fn, void *context)
{
    if (!active(o, index))
        return;
    anim_context c = {o, rand_fn, context};
    const mu_anim_inputs in = inputs(&c);
    const int status = mu_action_set(o->rt.images + (size_t)index * MU_OBJ_SIZE, 0, &in);
    o->rt.anim_sets += status == MU_ANIM_APPLIED;
    o->rt.anim_unsupported += status == MU_ANIM_UNSUPPORTED;
}

void mu_objects_anim_tick(mu_objects *o, int32_t index, const float hero[3], const float *camera,
                          mu_obj_rand_fn rand_fn, void *context)
{
    if (!active(o, index))
        return;
    anim_context c = {o, rand_fn, context};
    mu_anim_inputs in = inputs(&c);
    if (hero)
        memcpy(in.hero, hero, sizeof in.hero);
    in.camera = camera;   /* RENDER-WORLDS-AFTER6: tick handler 8 */
    int found = 0;
    const int status = mu_action_tick(o->rt.images + (size_t)index * MU_OBJ_SIZE, &in, &found);
    o->rt.anim_ticks += found;
    o->rt.anim_unsupported += status == MU_ANIM_UNSUPPORTED;
}
