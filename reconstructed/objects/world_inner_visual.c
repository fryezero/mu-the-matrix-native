/* Classless inline visuals: Kanturu 0x00e75089 and Blood Castle 0x017fc023.
 * Bounded authored reconstruction; docs/research/client-worlds-inner.md. */
#include "world_inner_visual.h"
#include "world_visual_slots.h"
#include "icarus.h"
#include "charsel_world.h"
#include <limits.h>

static void inner_particle(const uint8_t *o, int32_t i, int32_t id, int32_t sub, const float p[3],
                            const float light[3], float scale, int owner, mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, p, 12); memcpy(a + 4, o + MU_OBJF_ANGLE, 12); memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub; a[11] = wv_bits(scale); a[12] = (uint32_t)owner;
    wv_emit(l, MU_OBJ_CALL_PARTICLE, i, a, 13);
}
static void inner_joint(const uint8_t *o, int32_t i, const float p[3], const float target[3], int32_t sub,
                        float scale, mu_obj_log *l)
{
    uint32_t a[13] = {0x7f7c};
    memcpy(a + 1, p, 12); memcpy(a + 4, target, 12); memcpy(a + 7, o + MU_OBJF_ANGLE, 12);
    a[10] = (uint32_t)sub; a[12] = wv_bits(scale);
    wv_emit(l, MU_ICARUS_JOINT, i, a, 13);
}
int mu_kanturu_inner(uint8_t *o, uint8_t *b, int32_t i, int32_t world, float time, uint32_t clock,
                      mu_obj_rand_fn rnd, mu_world_bone_fn bone, void *c, mu_obj_log *l)
{
    if (world != 37 && world != 40) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float white[3] = {1, 1, 1}, zero[3] = {0, 0, 0};
    float p[3], q[3];
    memcpy(p, o + MU_OBJF_POSITION, 12);
    slot s = {o, b, i, time, NULL, l};
    if (t == 0x3b || t == 0x3d || t == 0x46) {
        mu_kanturu_flames(o, i, world, time, rnd, bone, c, l);
        return 1;
    }
    switch (t) {
    case 0x25:
        if (clock % 1024u < 10u) {
            uint32_t a[12] = {0x193};
            memcpy(a + 1, p, 12); memcpy(a + 4, o + MU_OBJF_ANGLE, 12); memcpy(a + 7, white, 12);
            a[10] = 3; a[11] = 1;
            wv_emit(l, MU_OBJ_CALL_EFFECT, i, a, 12);
        }
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 0x3e: {
        const float dark[3] = {0.04f, 0.04f, 0.04f};
        if (world == 37) {
            if (rnd(c) % 6 == 0) inner_particle(o, i, 0x7f89, 25, p, dark, mu_obj_f32(o, MU_OBJF_SCALE), 1, l);
        } else if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2) {
            for (int k = 0; k < 20; ++k)
                inner_particle(o, i, 0x7f89, 12, p, dark, mu_obj_f32(o, MU_OBJF_SCALE), 1, l);
        }
        break;
    }
    case 0x51:
        if (rnd(c) % 2 == 0) wv_particle(o, i, 0x801a, 2, white, 0, l);
        break;
    case 0x52: wv_particle(o, i, 0x801c, 4, white, 0, l); break;
    case 0x53:
        if (rnd(c) % 3 == 0) wv_particle(o, i, 0x801b, 2, white, 0, l);
        break;
    case 0x55: {
        const uint32_t a[1] = {wv_bits(A(&s))};
        wv_emit(l, MU_INNER_PUSH_MATRIX, i, a, 1);
        mesh_std(&s, 3, 0x42, -1);
        mesh_std(&s, 3, 0x84, 0x7f1f);
        wv_emit(l, MU_INNER_POP_MATRIX, i, NULL, 0);
        break;
    }
    case 0x5c:
        if (bone) { bone(c, 1, zero, p); bone(c, 2, zero, q); }
        if (rnd(c) % 30 == 1 && bone) inner_joint(o, i, p, q, 18, 50.0f, l);
        break;
    case 0x60: {
        stream(&s, 0);
        const uint32_t a[2] = {0x204, wv_bits(0.0f)}, restore[2] = {0x204, wv_bits(0.25f)};
        wv_emit(l, MU_INNER_ALPHA_FUNC, i, a, 2);
        mesh(&s, 0, 2, 1.0f, BM(&s), BL(&s), U(&s), tmod(&s, 20000, 0.00005f, 1), -1);
        wv_emit(l, MU_INNER_ALPHA_FUNC, i, restore, 2);
        stream(&s, 0xff);
        break;
    }
    case 0x62:
        if (rnd(c) % 3 == 0 && bone) {
            const float light[3] = {0.5f, 0.6f, 0.1f};
            bone(c, 1, zero, p);
            inner_particle(o, i, 0x802a, 2, p, light, 1.0f, 0, l);
        }
        break;
    case 0x69: {
        const float pulse = (csin(time * 0.001f) + 1.0f) * 0.5f;
        const float light[3] = {pulse, pulse, pulse};
        if (bone) {
            bone(c, 4, zero, p);
            inner_particle(o, i, 0x7f2b, 0, p, light, 1.5f, 0, l);
            wv_sprite(i, 0x7f26, p, 10.0f, light, l);
        }
        memcpy(q, p, 12);
        p[0] -= 50.0f;
        p[0] -= (float)(rnd(c) % 100);
        q[0] += (float)(rnd(c) % 80);
        p[1] -= (float)(rnd(c) % 50);
        q[1] += (float)(rnd(c) % 50);
        p[2] += 10.0f; q[2] += 10.0f;
        if (rnd(c) % 20 == 0 && bone) inner_joint(o, i, p, q, 8, 40.0f, l);
        break;
    }
    case 0x6b: case 0x6c:
        if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2) {
            const float v = t == 0x6b ? 0.06f : 0.2f, light[3] = {v, v, v};
            for (int k = 0; k < 20; ++k)
                inner_particle(o, i, 0x7f89, t == 0x6b ? 2 : 7, p, light, mu_obj_f32(o, MU_OBJF_SCALE), 1, l);
        }
        break;
    case 0x6e:
        if (bone) {
            const float pulse = (csin(time * 0.002f) + 1.5f) * 0.5f;
            const float light[3] = {pulse * 0.6f, pulse, pulse * 0.8f};
            bone(c, 1, zero, p);
            wv_sprite(i, 0x7ef7, p, 1.1f, light, l);
        }
        break;
    default: break;
    }
    return 1;
}
int mu_blood_castle_inner(uint8_t *o, int32_t i, int32_t world, float time, mu_obj_rand_fn rnd,
                           mu_world_named_bone_fn bone, void *c, mu_obj_log *l)
{
    if (!((world >= 11 && world <= 17) || world == 52)) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float zero[3] = {0, 0, 0}, white[3] = {1, 1, 1};
    float p[3];
    if (t == 0x0b && bone) {
        const float pulse = csin((mu_obj_f32(o, MU_OBJF_ANGLE + 8) * 20.0f + time) * 0.001f) * 0.5f + 0.5f;
        const float light[3] = {pulse, pulse * 0.5f, 0}, local[3] = {0, 0, 2};
        static const char *const names[] = {"light", "light01", "light02", "light03", "light04", "light05", "light06"};
        for (int k = 0; k < 7; ++k) {
            bone(c, names[k], local, p);
            wv_sprite(i, 0x7ef7, p, 0.5f, light, l);
        }
    } else if (t == 0x0d && bone) {
        const float pulse = csin(time * 0.001f) * 0.3f + 0.7f, light[3] = {pulse, pulse, pulse};
        bone(c, "light01", zero, p);
        wv_sprite(i, 0x7f78, p, pulse + 0.5f, light, l);
    } else if (t == 0x2a) {
        memcpy(p, o + MU_OBJF_POSITION, 12);
        if (rnd(c) % 2 == 0) {
            const int32_t n = cvtt(mu_obj_f32(o, 0xb4) + 2.0f) % 4;
            mu_obj_set_f32(o, 0xb4, mu_obj_f32(o, 0xb4) + 1.0f);
            if (n == 0) {
                inner_particle(o, i, 0x8001, 0, p, white, 1.0f, 0, l);
                inner_particle(o, i, 0x8000, 0, p, white, 1.0f, 0, l);
            }
        }
        if (rnd(c) % 2 == 0) {
            const int32_t n = cvtt(mu_obj_f32(o, 0xb4)) % 4;
            mu_obj_set_f32(o, 0xb4, mu_obj_f32(o, 0xb4) + 1.0f);
            if (n == 0) {
                const float red[3] = {1, 0.8f, 0.8f};
                inner_particle(o, i, 0x7f89, 6, p, white, 1.0f, 0, l);
                inner_particle(o, i, 0x8000, 1, p, white, 1.0f, 0, l);
                inner_particle(o, i, 0x7f78, 4, p, red, 0.19f, 0, l);
            }
        }
    }
    return 1;
}
