#ifndef MU_WALK_H
#define MU_WALK_H

/* "Walk around the world" session (NATIVE-WORLD-001, docs/research/native-world.md).
 *
 * Joins the earlier native pieces into one in-world loop:
 *   - the real terrain of a world (mu_terrain, NATIVE-TERRAIN-001) as the
 *     height, attribute and picking grid of the frame loop;
 *   - the frame driver, camera, wheel zoom, input and terrain picking of
 *     NATIVE-FRAME-001 (mu_frame), with the world's camera record
 *     (Camera_Angle_Position.bmd: FOV and far factors) instead of the
 *     placeholders;
 *   - the hero's logic step as the client's MoveHero 0x016a9150 runs it for a
 *     plain walk, with the movement routines of reconstructed/movement:
 *     SetPlayerWalk (run counter, walk action), MovePath (spline and turn),
 *     MoveCharacterPosition with CharacterMoveSpeed, and on arrival the stop
 *     packet's Movement = 0 and SetPlayerStop;
 *   - the click-to-move start of MoveHero: terrain pick, target tile, path,
 *     SendMove's Movement = 1.
 * The path is the client's own path finder (reconstructed/path, NATIVE-PATH-001:
 * PathFinding2 0x012b0e85, FindPath 0x012b1c45) over the world's
 * attribute grid, with the client's neighbour order (direction table
 * 0x01cf1640, pinned by a live read, NATIVE-PATH-002) and near plane 20
 * (0x01cf162c), both static data of the third section. The run counter and
 * CharacterMoveSpeed's predicates follow the hero's gear (mu_hero.gear), and
 * the long-distance auto move walks the client's list (NATIVE-PATH-002).
 * Placeholders (labelled where used): the
 * operable-object grid (static objects are not decoded) and everything the
 * hero does besides walking (attacks, skills, auto-move, packets). */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/movement/client_movement.h"
#include "../../reconstructed/path/client_path.h"
#include "mu_character.h"
#include "mu_frame.h"
#include "mu_terrain.h"

/* Camera record of a world: Data/World<n>/Camera_Angle_Position.bmd, else
 * Data/G_Camera_Angle_Position.bmd (key 0), read by 0x0098af0c: "MAP\x01" +
 * Modulus envelope (else the v12 rolling cipher), the plaintext is an INI
 * file read with GetPrivateProfileStringA. Record layout 0x24 bytes. */
typedef struct mu_camera_info {
    float angle[3];       /* +0x00 [CAMERA ANGLE] Angle X/Y/Z */
    float position[3];    /* +0x0c [CAMERA POSITION] Position X/Y/Z */
    float z_distance;     /* +0x18 [CAMERA DISTANCE] Z_Distance */
    float distance;       /* +0x1c [CAMERA DISTANCE] Distance */
    float fov;            /* +0x20 [CAMERA FOV] FOV */
    int32_t key;          /* folder number of the record used, 0 for the global file */
} mu_camera_info;

/* Parses the decrypted INI text with the loader's keys, buffer sizes (11 or 30
 * characters including the terminator) and empty defaults; values go through
 * strtod and are stored as float. */
void mu_camera_info_parse(const char *text, size_t size, mu_camera_info *info);
/* Loads the record for a world folder as the client selects it (its folder's
 * file, else key 0). Returns 0 on success. */
int mu_camera_info_load(const char *game_root, int32_t folder, mu_camera_info *info, char *error, size_t error_size);

/* The CHARACTER / OBJECT fields the hero step uses (client offsets in
 * reconstructed/movement/client_movement.h). */
typedef struct mu_hero {
    uint8_t class_byte;       /* c + 0x12 */
    uint8_t safe_zone;        /* c + 0x04, TerrainWall[tile] & 1 in the render pass */
    uint8_t run;              /* c + 0x24 */
    uint8_t movement;         /* c + 0x38 */
    int32_t tile[2];          /* c + 0x180 / 0x184 */
    mu_path path;             /* c + 0x3194 */
    float position[3];        /* o + 0x158 */
    float angle[3];           /* o + 0x164 */
    float timer;              /* o + 0xb4 */
    uint16_t action, prior_action;   /* o + 0x2a / 0x2c */
    float frame, prior_frame;        /* o + 0xd0 / 0xd4 (mirrors of the Player model) */
    float play_speed;         /* PlaySpeed of the current action (the animation step reads it) */
    uint8_t action_changed;   /* set when SetAction changed the action this step */
    uint8_t step_result;      /* AL of the last animation tick (0 when it wrapped or clamped) */
    /* NATIVE-PATH-002: the run-counter and speed inputs besides class_byte and safe_zone (body-part
     * boots/gloves, the hero equipment's levels, buffs, riding pet, subtype); neutral by default
     * (no gear: only base classes 3, 4, 6 and 7 run). class_byte, safe_zone and the world are copied
     * in every step. */
    mu_run_input gear;
} mu_hero;

#define MU_WALK_LOG 64

/* The client's path-finder neighbour order (0x01cf1640). */
extern const int32_t mu_walk_default_directions[8][2];

typedef struct mu_walk {
    mu_frame_world frame;     /* clock, camera, input, pick; heights/walls are the world's */
    mu_world *map;            /* mu_world_frame updates its light and wave grids */
    mu_camera_info camera_info;
    mu_hero hero;
    int32_t world;            /* client world index (0x01cf15fc) */
    int32_t action_count;     /* Player model actions (SetAction bound) */
    int32_t target[2];        /* TargetX/Y 0x0b449ac0 / 0x0b449ac4 */
    int32_t directions[8][2]; /* path finder neighbour order (0x01cf1640) */
    mu_path_finder finder;    /* the client's path object (0x06fce374) over frame.walls (heap arrays: mu_walk_free) */
    uint32_t steps, moves, arrivals, path_refused;
    uint32_t position_steps;  /* MoveCharacterPosition calls */
    double position_distance; /* their summed horizontal displacement */
    char log[MU_WALK_LOG][80];
    int32_t log_count;
    /* NATIVE-WORLD-002: called at the end of every logic step (after MoveHero
     * and the hero's animation step), where MoveCharacters runs the other
     * characters and the hero's per-character routine 0x013b23f8. */
    void (*step_hook)(void *context, struct mu_walk *walk);
    void *step_context;
    /* NATIVE-COMBAT-001: called after the key scan, before MoveHero's walk
     * and click code (the attack case of MoveHero runs there). */
    void (*pre_step_hook)(void *context, struct mu_walk *walk);
    void *pre_step_context;
    /* NATIVE-PATH-002: the long-distance auto move held in the hero's PATH_t (flag 2 walks its
     * list three nodes at a time), and its counters. */
    mu_auto_path auto_path;
    uint32_t auto_moves, auto_segments, auto_searches;
    float speed, top_speed;   /* CharacterMoveSpeed of the last position step, and the highest so far */
    /* NATIVE-HELPERS-001: the ride word c + 0x322e (CharacterMoveSpeed's helper type, 0xffff none), the mount
     * manager's predicates for the hero (riding 0x0106bdb7, keeps_run 0x0106bd76), the rider action 0x0106c382
     * SetPlayerStop / SetPlayerWalk ask while riding (returns 1 when it set the action) and the rider lift
     * 0x0103da5c that mu_walk_place adds to the model position. */
    uint16_t helper_type;
    uint8_t riding, keeps_run;
    int (*ride_hook)(void *context, struct mu_walk *walk, int32_t how);
    void *ride_context;
    float place_offset[3];
} mu_walk;

/* Starts a session on a loaded world (mu_walk is large: allocate it
 * statically or on the heap). The hero stands at the centre of tile
 * (tile_x, tile_y), facing angle_z, with the class byte's stand action.
 * window_* are the drawable pixels. near_plane: the client's CameraViewNear
 * 0x01cf162c is 20. */
void mu_walk_init(mu_walk *walk, mu_world *map, const mu_camera_info *info, uint32_t window_width,
                  uint32_t window_height, int32_t tile_x, int32_t tile_y, float angle_z, uint8_t class_byte,
                  int32_t action_count, float near_plane);
/* Window messages and key states, Win32 form (forwarded to mu_frame). */
/* Releases the path finder's arrays (mu_walk_init allocates them). */
void mu_walk_free(mu_walk *walk);
void mu_walk_message(mu_walk *walk, uint32_t message, uint32_t wparam, uint32_t lparam);
void mu_walk_key(mu_walk *walk, int vk, int down);
/* Due logic steps (client accumulator); returns how many ran. character may
 * be NULL; otherwise it is animated inside each step (mu_walk_animate). */
int32_t mu_walk_update(mu_walk *walk, uint32_t now, mu_character *character);
/* One logic step in the in-world tick's order: key scan, MoveHero (the
 * hero's walk step, then the click start), then the character animation
 * step of MoveCharacters when character is not NULL. */
void mu_walk_step(mu_walk *walk, mu_character *character);
/* Render-pass state: safe-zone byte, MoveMainCamera, BeginOpengl and the
 * mouse ray (view.projection / view.modelview are then the GL matrices). */
void mu_walk_begin_render(mu_walk *walk, uint32_t now);
int32_t mu_walk_end_render(mu_walk *walk);

/* NATIVE-COMBAT-001: the hero's SetAction 0x012affa4 with the PlaySpeed
 * the animation step uses; a path toward a tile through the client path
 * finder (PathFinding2 0x012b0e85, Movement = 1, like the click start;
 * returns 1 when a path was found); and the stop packet's Movement = 0 with
 * SetPlayerStop's stand action. */
void mu_walk_set_action(mu_walk *walk, int32_t action, float speed);
int mu_walk_path_to(mu_walk *walk, int32_t tile_x, int32_t tile_y);
void mu_walk_stop(mu_walk *walk);

/* NATIVE-PATH-002: the long-distance auto move toward a tile, as MoveHero's S-click branch starts it
 * (0x016ad06b: 0x0129c6be(flag 2, tile, target, mode 2, error_check 0), SendMove on success; a
 * target on a safe-zone tile drops the auto move after the first segment, 0x016ad0a1). Each
 * logic step then hands the follower the next three nodes when the logical tile reaches the
 * waypoint, and a stopped hero searches again from its tile until it stands on the target.
 * Returns 1 when the first segment started. In the click handler, S + left click (after a
 * normal click path started) calls it; the client also gates it on option byte 0x0bdc5981 and a
 * helper-state check (static reading, not modelled). */
int mu_walk_auto_move_to(mu_walk *walk, int32_t tile_x, int32_t tile_y);
/* NATIVE-QUEST-002: the same start with the caller's flag (1 arms only, 2 walks), mode and error check: the quest
 * windows' "Go Now" (0x00d5029b: flag 2, mode 3, error check 1; the guide's 0x00d4bed6: mode 1). */
int mu_walk_auto_move_ex(mu_walk *walk, int32_t flag, int32_t tile_x, int32_t tile_y, int32_t mode,
                         int32_t error_check);

/* One animation step: applies the hero's action to the Player model the way
 * SetAction does (prior action and frame from the model, frame 0) when it
 * changed, then ticks the Player animation with the action's PlaySpeed. */
int mu_walk_animate(mu_walk *walk, mu_character *character);
/* Places the character at the hero (position, angles) and poses and skins
 * every part (mu_character_update). */
int mu_walk_place(const mu_walk *walk, mu_character *character);

#endif
