/* RENDER-WORLDS-O: the Abyss visual in the production object host. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int generic;
static void visual(void *c, mu_objects *o, int32_t i, int has, mu_object_model *m)
{ (void)c; (void)o; (void)i; (void)has; (void)m; ++generic; }
static int32_t prepare(mu_objects *o, int32_t world, int32_t type, int loaded)
{
    uint8_t *img = o->rt.images;
    mu_draw_options options;
    o->world = world;
    o->models[type]->loaded = loaded;
    mu_obj_set_i32(img, MU_OBJF_TYPE, type);
    mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -1);
    (void)mu_objects_prepare_index(o, 0, NULL, 6, &options);
    o->models[type]->loaded = 1;
    return mu_obj_i32(img, MU_OBJF_HIDDEN_MESH);
}
int main(int argc, char **argv)
{
    char error[256];
    mu_objects *o = calloc(1, sizeof *o);
    mu_object_model *m = calloc(1, sizeof *m);
    assert(argc == 2 && o && m);
    assert(mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    o->count = 1; o->rt.ready = 1; o->rt.images = calloc(1, MU_OBJ_SIZE); o->rt.visual = visual;
    assert(o->rt.images);
    m->loaded = 1;   /* authored two-bone model without meshes */
    o->models[38] = o->models[39] = m;
    uint8_t *img = o->rt.images;
    img[MU_OBJF_LIVE] = img[MU_OBJF_VISIBLE] = 1;
    mu_obj_set_f32(img, MU_OBJF_SCALE, 1); mu_obj_set_f32(img, MU_OBJF_ALPHA, 1);
    mu_obj_set_f32(img, MU_OBJF_ALPHA_TARGET, 1);
    for (int32_t world = 128; world <= 130; ++world) {
        assert(prepare(o, world, 39, 1) == -2);   /* 0x00d5d564/0x00d5f1f1/0x00d60948 */
        assert(prepare(o, world, 38, 1) == -1);
        assert(prepare(o, world, 39, 0) == -1);   /* model gate */
    }
    assert(generic == 0);                         /* primary visual replaces the generic hook */
    assert(prepare(o, 127, 39, 1) == -1 && generic == 1);
    assert(prepare(o, 139, 39, 1) == -1 && generic == 2);   /* 131 is a primary-visual world since RENDER-WORLDS-R */
    free(o->rt.images); free(o); free(m);
    return 0;
}
