/* Aida 0x00d622dd..0x00d63d6b. Authored from pinned instructions; see client-worlds-inner.md. */
#include "world_inner3_visual.h"
#include "world_visual_slots.h"
#include "worlds_r2.h"
#include "charsel_world.h"
#include "icarus.h"

static void aida_sprite(int32_t i, int32_t id, const float p[3], float size, const float light[3], float angle,
                         mu_obj_log *l)
{
    uint32_t a[12] = {(uint32_t)id};
    memcpy(a + 1, p, 12); a[4] = wv_bits(size); memcpy(a + 5, light, 12);
    a[8] = wv_bits(angle); a[9] = 1; a[11] = 4;
    wv_emit(l, MU_OBJ_CALL_SPRITE, i, a, 12);
}
static void aida_effect(const uint8_t *o, int32_t i, int32_t id, int32_t sub, const float light[3],
                         int word, mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, o + MU_OBJF_POSITION, 12); memcpy(a + 4, o + MU_OBJF_ANGLE, 12);
    memcpy(a + 7, light, 12); a[10] = (uint32_t)sub; a[11] = 1; a[12] = (uint32_t)word;
    /* The existing keyed effect channel carries CreateEffect word4, including zero. */
    wv_emit(l, id == 0x199 ? MU_R2_EFFECT : MU_OBJ_CALL_EFFECT, i, a, id == 0x199 ? 13 : 12);
}
static void aida_particle(const uint8_t *o, int32_t i, int32_t id, int32_t sub, const float light[3], int owner,
                           mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, o + MU_OBJF_POSITION, 12); memcpy(a + 4, o + MU_OBJF_ANGLE, 12); memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub; a[11] = wv_bits(mu_obj_f32(o, MU_OBJF_SCALE)); a[12] = (uint32_t)owner;
    wv_emit(l, MU_OBJ_CALL_PARTICLE, i, a, 13);
}
int mu_aida_inner(uint8_t *o, uint8_t *b, int32_t i, int32_t world, float time, uint32_t clock,
                  mu_obj_rand_fn rnd, mu_world_named_bone_fn bone, void *c, mu_obj_log *l)
{
    if (world != 33 && world != 54) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float white[3] = {1, 1, 1};
    slot s = {o, b, i, time, NULL, l};
    switch (t) {
    case 0x1e: case 0x47:
        if (bone) {
            static const char *const names[] = {"Box07", "Box08", "Box09", "Box13", "Box14", "Box18"};
            static const float local[6][3] = {{0,-3,1}, {0,-3,0}, {0,-3,0}, {-3,-1,0}, {-3,-3,0}, {0,2,-8}};
            static const float blue_sizes[6] = {5.5f,4.5f,4,4.5f,4,4};
            static const float red_sizes[6] = {6,5.5f,5,5.5f,5,5};
            const float blue[3] = {0.1f,0.1f,0.3f}, grey[3] = {0.15f,0.15f,0.15f};
            const float red_grey[3] = {0.15f,0,0};
            for (int k = 0; k < 6; ++k) {
                float p[3]; bone(c, names[k], local[k], p);
                const float red[3] = {k == 0 ? 0.5f : 0.25f,0,0};
                aida_sprite(i, 0x7f26, p, t == 0x1e ? blue_sizes[k] : red_sizes[k], t == 0x1e ? blue : red, 0, l);
                aida_sprite(i, 0x7f26, p, 3, t == 0x1e ? grey : red_grey, 0, l);
            }
        }
        break;
    case 0x38:
        if (rnd(c) % 2 == 0) aida_particle(o, i, 0x801a, 2, white, 0, l);
        break;
    case 0x39: aida_particle(o, i, 0x801c, 4, white, 0, l); break;
    case 0x3a:
        if (rnd(c) % 3 == 0) aida_particle(o, i, 0x801b, 2, white, 0, l);
        break;
    case 0x3b: case 0x3e: case 0x3f:
        if (H(&s) != -2) {
            const float light[3] = {t == 0x3b ? 0.01f : 0.05f, t == 0x3b ? 0.03f : t == 0x3e ? 0.05f : 0.02f,
                                    t == 0x3b ? 0.05f : t == 0x3e ? 0.05f : 0.02f};
            for (int k = 0; k < 20; ++k) aida_particle(o, i, 0x7f89, 26, light, 1, l);
        }
        break;
    case 0x3c:
        if (clock % 1024u < 10u) aida_effect(o, i, 0x193, 3, white, 0, l);
        set_hidden(&s, -2);
        break;
    case 0x41: case 0x42: case 0x4d: case 0x4e: {
        const uint32_t a[1] = {wv_bits(1.0f)};
        wv_emit(l, MU_INNER_PUSH_MATRIX, i, a, 1);
        stream(&s, 0);
        mesh(&s, 0, 2, A(&s), BM(&s), BL(&s), tmod(&s, 100000, t <= 0x42 ? 0.00005f : 0.0002f, t <= 0x42), V(&s), -1);
        stream(&s, 0xff);
        wv_emit(l, MU_INNER_POP_MATRIX, i, NULL, 0);
        break;
    }
    case 0x43: {
        const float light[3] = {0.3f,0.3f,0.3f};
        for (uint32_t k = 0; k < 3; ++k) mu_obj_set_f32(o, MU_OBJF_LIGHT + 4 * k, light[k]);
        aida_particle(o, i, 0x7f42, 7, light, 0, l);
        break;
    }
    case 0x46:
        if (rnd(c) % 5 == 1 && clock % 1024u < 30u) {
            const float light[3] = {0.1f,0.1f,0.1f};
            aida_effect(o, i, 0x199, 0, light, (uint16_t)(uint32_t)cvtt(mu_obj_f32(o, MU_OBJF_SCALE)), l);
        }
        break;
    case 0x4b:
        if (bone) {
            const float local[3] = {0,0,0}; float p[3];
            bone(c, "Bone01", local, p);
            /* The calculated pulse is overwritten with white before the draw. */
            aida_sprite(i, 0x7f78, p, 3, white, time / 10.0f, l);
        }
        break;
    default: break;
    }
    return 1;
}

/* Kanturu Remain 0x00e7df87..0x00e7ed6e. */
static void remain_particle(const uint8_t *o, int32_t i, int32_t id, int32_t sub, const float p[3],
                             const float light[3], float size, int owner, mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, p, 12); memcpy(a + 4, o + MU_OBJF_ANGLE, 12); memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub; a[11] = wv_bits(size); a[12] = (uint32_t)owner;
    wv_emit(l, MU_OBJ_CALL_PARTICLE, i, a, 13);
}
static void remain_joint(const uint8_t *o, int32_t i, int32_t id, int32_t sub, const float p[3],
                          const float q[3], float size, mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, p, 12); memcpy(a + 4, q, 12); memcpy(a + 7, o + MU_OBJF_ANGLE, 12);
    a[10] = (uint32_t)sub; a[12] = wv_bits(size);
    wv_emit(l, MU_ICARUS_JOINT, i, a, 13);
}
int mu_kanturu_remain_inner(uint8_t *o, int32_t i, int32_t world, float time, mu_obj_rand_fn rnd,
                            mu_world_bone_fn bone, void *c, mu_obj_log *l)
{
    if (world != 38) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float size = mu_obj_f32(o, MU_OBJF_SCALE), white[3] = {1,1,1}, zero[3] = {0,0,0};
    float p[3]; memcpy(p, o + MU_OBJF_POSITION, 12);
    switch (t) {
    case 4:
        if (bone) {
            const float pulse = (csin(time * 0.002f) + 2.0f) * 0.5f;
            const float light[3] = {pulse * 0.3f,pulse * 0.5f,pulse}, local[3] = {-1,0,0};
            bone(c, 1, local, p);
            const float scale = (float)((double)pulse / 3.2);
            aida_sprite(i, 0x7ef7, p, scale, light, 0, l);
            aida_sprite(i, 0x802b, p, scale, light, 0, l);
            aida_sprite(i, 0x802b, p, scale, light, 0, l);
        }
        break;
    case 8: {
        const float pulse = (csin(time * 0.001f) + 1.0f) * 0.5f, light[3] = {pulse,pulse,pulse};
        if (bone) {
            bone(c, 4, zero, p);
            remain_particle(o, i, 0x7f2b, 0, p, light, 1.5f, 0, l);
            aida_sprite(i, 0x7f26, p, 10, light, 0, l);
        }
        float a[3],b[3]; memcpy(a,p,12); memcpy(b,p,12);
        a[0] -= 50.0f; a[0] -= (float)(rnd(c) % 100); b[0] += (float)(rnd(c) % 80);
        a[1] -= (float)(rnd(c) % 50); b[1] += (float)(rnd(c) % 50);
        a[2] += 10.0f; b[2] += 10.0f;
        if (rnd(c) % 20 == 0 && bone) remain_joint(o, i, 0x7f7c, 18, a, b, 40, l);
        break;
    }
    case 0xa:
        if (rnd(c) % 6 == 0) {
            p[2] = 410;
            remain_particle(o, i, 0x801c, 7, p, white, size, 0, l);
        }
        break;
    case 0x2d: case 0x2e: case 0x2f: case 0x31:
        if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2) {
            const float v = t == 0x2f ? 0.2f : 0.06f;
            const float light[3] = {t == 0x31 ? 0 : v,t == 0x31 ? 0.01f : v,t == 0x31 ? 0.03f : v};
            const int sub = t == 0x2d || t == 0x31 ? 1 : t == 0x2e ? 2 : 7;
            for (int k = 0; k < (t == 0x31 ? 5 : 20); ++k)
                remain_particle(o, i, 0x7f89, sub, p, light, size, 1, l);
        }
        break;
    case 0x30:
        if (rnd(c) % 3 == 0) {
            const float light[3] = {0.2f,0.2f,0.2f};
            remain_particle(o, i, 0x7f89, 10, p, light, size, 1, l);
        }
        break;
    case 0x32:
        if (rnd(c) % 3 == 0) {
            const float light[3] = {0,0.01f,(float)(rnd(c) % 3) * 0.01f + 0.02f};
            remain_particle(o, i, 0x7f89, 11, p, light, size, 1, l);
        }
        break;
    case 0x34:
        if (rnd(c) % 6 == 0) remain_particle(o, i, 0x801c, 7, p, white, size, 0, l);
        break;
    case 0x35:
        if (rnd(c) % 3 == 0) {
            const float light[3] = {0.4f,0.6f,0.7f};
            remain_particle(o, i, 0x802a, 1, p, light, 1, 0, l);
        }
        break;
    case 0x36: case 0x38: case 0x41:
        if (rnd(c) % (t == 0x36 ? 20 : 10) == 0) {
            const float scale = (float)(rnd(c) % 10) + 30.0f;
            remain_joint(o, i, 0x7f7d, t == 0x36 ? 8 : t == 0x38 ? 9 : 10, p, p, scale, l);
        }
        break;
    case 0x37:
        if (rnd(c) % 5 == 0) {
            const float light[3] = {0.8f,0.8f,1};
            aida_effect(o, i, 0x4ac, 1, light, 0, l);
        }
        break;
    default: break;
    }
    return 1;
}

/* Land of Trials 0x00dfc095..0x00dfc3ce. */
int mu_trials_inner(uint8_t *o, int32_t i, int32_t world, float time, mu_obj_rand_fn rnd,
                     mu_world_bone_fn bone, void *c, mu_obj_log *l)
{
    if (world != 31) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float white[3] = {1,1,1};
    if (t == 3 || t == 0x35) {
        if (rnd(c) % 3 == 0) aida_particle(o, i, t == 3 ? 0x801c : 0x7f5a, t == 3 ? 3 : 22, white, 0, l);
    } else if (t == 0x31) {
        float p[3]; const float local[3] = {0,-10,0}, red[3] = {1,0,0}, grey[3] = {0.3f,0.3f,0.3f};
        if (bone) {
            bone(c, 3, local, p);
            const float pulse = csin(time * 0.002f) * 0.35f + 0.65f;
            aida_sprite(i, 0x7ef7, p, pulse * 1.2f + 0.3f, red, 0, l);
            aida_sprite(i, 0x7ef7, p, 0.5f, red, 0, l);
        }
        const float angle = (float)(rnd(c) % 360);
        if (bone) {
            /* Unlike the first two sprites, this third sprite has no OBJECT owner. */
            uint32_t a[12] = {0x7f67}; memcpy(a + 1, p, 12); a[4] = wv_bits(1.2f);
            memcpy(a + 5, grey, 12); a[8] = wv_bits(angle); a[11] = 4;
            wv_emit(l, MU_OBJ_CALL_SPRITE, i, a, 12);
        }
    }
    return 1;
}

/* Devil Square world 9, RenderObjectVisual 0x017fb7e7..0x017fba59. */
int mu_devil_square_inner(uint8_t *o, int32_t i, int32_t world, mu_obj_rand_fn rnd,
                          mu_world_named_bone_fn bone, void *c, mu_obj_log *l)
{
    if (world != 9) return 0;
    if (mu_obj_i32(o, MU_OBJF_TYPE) != 2) return 1;
    const float local[3] = {-15,0,0}, white[3] = {1,1,1}; float p[3];
    static const char *const names[] = {"Bip01 R UpperArm", "Bip01 L UpperArm", "Bip01 R UpperArm"};
    for (int k = 0; k < 3; ++k) {
        const int emit = k == 2 || rnd(c) % 4 == 0;
        if (emit && bone) {
            bone(c, names[k], local, p);
            remain_particle(o, i, 0x771d, 0, p, white, 1, 0, l);
        }
    }
    return 1;
}
