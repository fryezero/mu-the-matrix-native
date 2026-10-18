#ifndef MU_PATH_NATIVE_H
#define MU_PATH_NATIVE_H

/* Click-to-move for the native client (NATIVE-PATH-001): the client's path
 * finder, path follower and hero walk step on a 256 x 256 attribute map.
 *
 * The rules are the instruction-compared ports in reconstructed/path (see
 * docs/research/client-path.md). This layer owns the grids and wraps the hero
 * logic of the client's in-world tick into a small API:
 *
 *     mu_pathing pathing;                       // once per world
 *     mu_pathing_init(&pathing, world->attributes);
 *     mu_walker hero;
 *     mu_walker_place(&hero, 125, 125, 0.0f);    // spawn tile
 *     ...
 *     if (picked) mu_walker_click(&hero, &pathing, target_x, target_y);   // left click, target tile
 *     mu_walker_step(&hero, &pathing);           // every 40 ms logic step
 *     // hero.mover.position[0..1] and hero.mover.angle[2] drive the model;
 *     // the height (position[2]) is the caller's terrain height.
 *
 * Self-contained: no client data, no network. The point where the client
 * hands a new path to the network layer (SendMove 0x016b5cd0) is reported by
 * mu_walker_click's return value and mu_walker.sent; nothing is sent. */

#include <stdint.h>

#include "../../reconstructed/movement/client_movement.h"
#include "../../reconstructed/path/client_path.h"

#define MU_PATHING_CELLS 65536

typedef struct mu_pathing {
    uint16_t wall[MU_PATHING_CELLS];       /* TerrainWall copy (attributes & 0xfaff, character bits added) */
    uint32_t objects[MU_PATHING_CELLS];    /* 0x0b7b5420: bit 0 = blocking static object (zero unless set) */
    mu_path_finder finder;              /* the client finder object, persistent per world */
} mu_pathing;

/* attributes: the world's 256 x 256 attribute cells (mu_world.attributes). */
int mu_pathing_init(mu_pathing *pathing, const uint16_t *attributes);
void mu_pathing_free(mu_pathing *pathing);

/* MoveCharacters 0x0137a7ce: clear every character bit, then mark the given
 * tiles (x, y pairs) as occupied. The client runs it once per logic step
 * after the hero logic, including the hero's own tile. */
void mu_pathing_set_characters(mu_pathing *pathing, const int32_t *tiles, int32_t count);

/* PathFinding2 with the hero click arguments: distance 0, TW_CHARACTER
 * level, no siege flag. Returns 1 and fills *path when the client would
 * start walking. */
int mu_pathing_find(mu_pathing *pathing, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_client_path *path);

/* Walkability for the hero click level: (attribute & 0x1e) < 2. */
int mu_pathing_walkable(const mu_pathing *pathing, int32_t x, int32_t y);

typedef struct mu_walker {
    mu_path_mover mover;   /* tile (Character+0x180), position/angle (Object), PATH_t */
    uint8_t moving;        /* Character + 0x38 */
    uint8_t run;           /* Character + 0x24, the run counter (0..40) */
    float speed;           /* speed used by the last step */
    uint32_t sent;         /* paths handed to the network boundary (count only) */
    uint32_t steps;        /* logic steps while moving */
    /* NATIVE-PATH-002 */
    mu_run_input gear;     /* run-counter inputs (class, boots/gloves, buffs, pets, world); safe_zone is
                              refreshed from the tile each step when the pathing grid is given */
    mu_auto_path auto_path;/* the long-distance auto move kept in the hero's PATH_t */
    uint32_t segments;     /* auto-move segments handed to the follower */
} mu_walker;

/* Places the walker at the centre of a tile, stopped. angle: Object angle[2]. */
void mu_walker_place(mu_walker *walker, int32_t tile_x, int32_t tile_y, float angle);

/* The normal click-to-move branch of MoveHero 0x016a9150 (0x016acce8..):
 * ignored while moving if the object is two or more tiles away from its
 * logical tile, or when the target is the current tile while moving;
 * otherwise PathFinding2(tile, target, 0.0, 2). On success the client calls
 * SendMove (network boundary, not reproduced): the walker starts moving and
 * `sent` is incremented. Returns 1 when a new path started. */
int mu_walker_click(mu_walker *walker, mu_pathing *pathing, int32_t target_x, int32_t target_y);

/* CharacterMoveSpeed 0x013957b5 for the walker as a Player without helper or
 * wing: 12 while the run counter is below 40, then 15; ride buffs, riding
 * pets and the world rule as reconstructed (mu_move_speed_input_from). */
float mu_walker_base_speed(const mu_walker *walker);

/* Gear presets for mu_walker.gear (all neutral otherwise): no gear, a class
 * byte, boots of item level 5 on the body (they let any class run). */
void mu_walker_gear_default(mu_walker *walker, uint8_t class_byte, int32_t world);
void mu_walker_gear_boots(mu_walker *walker, int8_t level);

/* One 40 ms logic step, in MoveHero's order:
 *  - auto move with flag 2 while stopped (0x016a9976): restart from the tile
 *    toward the auto-move target (0x0129c6be), or reset when it has none;
 *  - while moving: the run counter (SetPlayerWalk prefix, mu_player_run_counter
 *    with gear; safe zone from the tile when pathing is given), the next
 *    auto-move segment when the logical tile reaches the waypoint
 *    (0x0129cc44, SendMove), MovePath(turn), then MoveCharacterPosition at
 *    CharacterMoveSpeed, or, on arrival, stop (SetPlayerStop resets the run
 *    counter).
 * Returns 1 on the arrival step. pathing may be NULL (no restart; gear.safe_zone
 * as set). */
int mu_walker_step(mu_walker *walker, mu_pathing *pathing);

/* The long-distance auto move of MoveHero's S-click branch (0x016ad06b):
 * 0x0129c6be(flag 2, tile, target, mode 2, error_check 0); on success the
 * first segment starts (SendMove) and 1 is returned. A target on a safe-zone
 * tile resets the auto move afterwards (0x016ad0a1), so only the first
 * segment is walked. */
int mu_walker_auto_move(mu_walker *walker, mu_pathing *pathing, int32_t target_x, int32_t target_y);

#endif
