/* RENDER-WORLDS-SLOTS2: RenderObjectVisual's outer flicker draw (0x017f9758: rand() % 30 at 0x017f9797) in the
 * production first pass (mu_objects_prepare_index) of every class world: one draw of the object generator for an
 * object with a model and a type no slot of the world draws for, none without a model. Then the custom slots this
 * lane adds, in the same pass. Production runtime. */
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

/* the first pass: the custom slot's RenderBody/RenderMesh count and their textures */
static int32_t slot_draws(mu_objects *o, mu_world *map, uint32_t textures[8])
{
    mu_draw_options options;
    (void)mu_objects_prepare_index(o, 0, map, 6, &options);
    int32_t draws = 0;
    for (int32_t k = 0; k < o->rt.slot_count; ++k)
        if (o->rt.slot_events[k].call == MU_OBJ_CALL_BODY || o->rt.slot_events[k].call == MU_OBJ_CALL_MESH) {
            if (draws < 8)
                textures[draws] = o->rt.slot_events[k].args[7];
            ++draws;
        }
    return draws;
}

int main(int argc, char **argv)
{
    assert(argc > 1);
    model_path = argv[1];
    mu_world *map = calloc(1, sizeof *map);
    assert(map);
    /* every class registration and two worlds without a class (RENDER-WORLDS-SLOTS3: 73 and Tormenta 141 now draw
     * it too; the built-in worlds 4/7/8 draw it in mu_builtin_visual) */
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
            const uint32_t expect = with_model ? msvc_next(1) : 1;
            if (o->rt.seed != expect) {
                fprintf(stderr, "world %d model %d: seed %u, expected %u\n", world, with_model, o->rt.seed, expect);
                ++failures;
            }
            release(o, type);
        }
    uint32_t tex[8];
    /* Santa Village 0x10: meshes 0..2 and mesh 2's 0x44 glow */
    mu_objects *o = population(62, 0x10, 1);
    assert(slot_draws(o, map, tex) == 4 && o->rt.slot_index == 0);
    release(o, 0x10);
    /* Arca War 96 forwards to Debenter's 0x32: the body mesh and its solight02 glow */
    o = population(96, 0x32, 1);
    assert(slot_draws(o, map, tex) == 2 && tex[0] == 0xffffffffu && tex[1] == 0x81a7);
    release(o, 0x32);
    /* Arca War 101 forwards to Uruk Mountain's 0x10: meshes 0 and 1 */
    o = population(101, 0x10, 1);
    assert(slot_draws(o, map, tex) == 2);
    release(o, 0x10);
    /* Imperial Guardian 72 type 0x60: the grey body (after world 69's slot answered no) */
    o = population(72, 0x60, 1);
    assert(slot_draws(o, map, tex) == 1 && tex[0] == 0xffffffffu);
    release(o, 0x60);
    /* World 82 type 0xa: flagged for the after pass, nothing drawn first */
    o = population(82, 0xa, 1);
    assert(slot_draws(o, map, tex) == 0 && o->rt.images[MU_OBJF_AFTER_CHARACTER] == 1);
    release(o, 0xa);
    /* Imperial Guardian 70 type 0x73 (world 69's slot): four meshes; without bone 9 the effect is refused and
     * counted, and the frame latch +0x60 still turns 0x64 into 0x65 */
    o = population(70, 0x73, 1);
    mu_obj_set_f32(o->rt.images, MU_OBJF_FRAME, 0.2f);
    mu_obj_set_i32(o->rt.images, 0x60, 0x64);
    assert(slot_draws(o, map, tex) == 4 && o->rt.draw_unsupported == 1 && o->rt.effect_events == 0 &&
           mu_obj_i32(o->rt.images, 0x60) == 0x65);
    release(o, 0x73);
    free(map);
    return failures != 0;
}
