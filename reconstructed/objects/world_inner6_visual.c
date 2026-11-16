/* RENDER-WORLDS-PICK-001: chain hook 11's producer, authored from pinned instructions
 * (0x00db7656..0x00db84d2). See client-worlds-inner.md. */
#include "world_inner6_visual.h"
#include "world_visual_slots.h"
#include "worlds_r2.h"

int mu_chain11_world(int32_t world)
{
    return (world >= 0x62 && world <= 0x63) || (world >= 0x2d && world <= 0x32);
}

/* CreateParticle(id, position, the object's angle, light, sub, scale, owner, 0) */
static void particle(const uint8_t *o, int32_t i, int id, const float position[3], const float light[3], int sub,
                     float scale, int owner, mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, position, 12);
    memcpy(a + 4, o + MU_OBJF_ANGLE, 12);
    memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub;
    a[11] = wv_bits(scale);
    a[12] = (uint32_t)owner;
    wv_emit(l, MU_OBJ_CALL_PARTICLE, i, a, 13);
}

/* the object's own smoke: light = colour * f, at the position, object scale, owned */
static void smoke(const uint8_t *o, int32_t i, const float colour[3], float f, int sub, mu_obj_log *l)
{
    float position[3];
    memcpy(position, o + MU_OBJF_POSITION, 12);
    const float light[3] = {colour[0] * f, colour[1] * f, colour[2] * f};
    particle(o, i, 0x7f89, position, light, sub, mu_obj_f32(o, MU_OBJF_SCALE), 1, l);
}

/* types 76 / 77: one owned 0x7dec particle at the position, then the 0x7ef7 glow 20 above it */
static void ember(const uint8_t *o, int32_t i, const float light[3], mu_obj_log *l)
{
    float position[3];
    memcpy(position, o + MU_OBJF_POSITION, 12);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    particle(o, i, 0x7dec, position, light, 0, scale, 1, l);
    position[2] = position[2] + 20.0f;
    uint32_t a[12] = {0x7ef7};
    memcpy(a + 1, position, 12);
    a[4] = wv_bits(scale * 6.0f);
    memcpy(a + 5, light, 12);
    a[8] = wv_bits(0.0f);
    a[9] = 1;
    a[11] = 4;
    wv_emit(l, MU_OBJ_CALL_SPRITE, i, a, 12);
}

/* CreateEffect(0x4cc, position, angle, light, sub, 0, -1, 0, 0, 0, 0.0, -1, 0, 0): no owner, word4 0 */
static void effect(const uint8_t *o, int32_t i, const float light[3], int sub, mu_obj_log *l)
{
    uint32_t a[13] = {0x4cc};
    memcpy(a + 1, o + MU_OBJF_POSITION, 12);
    memcpy(a + 4, o + MU_OBJF_ANGLE, 12);
    memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub;
    wv_emit(l, MU_R2_EFFECT, i, a, 13);
}

int mu_chain11_inner(uint8_t *o, int32_t i, int32_t world, int model, uint32_t clock, mu_obj_rand_fn rnd, void *c,
                     mu_obj_log *l)
{
    if (!model || !mu_chain11_world(world))
        return 0;
    static const float teal[3] = {0.2109375f, 0.69140625f, 0.5859375f};
    static const float pink[3] = {0.86328125f, 0.47265625f, 0.78515625f};
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    float position[3];
    memcpy(position, o + MU_OBJF_POSITION, 12);
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x36: {   /* 0x00db7709: the object's light becomes 0.15 grey; two 0x8022 particles 100 below */
        position[2] = position[2] - 100.0f;
        float light[3];
        for (unsigned k = 0; k < 3; ++k) {
            mu_obj_set_f32(o, MU_OBJF_LIGHT + 4 * k, 0.15f);
            light[k] = 0.15f;
        }
        particle(o, i, 0x8022, position, light, 0, 1.0f, 0, l);
        particle(o, i, 0x8022, position, light, 3, 1.0f, 0, l);
        break;
    }
    case 0x46: case 0x47: case 0x48:   /* 0x00db7859 / 0x00db7926 / 0x00db79f3 */
        if (rnd(c) % 3 == 0) {
            const float f = (float)(rnd(c) % 10) * 0.007f + 0.03f;
            const int t = mu_obj_i32(o, MU_OBJF_TYPE);
            if (t != 0x47)
                smoke(o, i, teal, f, 15, l);
            if (t != 0x46)
                smoke(o, i, pink, f, 15, l);
        }
        break;
    case 0x49:   /* 0x00db7b51 */
        if (rnd(c) % 3 == 0) {
            static const float grey[3] = {1.2f, 1.2f, 1.2f};
            smoke(o, i, grey, (float)(rnd(c) % 10) * 0.002f + 0.03f, 15, l);
        }
        break;
    case 0x4a:   /* 0x00db7c1e */
        if (rnd(c) % 2 == 0) {
            static const float black[3] = {0.0f, 0.0f, 0.0f};
            particle(o, i, 0x7f89, position, black, 16, scale, 1, l);
        }
        break;
    case 0x4b:   /* 0x00db7cab */
        if (rnd(c) % 35 == 5) {
            const float f = (float)(rnd(c) % 10) * 0.05f + 0.03f;
            const float light[3] = {1.0f * f, 1.0f * f, 1.0f * f};
            particle(o, i, 0x7dea, position, light, 0, scale, 1, l);
        }
        break;
    case 0x4c: {   /* 0x00db7d79: red, brightened by rand % 100 hundredths (binary64 product) */
        const float r = (float)((double)(rnd(c) % 100) * 0.01);
        const float light[3] = {0.7058823704719543f + r, 0.27843138575553894f, 0.21568627655506134f};
        ember(o, i, light, l);
        break;
    }
    case 0x4d: {   /* 0x00db7f3d: blue, brightened by rand % 100 two-hundredths */
        const float r = (float)((double)(rnd(c) % 100) * 0.005);
        const float light[3] = {0.21484375f, 0.27734375f, 0.703125f + r};
        ember(o, i, light, l);
        break;
    }
    case 0x4e: {   /* 0x00db8101: a short window of the clock's 500 ms cycle, drawn anew every call */
        const int32_t phase = (int32_t)(clock % 500u);
        const int32_t start = rnd(c) % 485;
        if (phase < start + rnd(c) % 5)
            break;
        if (phase >= start + rnd(c) % 10 + 5)
            break;
        const float flash[3] = {1.0f, 0.8f, 0.8f};
        for (int k = 0; k < 4; ++k)
            effect(o, i, flash, 0, l);
        effect(o, i, flash, 1, l);
        const float pale[3] = {0.7f, 0.7f, 0.8f};
        float near[3];
        memcpy(near, position, 12);
        near[0] = (float)(rnd(c) % 80 - 40) + near[0];
        near[1] = (float)(rnd(c) % 80 - 40) + near[1];
        particle(o, i, 0x801c + rnd(c) % 2, near, pale, 2, 1.0f, 0, l);
        const float red[3] = {0.9f, 0.0f, 0.0f};
        particle(o, i, 0x7f5a, position, red, 0, 1.5f, 0, l);
        break;
    }
    case 0x4f:   /* 0x00db83de: rand % 1 is always 0, the call is still made */
        if (rnd(c) % 1 == 0) {
            static const float slate[3] = {0.390625f, 0.4296875f, 0.625f};
            for (int k = 0; k < 5; ++k)
                smoke(o, i, slate, (float)(rnd(c) % 10) * 0.03f + 0.008f, 17, l);
        }
        break;
    default:
        return 0;
    }
    return 1;
}
