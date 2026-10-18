#ifndef MU_CLIENT_WORLD_CAMERA_H
#define MU_CLIENT_WORLD_CAMERA_H

/* In-world camera update of the client (MoveMainCamera 0x0185498e) and the
 * mouse-wheel FOV zoom (0x018588d9, 0x0185a9bf). Authored names. Only the
 * ordinary in-world path (scene 6) and the camera-record path of scenes 3
 * and 5 are modelled (not top view, no
 * scripted/tour camera object, not the special worlds listed in
 * docs/research/client-camera-input.md); the world/scene predicates the
 * client evaluates through other subsystems are explicit inputs. */

#include <stdint.h>

#include "client_camera.h"

/* GetTickCount-based timer at 0x0bdc5ed0 {start, duration, done}. */
typedef struct mu_tick_timer {
    uint32_t start, duration;
    uint8_t done;
} mu_tick_timer;

/* 0x018519ff: done ? duration : (start == 0 ? 0 : now - start). */
uint32_t mu_tick_timer_elapsed(const mu_tick_timer *timer, uint32_t now);
/* 0x00c9b4ac: duration 0 -> done; else not done, start on first call,
 * restart and done once now - start exceeds duration (unsigned). */
void mu_tick_timer_update(mu_tick_timer *timer, uint32_t now);

/* 0x0185047d: i >= n -> b; i <= 0 -> a; else a + (float)i*(b-a)/(float)n. */
float mu_camera_lerp_steps(float a, float b, int32_t i, int32_t n);
/* 0x018504c6: constant-deceleration ease from a to b over n units at time t
 * (forward), or the mirrored curve (forward = 0). */
float mu_camera_ease(float a, float b, float t, int32_t n, int forward);

typedef struct mu_world_camera {
    /* inputs from other subsystems */
    int32_t scene;              /* 0x01d1df70 */
    int32_t world;              /* 0x01cf15fc */
    float hero_position[3];     /* Hero + 0x33ac */
    int32_t hero_tile_x, hero_tile_y; /* Hero + 0x180, + 0x184 */
    uint8_t hero_byte4;         /* Hero + 0x4 (compared with 1 for worlds 0x5b/0x5c) */
    uint16_t hero_tile_wall;    /* TerrainWall[tile]: 0x40 water height, 0x80 lift zone */
    float camera_override[3];   /* (+0x15c of the 0x00ec3394 object); zero = follow the hero */
    float world_fov;            /* world info +0xc -> +0x20 */
    float far_scale[3];         /* world info +0xc -> +0x1c, +0xc -> +0x18, info +0x10 */
    uint8_t event_world;        /* 0x00e94004() || 0x00e3068f() */
    uint8_t zoom_object_active; /* 0x009a6ef3 object: 0x0099b3b1() and !byte +0x71 */
    int16_t zoom_object_level;  /* its 0x0099b4c0() result (zoom level 0..5) */
    uint8_t far_2300;           /* (0x009a6ef3()+0x78).0x009a645f() */
    float zoom_level5_distance; /* 0x009a6ef3()->+0x68, distance target for level 5 */
    float water_height;         /* 0x01cf15dc, written as 1201 on water tiles */
    float earthquake;           /* 0x0bdb588c, added to the pitch */
    float world_time;           /* 0x06fce370 (only world 5 sway) */
    /* state */
    float distance;             /* CameraDistance 0x0bdc5ef0 */
    float distance_target;      /* 0x01cf1860 */
    int16_t zoom_level;         /* 0x0bdc5b84 */
    float lift;                 /* 0x0bdc5978 */
    float fov_from, fov_to;     /* 0x01cf1638, 0x01cf163c */
    float angle_start[3];       /* 0x0bdc58fc */
    float angle_end[3];         /* 0x0bdc5908 */
    float position_start[3];    /* 0x0bdc5ac0 */
    float position_end[3];      /* 0x0bdc5acc */
    mu_tick_timer zoom_timer;   /* 0x0bdc5ed0 (done byte = zoom settled) */
    int32_t zoom_index;         /* 0x0bdc5914 */
    /* scenes 3 and 5 (NATIVE-CHARSEL-001): the world camera record's
     * [CAMERA ANGLE] (+0) and [CAMERA POSITION] (+0xc), input */
    float scene_angle[3];
    float scene_position[3];
} mu_world_camera;

/* World entry (0x0185613e first tick): yaw -45, settled zoom, index 2,
 * fov_from = fov_to = world FOV, start = current camera. */
void mu_world_camera_enter(mu_world_camera *camera, mu_client_view *view);

/* MoveMainCamera 0x0185498e, ordinary in-world path. Writes view->fov,
 * view_far, angle[0..1], position; updates the zoom transition and, last,
 * the distance (d += (target - d) / 3), so the position uses the previous
 * frame's distance. Trig: host libm through mu_angle_matrix and sin. */
void mu_move_main_camera(mu_world_camera *camera, mu_client_view *view, uint32_t now);

/* Mouse wheel 0x018588d9 (when allowed and settled) and 0x0185a9bf:
 * delta > 0 zooms in (index - 1), else out; the index is clamped to
 * [min_index, 2] over the FOV table {20, 30, world FOV}; then a 500 ms
 * transition of FOV, pitch (-48.5 - lerp(0,30.8,dFOV,26)) and height
 * (- lerp(0,580,dFOV,26)) starts. min_index is 1 for the hero states the
 * client lists in 0x0185a9bf, else 0. Returns 1 when the zoom changed. */
int mu_world_camera_wheel(mu_world_camera *camera, mu_client_view *view, float delta, int32_t min_index);
/* 0x0185a9bf alone (index already moved). */
void mu_world_camera_apply_zoom(mu_world_camera *camera, mu_client_view *view, int32_t min_index);

#endif
