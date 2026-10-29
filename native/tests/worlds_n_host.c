/* RENDER-WORLDS-N: authored populations through production creation and steps. */
#include "../core/mu_objects.h"
#include "../../reconstructed/objects/worlds_n.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static float f32(float v) { volatile float x = v; return x; }
static const int types[] = {0, 6, 22, 52, 60, 64, 67, 77, 106, 8};
enum { N = sizeof types / sizeof *types, STEPS = 200 };
static float range_of(mu_objects *o, int i) { return mu_obj_f32(o->rt.images + i * MU_OBJ_SIZE, MU_OBJF_RANGE); }
int main(int argc, char **argv)
{
    assert(argc == 2);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    const int worlds[] = {113, 116, 117, 118, 119, 120, 111};   /* 111: a sibling without methods (Q owns 112) */
    for (unsigned w = 0; w < sizeof worlds / sizeof *worlds; ++w) {
        const int world = worlds[w], dd = world >= 116 && world <= 120;
        mu_objects *o = calloc(1, sizeof *o);
        mu_object_record rec[N];
        memset(rec, 0, sizeof rec);
        for (int i = 0; i < N; ++i) {
            rec[i].type = (int16_t)types[i];
            rec[i].position[0] = 100.0f + 10.0f * (float)i; rec[i].position[1] = 200; rec[i].position[2] = 0;
            rec[i].scale = 2.5f;
        }
        mu_objects_init(o, world);
        o->records = rec; o->count = N;
        assert(mu_objects_start(o, NULL) == 0);
        assert(o->rt.created == N && o->rt.create_unsupported == (world == 111 ? N : 0));
        /* Creation: the arrival-capture range field and the class flags. */
        for (int i = 0; i < N; ++i) {
            const uint8_t *img = o->rt.images + i * MU_OBJ_SIZE;
            const int t = types[i];
            const int far = world == 113 ? (t == 0 || t == 8 || t == 52 || t == 106) : world == 116 ? t == 6 :
                            world == 117 ? t == 0 : world == 118 ? (t == 0 || t == 6) :
                            world == 119 ? t == 0 : world == 120 ? (t == 0 || t == 6 || t == 22) : 0;
            assert(range_of(o, i) == (far ? -400.0f : -30.0f));
            if (dd && (t == 52 || t == 60 || t == 64 || t == 67))
                assert(mu_obj_i32(img, MU_OBJF_HIDDEN_MESH) == -2);
            assert(img[MU_OBJF_AFTER_CHARACTER] == (world == 113 && t == 106));
            if (dd && t == 60) assert(mu_obj_f32(img, MU_OBJF_BOX_MAX + 8) == 160.0f);
        }
        for (int i = 0; i < N; ++i) {   /* the render pass's TestFrustrum2D result */
            o->models[types[i]] = m;
            o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
        }
        for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
        mu_objects_step_inputs in;
        memset(&in, 0, sizeof in);
        in.scene_state = 6;
        long lights = 0;
        for (int k = 0; k < STEPS; ++k) {
            in.time = 1000.0f * (float)k + 250.0f;
            const long before_ticks = o->rt.ticks;
            const uint32_t seed = o->rt.seed;
            mu_objects_step(o, &in);
            assert(o->rt.ticks - before_ticks == N);   /* exactly one generic tick per object */
            lights += o->rt.light_count;
            if (dd) {
                assert(o->rt.light_count == 2);         /* types 64 and 67, in sector order */
                for (int q = 0; q < 2; ++q) {
                    const mu_object_light *l = &o->rt.lights[q];
                    assert(l->range == 3 && l->y == 200.0f);
                    const float s = l->rgb[0] / (q == 0 ? 1.0f : 0.8f);
                    assert(s > 0.29f && s < 0.61f);
                }
                assert(o->rt.lights[0].x == 150.0f && o->rt.lights[1].x == 160.0f);
                assert(o->rt.lights[0].rgb[1] == f32(o->rt.lights[0].rgb[0] * 0.6f));
                assert(o->rt.seed != seed);
                /* Type 22's blend-mesh scroll: -(int(time) % 1000) * 0.001. */
                assert(mu_obj_f32(o->rt.images + 2 * MU_OBJ_SIZE, MU_OBJF_BLEND_V) == f32(-250.0f * 0.001f));
            } else {
                assert(o->rt.light_count == 0);
            }
            if (world == 113)
                assert(mu_obj_f32(o->rt.images + 7 * MU_OBJ_SIZE, MU_OBJF_BLEND_V) ==
                       f32((float)((1000 * k + 250) % 2000) * 0.0005f));
        }
        /* Type 52's CreateEffect 0x43a (DungeonStone, RENDER-EFFECTS-005) is forwarded as an effect. */
        if (dd) assert(o->rt.move_unsupported == 0 && o->rt.effect_events > 30 && o->rt.effect_events < 110 &&
                       lights == 2 * STEPS);
        else assert(o->rt.move_unsupported == (world == 111 ? N * STEPS : 0) && o->rt.effect_events == 0);
        assert(o->rt.particle_events == 0);
        assert(mu_worlds_n_visual(o->rt.images, 0) == 0);
        o->records = NULL;
        mu_objects_runtime_free(o);
        free(o);
    }
    mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m);
    return 0;
}
