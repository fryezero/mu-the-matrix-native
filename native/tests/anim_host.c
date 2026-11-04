/* RENDER-WORLDS-AFTER5: the action registry in the production runtime. argv[1] a two-action model, argv[2] a lang
 * directory with a synthetic mapanim.tsv (144: type 13 actions 0 <-> 1 at the end of each, type 32 a speed; 51:
 * type 32). Without MU_LANG_DIR the objects keep CreateObject's speeds; with it, the create tail sets the speeds
 * and the registry tick switches type 13's action at the end of each. World 51 has no factory class: unchanged.
 * RENDER-WORLDS-AFTER6: type 99 has a handler 8 row (60 x 60 x 200 box); with a camera at (3400, 3000, 150) the
 * camera -> hero (3000, 3000, 0) segment crosses it and the tick sets its alpha target +0xd8 to 0.1; without a
 * camera the tick is counted unsupported. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

static const int types[] = {13, 32, 99};
enum { N = 3, STEPS = 40 };

static mu_objects *start(int world, mu_object_model *m, mu_object_record *rec)
{
    mu_objects *o = calloc(1, sizeof *o);
    assert(o);
    memset(rec, 0, N * sizeof *rec);
    for (int i = 0; i < N; ++i) {
        rec[i].type = (int16_t)types[i];
        rec[i].position[0] = 3000.0f + 100.0f * (float)i;
        rec[i].position[1] = 3000.0f;
        rec[i].scale = 1.0f;
    }
    mu_objects_init(o, world);
    for (int i = 0; i < N; ++i)
        o->models[types[i]] = m;
    o->records = rec;
    o->count = N;
    assert(mu_objects_start(o, NULL) == 0 && o->rt.created == N);
    return o;
}

static float speed(const mu_objects *o, int i) { return mu_obj_f32(o->rt.images + i * MU_OBJ_SIZE, MU_OBJF_VELOCITY); }
static int action(const mu_objects *o, int i) { return mu_obj_u16(o->rt.images + i * MU_OBJ_SIZE, MU_OBJF_ACTION); }
static float fade(const mu_objects *o, int i)
{
    return mu_obj_f32(o->rt.images + i * MU_OBJ_SIZE, MU_OBJF_ALPHA_TARGET);
}

static void step(mu_objects *o, int switches[N], const float *camera)
{
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    in.hero[0] = 3000.0f;
    in.hero[1] = 3000.0f;
    in.camera = camera;   /* RENDER-WORLDS-AFTER6: tick handler 8 */
    for (int i = 0; i < N; ++i)
        o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
    for (int s = 0; s < 256; ++s)
        o->rt.world.block_visible[s] = 1;
    int last[N];
    for (int i = 0; i < N; ++i) {
        last[i] = action(o, i);
        switches[i] = 0;
    }
    for (int k = 0; k < STEPS; ++k) {
        in.time = 40.0f * (float)k;
        mu_objects_step(o, &in);
        for (int i = 0; i < N; ++i) {
            switches[i] += action(o, i) != last[i];
            last[i] = action(o, i);
        }
    }
}

static void release(mu_objects *o)
{
    mu_objects_runtime_free(o);
    free(o);
}

int main(int argc, char **argv)
{
    assert(argc == 3);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    assert(m->bmd.action_count == 2 && m->bmd.actions[0].keys == 2);
    mu_object_record rec[N];
    int switches[N];

    unsetenv("MU_LANG_DIR");   /* no table: CreateObject's speeds, no action changes */
    mu_objects *o = start(144, m, rec);
    const float base[N] = {speed(o, 0), speed(o, 1), speed(o, 2)};
    assert(o->rt.anim_count == 0 && o->rt.anim_sets == 0);
    step(o, switches, NULL);
    assert(switches[0] == 0 && o->rt.anim_ticks == 0);
    release(o);

    setenv("MU_LANG_DIR", argv[2], 1);
    o = start(144, m, rec);
    assert(o->rt.anim_count == 4 && o->rt.anim_sets == 3 && o->rt.anim_unsupported == 0);
    assert(speed(o, 0) == 0.25f && speed(o, 1) == 0.07f && speed(o, 2) == base[2]);
    const float camera[3] = {3400.0f, 3000.0f, 150.0f};
    assert(fade(o, 2) != 0.1f);
    step(o, switches, camera);
    assert(fade(o, 2) == 0.1f);
    /* type 13: frame += 0.25 until 2 - 0.25, then action 1 (speed 0.5) until 2 - 0.5, then 0 again */
    assert(switches[0] >= 4 && switches[1] == 0 && switches[2] == 0);
    assert(o->rt.anim_ticks >= 2 * STEPS && o->rt.anim_unsupported == 0);
    assert(speed(o, 0) == (action(o, 0) ? 0.5f : 0.25f));
    release(o);

    o = start(144, m, rec);   /* no camera: handler 8 is counted, nothing else changes */
    step(o, switches, NULL);
    assert(o->rt.anim_unsupported >= STEPS && fade(o, 2) != 0.1f && switches[0] >= 4);
    release(o);

    o = start(51, m, rec);   /* a table row but no factory class: nothing runs */
    assert(o->rt.anim_count == 1 && o->rt.anim_sets == 0);
    release(o);

    unsetenv("MU_LANG_DIR");
    mu_bmd_free(&m->bmd);
    mu_model_free(&m->model);
    free(m);
    return 0;
}
