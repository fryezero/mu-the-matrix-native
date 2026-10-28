#include "world_visual_internal.h"
#include <math.h>
/* Slot 0x38: flag-writing branches 0x00e95c89..0x00e964d3. */
int mu_raklion_defer(uint8_t *o)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x2e:
    case 0x35:
    case 0x4c:
    case 0x53:
    case 0x59:
    case 0x5c:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    default:
        return 0;
    }
}
/* Slot 0x3c 0x00e96536. */
int mu_raklion_after(uint8_t *o, int32_t i, float time, mu_obj_log *l)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE), b = mu_obj_i32(o, MU_OBJF_BLEND_MESH);
    const float light = mu_obj_f32(o, MU_OBJF_BLEND_LIGHT), u = mu_obj_f32(o, MU_OBJF_BLEND_U),
                v = mu_obj_f32(o, MU_OBJF_BLEND_V);
    if (t == 0x4c) {
        const float rates[3] = {0.002f, 0.0015f, 0.0014f};
        for (int q = 0; q < 3; ++q)
            mu_obj_set_f32(o, MU_OBJF_LIGHT + (uint32_t)q * 4,
                           (float)sin((double)(time * rates[q])) * 0.2f + 0.5f);
        wv_body(o, i, l);
    } else if (t == 0x2e || t == 0x35)
        wv_body(o, i, l);
    else if (t == 0x53)
        wv_mesh(o, i, 4, 0x42, 4, light, u, v, l);
    else if (t == 0x59)
        wv_mesh(o, i, 0, 0x42, 0, light, u, v, l);
    else if (t == 0x5c)
        wv_mesh(o, i, 1, 0x42, 1, light, u, v, l);
    else
        return MU_OBJ_UNSUPPORTED;
    (void)b;
    return MU_OBJ_OK;
}

/* The meshes left in slot 0x38 before its after-character flag is set. */
int mu_raklion_before(const uint8_t *o, int32_t i, mu_obj_log *l)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE), b = mu_obj_i32(o, MU_OBJF_BLEND_MESH);
    const float light = mu_obj_f32(o, MU_OBJF_BLEND_LIGHT), u = mu_obj_f32(o, MU_OBJF_BLEND_U),
                v = mu_obj_f32(o, MU_OBJF_BLEND_V);
    if (t == 0x53) {
        wv_mesh(o, i, 0, 2, b, light, u, v, l);
        wv_mesh(o, i, 1, 2, b, light, u, v, l);
        wv_mesh(o, i, 2, 0x42, 2, light, u, v, l);
        wv_mesh(o, i, 3, 0x42, 3, light, u, v, l);
    } else if (t == 0x5c)
        wv_mesh(o, i, 0, 2, b, light, u, v, l);
    else
        return MU_OBJ_UNSUPPORTED;
    return MU_OBJ_OK;
}
