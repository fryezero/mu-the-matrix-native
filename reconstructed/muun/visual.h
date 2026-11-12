#ifndef MU_MUUN_VISUAL_H
#define MU_MUUN_VISUAL_H
#include <stdint.h>

/* MUUN-VISUAL-001, client-muun.md. Base slot only; auxiliary attack/command classes are excluded. */
typedef struct mu_mv_info {
    int32_t code, item;
    float scale, offset[3], speed[5];
} mu_mv_info;

typedef struct mu_mv_owner {
    int32_t key;
    uint8_t live, moving;
    float position[3], angle[3];
} mu_mv_owner;

typedef struct mu_mv_state {
    int32_t model, key, state;
    uint16_t action, prior_action;
    float scale, radius, frame, prior_frame;
    float position[3], angle[3], offset[3], target[3];
    float step[3], acceleration[3], velocity[3], force[3], delta[3];
} mu_mv_state;

/* 0x009a9516: after a fresh slot/OBJECT constructor, before bounds/auxiliary/effect calls. */
void mu_mv_setup(mu_mv_state *s, const mu_mv_info *info, const mu_mv_owner *owner);
/* 0x009a9e29. keys is the current action's key count; rand_value is used only in idle. Returns requested action,
 * or -1. The caller implements SetAction and the model getter, as the original does. */
int32_t mu_mv_select(mu_mv_state *s, const mu_mv_info *info, const mu_mv_owner *owner, int32_t keys,
                     int32_t rand_value);
/* 0x009aafd4: three-component damped move. velocity (+0x54) is read, not overwritten. */
void mu_mv_spring(mu_mv_state *s, const float from[3], const float target[3], float out[3]);
/* 0x009aa268: target selection and chase heading/move, uses the already verified movement angle helpers. */
void mu_mv_follow(mu_mv_state *s, const mu_mv_info *info, const mu_mv_owner *owner);
/* Base lifetime/visibility caller gates, 0x009a99a9 and 0x009a9ae2, no auxiliary slot exception. */
int mu_mv_alive(int has_object, int has_owner_object, int object_live, int scene, int owner_live, int owner_kind);
int mu_mv_visible(int has_object, int object_live, int frustum, int32_t key, int32_t owner_key);
#endif
