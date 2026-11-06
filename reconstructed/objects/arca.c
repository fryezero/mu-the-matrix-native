/* Arca War class 0x01aa6154, worlds 92, 96, 101 and 111 (on Acheron, Debenter, Uruk Mountain and Nars).
 * Create 0x00d7bd7d, move 0x00d7be29, visual 0x00d7be80; base world 0x00d7b225; own types 0x00d7b373. */
#include "worlds_s2.h"
#include "charsel_world.h"
#include "worlds_b_internal.h"
/* Light table at handler +0x40, six f32[3] entries set by the constructor 0x00d7a185. */
static const float stage_light[MU_ARCA_STAGES][3] = {
    {1.0f, 0.37f, 0.66f}, {1.0f, 0.37f, 0.66f}, {0.58f, 1.0f, 0.86f},
    {0.08f, 1.0f, 0.86f}, {0.6f, 0.9f, 0.95f}, {0.88f, 0.4f, 0.86f}};
#define ARCA_TYPE 0x59b
static const float zero3[3] = {0.0f, 0.0f, 0.0f};

/* 0x00d806b0: the world is one of the class's registered worlds (handler +8). */
int mu_arca_world(int32_t world) { return world == 92 || world == 96 || world == 101 || world == 111; }
int32_t mu_arca_base_world(int32_t world) { return mu_arca_world(world) ? world - 1 : -1; }
int32_t mu_arca_type_index(int32_t type) { return type >= 0x88a && type <= 0x88e ? type - 0x889 : 0; }

static int forwarded(int r) { return r < 0 ? -1 : (uint8_t)r != 0; }
int mu_arca_create(uint8_t *o, int32_t world, int32_t base_world, mu_arca_forward_fn forward, void *context)
{
    if (!mu_arca_world(world) || base_world == -1) return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (mu_arca_type_index(type) > 0 || type == ARCA_TYPE) {
        mu_obj_set_f32(o, MU_OBJF_SCALE, 0.85f);
        return 1;
    }
    return forwarded(forward(context, MU_ARCA_CREATE_SLOT, base_world));
}
int mu_arca_move(int32_t world, int32_t base_world, mu_arca_forward_fn forward, void *context)
{
    if (!mu_arca_world(world)) return 0;
    return forwarded(forward(context, MU_ARCA_MOVE_SLOT, base_world));
}
int mu_arca_visual_bones(int32_t type) { return type == ARCA_TYPE ? 3 : -1; }
int mu_arca_visual(const uint8_t *o, int32_t i, int32_t world, int32_t base_world, int32_t stage, mu_world_bone_fn bone,
                   void *bone_context, mu_arca_forward_fn forward, void *context, mu_obj_log *log)
{
    if (!mu_arca_world(world)) return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (type == ARCA_TYPE) {
        if (!bone || stage < 0 || stage >= MU_ARCA_STAGES) return -1;
        float p[3], a[3];
        bone(bone_context, 3, zero3, p);
        wb_get(o, MU_OBJF_ANGLE, a);
        mu_obj_event *e = wb_event(log, MU_OBJ_CALL_EFFECT, i);
        wb_arg(e, 0x413); wb_vec(e, p); wb_vec(e, a); wb_vec(e, stage_light[stage]);
        wb_arg(e, stage < 4 ? 10 : 11); wb_arg(e, 0); wb_float(e, mu_obj_f32(o, MU_OBJF_SCALE) * 1.0f);
        return 1;
    }
    if (mu_arca_type_index(type)) return 1;
    return forwarded(forward(context, MU_ARCA_VISUAL_SLOT, base_world));
}
