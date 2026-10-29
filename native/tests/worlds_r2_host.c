/* RENDER-WORLDS-R2: authored Twisted Karutan / Kardamahal / Swamp of Destruction populations through production
 * creation, steps and the visual pass. The model has 13 bones; bones 5 and 9 are named E002 and E005. */
#include "../core/mu_objects.h"
#include "../../reconstructed/objects/worlds_r2.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static int sprites, particles, joints, sounds[8];
static float joint_scale;
static void sprite(void *ctx, int32_t type, const float p[3], float scale, const float l[3], int32_t owner,
                   float rotation, int32_t a, int32_t b)
{
    (void)ctx; (void)p; (void)l; (void)owner; (void)rotation; (void)a; (void)b;
    assert(type == 0x7ef7 || type == 0x7f26);
    assert(scale == 2.0f || scale == 1.5f || scale == 4.0f || scale == 5.0f);
    ++sprites;
}
static void particle(void *ctx, int32_t type, const float p[3], const float a[3], const float l[3], int32_t sub,
                     float scale, int32_t owner)
{
    (void)ctx; (void)p; (void)a; (void)l; (void)sub; (void)scale; (void)owner;
    assert(type == 0x8084 || type == 0x806e || type == 0x8085 || type == 0x7f89 || type == 0x7f5a);
    ++particles;
}
static void joint(void *ctx, int32_t type, const float p[3], const float t[3], const float a[3], int32_t sub,
                  int32_t owner, float scale)
{
    (void)ctx; (void)a;
    assert(type == 0x7f7d && (sub == 0x12 || sub == 0x19 || sub == 0x1a) && owner >= 0);
    assert(p[0] == t[0] && p[1] == t[1] && p[2] == t[2]);
    joint_scale = scale;
    ++joints;
}
static void sound(void *ctx, int32_t id)
{
    (void)ctx;
    assert(id >= 0x5a4 && id <= 0x5a9);
    ++sounds[id - 0x5a4];
}
enum { N = 10, STEPS = 200 };
static const int karutan[N] = {0, 1, 72, 113, 115, 116, 118, 160, 196, 162};
static const int kardamahal[N] = {0, 4, 34, 78, 113, 115, 128, 133, 146, 161};
static const int swamp[N] = {6, 32, 64, 76, 160, 169, 183, 185, 187, 7};
static mu_objects *start(int world, const int *types, mu_object_record *rec, mu_object_model *m)
{
    mu_objects *o = calloc(1, sizeof *o);
    memset(rec, 0, N * sizeof *rec);
    for (int i = 0; i < N; ++i) {
        rec[i].type = (int16_t)types[i];
        rec[i].position[0] = 100.0f + 10.0f * (float)i; rec[i].position[1] = 200; rec[i].position[2] = 5;
        rec[i].scale = 2.5f;
        rec[i].flag_2c = 1; rec[i].flag_2d = 1; rec[i].flag_2e = 1;
    }
    mu_objects_init(o, world);
    o->records = rec; o->count = N;
    assert(mu_objects_start(o, NULL) == 0);
    assert(o->rt.created == N && o->rt.create_unsupported == 0);
    for (int i = 0; i < N; ++i) {
        o->models[types[i]] = m;
        o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
    }
    for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
    o->rt.sprite = sprite; o->rt.particle = particle; o->rt.joint = joint;
    o->sound = sound;
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
static const uint8_t *img(const mu_objects *o, int i) { return o->rt.images + i * MU_OBJ_SIZE; }
int main(int argc, char **argv)
{
    assert(argc == 2);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(m->bmd.bone_count == 13);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    mu_object_record rec[N];
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    /* ---- Twisted Karutan ---- */
    mu_objects *o = start(142, karutan, rec, m);
    for (int i = 0; i < N; ++i) {
        const int t = karutan[i];
        assert(img(o, i)[MU_OBJF_AFTER_CHARACTER] == (t == 1 || t == 162));
    }
    long refused = o->rt.draw_unsupported;
    for (int k = 0; k < STEPS; ++k) {
        in.time = 37.0f * (float)k;
        mu_objects_step(o, &in);
        assert(o->rt.light_count == 1);   /* type 160 */
        const mu_object_light *l = &o->rt.lights[0];
        assert(l->range == 2 && l->x == 170.0f && l->y == 200.0f && l->rgb[0] >= 0.29f && l->rgb[0] <= 0.61f);
        assert(fabsf(l->rgb[1] - l->rgb[0] * 0.6f) < 1e-6f && fabsf(l->rgb[2] - l->rgb[0] * 0.2f) < 1e-6f);
        visual_pass(o);
    }
    /* Type 72: four bone sprites per frame; type 113: one sprite and one particle per frame; type 115: 20
     * particles on the first frame, then hidden; type 118 hidden; type 116 the 1-in-8 pair. */
    assert(sprites == 5 * STEPS);
    assert(particles >= STEPS + 20 && particles < 2 * STEPS + 20 + 2 * STEPS / 8 + 40);
    assert(mu_obj_i32(img(o, 4), MU_OBJF_HIDDEN_MESH) == -2 && mu_obj_i32(img(o, 6), MU_OBJF_HIDDEN_MESH) == -2);
    assert(o->rt.move_unsupported == 0);
    refused = o->rt.draw_unsupported - refused;   /* type 196's effects (1 in 50), never approximated */
    assert(refused >= 0 && refused < 20 && o->rt.effect_events == 0);
    /* Without enough posed bones type 72 requests nothing and is counted. */
    m->bmd.bone_count = 11;
    sprites = 0;
    const long before = o->rt.draw_unsupported;
    visual_pass(o);
    assert(sprites == 1 && o->rt.draw_unsupported >= before + 1);
    m->bmd.bone_count = 13;
    finish(o);
    /* ---- Kardamahal ---- */
    o = start(143, kardamahal, rec, m);
    assert(mu_obj_f32(img(o, 0), MU_OBJF_POSITION + 8) == 64.0f && img(o, 0)[MU_OBJF_AFTER_CHARACTER] == 1);
    assert(img(o, 0)[MU_OBJF_LIGHT_FULL] == 0 && img(o, 0)[MU_OBJF_LIGHT_ENABLE] == 0);
    assert(img(o, 1)[MU_OBJF_AFTER_CHARACTER] == 1 && img(o, 2)[MU_OBJF_LIGHT_DYNAMIC] == 0);
    assert(mu_obj_f32(img(o, 3), MU_OBJF_RANGE) == -50.0f && mu_obj_f32(img(o, 5), MU_OBJF_RANGE) == -150.0f);
    assert(mu_obj_i32(img(o, 9), MU_OBJF_HIDDEN_MESH) == -2);
    mu_obj_set_u16(o->rt.images + 8 * MU_OBJ_SIZE, MU_OBJF_ACTION, 2);   /* type 146 in action 2 */
    memset(sounds, 0, sizeof sounds);
    particles = sprites = joints = 0;
    refused = o->rt.draw_unsupported;
    for (int k = 0; k < STEPS; ++k) {
        in.time = 37.0f * (float)k;
        mu_objects_step(o, &in);
        /* type 113 (range 3), type 115 at its two named bones (range 4), type 128 (range 2) */
        assert(o->rt.light_count == 4);
        int r[5] = {0};
        for (int q = 0; q < 4; ++q) r[o->rt.lights[q].range]++;
        assert(r[3] == 1 && r[4] == 2 && r[2] == 1);
        visual_pass(o);
    }
    assert(sounds[2] == STEPS && sounds[5] == STEPS && o->rt.move_unsupported == 0);   /* 0x5a6, 0x5a9 */
    refused = o->rt.draw_unsupported - refused;   /* type 161's effect (1 in 80) */
    assert(refused >= 0 && refused < 15 && particles == 0 && sprites == 0 && joints == 0);
    finish(o);
    /* ---- Swamp of Destruction ---- */
    o = start(144, swamp, rec, m);
    for (int i = 0; i < N; ++i) {
        const int t = swamp[i];
        assert(img(o, i)[MU_OBJF_AFTER_CHARACTER] == (t == 32 || t == 64 || t == 76));
        assert(mu_obj_f32(img(o, i), MU_OBJF_RANGE) == (t == 6 || t == 32 || t == 64 || t == 183 ? -300.0f : -30.0f));
    }
    joints = 0;
    for (int k = 0; k < STEPS; ++k) {
        in.time = 37.0f * (float)k;
        mu_objects_step(o, &in);
        assert(o->rt.light_count == 1 && o->rt.lights[0].range == 3 && o->rt.lights[0].x == 160.0f);
        visual_pass(o);
    }
    /* types 160/169/187: 1 in 50 per frame each; 0x7f7d subtypes 0x12/0x19/0x1a are native joint kinds */
    assert(joints > 0 && joints < 40 && joint_scale == 2.5f);
    assert(mu_obj_f32(img(o, 4), MU_OBJF_LIGHT) == 0.93f && mu_obj_f32(img(o, 5), MU_OBJF_LIGHT + 8) == 0.4f);
    finish(o);
    mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m);
    return 0;
}
