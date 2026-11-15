#ifndef MU_MUUN_RIDING_H
#define MU_MUUN_RIDING_H
#include <stdint.h>
#include "passes.h"
/* All inputs are authored visual state; no selection, inventory or server feed. */
int mu_mv_rider_lifts(uint16_t action);
void mu_mv_rider_position(const float position[3], const float offset[3], float out[3]);
float mu_mv_owner_fade(int owner_kind, float alpha);
int32_t mu_mv_mount_mode(int has_owner_object, int buff18);
void mu_mv_mount_buff_pass(int32_t blend, float light, float u, float v, mu_mv_pass *out, float uv[2]);
int32_t mu_mv_mount_counter(int32_t counter, int admitted);
typedef struct mu_mv_mount_particle {
    int32_t type, subtype;
    float scale, light[3];
} mu_mv_mount_particle;
/* 0x009bfe13, both particles use a random posed bone's zero point. */
int mu_mv_mount_particles(int32_t model, int32_t random_value, mu_mv_mount_particle out[2]);
/* 0x009c2371 remote transition only. Seconds, caller supplied delta. Returns one expiry request. */
int mu_mv_transition_step(int *remote, float *elapsed, float period, float delta);
#endif
