/* RENDER-WORLDS-PICK-001: the map object's box +0x31c and the registry's mouse-over tick handlers in the
 * production runtime. argv[1] a two-action model, argv[2] a lang directory with a synthetic mapanim.tsv for world
 * 144: type 13 action 0 -> 1 while the mouse is over it (handler 4, step 0) and back when it leaves (step 2);
 * type 32 action 0 -> 1 once the mouse is over it (handler 6, latch); type 99 like type 13 but never drawn.
 *
 * The render pass (RenderObject's Transform call) writes the box: CreateObject's (-40, -40, 0)..(40, 40, 80) at
 * the position, whatever the object's turn and scale. The step takes the mouse segment from rt.mouse_start /
 * rt.mouse_end; without one the handlers count unsupported. An object that was never drawn keeps the all-zero
 * box, which the client's test reports as over for every segment. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

static const int types[] = {13, 32, 99};
enum { N = 3 };

static mu_objects *start(mu_object_model *m, mu_object_record *rec)
{
    mu_objects *o = calloc(1, sizeof *o);
    assert(o);
    memset(rec, 0, N * sizeof *rec);
    for (int i = 0; i < N; ++i) {
        rec[i].type = (int16_t)types[i];
        rec[i].position[0] = 3000.0f + 200.0f * (float)i;
        rec[i].position[1] = 3000.0f;
        rec[i].position[2] = 50.0f;
        rec[i].angle[2] = 45.0f * (float)i;   /* neither the turn nor the scale enters the box */
        rec[i].scale = 1.0f + 0.5f * (float)i;
    }
    mu_objects_init(o, 144);
    for (int i = 0; i < N; ++i)
        o->models[types[i]] = m;
    o->records = rec;
    o->count = N;
    assert(mu_objects_start(o, NULL) == 0 && o->rt.created == N);
    return o;
}

static uint8_t *image(mu_objects *o, int i) { return o->rt.images + i * MU_OBJ_SIZE; }
static int action(mu_objects *o, int i) { return mu_obj_u16(image(o, i), MU_OBJF_ACTION); }

static void step(mu_objects *o, const float *from, const float *to)
{
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    in.hero[0] = 3000.0f;
    in.hero[1] = 3000.0f;
    for (int i = 0; i < N; ++i)
        image(o, i)[MU_OBJF_VISIBLE] = 1;
    for (int s = 0; s < 256; ++s)
        o->rt.world.block_visible[s] = 1;
    o->rt.mouse_start = from;
    o->rt.mouse_end = to;
    mu_objects_step(o, &in);
}

static void draw(mu_objects *o, int i)
{
    mu_draw_options options;
    (void)mu_objects_prepare_index(o, i, NULL, 6, &options);
}

static void box(mu_objects *o, int i, float out[12]) { memcpy(out, image(o, i) + 0x31c, 48); }

int main(int argc, char **argv)
{
    assert(argc == 3);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    mu_object_record rec[N];
    setenv("MU_LANG_DIR", argv[2], 1);
    mu_objects *o = start(m, rec);
    assert(o->rt.anim_count == 6 && o->rt.anim_unsupported == 0);
    float b[12];
    static const float zero[12];

    /* no mouse segment: the mouse-over handlers count unsupported and change nothing; the boxes are still the
     * initialiser's zeros (the alpha ramp of these steps makes the objects drawable) */
    for (int k = 0; k < 12; ++k)
        step(o, NULL, NULL);
    assert(o->rt.anim_unsupported == 12 * N && action(o, 0) == 0 && action(o, 1) == 0 && action(o, 2) == 0);
    for (int i = 0; i < N; ++i) {
        box(o, i, b);
        assert(!memcmp(b, zero, sizeof zero));
    }
    assert(o->rt.obb_writes == 0);

    /* the render pass writes the box of the objects it draws: types 13 and 32, not 99 */
    draw(o, 0);
    draw(o, 1);
    assert(o->rt.obb_writes == 2);
    for (int i = 0; i < 2; ++i) {
        const float x = 3000.0f + 200.0f * (float)i;
        const float expect[12] = {x - 40.0f, 2960.0f, 50.0f, 80.0f, 0.0f, 0.0f, 0.0f, 80.0f, 0.0f, 0.0f, 0.0f, 80.0f};
        box(o, i, b);
        assert(!memcmp(b, expect, sizeof expect));
    }
    box(o, 2, b);
    assert(!memcmp(b, zero, sizeof zero));
    const long unsupported = o->rt.anim_unsupported;

    /* a segment beside the two drawn boxes: nothing over them. The undrawn object's zero box is over for every
     * segment (the client's test), so its handler 4 switches at once */
    const float beside[2][3] = {{3100.0f, 3500.0f, 900.0f}, {3100.0f, 3500.0f, -100.0f}};
    step(o, beside[0], beside[1]);
    assert(action(o, 0) == 0 && action(o, 1) == 0 && action(o, 2) == 1 && o->rt.anim_unsupported == unsupported);

    /* through the first box (2960..3040 x 2960..3040 x 50..130): handler 4 switches type 13 to action 1 */
    const float first[2][3] = {{3000.0f, 3000.0f, 900.0f}, {3000.0f, 3000.0f, -100.0f}};
    step(o, first[0], first[1]);
    assert(action(o, 0) == 1 && action(o, 1) == 0);
    step(o, first[0], first[1]);   /* still over: action 1's row (step 2) keeps it */
    assert(action(o, 0) == 1);
    /* exactly on the box's face plane x = 3040: the boundary counts as over */
    const float face[2][3] = {{3040.0f, 3000.0f, 900.0f}, {3040.0f, 3000.0f, -100.0f}};
    step(o, face[0], face[1]);
    assert(action(o, 0) == 1);
    /* one unit outside: it leaves, and action 1's row returns to action 0 */
    const float outside[2][3] = {{3041.0f, 3000.0f, 900.0f}, {3041.0f, 3000.0f, -100.0f}};
    step(o, outside[0], outside[1]);
    assert(action(o, 0) == 0 && action(o, 1) == 0);

    /* through the second box (3160..3240): handler 6 latches type 32 into action 1 */
    const float second[2][3] = {{3200.0f, 3000.0f, 900.0f}, {3200.0f, 3000.0f, -100.0f}};
    step(o, second[0], second[1]);
    assert(action(o, 0) == 0 && action(o, 1) == 1);
    assert(o->rt.anim_unsupported == unsupported);

    /* the box follows the object: a moved object's next draw rewrites it */
    mu_obj_set_f32(image(o, 0), MU_OBJF_POSITION + 8, 250.0f);
    draw(o, 0);
    box(o, 0, b);
    assert(b[2] == 250.0f && b[11] == 80.0f && o->rt.obb_writes == 3);

    mu_objects_runtime_free(o);
    free(o);
    unsetenv("MU_LANG_DIR");
    mu_bmd_free(&m->bmd);
    mu_model_free(&m->model);
    free(m);
    return 0;
}
