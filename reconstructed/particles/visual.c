/* RenderObjectVisual 0x017f9758 for Lorencia and Tormenta Island
 * (NATIVE-PARTICLE-001). */
#include <string.h>

#include "particles.h"
#include "particles_internal.h"

static int32_t vrand(const mu_pt_visual_host *h)
{
    return h->rand ? h->rand(h->context) : 0;
}

static int32_t trunc_i32(float v)
{
    return mu_pt_cvttss2si(v);
}

static void bone(const mu_pt_visual_host *h, const mu_pt_visual_object *o, const char *name, const float in[3],
                 float out[3])
{
    if (h->bone_position)
        h->bone_position(h->context, o, name, in, out);
}

static void lorencia(mu_pt_visual_object *o, const mu_pt_visual_host *h, float l)
{
    if (o->type == 0x69) {
        /* 0x017f9844 Waterspout01: the blend mesh scroll, then two smoke puffs */
        o->blend_light = 1.0f;
        o->blend_v = (float)((int32_t)(0u - (uint32_t)trunc_i32(h->world_time)) % 1000) * 0.001f;
        if (vrand(h) % 2 != 0)
            return;
        static const char *const bones[2] = {"Box04", "Box03"};
        static const float drop[2] = {-20.0f, -80.0f};
        for (int k = 0; k < 2; ++k) {
            float p[3], out[3] = {0.0f, 0.0f, 0.0f};
            p[0] = (float)(vrand(h) % 32 - 16);
            p[1] = drop[k];
            p[2] = (float)(vrand(h) % 32 - 16);
            bone(h, o, bones[k], p, out);
            if (h->particle)
                h->particle(h->context, MU_PT_BITMAP_SMOKE, out, o->angle, o->light, 0, 1.0f, MU_PT_NO_OWNER);
        }
    } else if (o->type == 0x38) {
        /* 0x017f9a6d MerchantAnimal01: two flares. The input vector of TransformPosition is a local the routine
         * never writes ([ebp-0x2c]); the C passes the bone's origin. */
        const float scale = l * 5.0f;
        const float light[3] = {l * 0.6f, l * 0.3f, l * 0.1f};
        static const char *const bones[2] = {"Box04", "Box10"};
        static const float zero[3] = {0.0f, 0.0f, 0.0f};
        for (int k = 0; k < 2; ++k) {
            float out[3] = {0.0f, 0.0f, 0.0f};
            bone(h, o, bones[k], zero, out);
            if (h->sprite)
                h->sprite(h->context, MU_PT_BITMAP_FLARE, out, scale, light, o->index, 0.0f, 0, 4);
        }
    }
}

/* Tormenta Island handler slot 0x34 0x00e4ef4b. */
static void tormenta(mu_pt_visual_object *o, const mu_pt_visual_host *h)
{
    int32_t subtype = -1;
    switch (o->type) {
    case 2: subtype = 0x1a; break;
    case 3: subtype = 0x10; break;
    case 4: subtype = 0x11; break;
    case 5: subtype = 0x18; break;
    case 0xbf: subtype = 0x19; break;
    case 0xc0: subtype = 0x12; break;
    case 0xc1: subtype = 0x13; break;
    case 0xc2: subtype = 0x14; break;
    case 0xc3: subtype = 0x15; break;
    case 0xc4: subtype = 0x16; break;
    case 0xc5: subtype = 0x17; break;
    case 9:
        /* 0x00e4f33f: one step in 500 the effect 0x40e */
        if (vrand(h) % 500 == 1 && h->effect)
            h->effect(h->context, 0x40e, o->position, o->angle, o->light, 0, o->index);
        return;
    default:
        return;
    }
    if (vrand(h) % 50 != 0)
        return;
    o->light[0] = 0.59f;
    o->light[1] = 0.59f;
    o->light[2] = 1.0f;
    if (h->joint)
        h->joint(h->context, 0x7f7d, o->position, o->angle, subtype, o->index, o->scale);
}

/* ---- NATIVE-JOINT-001: Dungeon, Devias, Noria ---- */

static void sprite(const mu_pt_visual_host *h, const mu_pt_visual_object *o, int32_t bitmap, const float p[3],
                   float scale, const float light[3], float rotation)
{
    if (h->sprite)
        h->sprite(h->context, bitmap, p, scale, light, o->index, rotation, 0, 4);
}

/* (int)(WorldTime * 0.1) % 360 */
static float spin(const mu_pt_visual_host *h)
{
    return (float)(trunc_i32(h->world_time * 0.1f) % 360);
}

/* 0x017fc8e0 Dungeon (world 1) */
static void dungeon(mu_pt_visual_object *o, const mu_pt_visual_host *h, float l)
{
    if (o->type != 0x3d)
        return;
    const float light[3] = {l * 0.4f, l * 0.8f, l * 1.0f};
    const float r = spin(h);
    static const int32_t bones[3] = {15, 19, 21};
    static const float scales[3] = {0.3f, 0.3f, 1.5f};
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    float p[3] = {0.0f, 0.0f, 0.0f};
    for (int k = 0; k < 3; ++k) {
        if (h->bone_index_position)
            h->bone_index_position(h->context, o, bones[k], zero, p);
        sprite(h, o, MU_PT_BITMAP_LIGHTNING2, p, scales[k], light, r);
        sprite(h, o, MU_PT_BITMAP_LIGHTNING2, p, scales[k], light, -r);
    }
}

/* 0x017f9bdc Devias (world 2) */
static void devias(mu_pt_visual_object *o, const mu_pt_visual_host *h, float l)
{
    if (o->type != 0x64)
        return;   /* type 0x67 picks its next action at the end of the current one (0x012affa4), not ported */
    const float light[3] = {l * 1.0f, l * 1.0f, l * 1.0f};
    const float r = spin(h);
    static const float up[3] = {0.0f, 0.0f, 150.0f};
    float p[3] = {0.0f, 0.0f, 0.0f};
    bone(h, o, "Cylinder01", up, p);
    sprite(h, o, MU_PT_BITMAP_LIGHTNING2, p, 2.5f, light, r);
    sprite(h, o, MU_PT_BITMAP_LIGHTNING2, p, 2.5f, light, -r);
}

static void flares(mu_pt_visual_object *o, const mu_pt_visual_host *h, const char *const *bones, int count,
                   float scale, const float light[3])
{
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    float p[3] = {0.0f, 0.0f, 0.0f};
    for (int k = 0; k < count; ++k) {
        bone(h, o, bones[k], zero, p);
        sprite(h, o, MU_PT_BITMAP_FLARE, p, scale, light, 0.0f);
    }
}

/* 0x017f9dd1 Noria (world 3) */
static void noria(mu_pt_visual_object *o, const mu_pt_visual_host *h, float l)
{
    const float lamp[3] = {l * 0.4f, l * 0.7f, l * 1.0f};
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    switch (o->type) {
    case 9: {
        static const char *const b[1] = {"Box01"};
        flares(o, h, b, 1, 1.5f, lamp);
        break;
    }
    case 0x23: {
        static const char *const b[1] = {"Box04"};
        flares(o, h, b, 1, 1.5f, lamp);
        break;
    }
    case 1: {
        static const char *const b[3] = {"light03", "light02", "light01"};
        flares(o, h, b, 3, 0.5f, lamp);
        break;
    }
    case 0x11: {
        static const char *const b[4] = {"Box03", "Box08", "Box11", "Box14"};
        flares(o, h, b, 4, 1.0f, lamp);
        break;
    }
    case 0x27: {
        /* 0x017fa423 */
        const float glow[3] = {l * 0.4f, l * 0.8f, l * 1.0f};
        const float r = spin(h);
        float p[3] = {0.0f, 0.0f, 0.0f};
        bone(h, o, "light01", zero, p);
        sprite(h, o, MU_PT_BITMAP_LIGHTNING2, p, 1.0f, glow, r);
        sprite(h, o, MU_PT_BITMAP_LIGHTNING2, p, 1.0f, glow, -r);
        static const char *const lamps[5] = {"light06", "light04", "light03", "light05", "light02"};
        static const float white[3] = {1.0f, 1.0f, 1.0f};
        for (int k = 0; k < 5; ++k) {
            bone(h, o, lamps[k], zero, p);
            sprite(h, o, MU_PT_BITMAP_FLARE, p, 1.0f, white, 0.0f);
            if (vrand(h) % 32 == 0 && h->particle) {
                h->particle(h->context, MU_PT_BITMAP_SHINY1, p, o->angle, white, 0, 1.0f, MU_PT_NO_OWNER);
                h->particle(h->context, MU_PT_BITMAP_SHINY1, p, o->angle, white, 1, 1.0f, MU_PT_NO_OWNER);
            }
        }
        bone(h, o, "light07", zero, p);
        if (vrand(h) % 8 == 0) {
            for (int k = 0; k < 8; ++k) {
                float a[3];
                a[0] = (float)(vrand(h) % 60 + 60);
                a[1] = 140.0f;
                a[2] = (float)(vrand(h) % 30);
                if (h->joint)
                    h->joint(h->context, 0x7fd5, p, a, 0, MU_PT_NO_OWNER, 10.0f);
                if (h->particle)
                    h->particle(h->context, MU_PT_BITMAP_SPARK2, p, a, white, 0, 1.0f, MU_PT_NO_OWNER);
            }
        }
        break;
    }
    default:
        break;
    }
}

int mu_pt_object_visual(mu_pt_visual_object *o, const mu_pt_visual_host *h)
{
    if (h->world != 0 && h->world != 0x8d && h->world != 1 && h->world != 2 && h->world != 3)
        return 0;
    if (h->has_model && !h->has_model(h->context, o))
        return 1;
    /* 0x017f9797: one rand() for every object with a model, before the world switch */
    const float l = (float)(vrand(h) % 30 + 70) * 0.01f;
    switch (h->world) {
    case 0: lorencia(o, h, l); break;
    case 1: dungeon(o, h, l); break;
    case 2: devias(o, h, l); break;
    case 3: noria(o, h, l); break;
    default: tormenta(o, h); break;
    }
    return 1;
}
