/* Authored synthetic objects through the production preparation path. No assets. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int sprites, particles, joints, generic;
static void sprite(void *ctx, int32_t type, const float p[3], float scale, const float l[3],
                   int32_t owner, float rotation, int32_t blend, int32_t axes)
{
    (void)ctx;
    assert(type == 0x7ef7 && p[0] == 100 && p[1] == 200 && p[2] == 300);
    assert(scale == 4 || scale == 16);
    assert(l[0] >= 0 && l[1] > 0 && owner == 0 && rotation == 0 && blend == 0 && axes == 4);
    ++sprites;
}
static void particle(void *ctx, int32_t type, const float p[3], const float a[3], const float l[3],
                     int32_t sub, float scale, int32_t owner)
{
    (void)ctx; (void)a; (void)l;
    assert(type > 0 && p[0] == 100 && scale == 2 && (owner == 0 || owner == -1) && sub >= 0);
    ++particles;
}
static void joint(void *ctx, int32_t type, const float p[3], const float t[3], const float a[3],
                  int32_t sub, int32_t owner, float scale)
{
    (void)ctx;
    assert(type == 0x7fd5 && p[0] == 100 && memcmp(p,t,12) == 0 && a[0] >= 120);
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
    mu_obj_set_f32(img, MU_OBJF_POSITION, 100);
    mu_obj_set_f32(img, MU_OBJF_POSITION+4, 200);
    mu_obj_set_f32(img, MU_OBJF_POSITION+8, 300);
    mu_draw_options options;
    /* Hidden geometry still has a model, and must produce its visual effects. */
    m->loaded = 1;
    for (int type = 0; type <= 6; ++type) {
        o->models[type] = m;
        mu_obj_set_i32(img, MU_OBJF_TYPE, type);
        for (int k = 0; k < 200; ++k)
            assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
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
    /* Missing model must not consume RNG or emit. */
    uint32_t seed = o->rt.seed;
    o->world = 63; mu_obj_set_i32(img, MU_OBJF_TYPE, 6);
    assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
    assert(sprites == 203 && seed == o->rt.seed);
    o->world = 64;
    assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
    assert(generic == 1 && sprites == 203);
    free(o->rt.images); free(m); free(o);
    return 0;
}
