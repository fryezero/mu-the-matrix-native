/* RENDER-WORLDS-121 in the production first pass (mu_objects_prepare_index, no particle module attached):
 * - Test Area 121 types 6..12: the custom slot's per-vertex light 0.5 lands in the model's light buffer after the
 *   pose and before the draw (MU_OBJ_CALL_VERTEX_LIGHT replayed by slot_vertex_light); type 0x52 and world 120 keep
 *   the transform's lights;
 * - type 0x13: one bone-placed CreateParticle per bone and window, through the visual pass's consumer; a bone the
 *   model does not have is refused and counted;
 * - Devias 0x67: the action choice's rand() after the outer draw, at the action's last key only;
 * - RENDER-WORLDS-RAKLION: Raklion 57/58 run the same slot (world 56 does not): the per-vertex light, the 0x13
 *   particles, and type 0x52's frame restart while the handler byte +0x22 is 0 (Raklion event state above 6). */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects.h"

static mu_object_model model;

static uint32_t msvc_next(uint32_t seed) { return seed * 214013u + 2531011u; }
static int32_t msvc_value(uint32_t seed) { return (int32_t)((seed >> 16) & 0x7fff); }

static void reset(mu_objects *o, int32_t world, int32_t type, uint16_t action, float frame)
{
    uint8_t *img = o->rt.images;
    memset(img, 0, MU_OBJ_SIZE);
    img[MU_OBJF_LIVE] = 1;
    img[MU_OBJF_LIGHT_ENABLE] = 1;   /* lit: Transform writes the per-vertex light */
    mu_obj_set_i32(img, MU_OBJF_TYPE, type);
    mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -1);
    mu_obj_set_i32(img, MU_OBJF_BLEND_MESH, -1);
    mu_obj_set_f32(img, MU_OBJF_ALPHA, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_SCALE, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION, 3050.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION + 4, 4040.0f);
    mu_obj_set_u16(img, MU_OBJF_ACTION, action);
    mu_obj_set_f32(img, MU_OBJF_FRAME, frame);
    memset(o->models, 0, sizeof o->models);
    o->models[type] = &model;
    memset(o->rt.stream, 0xff, sizeof o->rt.stream);
    o->world = world;
    o->rt.seed = 1;
    o->rt.particle_count = 0;
    o->rt.draw_unsupported = 0;
}

static mu_object_model *pass(mu_objects *o)
{
    mu_draw_options options;
    return mu_objects_prepare_index(o, 0, NULL, 6, &options);
}

static int draws_since_one(const mu_objects *o)
{
    int n = 0;
    for (uint32_t s = 1; s != o->rt.seed && n < 64; s = msvc_next(s))
        ++n;
    return n;
}

int main(int argc, char **argv)
{
    assert(argc > 1);
    char error[256];
    assert(mu_bmd_load_file(argv[1], &model.bmd, error, sizeof error) == 0);
    assert(mu_model_init(&model.model, &model.bmd, NULL, error, sizeof error) == 0);
    model.loaded = 1;
    assert(model.bmd.mesh_count == 1 && model.bmd.meshes[0].normal_count == 3 && model.bmd.bone_count == 2);
    mu_objects *o = calloc(1, sizeof *o);
    assert(o);
    o->count = 1;
    o->rt.ready = 1;
    o->rt.images = calloc(1, MU_OBJ_SIZE);
    assert(o->rt.images);
    const float *lights = mu_model_lights(&model.model, 0);

    /* default: world 120 (the base custom slot answers no) and 121 type 0x52 keep the transform's lights */
    float base[3];
    reset(o, 120, 6, 0, 0.0f);
    assert(pass(o) == &model);
    memcpy(base, lights, sizeof base);
    assert(base[0] != 0.5f && base[0] != 0.0f);
    reset(o, 121, 0x52, 0, 0.0f);
    assert(pass(o) == &model && memcmp(base, lights, sizeof base) == 0);

    /* 121 types 6..12: 0.5 for every normal, the object light 1 */
    for (int32_t type = 6; type <= 12; ++type) {
        reset(o, 121, type, 0, 0.0f);
        assert(pass(o) == &model);
        for (int k = 0; k < 3; ++k)
            assert(lights[k] == 0.5f);
        assert(mu_obj_f32(o->rt.images, MU_OBJF_LIGHT) == 1.0f && mu_obj_f32(o->rt.images, MU_OBJF_LIGHT + 8) == 1.0f);
    }
    reset(o, 120, 6, 0, 0.0f);   /* the next pose writes the transform's lights again */
    assert(pass(o) == &model && memcmp(base, lights, sizeof base) == 0);

    /* 121 type 0x13, action 0: frame 3 creates 0x801e then 0x801c per bone (2 + 2); frame 11.5 names bones 6..8,
     * which the model lacks (3 refused), then 0x801c per bone */
    reset(o, 121, 0x13, 0, 3.0f);
    assert(pass(o) == &model);
    assert(o->rt.particle_count == 4 && o->rt.draw_unsupported == 0);
    assert(o->rt.particles[0].bitmap == 0x801e && o->rt.particles[0].sub == 7 && o->rt.particles[0].scale == 1.0f);
    assert(o->rt.particles[3].bitmap == 0x801c && o->rt.particles[3].sub == 8 && o->rt.particles[3].scale == 1.5f);
    reset(o, 121, 0x13, 0, 11.5f);
    assert(pass(o) == &model);
    assert(o->rt.particle_count == 2 && o->rt.draw_unsupported == 3);
    reset(o, 121, 0x13, 0, 20.0f);   /* past 19.5: action 1 by a direct write */
    assert(pass(o) == &model && mu_obj_u16(o->rt.images, MU_OBJF_ACTION) == 1);

    /* Raklion 57/58: the same per-vertex light and particles; world 56 keeps the transform's lights */
    for (int32_t world = 57; world <= 58; ++world) {
        reset(o, world, 9, 0, 0.0f);
        assert(pass(o) == &model);
        for (int k = 0; k < 3; ++k)
            assert(lights[k] == 0.5f);
        assert(mu_obj_f32(o->rt.images, MU_OBJF_LIGHT + 4) == 1.0f);
        reset(o, world, 0x13, 0, 3.0f);
        assert(pass(o) == &model && o->rt.particle_count == 4 && o->rt.draw_unsupported == 0);
        assert(o->rt.particles[0].bitmap == 0x801e && o->rt.particles[3].bitmap == 0x801c);
    }
    reset(o, 56, 9, 0, 0.0f);
    assert(pass(o) == &model && memcmp(base, lights, sizeof base) == 0);
    /* 0x52: the frame stays while the event state is <= 6 (+0x22 = 1), restarts past 6; 11 leaves +0x22 alone */
    o->world = 57;
    mu_objects_raklion_set_event(o, 2);
    assert(o->rt.raklion_state[0x22] == 1);
    reset(o, 57, 0x52, 0, 7.5f);
    mu_obj_set_f32(o->rt.images, MU_OBJF_PRIOR_FRAME, 6.5f);
    assert(pass(o) == &model && mu_obj_f32(o->rt.images, MU_OBJF_FRAME) == 7.5f);
    mu_objects_raklion_set_event(o, 7);
    mu_objects_raklion_set_event(o, 11);
    assert(o->rt.raklion_state[0x22] == 0);
    reset(o, 57, 0x52, 0, 7.5f);
    mu_obj_set_f32(o->rt.images, MU_OBJF_PRIOR_FRAME, 6.5f);
    assert(pass(o) == &model && mu_obj_f32(o->rt.images, MU_OBJF_FRAME) == 0.0f &&
           mu_obj_f32(o->rt.images, MU_OBJF_PRIOR_FRAME) == 0.0f);
    reset(o, 121, 0x52, 0, 7.5f);   /* 121 has no gate */
    assert(pass(o) == &model && mu_obj_f32(o->rt.images, MU_OBJF_FRAME) == 7.5f);
    mu_objects_raklion_set_event(o, 0);   /* only in 57/58 */

    /* Devias 0x67 (action 0 has 2 keys): at frame 1 (the last key) a second draw picks the action */
    reset(o, 2, 0x67, 0, 1.0f);
    (void)pass(o);
    assert(draws_since_one(o) == 2);
    const uint32_t second = msvc_next(msvc_next(1));
    assert(mu_obj_u16(o->rt.images, MU_OBJF_ACTION) == (msvc_value(second) % 32 == 0 ? 1 : 0));
    reset(o, 2, 0x67, 0, 0.0f);
    (void)pass(o);
    assert(draws_since_one(o) == 1);
    reset(o, 2, 0x64, 0, 1.0f);   /* another Devias type: the outer draw only */
    (void)pass(o);
    assert(draws_since_one(o) == 1);

    free(o->rt.images);
    free(o);
    mu_model_free(&model.model);
    mu_bmd_free(&model.bmd);
    puts("worlds-121-host ok");
    return 0;
}
