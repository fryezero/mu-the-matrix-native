/* RENDER-WORLDS-S: authored Aquila's Temple / Debenter / Boss Battle / world 115 populations through production
 * creation, steps and the visual pass. The model has 28 bones in a chain along z and two actions. */
#include "../core/mu_objects.h"
#include "../../reconstructed/objects/worlds_s.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static int sprites, particles, joints;
static void sprite(void *ctx, int32_t type, const float p[3], float scale, const float l[3], int32_t owner,
                   float rotation, int32_t a, int32_t b)
{
    (void)ctx; (void)p; (void)scale; (void)l; (void)owner; (void)rotation; (void)a; (void)b;
    assert(type == 0x7f6b || type == 0x7ef7 || type == 0x8155);
    ++sprites;
}
static void particle(void *ctx, int32_t type, const float p[3], const float a[3], const float l[3], int32_t sub,
                     float scale, int32_t owner)
{
    (void)ctx; (void)p; (void)a; (void)l; (void)sub; (void)scale; (void)owner;
    assert(type == 0x7f5a || type == 0x8089 || type == 0x7efa || type == 0x7f26 || type == 0x7f89 ||
           type == 0x7dea || (type >= 0x807e && type <= 0x8080));
    ++particles;
}
static void joint(void *ctx, int32_t type, const float p[3], const float t[3], const float a[3], int32_t sub,
                  int32_t owner, float scale)
{
    (void)ctx; (void)type; (void)p; (void)t; (void)a; (void)sub; (void)owner; (void)scale;
    ++joints;
}
enum { N = 10, STEPS = 200 };
static const int aquila[N] = {51, 90, 136, 137, 142, 152, 50, 99, 141, 138};
static const int debenter[N] = {9, 11, 21, 27, 50, 56, 63, 65, 67, 31};
static const int boss[N] = {0, 1, 2, 3, 9, 11, 50, 63, 90, 136};
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
    for (int i = 0; i < N; ++i) o->models[types[i]] = m;   /* before start: Debenter's create reads the table */
    assert(mu_objects_start(o, NULL) == 0);
    assert(o->rt.created == N && o->rt.create_unsupported == 0);
    for (int i = 0; i < N; ++i) o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
    for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
    o->rt.sprite = sprite; o->rt.particle = particle; o->rt.joint = joint;
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
    assert(m->bmd.bone_count == 28);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    mu_object_record rec[N];
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    /* ---- Aquila's Temple ---- */
    mu_objects *o = start(145, aquila, rec, m);
    for (int i = 0; i < N; ++i) {
        const int t = aquila[i];
        assert(mu_obj_f32(img(o, i), MU_OBJF_RANGE) == (t == 51 || t == 99 ? -150.0f : -30.0f));
    }
    long refused = o->rt.draw_unsupported;
    for (int k = 0; k < STEPS; ++k) {
        in.time = 37.0f * (float)k;
        mu_objects_step(o, &in);
        /* type 90 at its own x/y; 136, 137, 138 (range 2) and 142 (range 3) at +0x188, bone 6 of the last visual */
        assert(o->rt.light_count == 5);
        int r[4] = {0};
        for (int q = 0; q < 5; ++q) {
            const mu_object_light *l = &o->rt.lights[q];
            r[l->range]++;
            assert(k == 0 ? (l->x == 0.0f || l->x == 110.0f) : (l->x >= 110.0f && l->x <= 190.0f));
            assert(l->rgb[0] > 0.0f && l->rgb[1] > 0.0f && l->y == (k == 0 && l->x == 0.0f ? 0.0f : l->y));
        }
        assert(r[2] == 4 && r[3] == 1);
        assert(img(o, 5)[MU_OBJF_AFTER_CHARACTER] == 1);   /* type 152 */
        visual_pass(o);
    }
    for (int i = 0; i < N; ++i)   /* the visual stored bone 6's x/y: on the object's x (the chain runs along z) */
        if (mu_aquila_bone_type(aquila[i]))
            assert(fabsf(mu_obj_f32(img(o, i), MU_OBJF_POINT_A) - (100.0f + 10.0f * (float)i)) < 1e-3f &&
                   fabsf(mu_obj_f32(img(o, i), MU_OBJF_POINT_A + 4) - 200.0f) < 1e-3f);
    assert(o->rt.draw_unsupported == refused && o->rt.move_unsupported == 0);
    m->bmd.bone_count = 6;   /* bone 6 missing: the four bone types are refused and counted */
    visual_pass(o);
    assert(o->rt.draw_unsupported == refused + 4);
    m->bmd.bone_count = 28;
    finish(o);
    /* ---- Debenter ---- */
    for (int32_t a = 0; a < m->bmd.action_count; ++a) {   /* PlaySpeed 1.5: an action ends at frame >= keys - 1.5 */
        const float speed = 1.5f;
        memcpy(mu_model_host(&m->model, m->model.actions + 16u * (uint32_t)a + 4u, 4), &speed, 4);
    }
    o = start(95, debenter, rec, m);
    for (int i = 0; i < N; ++i)   /* +0x60 is 0 after construction: no create case applies */
        assert(mu_obj_i32(img(o, i), MU_OBJF_HIDDEN_MESH) != -2);
    particles = sprites = joints = 0;
    refused = o->rt.draw_unsupported;
    int swung = 0;
    for (int k = 0; k < STEPS; ++k) {
        in.time = 37.0f * (float)k;
        mu_objects_step(o, &in);
        assert(o->rt.light_count == 1 && o->rt.lights[0].range == 2 && o->rt.lights[0].x == 140.0f);
        assert(o->rt.lights[0].rgb[2] == 0.0f && o->rt.lights[0].rgb[0] >= 0.059f && o->rt.lights[0].rgb[0] <= 0.141f);
        swung += mu_obj_u16(img(o, 0), MU_OBJF_ACTION) == 1;
        visual_pass(o);
    }
    assert(swung > 0 && swung < STEPS && o->rt.move_unsupported == 0);
    /* per frame: 7 sprites (27, 31: two; 21: two; 11: one); 63: two particles; 9: four at its bone points */
    assert(sprites == 7 * STEPS && particles >= 6 * STEPS && joints == 0);
    refused = o->rt.draw_unsupported - refused;   /* type 65's effect (1 in 5 at clock phase 0) */
    assert(refused > 0 && refused < STEPS / 2 && o->rt.effect_events == 0);
    assert(mu_obj_f32(img(o, 0), MU_OBJF_POINT_A + 8) != 0.0f && mu_obj_f32(img(o, 0), MU_OBJF_POINT_B + 8) != 0.0f);
    m->bmd.bone_count = 5;   /* types 9 and 11 need bones 23/27: refused; 21 and 27/31 still draw */
    const long before = o->rt.draw_unsupported;
    sprites = 0;
    visual_pass(o);
    assert(o->rt.draw_unsupported >= before + 2 && sprites == 6);
    m->bmd.bone_count = 28;
    finish(o);
    /* ---- Boss Battle (139) and world 115: return-false slots, the generic part only ---- */
    for (int w = 0; w < 2; ++w) {
        o = start(w ? 115 : 139, boss, rec, m);
        for (int k = 0; k < 20; ++k) {
            in.time = 37.0f * (float)k;
            mu_objects_step(o, &in);
            assert(o->rt.light_count == 0);
        }
        assert(o->rt.move_unsupported == 0 && o->rt.create_unsupported == 0);
        finish(o);
    }
    mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m);
    return 0;
}
