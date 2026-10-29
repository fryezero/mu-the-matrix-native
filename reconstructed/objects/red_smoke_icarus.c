/* Red Smoke Icarus, world 132 (0x84), vtable 0x01aa8ff4. Create 0x00e00b4a, move 0x00e00cfe, visual 0x00e00e97;
 * world predicate 0x00e0558b. */
#include "worlds_r.h"
#include "worlds_b_internal.h"
#include "world_visual_internal.h"
int mu_red_smoke_icarus_create(uint8_t *o, int32_t world)
{
    if (world != 0x84 || !o)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 0x1e) {   /* the sky plate */
        mu_obj_set_f32(o, MU_OBJF_POSITION + 8, -1600.0f);
        mu_obj_set_f32(o, 0xcc, -3000.0f);
        mu_obj_set_f32(o, MU_OBJF_SCALE, 3.25f);
        mu_obj_set_f32(o, MU_OBJF_ANGLE + 8, 340.0f);
        mu_obj_set_f32(o, MU_OBJF_RANGE, -30000.0f);
    } else if (t >= 6 && t <= 0x3c && t != 0xb && !(t >= 0x17 && t <= 0x1c) && !(t >= 0x2c && t <= 0x2e)) {
        o[MU_OBJF_AFTER_CHARACTER] = 1;   /* jump table 0x00e00c22 */
    }
    return 1;
}

int mu_red_smoke_icarus_move(const uint8_t *o, int32_t world, int has_model)
{
    return world == 0x84 && o && has_model;
}

int mu_red_smoke_icarus_visual(uint8_t *o, int32_t i, int present, mu_world_bone_fn bone, void *c, mu_obj_log *log)
{
    if (!o || !present)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t >= 0 && t <= 4) {   /* one burst of red smoke, then the emitter hides */
        if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2) {
            const float light[3] = {0.05f, 0.02f, 0.01f};
            const int32_t count = t < 3 ? 20 : 10;
            for (int32_t k = 0; k < count; ++k)
                wv_particle(o, i, 0x7f89, t, light, 1, log);
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        }
    } else if (t == 0xa && bone) {
        const float zero[3] = {0, 0, 0}, light[3] = {1, 1, 1};
        float pos[3], angle[3];
        bone(c, 3, zero, pos);
        wb_get(o, MU_OBJF_ANGLE, angle);
        mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
        wb_arg(e, 0x7ef7); wb_vec(e, pos); wb_vec(e, angle); wb_vec(e, light);
        wb_arg(e, 0); wb_float(e, 1.0f); wb_arg(e, 0);
    }
    return 1;
}
