#include "world_visual_internal.h"
/* 0x00e31ab1..0x00e31b11. */
int mu_elbeland_defer(uint8_t *o)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 2:
    case 0x35:
    case 0x37:
    case 0x6e:
    case 0x59:
    case 0x4e:
    case 0x4f:
    case 0x7d:
    case 0x80:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    default:
        return 0;
    }
}
/* 0x00e321bb's deferred mesh/body branches. Bone sprites of 78/79 are
 * emitted separately once the native object has been posed. */
int mu_elbeland_after(uint8_t *o, int32_t i, float time, mu_obj_log *l)
{
    (void)time;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE), b = mu_obj_i32(o, MU_OBJF_BLEND_MESH);
    const float light = mu_obj_f32(o, MU_OBJF_BLEND_LIGHT), u = mu_obj_f32(o, MU_OBJF_BLEND_U),
                v = mu_obj_f32(o, MU_OBJF_BLEND_V);
    switch (t) {
    case 2:
    case 0x35:
    case 0x37:
    case 0x59:
    case 0x7d:
    case 0x80:
        wv_body(o, i, l);
        break;
    case 0x6e:
        wv_mesh(o, i, 2, 0x242, b, light, 0, 0, l);
        wv_mesh(o, i, 1, 0x42, b, light, 0, 0, l);
        wv_mesh(o, i, 0, 0x42, b, light, 0, 0, l);
        break;
    case 0x4e:
    case 0x4f:
        wv_mesh(o, i, 0, 2, b, light, u, v, l);
        wv_mesh(o, i, 0, 0x42, b, light, u, v, l);
        break;
    default:
        return MU_OBJ_UNSUPPORTED;
    }
    return MU_OBJ_OK;
}

void mu_elbeland_after_sprites(const uint8_t *o, int32_t i, mu_world_bone_fn bone, void *c, mu_obj_log *l)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (!bone || (t != 0x4e && t != 0x4f))
        return;
    const float local[3] = {0, 0, 0}, light[3] = {0.1f, 0.1f, 0.3f};
    for (int32_t k = 1; k <= (t == 0x4e ? 4 : 6); ++k) {
        float pos[3];
        bone(c, k, local, pos);
        wv_sprite(i, 0x7f26, pos, 5.5f, light, l);
    }
}
