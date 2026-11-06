/* RENDER-WORLDS-SLOTS2: RenderObjectVisual's outer flicker draw (0x017f9758: rand() % 30 at 0x017f9797) in the
 * production first pass (mu_objects_prepare_index) of every class world: one draw of the object generator for an
 * object with a model and a type no slot of the world draws for, none without a model. Production runtime. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects.h"
#include "../core/mu_terrain.h"

static const char *model_path;

static mu_objects *population(int32_t world, int32_t type, int with_model)
{
    mu_objects *o = calloc(1, sizeof *o);
    assert(o);
    o->world = world;
    o->rt.ready = 1;
    o->count = 1;
    o->rt.images = calloc(1, MU_OBJ_SIZE);
    assert(o->rt.images);
    uint8_t *img = o->rt.images;
    img[MU_OBJF_LIVE] = 1;
    mu_obj_set_i32(img, MU_OBJF_TYPE, type);
    mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -1);
    mu_obj_set_i32(img, MU_OBJF_BLEND_MESH, -1);
    mu_obj_set_f32(img, MU_OBJF_ALPHA, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_SCALE, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION, 3050.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION + 4, 4040.0f);
    o->rt.seed = 1;
    memset(o->rt.stream, 0xff, sizeof o->rt.stream);
    if (with_model) {
        mu_object_model *m = calloc(1, sizeof *m);
        char error[256];
        assert(m && mu_bmd_load_file(model_path, &m->bmd, error, sizeof error) == 0);
        assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
        m->loaded = 1;
        o->models[type] = m;
    }
    return o;
}

static void release(mu_objects *o, int32_t type)
{
    if (o->models[type]) {
        mu_model_free(&o->models[type]->model);
        mu_bmd_free(&o->models[type]->bmd);
        free(o->models[type]);
    }
    free(o->rt.images);
    free(o);
}

static uint32_t msvc_next(uint32_t seed) { return seed * 214013u + 2531011u; }

int main(int argc, char **argv)
{
    assert(argc > 1);
    model_path = argv[1];
    mu_world *map = calloc(1, sizeof *map);
    assert(map);
    /* every class registration (Tormenta 141's draw is the particle visual's), and two worlds without a class */
    static const int32_t worlds[] = {57, 58, 62, 63, 64, 69, 70, 71, 72, 79, 80, 81, 82, 91, 92, 93, 94, 95, 96, 100,
                                     101, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124,
                                     125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140,
                                     142, 143, 144, 145, 73, 141};
    const int32_t type = 250;   /* no slot of these worlds names it */
    int failures = 0;
    for (size_t k = 0; k < sizeof worlds / sizeof worlds[0]; ++k)
        for (int with_model = 0; with_model <= 1; ++with_model) {
            const int32_t world = worlds[k];
            mu_objects *o = population(world, type, with_model);
            mu_draw_options options;
            (void)mu_objects_prepare_index(o, 0, map, 6, &options);
            const uint32_t expect = with_model && world != 73 && world != 141 ? msvc_next(1) : 1;
            if (o->rt.seed != expect) {
                fprintf(stderr, "world %d model %d: seed %u, expected %u\n", world, with_model, o->rt.seed, expect);
                ++failures;
            }
            release(o, type);
        }
    free(map);
    return failures != 0;
}
