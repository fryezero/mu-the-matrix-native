#ifndef MU_MUUN_SECONDARY_H
#define MU_MUUN_SECONDARY_H
#include <stdint.h>
/* Kind-1 visual-only helpers. The fixture supplies selection/owner flags explicitly. */
int32_t mu_mv_riding_action(int32_t owner_action);
float mu_mv_riding_scale(int32_t model);
float mu_mv_riding_speed(int32_t model, int32_t action);
int mu_mv_riding_admit(int has_owner, int hidden, int has_object, int live, int buff26,
                     int32_t selected_item, int32_t record_item, int predicate);
/* 0x009bf820: named bone's local zero point, scaled once. No shared-bone fallback. */
void mu_mv_riding_attachment(const float matrix[12], float scale, float out[3]);
#endif
