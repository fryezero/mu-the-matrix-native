#include "riding.h"
int mu_mv_rider_lifts(uint16_t a)
{
    return (a >= 0x26 && a < 0x32) || (a >= 0x47 && a < 0x4f) ||
           (a >= 0x67 && a < 0x6f) || (a >= 0x118 && a < 0x133) ||
           (a >= 0x13b && a < 0x142);
}
void mu_mv_rider_position(const float position[3], const float offset[3], float out[3])
{
    for (int k = 0; k < 3; ++k) out[k] = position[k] + offset[k];
}
/* Called after the existing FadeAlpha consumer, as in 0x009bf225. No clamp in the original. */
float mu_mv_owner_fade(int owner_kind, float alpha)
{
    if (owner_kind == 2 && alpha != 0.0f) alpha = alpha - 0.1f;
    return alpha;
}
int32_t mu_mv_mount_mode(int has_owner_object, int buff18)
{
    return has_owner_object && buff18 == 1 ? 10 : 0;
}
int32_t mu_mv_mount_counter(int32_t counter, int admitted)
{
    if (!admitted) return 0;
    counter = (int32_t)((uint32_t)counter + 1u);
    return counter > 100 ? 25 : counter;
}
int mu_mv_mount_particles(int32_t model, int32_t random_value, mu_mv_mount_particle out[2])
{
    if (model < 0x5cb || model > 0x5d2) return 0;
    out[0].type = 0x8081 + random_value % 2;
    out[0].subtype = 1;
    out[0].scale = 1.0f;
    out[1].type = 0x7ef7;
    out[1].subtype = 19;
    out[1].scale = 3.5f;
    if (model <= 0x5cc) {
        out[0].light[0] = 0.9f; out[0].light[1] = 0.1f; out[0].light[2] = 0.1f;
        out[1].light[0] = 0.9f; out[1].light[1] = 0.1f; out[1].light[2] = 0.1f;
    } else {
        out[0].light[0] = model <= 0x5ce ? 1.0f : (model <= 0x5d0 ? 0.9f : 1.0f);
        out[0].light[1] = model <= 0x5ce ? 0.98f : (model <= 0x5d0 ? 1.0f : 0.98f);
        out[0].light[2] = 0.65f;
        out[1].light[0] = model <= 0x5ce ? 0.9f : (model <= 0x5d0 ? 1.0f : 0.1f);
        out[1].light[1] = model <= 0x5ce ? 0.1f : (model <= 0x5d0 ? 0.5f : 1.0f);
        out[1].light[2] = model <= 0x5ce ? 0.1f : 0.0f;
    }
    return 2;
}
int mu_mv_transition_step(int *remote, float *elapsed, float period, float delta)
{
    if (*remote != 1) return 0;
    *elapsed = *elapsed + delta;
    if (*elapsed >= period) {
        *remote = 0;
        *elapsed = 0.0f;
        return 1;
    }
    return 0;
}

/* Local owner branch of 0x017f746f. Remote class/team visibility is not authored here. */
void mu_mv_mount_buff_pass(int32_t blend, float light, float u, float v, mu_mv_pass *out, float uv[2])
{
    *out = (mu_mv_pass){.mesh = -1, .flags = 0x4040, .blend = blend, .texture = 0x7fcf,
        .alpha = 0.5f, .light = light, .color = {1.0f, 1.0f, 1.0f}};
    uv[0] = u * 8.0f;
    uv[1] = v * 2.0f;
}
