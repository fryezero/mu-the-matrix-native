/* RENDER-WORLDS-S3: authored Imperial Guardian / Event square / Test Area populations through production creation,
 * steps and the visual pass. The model has 28 bones in a chain along z and two actions of 30 keys. */
#include "../core/mu_objects.h"
#include "../../reconstructed/objects/worlds_s3.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static int sprites, particles, joints, effects;
static void sprite(void *ctx, int32_t type, const float p[3], float scale, const float l[3], int32_t owner,
                   float rotation, int32_t a, int32_t b)
{
    (void)ctx; (void)p; (void)scale; (void)l; (void)owner; (void)rotation; (void)a; (void)b;
    assert(type == 0x7f6b || type == 0x7f78 || type == 0x7ef7);
    ++sprites;
}
static void particle(void *ctx, int32_t type, const float p[3], const float a[3], const float l[3], int32_t sub,
                     float scale, int32_t owner)
{
    (void)ctx; (void)p; (void)a; (void)l; (void)sub; (void)scale; (void)owner;
    assert(type == 0x8089 || type == 0x8084 || type == 0x806e || type == 0x8085 || type == 0x7f89 ||
           type == 0x7f25 || type == 0x7f5a || type == 0x801e || type == 0x801c || type == 0x801b ||
           type == 0x8086 || type == 0x8087);
    ++particles;
}
static void joint(void *ctx, int32_t type, const float p[3], const float t[3], const float a[3], int32_t sub,
                  int32_t owner, float scale)
{
    (void)ctx; (void)type; (void)p; (void)t; (void)a; (void)sub; (void)owner; (void)scale;
    ++joints;
}
static void effect(void *ctx, int32_t type, int32_t sub, const float p[3], const float a[3], const float l[3],
                   int32_t owner)
{
    (void)ctx; (void)a; (void)l;
    assert(type >= 0x1ab && type <= 0x1ad && sub == 1 && owner == -1 && p[2] == 525.0f);
    ++effects;
}
enum { N = 10, STEPS = 200 };
static const int guardian[N] = {12, 20, 20, 37, 50, 64, 79, 85, 0x81, 0x51};
static const int guardian72[N] = {10, 0x73, 157, 158, 20, 0x84, 12, 50, 51, 64};
static const int square[N] = {30, 35, 8, 54, 55, 57, 58, 67, 68, 59};
static const int test_area[N] = {0x1a8, 0x1ab, 22, 70, 80, 0, 1, 2, 3, 4};
static mu_objects *start(int world, const int *types, mu_object_record *rec, mu_object_model *m)
{
    mu_objects *o = calloc(1, sizeof *o);
    memset(rec, 0, N * sizeof *rec);
    for (int i = 0; i < N; ++i) {
        rec[i].type = (int16_t)types[i];
        rec[i].position[0] = 100.0f + 10.0f * (float)i; rec[i].position[1] = 200; rec[i].position[2] = 5;
        rec[i].angle[2] = 725.0f;
        rec[i].scale = 2.5f;
        rec[i].flag_2c = 1; rec[i].flag_2d = 1; rec[i].flag_2e = 1;
    }
    mu_objects_init(o, world);
    o->records = rec; o->count = N;
    for (int i = 0; i < N; ++i) o->models[types[i]] = m;
    assert(mu_objects_start(o, NULL) == 0);
    assert(o->rt.created == N && o->rt.create_unsupported == 0);
    for (int i = 0; i < N; ++i) o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
    for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
    o->rt.sprite = sprite; o->rt.particle = particle; o->rt.joint = joint; o->rt.effect = effect;
    return o;
}
static void finish(mu_objects *o)
{
    o->records = NULL;
    mu_objects_runtime_free(o);
    free(o);
}
static void visual_pass(mu_objects *o)
{
    mu_draw_options options;
    for (int i = 0; i < N; ++i) (void)mu_objects_prepare_index(o, i, NULL, 6, &options);
}
static uint8_t *img(const mu_objects *o, int i) { return o->rt.images + i * MU_OBJ_SIZE; }
int main(int argc, char **argv)
{
    assert(argc == 2);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(m->bmd.bone_count == 28);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    mu_object_record rec[N];
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    /* ---- Imperial Guardian, classes 69..71 (one body) ---- */
    for (int world = 69; world <= 71; ++world) {
        mu_objects *o = start(world, guardian, rec, m);
        assert(mu_obj_f32(img(o, 8), MU_OBJF_ANGLE + 8) == 5.0f);   /* 0x81: 725 % 360 */
        assert(memcmp(img(o, 8) + MU_OBJF_HEAD_ANGLE, img(o, 8) + MU_OBJF_ANGLE, 12) == 0);
        assert(memcmp(img(o, 8) + MU_OBJF_POSITION_COPY, img(o, 8) + MU_OBJF_POSITION, 12) == 0);
        mu_obj_set_f32(img(o, 2), MU_OBJF_FRAME, 3.0f);   /* the second type-20 object leads */
        sprites = particles = joints = effects = 0;
        long refused = o->rt.draw_unsupported;
        for (int k = 0; k < STEPS; ++k) {
            in.time = 37.0f * (float)k;
            const long ticks = o->rt.ticks;
            mu_objects_step(o, &in);
            assert(o->rt.ticks == ticks + 2 * N);   /* MoveObject's tick and the class slot's own */
            /* type 20's class static: the last type-20 object leaves its frame in it (or takes it) */
            assert(mu_obj_f32(img(o, 2), MU_OBJF_FRAME) == o->rt.imperial_frame);
            assert(mu_obj_i32(img(o, 8), MU_OBJF_HIDDEN_MESH) == -2);
            visual_pass(o);
        }
        assert(o->rt.imperial_frame != 0.0f && o->rt.move_unsupported == 0);
        assert(fabsf(mu_obj_f32(img(o, 9), MU_OBJF_BLEND_V) - 0.015f * (float)STEPS) < 1e-3f);   /* 0x51 */
        /* per frame: 12 four sprites, 37 and 79 one each; 50 twelve particles, 79 one */
        assert(sprites == 6 * STEPS && particles >= 13 * STEPS && joints == 0);
        /* refused: the 0x7fd5 subtype-5 joints of type 20 and type 85's word4 effects (no word4 hook) */
        assert(o->rt.draw_unsupported > refused && effects == 0);
        m->bmd.bone_count = 2;   /* types 12 (bone 3) and 50 (bone 7) are refused; 37 (bone 1) still draws */
        refused = o->rt.draw_unsupported;
        sprites = 0;
        visual_pass(o);
        assert(o->rt.draw_unsupported >= refused + 2 && sprites == 2);
        m->bmd.bone_count = 28;
        finish(o);
    }
    /* ---- Imperial Guardian, class 72 ---- */
    {
        mu_objects *o = start(72, guardian72, rec, m);
        const int32_t countdown = mu_obj_i32(img(o, 0), 0x60);
        assert(countdown >= 0 && countdown < 50 && mu_obj_i32(img(o, 1), 0x60) == 100);
        particles = 0;
        for (int k = 0; k < STEPS; ++k) {
            in.time = 37.0f * (float)k;
            mu_objects_step(o, &in);
            visual_pass(o);
        }
        assert(mu_obj_i32(img(o, 0), 0x60) == 0);   /* type 10 counted down, one per step */
        /* per frame: 157 forty-two particles, 158 one, 50 twelve */
        assert(particles >= 55 * STEPS && o->rt.move_unsupported == 0);
        finish(o);
    }
    /* ---- Event square: Loren Market's bodies; the same population steps identically in 79 and 114 ---- */
    {
        mu_objects *market = start(79, square, rec, m);
        mu_object_record rec2[N];
        mu_objects *o = start(114, square, rec2, m);
        assert(mu_obj_i32(img(o, 7), MU_OBJF_HIDDEN_MESH) == -2 && img(o, 8)[MU_OBJF_AFTER_CHARACTER] == 1);
        for (int k = 0; k < STEPS; ++k) {
            in.time = 37.0f * (float)k;
            mu_objects_step(market, &in);
            mu_objects_step(o, &in);
            assert(o->rt.light_count == 2 && market->rt.light_count == 2);   /* types 30 and 35 at their bones */
            for (int q = 0; q < 2; ++q)
                assert(memcmp(&o->rt.lights[q], &market->rt.lights[q], sizeof o->rt.lights[q]) == 0);
        }
        assert(memcmp(o->rt.images, market->rt.images, (size_t)N * MU_OBJ_SIZE) == 0);
        assert(mu_obj_f32(img(o, 2), MU_OBJF_VELOCITY) == 0.2f);
        sprites = particles = 0;
        visual_pass(o);
        assert(sprites > 0 && particles > 0 && o->rt.move_unsupported == 0);
        finish(market);
        finish(o);
    }
    /* ---- Test Area ---- */
    {
        effects = 0;
        mu_objects *o = start(121, test_area, rec, m);
        particles = 0;
        for (int k = 0; k < STEPS; ++k) {
            in.time = 37.0f * (float)k;
            const long ticks = o->rt.ticks;
            mu_objects_step(o, &in);
            assert(o->rt.ticks == ticks + N);   /* no class tick */
            const float s = (float)sin((double)(in.time * 0.001f)) + 1.0f;
            assert(mu_obj_f32(img(o, 2), MU_OBJF_BLEND_LIGHT) == s);
            assert(mu_obj_i32(img(o, 3), MU_OBJF_HIDDEN_MESH) == -2 && mu_obj_i32(img(o, 4), MU_OBJF_HIDDEN_MESH) == -2);
            visual_pass(o);
        }
        assert(effects == 3);   /* type 0x1ab's three warp effects, at the first step */
        assert(particles == 4 * STEPS && o->rt.move_unsupported == 0);
        finish(o);
    }
    mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m);
    return 0;
}
