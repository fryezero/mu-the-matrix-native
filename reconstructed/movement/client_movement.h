#ifndef MU_CLIENT_MOVEMENT_H
#define MU_CLIENT_MOVEMENT_H

/* Hero movement of the client (NATIVE-WORLD-001, docs/research/native-world.md).
 * Authored names; addresses are the original routines in the pinned restored
 * text. Every client operation is binary32 SSE unless noted: build with
 * -ffp-contract=off. x87 returns (fld/fstp dword) round to binary32, which the
 * float return types reproduce.
 *
 * Character fields (CHARACTER c, its OBJECT o at c + 0x3254):
 *   c + 0x004 safe zone byte (0x0095fb27), c + 0x012 class byte,
 *   c + 0x024 run counter, c + 0x038 movement flag, c + 0x039 movement type,
 *   c + 0x14c move speed (word), c + 0x180 / 0x184 tile position,
 *   c + 0x190 byte (stops walking), c + 0x21a4 wing type,
 *   c + 0x3194 path (mu_path), o + 0x02a action, o + 0x02c prior action,
 *   o + 0x03b kind, o + 0x05c type (0xa91 = Player), o + 0x060 subtype,
 *   o + 0x0b4 float timer, o + 0x0d0 / 0x0d4 frame / prior frame,
 *   o + 0x158 position, o + 0x164 angles (degrees). */

#include <stdint.h>

#define MU_PATH_CELLS 15

/* Path record at c + 0x3194 (copied out of the path finder by 0x012b0e85). */
typedef struct mu_path {
    uint8_t current;        /* +0x00 index of the cell being left */
    uint8_t current_float;  /* +0x01 spline sub-step 0..3 */
    uint8_t count;          /* +0x02 number of cells */
    uint8_t x[MU_PATH_CELLS];  /* +0x03 */
    uint8_t y[MU_PATH_CELLS];  /* +0x12 */
} mu_path;

/* CreateAngle 0x012aed9e: heading in degrees from (x1, y1) to (x2, y2).
 * |dx| < 0.0001: 0 when dy < 0 else 180; |dy| < 0.0001: 270 when dx < 0
 * else 90; otherwise atan(dy/dx)/pi*180 + 90 (+180 when dx < 0). atan is
 * the float wrapper 0x012b2bca over the CRT double atan; host libm here. */
float mu_create_angle(float x1, float y1, float x2, float y2);

/* FarAngle 0x012af218: signed shortest difference target - angle after
 * wrapping both into [0, 360); absolute value when abs_flag == 1. */
float mu_far_angle(float angle, float target, uint8_t abs_flag);

/* TurnAngle2 0x012aefff: turns angle toward target by step degrees, or
 * returns target when the step would pass it. */
float mu_turn_angle2(float angle, float target, float step);

/* MovePath 0x012b0846(c, turn): follows the path with a 4-sub-step cubic
 * spline through the cell centres ((cell + 0.5) * 100). Writes the tile
 * position when a sub-step starts, advances the sub-step when the object is
 * within (int)30 units of the spline point, and at the last cell snaps the
 * object to it and returns 1. Otherwise, when turn != 0, turns the object
 * toward the spline point: snap when FarAngle >= 45, else TurnAngle2 by half
 * the difference. sqrt is the float wrapper 0x00961a07 over CRT sqrt. */
int mu_move_path(mu_path *path, int32_t tile[2], float position[3], float angles[3], uint8_t turn);

/* RequestTerrainHeight 0x016cc9e2: 0 in scene states 1, 2 and 4
 * (0x009b0bc1 on 0x01d1df70) or for negative x/y; the special height
 * 0x01cf15dc outside the map or on attribute 0x40 tiles; else the bilinear
 * height of TerrainHeight 0x0b6f5420 (y first, then x). */
float mu_request_terrain_height(const float *height, const uint16_t *wall, float special_height,
                                int32_t scene_state, float x, float y);

/* Inputs of CharacterMoveSpeed 0x013957b5 that come from other client
 * subsystems (each named after the call that produces it). */
typedef struct mu_move_speed_input {
    uint16_t move_speed;       /* c + 0x14c */
    int32_t object_type;       /* o + 0x5c */
    uint8_t object_kind;       /* o + 0x3b */
    uint8_t special_state;     /* 0x009fa30a(c) -> 0x009fbb31() */
    uint16_t helper_type;      /* 0x0129dcda(c) (0xffff: none) */
    int32_t mount_type;        /* 0x0106c5e9(c), asked when helper_type is 0xffff */
    uint8_t helper_option;     /* c + 0x299f */
    uint8_t safe_zone;         /* c + 4 (0x0095fb27) */
    int32_t subtype;           /* c + 0x32b4 */
    uint8_t mounted_item;      /* 0x0139fcbf(c) */
    int16_t wing_type;         /* c + 0x21a4 */
    uint8_t transformed;       /* 0x00b9929c(c) */
    uint8_t world_runs;        /* 0x009dacb8(world) == 1 */
    uint8_t stunned;           /* c + 0x190 */
    uint32_t buffs;            /* bit set of 0x01295ade(c + 0x35ac, id) results, MU_BUFF_* */
    double buff_18b_bonus;     /* 0x0117b5eb(0x00966c42(7, 0x27, 0)) */
} mu_move_speed_input;

enum {
    MU_BUFF_18B = 1u << 0, MU_BUFF_38 = 1u << 1, MU_BUFF_B8 = 1u << 2, MU_BUFF_BA = 1u << 3,
    MU_BUFF_D1 = 1u << 4, MU_BUFF_D2 = 1u << 5, MU_BUFF_F0 = 1u << 6, MU_BUFF_56 = 1u << 7,
    MU_BUFF_112 = 1u << 8, MU_BUFF_116 = 1u << 9, MU_BUFF_20 = 1u << 10
};

/* CharacterMoveSpeed 0x013957b5: units per logic step. *run is the run
 * counter c + 0x24 (read, and set to 40 by several branches). For a Player
 * (type 0xa91, kind 1) without helper, mount, wing or buffs: 12 while
 * run < 40, else 15. */
float mu_character_move_speed(const mu_move_speed_input *input, uint8_t *run);

/* MoveCharacterPosition 0x0137b351 with the speed already computed:
 * position += VectorRotate((0, -speed, 0), AngleMatrix(angles)); then z from
 * RequestTerrainHeight (+90 in worlds 8, 10 and 0x84, +30 elsewhere, for a
 * Dinorant 0x1a03 outside the safe zone; world -1 always plain); the
 * 0x7a7-type bob; finally timer += 0.15. AngleMatrix and VectorRotate are the
 * record-math ports (0x00cff32a, 0x00d000ad). */
typedef struct mu_position_input {
    float speed;
    int32_t world;             /* 0x01cf15fc */
    uint16_t helper_type;      /* 0x0129dcda(c), asked when world != -1 */
    uint8_t safe_zone;         /* 0x0095fb27(c) */
    int32_t object_type;       /* o + 0x5c */
    const float *height;       /* RequestTerrainHeight inputs */
    const uint16_t *wall;
    float special_height;
    int32_t scene_state;
} mu_position_input;
void mu_move_character_position(const mu_position_input *input, float position[3], const float angles[3],
                                float *timer);

/* SetAction 0x012affa4(o, action): when action < the model's action count
 * and differs from the current one, the current action and frame become the
 * prior ones and the frame restarts at 0. Returns 1 when it changed. */
int mu_set_action(uint16_t *action, uint16_t *prior_action, float *frame, float *prior_frame, int32_t action_count,
                  int32_t new_action);

/* ---- Player walk/stand selection: the minimal case (isolated) ----
 * Recovered by executing SetPlayerWalk 0x0139002a (up to its tail
 * 0x01391c19) and the player stop selector 0x01391e55 under emulation for
 * every class byte: unarmed, no wing, helper, mount, buff or flight state,
 * world 0. The full routines (weapon and mount actions) are not ported; the
 * NATIVE-ACTOR-001 action tables supersede this when merged. */
enum {
    MU_PLAYER_WALK_MALE = 0x32, MU_PLAYER_WALK_FEMALE = 0x33, MU_PLAYER_RUN = 0x4f, MU_PLAYER_RUN_CLASS11 = 0x63
};
/* Run-counter part of SetPlayerWalk for that case: in a safe zone (world not
 * 0x84) the counter is reset to 0; otherwise, below 40, it grows by one for
 * base classes 3, 4, 6 and 7 (the other growth conditions need equipment,
 * stats or buffs). Returns the new counter. */
uint8_t mu_player_walk_run(uint8_t class_byte, uint8_t safe_zone, int32_t world, uint8_t run);
/* Walk action chosen afterwards (unarmed: no safe-zone test here, the zone
 * acts through the counter): MU_PLAYER_RUN (0x63 for base class 11) when
 * run >= 40, else the walk action of the class (0x33 for
 * base classes 2, 5, 7, 8, 9, 12 and 14, 0x32 otherwise).
 * *speed receives the PlaySpeed SetPlayerWalk writes for that action. */
int32_t mu_player_walk_action(uint8_t class_byte, uint8_t run, float *speed);
/* Stand action of 0x01391e55 for that case, per base class 0..15:
 * 1 1 2 1 1 3 1 5 6 6 1 1 2 1 6 8. */
int32_t mu_player_stop_action(uint8_t class_byte);
/* PlaySpeed of those stand actions as set by the player loader 0x01830aa6
 * (block 0x018311f7..0x018321e1, executed): 0.28, action 3: 0.24. */
float mu_player_stop_speed(int32_t action);

#endif
