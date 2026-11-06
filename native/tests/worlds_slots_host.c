/* RENDER-WORLDS-SLOTS: the class custom render (slot 0x38) of Loren Market, Event square, Ferea, Swamp of Darkness
 * and Kubera in the production first pass (mu_objects_prepare_index), their after render (slot 0x3c) in the after
 * pass (mu_objects_prepare_after), and Loren Market's outer RenderObjectVisual flicker draw. Production runtime. */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects.h"
#include "../core/mu_terrain.h"

static const char *model_path, *boned_path;

static mu_objects *population(int32_t world, int32_t type)
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
    o->rt.after_list = calloc(1, sizeof(int32_t));
    o->rt.after_count = 1;
    o->rt.seed = 1;
    memset(o->rt.stream, 0xff, sizeof o->rt.stream);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(model_path, &m->bmd, error, sizeof error) == 0);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    o->models[type] = m;
    return o;
}

static void release(mu_objects *o, int32_t type)
{
    mu_model_free(&o->models[type]->model);
    mu_bmd_free(&o->models[type]->bmd);
    free(o->models[type]);
    free(o->rt.after_list);
    free(o->rt.images);
    free(o);
}

/* the first pass: returns whether the object is drawn there; *draws: the slot's RenderBody/RenderMesh calls */
static int first_pass(mu_objects *o, mu_world *map, int32_t *draws, uint32_t textures[8])
{
    mu_draw_options options;
    const int drawn = mu_objects_prepare_index(o, 0, map, 6, &options) != NULL;
    *draws = 0;
    for (int32_t k = 0; k < o->rt.slot_count; ++k)
        if (o->rt.slot_events[k].call == MU_OBJ_CALL_BODY || o->rt.slot_events[k].call == MU_OBJ_CALL_MESH) {
            if (*draws < 8)
                textures[*draws] = o->rt.slot_events[k].args[7];
            ++*draws;
        }
    return drawn;
}

static uint32_t msvc_next(uint32_t seed) { return seed * 214013u + 2531011u; }

int main(int argc, char **argv)
{
    assert(argc > 1);
    model_path = argv[1];
    boned_path = argc > 2 ? argv[2] : argv[1];
    mu_world *map = calloc(1, sizeof *map);
    assert(map);
    int32_t draws;
    uint32_t tex[8];

    /* Loren Market and Event square type 8: the custom render flags it for the after pass and draws nothing */
    for (int32_t world = 79; world <= 114; world += 35) {
        mu_objects *o = population(world, 8);
        assert(!first_pass(o, map, &draws, tex) && draws == 0 && o->rt.images[MU_OBJF_AFTER_CHARACTER] == 1);
        if (world == 79) {   /* the outer RenderObjectVisual draw rand() % 30 is the only one for type 8 */
            assert(o->rt.seed == msvc_next(1));
            mu_object_mesh meshes[8];
            int32_t count = -1;
            assert(mu_objects_prepare_after(o, 0, map, 6, meshes, 8, &count) == o->models[8]);
        }
        release(o, 8);
    }
    /* Loren Market type 0x32: three meshes and the pulsing mesh 2 in the first pass, no RenderBody */
    {
        mu_objects *o = population(79, 0x32);
        first_pass(o, map, &draws, tex);
        assert(draws == 4 && o->rt.slot_index == 0 && o->rt.images[MU_OBJF_AFTER_CHARACTER] == 0);
        release(o, 0x32);
    }
    /* Kubera (world 125's loader bitmaps): type 0x75 draws mesh 0/1 with the handler's gem bitmaps, then chrome */
    {
        mu_objects *o = population(125, 0x75);
        first_pass(o, map, &draws, tex);
        assert(draws == 3 && tex[0] == 0x82b5 && tex[1] == 0x82b6 && tex[2] == 0x829a);
        release(o, 0x75);
        o = population(127, 0x1d);   /* an after-character type: the first pass skips it */
        assert(!first_pass(o, map, &draws, tex) && draws == 0);
        release(o, 0x1d);
    }
    /* Ferea's statue (type 0x7b) takes hs_statueB only while the handler's door state is 2 or 3 */
    for (int32_t state = 0; state <= 2; state += 2) {
        mu_objects *o = population(112, 0x7b);
        o->rt.q_handler.ferea_state = state;
        first_pass(o, map, &draws, tex);
        assert(draws == 1 && tex[0] == (state == 2 ? 0x8225u : 0xffffffffu));
        release(o, 0x7b);
    }
    /* Swamp of Darkness crocodile: RenderBody and three hsCrocodileA_R glows */
    {
        mu_objects *o = population(122, 0x83);
        first_pass(o, map, &draws, tex);
        assert(draws == 4 && tex[0] == 0xffffffffu && tex[1] == 0x8273 && tex[3] == 0x8273);
        release(o, 0x83);
    }
    /* Vulcanus statue 0x44 without bone 6: the draws stay, the flares and spark are refused and counted, and the
     * slot's two rand draws for the spark offset still happen */
    {
        mu_objects *o = population(63, 0x44);
        first_pass(o, map, &draws, tex);
        assert(draws == 3 && o->rt.draw_unsupported == 1 && o->rt.sprite_events == 0 &&
               o->rt.particle_events == 0 && o->rt.seed == msvc_next(msvc_next(1)));
        release(o, 0x44);
    }
    /* with seven posed bones: two flares on bone 6 and, at frame 36, the eyes shut and a spark from bone 4 */
    {
        const char *one = model_path;
        model_path = boned_path;
        mu_objects *o = population(63, 0x43);
        model_path = one;
        mu_obj_set_f32(o->rt.images, MU_OBJF_FRAME, 36.0f);
        first_pass(o, map, &draws, tex);
        assert(draws == 3 && o->rt.draw_unsupported == 0 && o->rt.sprite_events == 2 && o->rt.sprite_count == 2 &&
               o->rt.particle_events == 1 && mu_obj_u16(o->rt.images, 0x54) == 0xffff && o->rt.seed == 1);
        release(o, 0x43);
    }
    /* a world without these slots keeps RenderBody in the first pass */
    {
        mu_objects *o = population(73, 8);
        assert(first_pass(o, map, &draws, tex) && draws == 0 && o->rt.images[MU_OBJF_AFTER_CHARACTER] == 0);
        release(o, 8);
    }
    free(map);
    return 0;
}
