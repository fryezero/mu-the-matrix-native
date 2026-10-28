/* MoveObject world 2: 0x017fffda..0x018006dd. */
#include "../movement/client_movement.h"
#include "worlds_b_internal.h"
void mu_devias_move(uint8_t *o, int32_t i, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 0x4e:
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, (float)(in->rand_fn(in->context) % 4 + 4) * 0.1f);
        break;
    case 0x1e: {
        float p[3];
        wb_get(o, MU_OBJF_POSITION, p);
        p[2] += 160.0f;
        wb_particle(log, i, o, 0x8016, p, 0, mu_obj_f32(o, MU_OBJF_SCALE));
        wb_particle(log, i, o, 0x7f5a, p, 0x15, (float)(in->rand_fn(in->context) % 9) * 0.1f + 0.5f);
        break;
    }
    case 0x42:
        mu_obj_create_fire(0, o, i, 0, 0, 50, in->rand_fn, in->context, log);
        break;
    case 0x14:
    case 0x41:
    case 0x56:
    case 0x58: {
        if (in->bounds_mode)
            break;
        const float dx = in->hero[0] - mu_obj_f32(o, 0x17c), dy = in->hero[1] - mu_obj_f32(o, 0x180);
        float sum = dx * dx;
        sum = sum + dy * dy;
        const float distance = (float)sqrt((double)sum);
        if (200.0f > distance) {
            const float az = mu_obj_f32(o, (t == 0x56 ? MU_OBJF_ANGLE : MU_OBJF_HEAD_ANGLE) + 8);
            const float delta = (200.0f - distance) * (t == 0x56 ? 2.0f : 0.5f);
            if (t == 0x56) {
                if (az == 90.0f)
                    mu_obj_set_f32(o, MU_OBJF_POSITION + 4, mu_obj_f32(o, 0x180) + delta);
                if (az == 270.0f)
                    mu_obj_set_f32(o, MU_OBJF_POSITION + 4, mu_obj_f32(o, 0x180) - delta);
                if (az == 0.0f)
                    mu_obj_set_f32(o, MU_OBJF_POSITION, mu_obj_f32(o, 0x17c) + delta);
                if (az == 180.0f)
                    mu_obj_set_f32(o, MU_OBJF_POSITION, mu_obj_f32(o, 0x17c) - delta);
                wb_sound(log, i, 0x12, 0, 0);
            } else {
                if (az == 90.0f)
                    mu_obj_set_f32(o, MU_OBJF_ANGLE + 8, 30.0f - delta);
                if (az == 270.0f)
                    mu_obj_set_f32(o, MU_OBJF_ANGLE + 8, delta + 330.0f);
                if (az == 0.0f)
                    mu_obj_set_f32(o, MU_OBJF_ANGLE + 8, 300.0f - delta);
                if (az == 180.0f)
                    mu_obj_set_f32(o, MU_OBJF_ANGLE + 8, delta + 240.0f);
                wb_sound(log, i, 0x11, 0, 0);
            }
        } else {
            mu_obj_set_f32(
                o, MU_OBJF_ANGLE + 8,
                mu_turn_angle2(mu_obj_f32(o, MU_OBJF_ANGLE + 8), mu_obj_f32(o, MU_OBJF_HEAD_ANGLE + 8), 10.0f));
            for (uint32_t k = 0; k < 8; k += 4) {
                const float p = mu_obj_f32(o, MU_OBJF_POSITION + k);
                mu_obj_set_f32(o, MU_OBJF_POSITION + k, (mu_obj_f32(o, 0x17c + k) - p) * 0.2f + p);
            }
        }
        break;
    }
    default:
        break;
    }
}
/* AccessModels world 2, 0x018394d3..0x01839797. */
int32_t mu_devias_records(mu_object_record *r)
{
    for (int k = 0; k < 3; ++k)
        mu_objects_record_init(&r[k]);
    r[0].type = 422;
    r[0].position[0] = 19100;
    r[0].position[1] = 1600;
    r[0].position[2] = 270;
    r[1].type = 423;
    r[1].position[0] = 19100;
    r[1].position[1] = 1700;
    r[1].position[2] = 270;
    r[2].type = 424;
    r[2].position[0] = 5350;
    r[2].position[1] = 9220;
    r[2].angle[2] = 10;
    return 3;
}
