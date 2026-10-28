/* Karutan handler slot 0x34, 0x00e1409c..0x00e14277, brazier 113. */
#include "world_visual_internal.h"
#include <math.h>
int mu_karutan_flames(const uint8_t *o, int32_t i, mu_obj_rand_fn rnd, void *c, mu_obj_log *l)
{
    if (mu_obj_i32(o, MU_OBJF_TYPE) != 0x71)
        return MU_OBJ_UNSUPPORTED;
    float pos[3];
    memcpy(pos, o + MU_OBJF_POSITION, 12);
    const float warm[3] = {1, 0.2f, 0}, white[3] = {1, 1, 1};
    wv_sprite(i, 0x7ef7, pos, 2.0f * mu_obj_f32(o, MU_OBJF_SCALE), warm, l);
    const int32_t choice = rnd(c) % 3;
    if (choice == 0)
        wv_particle(o, i, 0x8084, 0, white, 0, l);
    else if (choice == 1)
        wv_particle(o, i, 0x806e, 4, white, 0, l);
    else if (choice == 2)
        wv_particle(o, i, 0x8085, 0, white, 0, l);
    return MU_OBJ_OK;
}

/* Slot 0x38 0x00e146ce; 66 also changes action above frame 35, outside this flag slice. */
int mu_karutan_defer(uint8_t *o)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 1:
    case 3:
    case 0x36:
    case 0x37:
    case 0x38:
    case 0x39:
    case 0x3a:
    case 0x3e:
    case 0x3f:
    case 0x42:
    case 0x77:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    default:
        return 0;
    }
}
int mu_karutan_after(uint8_t *o, int32_t i, float time, mu_obj_log *l)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float light = mu_obj_f32(o, MU_OBJF_BLEND_LIGHT), u = mu_obj_f32(o, MU_OBJF_BLEND_U),
                v = mu_obj_f32(o, MU_OBJF_BLEND_V);
    const int32_t b = mu_obj_i32(o, MU_OBJF_BLEND_MESH);
    switch (t) {
    case 3:
    case 0x38:
    case 0x3e:
        wv_body(o, i, l);
        break;
    case 1:
        for (int k = 1; k <= 3; ++k)
            wv_mesh(o, i, k, 2, b, light, 0, 0, l);
        wv_mesh(o, i, 0, 0x42, b, light, 0, 0, l);
        break;
    case 0x36: {
        const float pulse = ((float)sin((double)(time * 0.002f)) + 0.5f) * 0.5f + 1.0f;
        wv_mesh(o, i, 0, 0x42, 0, pulse, 0, 0, l);
        break;
    }
    case 0x3a:
    case 0x3f:
    case 0x77: {
        const float pulse = ((float)sin((double)(time * 0.001f)) + 1.0f) * 0.5f;
        if (t == 0x3f)
            wv_mesh(o, i, 0, 0x42, 0, light, 0, 0, l);
        else
            wv_mesh(o, i, 0, 2, b, light, 0, 0, l);
        if (t == 0x77) {
            wv_mesh(o, i, 1, 0x42, 1, pulse, 0, 0, l);
            break;
        }
        wv_mesh(o, i, 1, t == 0x3f ? 2u : 0x42u, t == 0x3f ? b : 1, t == 0x3f ? light : pulse, 0, 0, l);
        if (t == 0x3a) {
            wv_mesh(o, i, 3, 2, b, light, 0, 0, l);
            wv_mesh(o, i, 2, 0x42, b, light, 0, 0, l);
        } else {
            wv_mesh(o, i, 2, 0x42, 2, pulse, 0, 0, l);
            wv_mesh(o, i, 3, 2, b, light, 0, 0, l);
        }
        break;
    }
    case 0x42:
        wv_mesh(o, i, 0, 2, b, light, 0, 0, l);
        wv_mesh(o, i, 1, 0x42, b, light, 0, 0, l);
        break;
    case 0x37:
    case 0x39:
        wv_mesh(o, i, 0, 0x42, b, light, u, (float)((int32_t)time % 10000) * 0.0001f, l);
        break;
    default:
        return MU_OBJ_UNSUPPORTED;
    }
    (void)v;
    return MU_OBJ_OK;
}
