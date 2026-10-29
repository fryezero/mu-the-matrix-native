/* RENDER-WORLDS-AFTER: Abyss of Atlans 1-3 (worlds 128..130) custom render (slot 0x38) and after render
 * (slot 0x3c). Custom 0x00d5d2f6 / 0x00d5ef96 / 0x00d606da, after 0x00d5d5ad / 0x00d5f23a / 0x00d60991.
 * The after bodies differ only in the world constant; the custom bodies differ in the type-7 gate:
 * 128 draws rand() % 10 >= 8 before testing frame >= 19; 129 and 130 test frame >= 19.97 first and only then
 * draw rand() % 10 >= 7, and 129 has no world test. */
#include "world_visual_internal.h"
#include <math.h>
static int32_t float_round_trip(int32_t v)   /* cvtsi2ss then cvttss2si */
{
    const float f = (float)v;
    if (!(f < 2147483648.0f) || !(f >= -2147483648.0f))
        return INT32_MIN;
    return (int32_t)f;
}
static void body(const uint8_t *o, int32_t i, uint32_t flags, int32_t blend, mu_obj_log *l)
{
    uint32_t a[8] = {flags, 0, (uint32_t)blend, 0, 0, 0, 0, 0xffffffffu};
    memcpy(a + 1, o + MU_OBJF_ALPHA, 4);
    memcpy(a + 3, o + MU_OBJF_BLEND_LIGHT, 12);
    memcpy(a + 6, o + MU_OBJF_HIDDEN_MESH, 4);
    wv_emit(l, MU_OBJ_CALL_BODY, i, a, 8);
}
static void mesh(const uint8_t *o, int32_t i, uint32_t flags, int32_t blend, float light, uint32_t texture,
                 mu_obj_log *l)
{
    uint32_t a[8] = {0, flags, 0, (uint32_t)blend, wv_bits(light), 0, 0, texture};
    memcpy(a + 2, o + MU_OBJF_ALPHA, 4);
    memcpy(a + 5, o + MU_OBJF_BLEND_U, 8);
    wv_emit(l, MU_OBJ_CALL_MESH, i, a, 8);
}
static void set_action(uint8_t *o, uint16_t action)
{
    mu_obj_set_u16(o, MU_OBJF_ACTION, action);
    mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
}
int mu_abyss_custom(int32_t cls, uint8_t *o, int32_t i, int32_t world, float time, mu_obj_rand_fn rand_fn,
                    void *context, mu_obj_log *l)
{
    if ((cls != 129 && world != cls) || !o)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 7: {
        const float limit = cls == 128 ? 19.0f : 19.97f;
        const int32_t chance = cls == 128 ? 8 : 7;
        const uint16_t action = mu_obj_u16(o, MU_OBJF_ACTION);
        if (action == 0) {
            if (cls != 128) {
                if (mu_obj_f32(o, MU_OBJF_FRAME) >= limit && rand_fn(context) % 10 >= chance)
                    set_action(o, 1);
            } else if (rand_fn(context) % 10 >= chance && mu_obj_f32(o, MU_OBJF_FRAME) >= limit) {
                set_action(o, 1);
            }
        } else if (action == 1) {
            if (mu_obj_f32(o, MU_OBJF_FRAME) >= limit)
                set_action(o, 0);
        } else {
            return 1;   /* other actions: handled, nothing drawn */
        }
        body(o, i, 2, mu_obj_i32(o, MU_OBJF_BLEND_MESH), l);
        return 1;
    }
    case 0x17: case 0x26: case 0x28: case 0x2c: case 0x32:
        return 1;   /* drawn by the after render */
    case 0x34: {
        const float s = (float)sin((double)(time * 0.001f));
        const float light = (float)fabs((double)s) * 0.4f + 0.3f;
        mesh(o, i, 2, mu_obj_i32(o, MU_OBJF_BLEND_MESH), mu_obj_f32(o, MU_OBJF_ALPHA), 0xffffffffu, l);
        mesh(o, i, 2, -2, light, 0x82df, l);
        return 1;
    }
    default:
        return 0;
    }
}
int mu_abyss_after(int32_t cls, const uint8_t *o, int32_t i, int32_t world, mu_obj_log *l)
{
    if (world != cls || !o)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE), blend = float_round_trip(mu_obj_i32(o, MU_OBJF_BLEND_MESH));
    if (t == 0x29) {
        mesh(o, i, 0x42, blend, mu_obj_f32(o, MU_OBJF_BLEND_LIGHT), 0x82de, l);
        return 1;
    }
    const int flagged = t == 0x17 || t == 0x26 || t == 0x28 || t == 0x2c || t == 0x32;
    body(o, i, flagged ? 2u : 0x42u, blend, l);
    return 1;
}
