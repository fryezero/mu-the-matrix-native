/* Synthetic production-path checks for RENDER-WORLDS-INNER-001. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects.h"

static mu_object_model model;
static int effects, joints;
static uint32_t next(uint32_t seed) { return seed * 214013u + 2531011u; }
static void effect(void *c, int32_t type, int32_t sub, const float p[3], const float a[3], const float l[3], int32_t owner)
{
    (void)c; (void)a;
    assert(type == 0x193 && sub == 3 && owner == 0 && p[0] == 3050.0f && l[0] == 1.0f);
    ++effects;
}
static void joint(void *c, int32_t type, const float p[3], const float q[3], const float a[3], int32_t sub,
                   int32_t owner, float scale)
{
    (void)c; (void)a;
    assert(type == 0x7f7c && sub == 18 && owner == -1 && scale == 50.0f && p[0] != q[0]);
    ++joints;
}
static void reset(mu_objects *o, int32_t world, int32_t type)
{
    uint8_t *img = o->rt.images;
    memset(img, 0, MU_OBJ_SIZE);
    img[MU_OBJF_LIVE] = 1;
    mu_obj_set_i32(img, MU_OBJF_TYPE, type);
    mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -1);
    mu_obj_set_i32(img, MU_OBJF_BLEND_MESH, -1);
    mu_obj_set_f32(img, MU_OBJF_ALPHA, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_SCALE, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION, 3050.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION + 4, 4040.0f);
    memset(o->models, 0, sizeof o->models);
    o->models[type] = &model;
    memset(o->rt.stream, 0xff, sizeof o->rt.stream);
    o->world = world; o->rt.seed = 1;
    o->rt.particle_count = o->rt.sprite_count = 0;
    o->rt.draw_unsupported = 0;
    effects = joints = 0;
}
static mu_object_model *pass(mu_objects *o)
{
    mu_draw_options options;
    return mu_objects_prepare_index(o, 0, NULL, 6, &options);
}
static uint32_t seed_for(int calls, int modulus, int residue)
{
    for (uint32_t seed = 0; seed < 100000; ++seed) {
        uint32_t s = seed;
        for (int n = 0; n < calls; ++n) s = next(s);
        if ((int)((s >> 16) & 0x7fff) % modulus == residue) return seed;
    }
    abort();
}
int main(int argc, char **argv)
{
    assert(argc > 1);
    char error[256];
    assert(mu_bmd_load_file(argv[1], &model.bmd, error, sizeof error) == 0);
    assert(mu_model_init(&model.model, &model.bmd, NULL, error, sizeof error) == 0);
    model.loaded = 1;
    mu_objects *o = calloc(1, sizeof *o); assert(o);
    o->count = 1; o->rt.ready = 1; o->rt.images = calloc(1, MU_OBJ_SIZE); assert(o->rt.images);
    int32_t index = 0; o->rt.draw_count = 1; o->rt.draw_list = &index;
    o->rt.effect = effect; o->rt.joint = joint;
    for (int32_t world = 11; world <= 52; ++world) {
        if (world > 17 && world != 52) continue;
        reset(o, world, 11); assert(pass(o) == &model);
        assert(o->rt.sprite_count == 7 && o->rt.draw_unsupported == 0 && o->rt.seed == next(1));
        reset(o, world, 13); assert(pass(o) == &model && o->rt.sprite_count == 1);
        reset(o, world, 42); assert(pass(o) == &model);
        assert(o->rt.particle_count == 3 && mu_obj_f32(o->rt.images, 0xb4) == 1.0f);
        assert(o->rt.seed == next(next(next(1))));
        assert(o->rt.particles[0].bitmap == 0x7f89 && o->rt.particles[0].sub == 6);
        assert(o->rt.particles[2].bitmap == 0x7f78 && o->rt.particles[2].scale == 0.19f);
    }
    reset(o, 11, 11);
    model.bmd.bones[6].name[0] = 'x'; assert(pass(o) == &model);
    assert(o->rt.sprite_count == 6 && o->rt.draw_unsupported == 1);
    model.bmd.bones[6].name[0] = 'l';
    reset(o, 11, 11); o->models[11] = NULL; assert(pass(o) == NULL && o->rt.seed == 1);
    reset(o, 18, 11); (void)pass(o); assert(o->rt.sprite_count == 0);
    for (int32_t world = 37; world <= 40; world += 3) {
        reset(o, world, 0x25); (void)pass(o);
        assert(effects == 1 && mu_obj_i32(o->rt.images, MU_OBJF_HIDDEN_MESH) == -2);
        reset(o, world, 0x5c); o->rt.seed = seed_for(2, 30, 1);
        assert(pass(o) == &model && joints == 1 && o->rt.draw_unsupported == 0);
        reset(o, world, 0x69); o->rt.seed = seed_for(6, 20, 0);
        assert(pass(o) == &model && o->rt.sprite_count == 1 && o->rt.particle_count == 1);
        assert(o->rt.draw_unsupported == 1);   /* joint 0x7f7c/8 has no existing native kind */
        reset(o, world, 0x55); assert(pass(o) == &model);
        mu_object_mesh meshes[4];
        int32_t n = mu_objects_first_meshes(o, 0, NULL, &model, meshes, 4);
        assert(n == 3 && meshes[0].options.mesh_plus_one == 0 && meshes[1].options.mesh_plus_one == 4);
        assert(meshes[1].options.flags == 0x42 && meshes[2].options.flags == 0x84 && meshes[2].options.texture == 0x7f1f);
        reset(o, world, 0x60); assert(pass(o) == &model);
        n = mu_objects_first_meshes(o, 0, NULL, &model, meshes, 4);
        assert(n == 2 && meshes[1].options.mesh_plus_one == 1 && meshes[1].fields.light_mesh == 0);
        assert(o->rt.stream[0x60] == 0xff);
        int8_t components[4] = {4, 3, 3, 3}; model.textures.model_count = 4; model.textures.components = components;
        reset(o, world, 0x60); assert(pass(o) == &model);
        n = mu_objects_first_meshes(o, 0, NULL, &model, meshes, 4);
        assert(n == 1 && o->rt.draw_unsupported == 1);   /* alpha reference refusal retains the base body */
        mu_obj_set_i32(o->rt.images, MU_OBJF_HIDDEN_MESH, -2);
        assert(pass(o) == NULL);   /* refusing the extra pass must not bypass RenderObject's hidden skip */
        model.textures.model_count = 0; model.textures.components = NULL;
        reset(o, world, 0x60); mu_obj_set_i32(o->rt.images, MU_OBJF_HIDDEN_MESH, -2);
        assert(pass(o) == &model && mu_objects_first_meshes(o, 0, NULL, &model, meshes, 4) == 1);
        reset(o, world, 0x55); mu_obj_set_i32(o->rt.images, MU_OBJF_HIDDEN_MESH, -2);
        assert(pass(o) == &model && mu_objects_first_meshes(o, 0, NULL, &model, meshes, 4) == 2);
    }
    reset(o, 40, 0x3e); (void)pass(o); assert(o->rt.particle_count == 20);
    mu_obj_set_i32(o->rt.images, MU_OBJF_HIDDEN_MESH, -2); o->rt.particle_count = 0;
    (void)pass(o); assert(o->rt.particle_count == 0);
    reset(o, 37, 0x6e); model.bmd.bone_count = 1; (void)pass(o);
    assert(o->rt.sprite_count == 0 && o->rt.draw_unsupported == 1); model.bmd.bone_count = 7;
    free(o->rt.images); free(o); mu_model_free(&model.model); mu_bmd_free(&model.bmd);
    puts("classless inline host: Blood Castle gates/bones/counter, Kanturu effects/joints/meshes/refusals OK");
    return 0;
}
