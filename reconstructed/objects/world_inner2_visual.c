/* Elbeland 0x00e3116a and Swamp of Calmness 0x00e5f94b, after the outer draw.
 * Authored from the pinned instructions. See docs/research/client-worlds-inner.md. */
#include "world_inner_visual.h"
#include "world_visual_slots.h"
#include "icarus.h"

static void later_particle(const uint8_t *o, int32_t i, int32_t id, int32_t sub, const float p[3],
                            const float light[3], float scale, int owner, mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, p, 12); memcpy(a + 4, o + MU_OBJF_ANGLE, 12); memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub; a[11] = wv_bits(scale); a[12] = (uint32_t)owner;
    wv_emit(l, MU_OBJ_CALL_PARTICLE, i, a, 13);
}
int mu_later_world_inner(uint8_t *o, int32_t i, int32_t world, float time, mu_obj_rand_fn rnd,
                          mu_world_bone_fn bone, void *c, const float stack_light[3], mu_obj_log *l)
{
    if (world != 51 && world != 56) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float white[3] = {1, 1, 1};
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    float p[3]; memcpy(p, o + MU_OBJF_POSITION, 12);
    if (world == 51) {
        switch (t) {
        case 0:
            if (rnd(c) % 3 == 0) later_particle(o, i, 0x8016, 0, p, white, scale, 0, l);
            break;
        case 0x36:
            if (rnd(c) % 4 == 0) later_particle(o, i, 0x801b, 4, p, white, scale, 0, l);
            break;
        case 0x3a:
            /* The original reads its uninitialised local [ebp-0x10..-8]. Only an explicit synthetic input
             * can define it. The production adapter supplies NULL and counts the refusal. */
            if (stack_light) later_particle(o, i, 0x801e, 0, p, stack_light, 1.0f, 0, l);
            else wv_emit(l, MU_INNER_UNWRITTEN_LIGHT, i, NULL, 0);
            break;
        case 0x3b: later_particle(o, i, 0x801c, 8, p, white, scale, 0, l); break;
        case 0x3c:
            if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2) {
                const float light[3] = {0.06f, 0.07f, 0.08f};
                for (int k = 0; k < 10; ++k) later_particle(o, i, 0x7f89, 3, p, light, scale, 1, l);
                mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
            }
            break;
        case 0x3d:
            if (rnd(c) % 3 == 0) later_particle(o, i, 0x8017, 0, p, white, scale, 0, l);
            break;
        case 0x3f:
            if (bone) {
                const float pulse = (csin(time * 0.001f) + 1.0f) * 0.3f + 0.4f;
                const float light[3] = {pulse, pulse, pulse * 0.6f}, local[3] = {-40, -10, 0};
                bone(c, 5, local, p);
                wv_sprite(i, 0x7ef7, p, scale * 6.0f, light, l);
            }
            break;
        case 0x6e:
            if (rnd(c) % 2 == 0) {
                float local[3] = {0, 0, 70};
                local[0] = (float)cos((double)(time * 0.03f)) * ((float)(rnd(c) % 5) + 30.0f);
                local[1] = csin(time * 0.03f) * ((float)(rnd(c) % 5) + 30.0f);
                if (bone) {
                    bone(c, 0, local, p);
                    later_particle(o, i, 0x7ef7, 11, p, white, 0.6f, 1, l);
                }
            }
            break;
        case 0x79:
            if (bone) {
                const float pulse = (csin(time * 0.002f) + 1.0f) * 0.5f + 0.5f;
                const float light[3] = {pulse, pulse * 0.5f, pulse * 0.3f}, local[3] = {5, -4, -1};
                for (int k = 3; k <= 8; ++k) {
                    bone(c, k, local, p);
                    wv_sprite(i, 0x7ef7, p, pulse / 1.0f, light, l);
                }
            }
            break;
        default: break;
        }
    } else {
        switch (t) {
        case 0x39:
            if (rnd(c) % 3 == 0) {
                later_particle(o, i, 0x8016, 5, p, white, scale, 0, l);
                later_particle(o, i, 0x7f5a, 21, p, white, scale, 0, l);
            }
            break;
        case 0x47:
            if (rnd(c) % 3 == 0) later_particle(o, i, 0x8016, 5, p, white, scale, 0, l);
            break;
        case 0x48:
            if (rnd(c) % 6 == 0) {
                const float light[3] = {0.03f, 0.03f, 0.03f};
                p[2] += 50.0f;
                later_particle(o, i, 0x7f5a, 49, p, light, scale, 0, l);
            }
            break;
        case 0x4a:
            if (rnd(c) % 3 == 0) later_particle(o, i, 0x7f5a, 21, p, white, scale * 2.0f, 0, l);
            break;
        case 0x4d: case 0x4e:
            if (rnd(c) % 6 == 0) {
                const float light[3] = {t == 0x4d ? 0.04f : 0.03f, t == 0x4d ? 0.06f : 0.03f,
                                         t == 0x4d ? 0.03f : 0.05f};
                later_particle(o, i, 0x7f89, 20, p, light, scale, 1, l);
            }
            break;
        case 0x63: case 0x64: case 0x65: case 0x66: case 0x67:
            if (rnd(c) % 50 == 0) {
                const int32_t sub = t == 0x63 ? 26 : t == 0x64 ? 16 : t == 0x65 ? 17 : t == 0x66 ? 24 : 25;
                mu_obj_set_f32(o, MU_OBJF_LIGHT, 1.0f);
                mu_obj_set_f32(o, MU_OBJF_LIGHT + 4, 0.65f);
                mu_obj_set_f32(o, MU_OBJF_LIGHT + 8, 0.0f);
                uint32_t a[13] = {0x7f7d};
                memcpy(a + 1, p, 12); memcpy(a + 4, p, 12); memcpy(a + 7, o + MU_OBJF_ANGLE, 12);
                a[10] = (uint32_t)sub; a[11] = 1; a[12] = wv_bits(scale);
                wv_emit(l, MU_ICARUS_JOINT, i, a, 13);
            }
            break;
        default: break;
        }
    }
    return 1;
}
