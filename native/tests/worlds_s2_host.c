/* RENDER-WORLDS-S2: authored Nars (110) and Arca War (92, 96, 101, 111) populations through production creation,
 * steps and the visual pass. The model has 28 bones in a chain along z and two actions. */
#include "../core/mu_objects.h"
#include "../../reconstructed/objects/worlds_s2.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static int sprites, particles, keyed, scaled;
static void sprite(void *ctx, int32_t type, const float p[3], float scale, const float l[3], int32_t owner,
                   float rotation, int32_t a, int32_t b)
{
    (void)ctx; (void)p; (void)scale; (void)l; (void)owner; (void)rotation; (void)a; (void)b;
    assert(type == 0x7f6b || type == 0x7ef7 || type == 0x7f26 || type == 0x8155);
    ++sprites;
}
static void particle(void *ctx, int32_t type, const float p[3], const float a[3], const float l[3], int32_t sub,
                     float scale, int32_t owner)
{
    (void)ctx; (void)type; (void)p; (void)a; (void)l; (void)sub; (void)scale; (void)owner;
    ++particles;
}
static void effect_word4(void *ctx, int32_t type, int32_t sub, const float p[3], const float a[3], const float l[3],
                         int32_t owner, uint16_t word4)
{
    (void)ctx; (void)p; (void)a; (void)l; (void)word4;
    assert(type == 0x413 && sub == 10 && owner == -1);   /* Nars fire: unowned */
    ++keyed;
}
static void effect_scaled(void *ctx, int32_t type, int32_t sub, const float p[3], const float a[3], const float l[3],
                          int32_t owner, float scale)
{
    (void)ctx; (void)type; (void)sub; (void)p; (void)a; (void)l; (void)owner; (void)scale;
    ++scaled;
}
enum { N = 10, STEPS = 200 };
static const int nars[N] = {1, 4, 11, 14, 26, 32, 77, 85, 87, 116};
static mu_objects *start(int world, const int *types, int n, mu_object_record *rec, mu_object_model *m)
{
    mu_objects *o = calloc(1, sizeof *o);
    memset(rec, 0, (size_t)n * sizeof *rec);
    for (int i = 0; i < n; ++i) {
        rec[i].type = (int16_t)types[i];
        rec[i].position[0] = 100.0f + 10.0f * (float)i; rec[i].position[1] = 200; rec[i].position[2] = 5;
        rec[i].scale = 2.5f;
        rec[i].flag_2c = 1; rec[i].flag_2d = 1; rec[i].flag_2e = 1;
    }
    mu_objects_init(o, world);
    o->records = rec; o->count = n;
    for (int i = 0; i < n; ++i)
        if (types[i] < MU_OBJECT_TYPES) o->models[types[i]] = m;
    assert(mu_objects_start(o, NULL) == 0);
    for (int i = 0; i < n; ++i) o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
    for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
    o->rt.sprite = sprite; o->rt.particle = particle;
    o->rt.effect_word4 = effect_word4; o->rt.effect_scaled = effect_scaled;
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
    for (int i = 0; i < o->count; ++i) (void)mu_objects_prepare_index(o, i, NULL, 6, &options);
}
static const uint8_t *img(const mu_objects *o, int i) { return o->rt.images + i * MU_OBJ_SIZE; }
/* Nars objects on world 110, or through the Arca War class on 111: the same creation, lights and requests. */
static void nars_population(int world, mu_object_model *m)
{
    mu_object_record rec[N];
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    mu_objects *o = start(world, nars, N, rec, m);
    assert(o->rt.created == N && o->rt.create_unsupported == 0);
    for (int i = 0; i < N; ++i) {
        const int t = nars[i];
        const int32_t phase = mu_obj_i32(img(o, i), 0x64);
        assert(mu_obj_i32(img(o, i), MU_OBJF_HIDDEN_MESH) == -2 || !(t == 14 || t == 26 || t == 32));
        if (t == 11) assert(mu_obj_f32(img(o, i), MU_OBJF_RANGE) == -200.0f);
        if (t == 85 || t == 87) assert(phase >= 0 && phase <= 2700 && phase % 300 == 0);
    }
    sprites = particles = keyed = scaled = 0;
    const long refused = o->rt.draw_unsupported;
    int swung = 0, lit = 0;
    const float v0 = mu_obj_f32(img(o, 6), MU_OBJF_BLEND_V);
    for (int k = 0; k < STEPS; ++k) {
        in.time = 37.0f * (float)k;
        mu_objects_step(o, &in);
        /* types 4 and 116: a flame light of range 1 at their own x/y */
        assert(o->rt.light_count == 2);
        for (int q = 0; q < 2; ++q) {
            const mu_object_light *l = &o->rt.lights[q];
            assert(l->range == 1 && (l->x == 110.0f || l->x == 190.0f) && l->y == 200.0f);
            assert(l->rgb[0] >= 0.8f && l->rgb[0] <= 0.961f && l->rgb[2] >= 0.2f && l->rgb[2] <= 0.361f);
        }
        swung += mu_obj_u16(img(o, 0), MU_OBJF_ACTION) == 1;
        visual_pass(o);
        lit |= mu_obj_f32(img(o, 4), MU_OBJF_LIGHT) == 1.0f && mu_obj_f32(img(o, 4), MU_OBJF_LIGHT + 4) == 0.5f;
    }
    assert(swung > 0 && swung < STEPS && o->rt.move_unsupported == 0);
    assert(fabsf(mu_obj_f32(img(o, 6), MU_OBJF_BLEND_V) - (v0 - 0.015f * (float)STEPS)) < 1e-3f);   /* type 77 */
    /* per frame: 4/116 one flame each, 11 four glows, 85 one flame, 87 twelve lantern sprites */
    assert(sprites == 19 * STEPS && keyed == 2 * STEPS && scaled == 0 && particles > 0);
    assert(o->rt.draw_unsupported == refused && lit);   /* type 26 set the object light (1, 0.5, 0.1) */
    m->bmd.bone_count = 5;   /* 4/116 (bone 7) and 87 (bone 15) are refused; 11 (bone 2) and 85 (bone 4) draw */
    sprites = 0;
    visual_pass(o);
    assert(o->rt.draw_unsupported == refused + 3 && sprites == 5);
    m->bmd.bone_count = 28;
    finish(o);
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(m->bmd.bone_count == 28);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    for (int32_t a = 0; a < m->bmd.action_count; ++a) {   /* PlaySpeed 1.5: an action ends at frame >= keys - 1.5 */
        const float speed = 1.5f;
        memcpy(mu_model_host(&m->model, m->model.actions + 16u * (uint32_t)a + 4u, 4), &speed, 4);
    }
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    /* ---- Nars, and Arca War on Nars (111) forwarding to it ---- */
    nars_population(110, m);
    nars_population(111, m);
    /* ---- Nars type 134 poses its model at creation: refused and counted; its light reads +0x110, which
     * CreateObject's generic part set to the position (bone 4 is not stored) ---- */
    mu_object_record rec[N];
    static const int posed[1] = {134};
    mu_objects *o = start(110, posed, 1, rec, m);
    assert(o->rt.create_unsupported == 1);
    mu_objects_step(o, &in);
    assert(o->rt.light_count == 1 && o->rt.lights[0].range == 2 && o->rt.lights[0].x == 100.0f);
    finish(o);
    /* ---- Arca War's own types (above the 512-type model table): scale 0.85; 0x59b's effect has no model ---- */
    static const int own[3] = {0x59b, 0x88a, 0x88e};
    for (int w = 0; w < 4; ++w) {
        static const int worlds[4] = {92, 96, 101, 111};
        o = start(worlds[w], own, 3, rec, m);
        assert(o->rt.create_unsupported == 0);
        for (int i = 0; i < 3; ++i) assert(mu_obj_f32(img(o, i), MU_OBJF_SCALE) == 0.85f);
        const long refused = o->rt.draw_unsupported;
        scaled = 0;
        visual_pass(o);
        assert(o->rt.draw_unsupported == refused + 1 && scaled == 0);
        finish(o);
    }
    /* ---- Arca War on Debenter (96): type 50's light; on Acheron (92): type 9's; on Uruk Mountain (101): 27's ---- */
    static const int on_debenter[1] = {50}, on_acheron[1] = {9}, on_uruk[2] = {27, 20};
    const struct { int world; const int *types; int n; int range; } bases[3] = {
        {96, on_debenter, 1, 2}, {92, on_acheron, 1, 2}, {101, on_uruk, 2, 3}};
    for (int b = 0; b < 3; ++b) {
        o = start(bases[b].world, bases[b].types, bases[b].n, rec, m);
        assert(o->rt.create_unsupported == 0);
        for (int k = 0; k < 20; ++k) {
            in.time = 37.0f * (float)k;
            mu_objects_step(o, &in);
            assert(o->rt.light_count == 1 && o->rt.lights[0].range == bases[b].range && o->rt.lights[0].x == 100.0f);
        }
        if (bases[b].world == 101) assert(mu_obj_f32(img(o, 1), MU_OBJF_RANGE) == -400.0f);   /* Uruk create 20 */
        assert(o->rt.move_unsupported == 0);
        finish(o);
    }
    mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m);
    return 0;
}
