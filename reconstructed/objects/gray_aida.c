/* Gray Aida, world 134 (0x86), vtable 0x01aa6908. Create 0x00d84821, move 0x00d849e4, visual 0x00d84dd8;
 * world predicate 0x00d8b139. */
#include "worlds_r.h"
#include "worlds_b_internal.h"
#include "world_visual_internal.h"
#include "charsel_world.h"
int mu_gray_aida_create(uint8_t *o, int32_t world)
{
    if (world != 0x86 || !o)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x24: case 0x3b: case 0x3e:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -50.0f);
        break;
    case 0x1f: case 0x2a: case 0x85:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -80.0f);
        break;
    case 4: case 6: case 7: case 8: case 9: case 0x10: case 0x11: case 0x13: case 0x16: case 0x18: case 0x21:
    case 0x22: case 0x23: case 0x2e: case 0x37: case 0x5c: case 0x6d:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -150.0f);
        break;
    case 0:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -150.0f);
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 0x19: case 0x29: case 0x4f: case 0x50: case 0x51: case 0x52: case 0x53:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    default:
        break;
    }
    return 1;
}

static void ga_turn(uint8_t *o, float step)
{
    mu_obj_set_f32(o, MU_OBJF_ANGLE + 4, mu_obj_f32(o, MU_OBJF_ANGLE + 4) + step);
}
int mu_gray_aida_move(uint8_t *o, int32_t i, int32_t world, mu_obj_rand_fn rnd, void *c, mu_obj_log *log)
{
    if (world != 0x86 || !o)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x19: case 0x1c:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.015f);
        break;
    case 0x29:
        mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.5f);
        break;
    case 0x38: case 0x39: case 0x3a: case 0x43: case 0x46:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    case 0x3f: {
        const float s = (float)(rnd(c) % 5) * 0.01f;
        wb_light(log, i, o, s + 0.4f, s + 0.6f, s + 0.4f, 2);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    }
    case 0x40:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.05f);
        break;
    case 0x48:
        ga_turn(o, 10.0f);
        break;
    case 0x49:
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        ga_turn(o, 5.0f);
        mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.6f);
        break;
    case 0x4a:
        mu_obj_set_f32(o, MU_OBJF_ALPHA, 1.0f);
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        ga_turn(o, 10.0f);
        break;
    default:
        break;
    }
    return 1;
}

/* Bones of the two statues (types 0x1e, 0x47), their local points and the large flare scales. */
static const int32_t ga_bones[6] = {6, 7, 8, 12, 13, 17};
static const float ga_local[6][3] = {{0, -3, 1}, {0, -3, 0}, {0, -3, 0}, {-3, -1, 0}, {-3, -3, 0}, {0, 2, -8}};
static const float ga_scale_1e[6] = {5.5f, 4.5f, 4.0f, 4.5f, 4.0f, 4.0f};
static const float ga_scale_47[6] = {6.0f, 5.5f, 5.0f, 5.5f, 5.0f, 5.0f};
/* Two TransformPosition flares per bone: the large one (first bone's light, then the others'), a dim one at 3. */
static void ga_eyes(int32_t i, const float *scale, const float first[3], const float rest[3], const float dim[3],
                    mu_world_bone_fn bone, void *c, mu_obj_log *log)
{
    for (int k = 0; k < 6; ++k) {
        float pos[3];
        bone(c, ga_bones[k], ga_local[k], pos);
        wv_sprite(i, 0x7f26, pos, scale[k], k ? rest : first, log);
        wv_sprite(i, 0x7f26, pos, 3.0f, dim, log);
    }
}
static void ga_burst(uint8_t *o, int32_t i, const float light[3], mu_obj_log *log)
{
    if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2)
        for (int k = 0; k < 10; ++k)
            wv_particle(o, i, 0x7f89, 0x1a, light, 1, log);
    mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
}
static void ga_effect(mu_obj_log *log, uint32_t call, int32_t i, const uint8_t *o, uint32_t type, const float light[3],
                      uint32_t sub)
{
    float pos[3], angle[3];
    wb_get(o, MU_OBJF_POSITION, pos); wb_get(o, MU_OBJF_ANGLE, angle);
    mu_obj_event *e = wb_event(log, call, i);
    wb_arg(e, type); wb_vec(e, pos); wb_vec(e, angle); wb_vec(e, light);
    wb_arg(e, sub); wb_arg(e, 1);
    if (call == MU_OBJ_CALL_EFFECT)
        wb_float(e, 0.0f);
    else
        wb_arg(e, (uint16_t)wb_int(mu_obj_f32(o, MU_OBJF_SCALE)));
}
/* RenderMesh 0x00966e4a(0, 2, alpha, blend mesh, blend light, u, v, -1) with the model streaming mesh 0. */
static void ga_mesh(const uint8_t *o, int32_t i, float u, mu_obj_log *log)
{
    wb_arg(wb_event(log, MU_WR_STREAM, i), 0);
    wv_mesh(o, i, 0, 2, mu_obj_i32(o, MU_OBJF_BLEND_MESH), mu_obj_f32(o, MU_OBJF_BLEND_LIGHT), u,
            mu_obj_f32(o, MU_OBJF_BLEND_V), log);
    wb_arg(wb_event(log, MU_WR_STREAM, i), 0xff);
}
int mu_gray_aida_visual(uint8_t *o, int32_t i, int present, float time, mu_obj_rand_fn rnd, mu_world_bone_fn bone,
                        void *c, mu_obj_log *log)
{
    if (!o || !present)
        return 0;
    const float one[3] = {1, 1, 1};
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x1e:
        if (bone) {
            const float glow[3] = {0.1f, 0.1f, 0.3f}, dim[3] = {0.15f, 0.15f, 0.15f};
            ga_eyes(i, ga_scale_1e, glow, glow, dim, bone, c, log);
        }
        break;
    case 0x47:
        if (bone) {
            const float first[3] = {0.5f, 0, 0}, rest[3] = {0.25f, 0, 0}, dim[3] = {0.15f, 0, 0};
            ga_eyes(i, ga_scale_47, first, rest, dim, bone, c, log);
        }
        break;
    case 0x38:
        if (rnd(c) % 2 == 0)
            wv_particle(o, i, 0x801f, 2, one, 0, log);
        break;
    case 0x39:
        wv_particle(o, i, 0x801c, 8, one, 0, log);
        break;
    case 0x3a:
        if (rnd(c) % 3 == 0)
            wv_particle(o, i, 0x801b, 2, one, 0, log);
        break;
    case 0x3b: {
        const float light[3] = {0.01f, 0.03f, 0.05f};
        ga_burst(o, i, light, log);
        break;
    }
    case 0x3e: case 0x5c: {
        const float light[3] = {0.06f, 0.06f, 0.06f};
        ga_burst(o, i, light, log);
        break;
    }
    case 0x3c: {
        const int32_t t = wb_int(time) % 1024;
        if (t >= 0 && t < 10)
            ga_effect(log, MU_OBJ_CALL_EFFECT, i, o, 0x193, one, 3);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    }
    case 0x41: case 0x42: case 0x84: case 0x85:
        ga_mesh(o, i, wb_scroll(time, 100000, 0.00005f), log);
        break;
    case 0x4d: case 0x4e:
        ga_mesh(o, i, (float)(wb_int(time) % 100000) * 0.0002f, log);
        break;
    case 0x43: {
        const float light[3] = {0.3f, 0.3f, 0.3f};
        memcpy(o + MU_OBJF_LIGHT, light, sizeof light);
        wv_particle(o, i, 0x7f42, 6, light, 0, log);
        break;
    }
    case 0x46: {
        const int32_t t = wb_int(time) % 1024;
        if (rnd(c) % 5 == 1 && t >= 0 && t < 30) {
            const float light[3] = {0.1f, 0.1f, 0.1f};
            ga_effect(log, MU_WR_EFFECT_SCALED, i, o, 0x199, light, 0);
        }
        break;
    }
    case 0x49: case 0x4a: {
        const float r = (float)sin((double)(time * 0.0011f)) * 0.2f;
        const float g = (float)sin((double)(time * 0.0017f)) * 0.2f;
        const float b = (float)sin((double)(time * 0.0013f)) * 0.2f;
        const float light[3] = {r + 0.2f, g + 0.2f, b + 0.2f}, half[3] = {0.5f, 0.5f, 0.5f};
        memcpy(o + MU_OBJF_LIGHT, light, sizeof light);
        float pos[3], angle[3];
        wb_get(o, MU_OBJF_POSITION, pos); wb_get(o, MU_OBJF_ANGLE, angle);
        mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
        wb_arg(e, 0x7f26); wb_vec(e, pos); wb_vec(e, angle); wb_vec(e, half);
        wb_arg(e, 2); wb_float(e, 1.3f); wb_arg(e, 0);
        break;
    }
    default:
        break;
    }
    return 1;
}
