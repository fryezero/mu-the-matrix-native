/* Synthetic objects through production preparation. No installed assets required. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int particles, sprites, effects, generic, current_type, current_world;
static void particle(void *ctx, int32_t type, const float p[3], const float a[3], const float l[3],
                     int32_t sub, float scale, int32_t owner)
{
    (void)ctx; (void)a; (void)l;
    assert(scale == 2 && p[2] == 300);
    if (current_type == 48) {
        assert(type == 0x7ef7 && sub == 15 && owner == 0);
        assert(p[0] >= 39 && p[0] <= 158 && p[1] >= 140 && p[1] <= 259);
    } else {
        assert(p[0] == 99 && p[1] == 200);
        assert(owner == ((current_type <= 3 || current_type == 35) ? 0 : -1));
        switch (current_type) {
        case 0: assert(type == 0x801b && sub == 7); break;
        case 1: assert(type == 0x7f5a && sub == 69); break;
        case 2: assert(type == 0x7f89 && sub == 16); break;
        case 3: assert(type == 0x7f89 && sub == 11); break;
        case 5: assert(type == 0x7f5a && sub == 21); break;
        case 6: case 36:
            assert((type == 0x8084 && sub == 0) || (type == 0x806e && sub == 4) ||
                   (type == 0x8085 && sub == 0)); break;
        case 35: assert(type == 0x7f5a && sub == 22 && current_world == 64); break;
        case 47:
            assert((type == 0x8086 && sub == 2) || (type == 0x8087 && sub == 6) ||
                   (type == 0x8089 && sub == 2)); break;
        default: assert(0);
        }
    }
    ++particles;
}
static void sprite(void *ctx, int32_t type, const float p[3], float scale, const float l[3],
                   int32_t owner, float rotation, int32_t blend, int32_t axes)
{
    (void)ctx;
    assert(type == 0x7ef7 && p[0] == 99 && p[1] == 200 && p[2] == 300 && scale == 4);
    assert(l[0] == 1 && l[1] == 0.2f && l[2] == 0);
    assert(owner == 0 && rotation == 0 && blend == 0 && axes == 4);
    ++sprites;
}
static void effect(void *ctx, int32_t type, int32_t sub, const float p[3], const float a[3],
                   const float l[3], int32_t owner, float scale)
{
    (void)ctx; (void)a;
    assert(type == 0x7f42 && sub == 7 && p[0] == 99 && p[1] == 200 && p[2] == 300);
    assert(l[0] == 0.5f && l[1] == 0.5f && l[2] == 0.5f && owner == -1 && scale == 2);
    ++effects;
}
static void visual(void *ctx, mu_objects *o, int32_t i, int model, mu_object_model *m)
{ (void)ctx; (void)o; (void)i; (void)model; (void)m; ++generic; }
int main(void)
{
    mu_objects *o = calloc(1, sizeof *o);
    mu_object_model *m = calloc(1, sizeof *m);
    assert(o && m);
    o->count = 1; o->rt.ready = 1;
    o->rt.images = calloc(1, MU_OBJ_SIZE); assert(o->rt.images);
    o->rt.particle = particle; o->rt.sprite = sprite; o->rt.effect_scaled = effect; o->rt.visual = visual;
    uint8_t *img = o->rt.images;
    img[MU_OBJF_LIVE] = img[MU_OBJF_VISIBLE] = 1;
    mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -2);
    mu_obj_set_f32(img, MU_OBJF_SCALE, 2);
    mu_obj_set_f32(img, MU_OBJF_POSITION, 99);
    mu_obj_set_f32(img, MU_OBJF_POSITION+4, 200);
    mu_obj_set_f32(img, MU_OBJF_POSITION+8, 300);
    mu_draw_options options;
    const int types[] = {0, 1, 2, 3, 4, 5, 6, 47, 48, 35, 36};
    for (unsigned n = 0; n < sizeof types / sizeof *types; ++n) {
        current_type = types[n]; current_world = n < 9 ? 82 : 64;
        o->world = current_world; m->loaded = 1; o->models[current_type] = m;
        mu_obj_set_i32(img, MU_OBJF_TYPE, current_type);
        int old_p = particles, old_s = sprites, old_e = effects;
        for (int k = 0; k < 200; ++k)
            assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
        if (current_type == 4) assert(effects - old_e >= 800);
        else assert(particles > old_p);
        if (current_type == 0) assert(particles - old_p == 4000);
        if (current_type == 47) assert(particles - old_p == 400);
        if (current_type == 6 || current_type == 36) assert(sprites - old_s == 200);
        /* Missing and unloaded models must neither emit nor consume random state. */
        uint32_t seed = o->rt.seed;
        old_p = particles; old_s = sprites; old_e = effects;
        o->models[current_type] = NULL;
        assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
        o->models[current_type] = m; m->loaded = 0;
        assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
        assert(seed == o->rt.seed && particles == old_p && sprites == old_s && effects == old_e);
        o->models[current_type] = NULL;
    }
    assert(generic == 0);
    o->world = 65;
    assert(!mu_objects_prepare_index(o, 0, NULL, 6, &options));
    assert(generic == 1);
    free(o->rt.images); free(m); free(o);
    return 0;
}
