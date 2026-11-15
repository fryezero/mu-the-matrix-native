#include "special.h"
#include <string.h>
#include <math.h>
int mu_mv_special_admit(int32_t model, int32_t mesh)
{
    return !((model == 0x2b8d && mesh == 1) || (model == 0x2b8e && mesh == 2) ||
             (model == 0x2b90 && mesh == 4));
}
void mu_mv_special_pass(int32_t model, int32_t action, const uint8_t record[300], float delta, float time,
                         float alpha, float light, float *c8, mu_mv_pass *pass, float uv[2])
{
    if ((model == 0x2b7a || model == 0x2b7b) && pass->mesh == 2) {
        float limit;
        memcpy(&limit, record + 0x114, sizeof limit);
        if (action == 2) {
            *c8 = *c8 - delta * 2.5f;
            if (*c8 <= 0.0f) *c8 = 0.0f;
        } else {
            *c8 = *c8 + delta * 0.35f;
            if (*c8 > limit) *c8 = limit;
        }
        pass->alpha = 1.0f;
        pass->light = *c8;
    } else if (model == 0x2b8e && (pass->mesh == 5 || pass->mesh == 6)) {
        int32_t frames = pass->mesh == 5 ? 13 : 15;
        int32_t clock = !isfinite(time) || time >= 2147483648.0f || time < -2147483648.0f
                            ? INT32_MIN : (int32_t)time;
        int32_t frame = (clock % (20 * frames)) / 20;
        uv[0] = (float)(frame % 4) * 0.25f;
        uv[1] = (float)(frame / 4) * 0.25f;
        pass->flags = 0x42;
        pass->blend = pass->mesh;
        pass->alpha = alpha;
        pass->light = light;
        pass->texture = -1;
    }
}
