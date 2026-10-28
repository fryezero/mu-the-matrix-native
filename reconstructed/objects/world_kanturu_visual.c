/* RenderObjectVisual hook 0x00e75089, flame branches only (worlds 37/40). */
#include "world_visual_internal.h"
#include <math.h>
int mu_kanturu_flames(const uint8_t *o, int32_t i, int32_t world, float time, mu_obj_rand_fn rnd,
                      mu_world_bone_fn bone, void *c, mu_obj_log *l)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float white[3] = {1, 1, 1};
    if (world != 0x25 && world != 0x28)
        return MU_OBJ_UNSUPPORTED;
    switch (t) {
    case 0x3b:
        if (rnd(c) % 3 == 0)
            wv_particle(o, i, 0x7f5a, 21, white, 0, l);
        break;
    case 0x3d:
        if (rnd(c) % 3 == 0)
            wv_particle(o, i, 0x8016, 0, white, 0, l);
        break;
    case 0x46: {
        if (!bone)
            return MU_OBJ_SKIPPED;
        float pos[3], zero[3] = {0, 0, 0};
        bone(c, 6, zero, pos);
        const float pulse = (float)sin((double)(time * 0.002f)) + 1.8f;
        const float warm[3] = {0.8f, 0.4f, 0.2f}, soft[3] = {0.65f, 0.65f, 0.65f};
        wv_sprite(i, 0x7f26, pos, pulse * 7.0f, warm, l);
        wv_sprite(i, 0x7f26, pos, pulse * 4.0f, soft, l);
        break;
    }
    default:
        return MU_OBJ_UNSUPPORTED;
    }
    return MU_OBJ_OK;
}
