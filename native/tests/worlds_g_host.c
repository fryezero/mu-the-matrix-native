/* Authored synthetic objects through the production preparation path. No assets. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int sprites, particles, joints, generic, current_type;
static void sprite(void *ctx, int32_t type, const float p[3], float scale, const float l[3],
                   int32_t owner, float rotation, int32_t blend, int32_t axes)
{
    (void)ctx;
    assert(type == 0x7ef7 && p[0] == 99 && p[1] == 200 && p[2] == 300);
    assert(scale == 4 || scale == 16);
    assert(l[0] >= 0 && l[1] > 0 && owner == 0 && rotation == 0 && blend == 0 && axes == 4);
    ++sprites;
}
static void particle(void *ctx, int32_t type, const float p[3], const float a[3], const float l[3],
                     int32_t sub, float scale, int32_t owner)
{
    (void)ctx; (void)a; (void)l;
    assert(p[0] == 99 && p[1] == 200 && p[2] == 300 && scale == 2);
    assert(owner == (current_type <= 3 ? 0 : -1));
    switch (current_type) {
    case 0: assert(type == 0x801b && sub == 6); break;
    case 1: assert(type == 0x7f5a && sub == 0x3c); break;
    case 2: assert(type == 0x7f89 && sub == 0x10); break;
    case 3: assert(type == 0x7f89 && sub == 0xb); break;
    case 4: assert(type == 0x7f25 && sub == 9); break;
    case 5: assert(type == 0x7f5a && sub == 0x15); break;
    case 6: assert((type == 0x8084 && sub == 0) || (type == 0x806e && sub == 4) ||
                   (type == 0x8085 && sub == 0)); break;
    default: assert(0);
    }
    ++particles;
}
static void joint(void *ctx, int32_t type, const float p[3], const float t[3], const float a[3],
                  int32_t sub, int32_t owner, float scale)
{
    (void)ctx;
    assert(type == 0x7fd5 && p[0] == 99 && memcmp(p,t,12) == 0 && a[0] >= 120);
    assert(sub == 4 && owner == 0 && scale == 2);
    ++joints;
}
static void visual(void *ctx, mu_objects *o, int32_t i, int model, mu_object_model *m)
{ (void)ctx; (void)o; (void)i; (void)model; (void)m; ++generic; }
int main(void)
{
    mu_objects *o = calloc(1, sizeof *o);
    mu_object_model *m = calloc(1, sizeof *m);
    assert(o && m);
    o->count = 1; o->world = 63; o->rt.ready = 1;
    o->rt.images = calloc(1, MU_OBJ_SIZE); assert(o->rt.images);
    o->rt.sprite = sprite; o->rt.particle = particle; o->rt.joint = joint; o->rt.visual = visual;
    uint8_t *img = o->rt.images;
    img[MU_OBJF_LIVE] = img[MU_OBJF_VISIBLE] = 1;
    mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -2);
    mu_obj_set_f32(img, MU_OBJF_SCALE, 2);
    /* X % 3 == 0 puts type 0 inside its emission window at time zero. */
    mu_obj_set_f32(img, MU_OBJF_POSITION, 99);
    mu_obj_set_f32(img, MU_OBJF_POSITION+4, 200);
    mu_obj_set_f32(img, MU_OBJF_POSITION+8, 300);
    mu_draw_options options;
    /* Hidden geometry still has a model, and must produce its visual effects. */
    m->loaded = 1;
    for (int type = 0; type <= 6; ++type) {
        current_type = type;
        const int old_particles = particles, old_joints = joints;
        o->models[type] = m;
        mu_obj_set_i32(img, MU_OBJF_TYPE, type);
        for (int k = 0; k < 200; ++k)
            assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
        assert(particles > old_particles);
        if (type == 0)
            assert(particles - old_particles == 4000);
        if (type == 4)
            assert(joints - old_joints == particles - old_particles);
        o->models[type] = NULL;
    }
    assert(sprites == 200 && particles > 100 && joints > 0 && generic == 0);
    o->world = 62;
    for (int type = 0x1a; type <= 0x1c; ++type) {
        o->models[type] = m;
        mu_obj_set_i32(img, MU_OBJF_TYPE, type);
        assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
        o->models[type] = NULL;
    }
    assert(sprites == 203 && generic == 0);
    /* Missing and unloaded models must not consume RNG or emit any call. */
    uint32_t seed = o->rt.seed;
    const int old_particles = particles, old_joints = joints;
    o->world = 63; current_type = 6; mu_obj_set_i32(img, MU_OBJF_TYPE, 6);
    assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
    o->models[6] = m; m->loaded = 0;
    assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
    assert(sprites == 203 && seed == o->rt.seed);
    assert(particles == old_particles && joints == old_joints);
    o->models[6] = NULL;
    o->world = 65;
    assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
    assert(generic == 1 && sprites == 203);
    free(o->rt.images); free(m); free(o);
    return 0;
}
