/* RENDER-WORLDS-Q: authored populations through production creation, steps and the primary visual. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int generic;
static void visual(void *c, mu_objects *o, int32_t i, int has, mu_object_model *m)
{ (void)c; (void)o; (void)i; (void)has; (void)m; ++generic; }
static const int types[] = {9, 15, 22, 29, 39, 49, 51, 55, 61, 88, 127, 131, 152, 158};
enum { N = sizeof types / sizeof *types, STEPS = 50 };
static int at(int type) { for (int i = 0; i < N; ++i) if (types[i] == type) return i; return -1; }
static uint8_t *img(mu_objects *o, int type) { return o->rt.images + at(type) * MU_OBJ_SIZE; }
int main(int argc, char **argv)
{
    assert(argc == 2);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    assert(m->bmd.action_count == 2);
    const int worlds[] = {91, 112, 122, 123, 127, 111};
    for (unsigned w = 0; w < sizeof worlds / sizeof *worlds; ++w) {
        const int world = worlds[w], owned = world != 111;
        mu_objects *o = calloc(1, sizeof *o);
        mu_object_record rec[N];
        memset(rec, 0, sizeof rec);
        for (int i = 0; i < N; ++i) {
            rec[i].type = (int16_t)types[i];
            rec[i].position[0] = 1000.0f + 10.0f * (float)i; rec[i].position[1] = 2000; rec[i].scale = 1.0f;
        }
        mu_objects_init(o, world);
        for (int i = 0; i < N; ++i) o->models[types[i]] = m;   /* models load before creation */
        o->records = rec; o->count = N;
        assert(mu_objects_start(o, NULL) == 0);
        assert(o->rt.created == N && o->rt.create_unsupported == (owned ? 0 : N));
        const float far = mu_obj_f32(img(o, 49), MU_OBJF_RANGE);
        if (world == 91) {
            assert(mu_obj_f32(img(o, 61), MU_OBJF_RANGE) == -428.571442f);
            assert(mu_obj_i32(img(o, 55), MU_OBJF_HIDDEN_MESH) == -2);
        } else if (world == 112) {
            assert(mu_obj_f32(img(o, 152), MU_OBJF_RANGE) == -400.0f && o->rt.q_handler.ferea_object == img(o, 39));
        } else if (world == 122) {
            assert(far == -400.0f && mu_obj_i32(img(o, 88), MU_OBJF_TYPE) == 88 && img(o, 88)[MU_OBJF_AFTER_CHARACTER]);
            assert(mu_obj_i32(img(o, 131), 0x64) >= 4 && mu_obj_i32(img(o, 131), 0x64) <= 10);
        } else if (world == 123 || world == 127) {
            assert(img(o, 29)[MU_OBJF_AFTER_CHARACTER] == 1 && mu_obj_f32(img(o, 29), MU_OBJF_RANGE) == -300.0f);
            assert(mu_obj_f32(img(o, 158), MU_OBJF_RANGE) == -600.0f && o->rt.q_handler.kubera_object == img(o, 158));
            for (uint32_t k = 0; k < 2; ++k) {   /* type 15: every action of the shared model plays at 0.3 */
                float speed;
                memcpy(&speed, mu_model_host(&m->model, m->model.actions + 16u * k + 4u, 4), 4);
                assert(speed == 0.3f && *mu_model_host(&m->model, m->model.actions + 16u * k + 0xa, 1) == 0);
            }
        } else {
            assert(far == -30.0f && o->rt.q_handler.ferea_object == NULL && o->rt.q_handler.kubera_object == NULL);
        }
        assert(o->rt.q_handler.swamp_variant == 1);
        for (int i = 0; i < N; ++i) o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
        for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
        mu_objects_step_inputs in;
        memset(&in, 0, sizeof in);
        in.scene_state = 6;
        in.hero[0] = 3050.0f; in.hero[1] = 12050.0f;   /* tile (30, 120): Ferea's type 51 fades */
        for (int k = 0; k < STEPS; ++k) {
            in.time = 40.0f * (float)k;
            const long ticks = o->rt.ticks;
            mu_objects_step(o, &in);
            assert(o->rt.ticks - ticks == N);   /* the generic tick still runs once per object */
            if (world == 91) assert(o->rt.light_count == 1 && o->rt.lights[0].range == 2);   /* type 9 */
            else if (world == 112) assert(o->rt.light_count == 0);
        }
        assert(o->rt.move_unsupported == (owned ? 0 : N * STEPS));
        if (world == 91) assert(mu_obj_f32(img(o, 22), MU_OBJF_BLEND_V) < -0.4f);
        if (world == 112) assert(mu_obj_f32(img(o, 51), MU_OBJF_ALPHA_TARGET) == 0.1f);
        /* Visual: Acheron's type 55 particle replaces the generic hook; Ferea keeps it. */
        o->rt.visual = visual;
        generic = 0;
        mu_draw_options options;
        const long particles = o->rt.particle_events;
        mu_obj_set_i32(img(o, 55), MU_OBJF_HIDDEN_MESH, -1);
        (void)mu_objects_prepare_index(o, at(55), NULL, 6, &options);
        if (world == 91) assert(o->rt.particle_events == particles + 1 && generic == 0);
        else if (world == 112 || world == 111) assert(generic == 1);
        else assert(generic == 0);
        o->records = NULL;
        mu_objects_runtime_free(o);
        free(o);
    }
    mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m);
    return 0;
}
