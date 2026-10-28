/* Raklion handler slots 0x2c/0x30, 0x00e943c0/0x00e94619. */
#include "worlds_b_internal.h"
void mu_raklion_move(uint8_t *o, float time)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 0x16)
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, (float)sin((double)(time * 0.001f)) + 1.0f);
    else if (t == 0x46 || t == 0x50)
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
}
void mu_raklion_create(uint8_t *o, int32_t i, mu_obj_log *log)
{
    if (mu_obj_i32(o, MU_OBJF_TYPE) != 0x1ab)
        return;
    const float dy[3] = {40, 36, 20};
    for (int k = 0; k < 3; ++k) {
        float p[3];
        wb_get(o, MU_OBJF_POSITION, p);
        p[1] -= dy[k];
        p[2] += 520;
        mu_obj_event *e = wb_event(log, MU_OBJ_CALL_CREATE_EFFECT, i);
        wb_arg(e, (uint32_t)(0x1ab + k));
        wb_vec(e, p);
        /* Match CreateObject's effect convention: angle/light offsets, then ten
         * tail words. */
        wb_arg(e, MU_OBJF_ANGLE);
        wb_arg(e, MU_OBJF_LIGHT);
        wb_arg(e, 1);
        wb_arg(e, 0);
        wb_arg(e, 0xffffffffu);
        wb_arg(e, 0);
        wb_arg(e, 0);
        wb_arg(e, 0);
        wb_arg(e, 0);
        wb_arg(e, 0xffffffffu);
        wb_arg(e, 0);
        wb_arg(e, 0);
    }
}
/* AccessModels 0x0183f710..0x0183fa87. */
int32_t mu_raklion_records(int32_t world, mu_object_record *r)
{
    for (int k = 0; k < 2; ++k)
        mu_objects_record_init(&r[k]);
    if (world == 57) {
        r[0].type = 424;
        r[0].position[0] = 16200;
        r[0].position[1] = 8300;
        r[0].angle[2] = 35;
        r[1].type = 427;
        r[1].position[0] = 17100;
        r[1].position[1] = 2400;
        r[1].angle[2] = 80;
    } else {
        r[0].type = 427;
        r[0].position[0] = 16900;
        r[0].position[1] = 2400;
        r[0].angle[2] = 85;
        r[1] = r[0];
        r[1].position[0] = 17000;
    }
    return 2;
}
