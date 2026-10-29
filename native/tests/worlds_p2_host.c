/* RENDER-WORLDS-P2: authored Kanturu Underground / Ignis Volcano populations through production creation,
 * steps and the visual pass. */
#include "../core/mu_objects.h"
#include "../../reconstructed/objects/worlds_p2.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static int sprites, particles, joints, sounds;
static void sprite(void *ctx, int32_t type, const float p[3], float scale, const float l[3], int32_t owner,
                   float rotation, int32_t a, int32_t b)
{
    (void)ctx; (void)p; (void)l; (void)owner; (void)rotation; (void)a; (void)b;
    assert(type == 0x7f26 && scale == 10.0f);
    ++sprites;
}
static void particle(void *ctx, int32_t type, const float p[3], const float a[3], const float l[3], int32_t sub,
                     float scale, int32_t owner)
{
    (void)ctx; (void)p; (void)a; (void)l; (void)owner;
    assert(type == 0x7f2b && sub == 0 && scale == 1.5f);
    ++particles;
}
static void joint(void *ctx, int32_t type, const float p[3], const float t[3], const float a[3], int32_t sub,
                  int32_t owner, float scale)
{
    (void)ctx; (void)type; (void)p; (void)t; (void)a; (void)sub; (void)owner; (void)scale;
    ++joints;
}
static void sound(void *ctx, int32_t id) { (void)ctx; assert(id == 0x570); ++sounds; }
static const int k_types[] = {0, 3, 8, 10, 38, 44, 54, 65, 125, 7};
static const int i_types[] = {0, 45, 79, 88, 126, 177, 12, 13, 148, 7};
enum { N = 10, STEPS = 200 };
static mu_objects *start(int world, const int *types, mu_object_record *rec)
{
    mu_objects *o = calloc(1, sizeof *o);
    memset(rec, 0, N * sizeof *rec);
    for (int i = 0; i < N; ++i) {
        rec[i].type = (int16_t)types[i];
        rec[i].position[0] = 100.0f + 10.0f * (float)i; rec[i].position[1] = 200; rec[i].position[2] = 0;
        rec[i].scale = 2.5f;
        rec[i].flag_2e = 1;
    }
    mu_objects_init(o, world);
    o->records = rec; o->count = N;
    assert(mu_objects_start(o, NULL) == 0);
    return o;
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(argv[1], &m->bmd, error, sizeof error) == 0);
    assert(m->bmd.action_count == 4 && m->bmd.bone_count == 5);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    mu_object_record rec[N];
    /* ---- Kanturu Underground ---- */
    mu_objects *o = start(137, k_types, rec);
    assert(o->rt.created == N && o->rt.create_unsupported == 0);
    for (int i = 0; i < N; ++i) {
        const uint8_t *img = o->rt.images + i * MU_OBJ_SIZE;
        const int t = k_types[i];
        assert(img[MU_OBJF_LIGHT_DYNAMIC] == 0);                       /* record +0x2e cleared */
        assert(mu_obj_f32(img, MU_OBJF_RANGE) == (t == 0 ? -300.0f : -30.0f));
        assert(mu_obj_i32(img, MU_OBJF_HIDDEN_MESH) == (t == 54 || t == 65 ? -2 : -1));
        assert(o->rt.play_speed_set[t] == 2 && o->rt.play_speed[t] == 0.3f);   /* every action: 0.3 */
        if (t == 125) assert(mu_obj_i32(img, 0x34) >= 20 && mu_obj_i32(img, 0x34) < 50);
    }
    for (int i = 0; i < N; ++i) {
        o->models[k_types[i]] = m;
        o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
    }
    for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
    o->rt.sprite = sprite; o->rt.particle = particle; o->rt.joint = joint;
    o->sound = sound;
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    int seen[4] = {0};
    for (int k = 0; k < STEPS; ++k) {
        in.time = 37.0f * (float)k;
        const long before = o->rt.ticks;
        mu_objects_step(o, &in);
        assert(o->rt.ticks - before == N);
        const uint8_t *img10 = o->rt.images + 3 * MU_OBJ_SIZE, *img38 = o->rt.images + 4 * MU_OBJ_SIZE;
        const float l10 = mu_obj_f32(img10, MU_OBJF_BLEND_LIGHT), l38 = mu_obj_f32(img38, MU_OBJF_BLEND_LIGHT);
        assert(l10 >= 0.1f && l10 <= 0.9f && l38 <= 1.0f && l38 >= 0.0f);
        assert(mu_obj_f32(img10, MU_OBJF_VELOCITY) == 0.04f);
        assert(mu_obj_f32(o->rt.images + 5 * MU_OBJ_SIZE, MU_OBJF_VELOCITY) == 0.02f);
        const uint16_t action = mu_obj_u16(o->rt.images + 8 * MU_OBJ_SIZE, MU_OBJF_ACTION);
        assert(action < 4);
        seen[action] = 1;
        mu_draw_options options;
        for (int i = 0; i < N; ++i) (void)mu_objects_prepare_index(o, i, NULL, 6, &options);
    }
    assert(seen[0] && seen[1] && seen[2] && seen[3]);   /* type 125 runs its full 0-1-2-3 cycle */
    assert(o->rt.move_unsupported == 0 && o->rt.light_count == 0);
    /* Type 8's bone 4 sprite and particle every frame; joints of kinds the pool lacks are refused. */
    assert(sprites == STEPS && particles == STEPS && joints == 0 && o->rt.draw_unsupported > 0);
    o->records = NULL;
    mu_objects_runtime_free(o);
    free(o);
    /* ---- Ignis Volcano ---- */
    o = start(138, i_types, rec);
    assert(o->rt.created == N && o->rt.create_unsupported == 2);   /* types 79/148: StreamMesh refused */
    for (int i = 0; i < N; ++i) {
        const uint8_t *img = o->rt.images + i * MU_OBJ_SIZE;
        const int t = i_types[i];
        const int far = t == 0 || t == 45 || t == 13 || t == 7;
        assert(mu_obj_f32(img, MU_OBJF_RANGE) == (far ? -800.0f : -30.0f));
        assert(img[MU_OBJF_AFTER_CHARACTER] == (t == 45));
        assert(mu_obj_i32(img, MU_OBJF_HIDDEN_MESH) == (t == 88 || t == 126 ? -2 : -1));
        assert(mu_obj_f32(img, MU_OBJF_VELOCITY) == 0.16f);
    }
    for (int i = 0; i < N; ++i) {
        o->models[i_types[i]] = m;
        o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
    }
    for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
    o->sound = sound;
    sounds = 0;
    mu_obj_set_u16(o->rt.images + 5 * MU_OBJ_SIZE, MU_OBJF_ACTION, 1);   /* type 177 at the start of action 1 */
    for (int k = 0; k < STEPS; ++k) {
        in.time = 37.0f * (float)k;
        mu_objects_step(o, &in);
        assert(o->rt.light_count == 1);
        const mu_object_light *l = &o->rt.lights[0];
        const float s = l->rgb[1] / 0.3f;
        assert(l->range == 3 && l->x == 130.0f && l->y == 200.0f && s > 0.29f && s < 0.61f);
    }
    assert(sounds > 0 && o->rt.move_unsupported == 0);
    assert(mu_ignis_visual(o->rt.images, 0) == 0);
    o->records = NULL;
    mu_objects_runtime_free(o);
    free(o);
    mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m);
    return 0;
}
