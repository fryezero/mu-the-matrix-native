#ifndef MU_CLIENT_PATH_H
#define MU_CLIENT_PATH_H

/* Click-to-move path finding and path following of the client
 * (NATIVE-PATH-001). Authored C ports; names are ours. Every routine equals
 * the client's instructions on the compared domain (scripts/validate_path.py,
 * Unicorn over the pinned restored text). Addresses, evidence levels and
 * limits: docs/research/client-path.md.
 *
 *   path finder object   [0x06fce374], 0x428 bytes (ctor 0x012b1855,
 *                        SetMapDimensions 0x012b281e(256, 256, TerrainWall))
 *   FindPath             0x012b1c45 (thiscall, 10 arguments), BuildPath 0x012b21c6
 *                        (both variants)
 *   long-distance helper 0x012b104c and the auto-move PATH_t methods 0x0129c4d2,
 *                        0x0129c51d, 0x0129c6be, 0x0129cc44 (NATIVE-PATH-002)
 *   PathFinding2         0x012b0e85 (cdecl, 7 arguments)
 *   MovePath             0x012b0846 (Catmull-Rom sub-targets, turning)
 *   CreateAngle          0x012aed9e, angle difference 0x012af218,
 *   TurnAngle            0x012aefff
 *   MoveCharacterPosition 0x0137b351 (horizontal step only)
 *   character occupancy  first loop of MoveCharacters 0x0137a7ce
 *
 * Build with -ffp-contract=off: binary32 operations in source order. */

#include <stdint.h>

/* TerrainWall (0x0b795420) attribute bits used by the movement code. */
#define MU_TW_SAFEZONE 0x0001u
#define MU_TW_CHARACTER 0x0002u
#define MU_TW_NOMOVE 0x0004u
#define MU_TW_NOGROUND 0x0008u
#define MU_TW_WATER 0x0010u
#define MU_TW_ACTION 0x0020u

#define MU_PATH_MAX_STEPS 500       /* BuildPath limit, FindPath pop budget used by PathFinding2, auto-move list cap */
#define MU_PATH_CLIENT_NODES 15     /* PATH_t capacity (GetPath clamp) */
#define MU_PATH_INFINITE 0x743aa380 /* "no cost" sentinel and reset marker */
#define MU_PATH_WALL_MASK 0x1e      /* PathFinding2's passability mask */

/* Mark bits of the per-tile byte array (+0x400). */
#define MU_PATH_OPEN 1u
#define MU_PATH_CLOSED 2u
#define MU_PATH_TARGET 4u

/* Priority queue entry. The client keeps an unbalanced binary search tree
 * (+0x418, nodes {index, cost, left, right, parent}); equal costs are inserted
 * to the right and the minimum is the leftmost node, so the pop order is
 * (cost, insertion order). A binary heap keyed on (cost, sequence) gives the
 * same order. */
typedef struct mu_path_queue_entry {
    int32_t index, cost;
    uint32_t sequence;
} mu_path_queue_entry;

/* The client object at [0x06fce374]. Field offsets of the client object are
 * given for reference. The arrays persist between searches as in the client:
 * only the marks of the touched index range are cleared by a reset. */
typedef struct mu_path_finder {
    int32_t width, height, size;     /* +0, +4, +8 */
    uint16_t *wall;                  /* +0xc: TerrainWall, not owned (flag 1 writes it) */
    const uint32_t *object_flags;    /* global 0x0b7b5420 (bit 0: blocking object), may be NULL */
    int32_t count;                   /* +0x10 nodes of the last built path */
    uint8_t path_x[MU_PATH_MAX_STEPS]; /* +0x14, filled from the end */
    uint8_t path_y[MU_PATH_MAX_STEPS]; /* +0x208 */
    int16_t end_x, end_y;            /* +0x3fc, +0x3fe */
    uint8_t *mark;                   /* +0x400 */
    int32_t touched_min, touched_max;/* +0x404, +0x408 */
    int32_t *cost, *parent_x, *parent_y; /* +0x40c, +0x410, +0x414 */
    mu_path_queue_entry *queue;      /* +0x418 tree */
    int32_t queue_count, queue_capacity;
    uint32_t queue_sequence;
    /* diagnostics (not client state) */
    int32_t pops, pushes, index_errors;
    /* neighbour order; NULL = the client's table 0x01cf1640 (mu_path_directions). The validators
     * also run the client with other tables written there. */
    const int32_t (*directions)[2];
} mu_path_finder;

/* PATH_t at Character + 0x3194. */
typedef struct mu_client_path {
    uint8_t current;                 /* +0 CurrentPath */
    uint8_t current_float;           /* +1 sub-target 0..3 */
    uint8_t count;                   /* +2 PathNum */
    uint8_t x[MU_PATH_CLIENT_NODES]; /* +3 */
    uint8_t y[MU_PATH_CLIENT_NODES]; /* +0x12 */
} mu_client_path;

/* Allocates the arrays (SetMapDimensions). Marks start cleared; the cost and
 * parent arrays start zeroed (the client's are uninitialised heap memory that
 * the search never reads before writing). touched_min/max start in the reset
 * state. Returns 0 on success. */
int mu_path_finder_init(mu_path_finder *finder, int32_t width, int32_t height, uint16_t *wall,
                        const uint32_t *object_flags);
void mu_path_finder_free(mu_path_finder *finder);

/* 0x012b2515: clear the marks of the touched range, end = (0, 0). */
void mu_path_finder_reset(mu_path_finder *finder);

/* Heuristic 0x012b1bcf: dx = |x - tx|, dy = |y - ty|,
 * (3 * (5 * |dx - dy| + 7 * min(dx, dy) + 1)) / 4 (C division). */
int32_t mu_path_heuristic(int32_t tx, int32_t ty, int32_t x, int32_t y);
/* Step cost 0x012b1b67: 7 diagonal, 5 orthogonal. */
int32_t mu_path_step_cost(int32_t dx, int32_t dy);
/* Neighbour order of FindPath (table 0x01cf1640). */
extern const int32_t mu_path_directions[8][2];

/* FindPath 0x012b1c45. error_check: when 0, a failed search builds the path
 * to the expanded node with the smallest heuristic. clear_target_wall (the
 * client's "flag", PathFinding2's siege-skill check) zeroes TerrainWall at the
 * target in the distance-0 case. Returns 1 when a path was built (count, the
 * tail of path_x/path_y and end_x/end_y hold it). */
int mu_path_find(mu_path_finder *finder, int32_t sx, int32_t sy, int32_t tx, int32_t ty, int error_check,
                 int32_t wall_level, int clear_target_wall, float distance, int32_t max_pops, int32_t wall_mask);

/* GetPath 0x012b2489: min(count, 15); first node pointers 0x012b24b1/c8. */
int32_t mu_path_finder_nodes(const mu_path_finder *finder);
const uint8_t *mu_path_finder_x(const mu_path_finder *finder);
const uint8_t *mu_path_finder_y(const mu_path_finder *finder);

/* PathFinding2 0x012b0e85: FindPath(error_check 1, wall_level, budget 500,
 * mask 0x1e); on failure, if the start or target tile is a safe zone and the
 * target has no character, wall_level becomes 4; then FindPath(error_check
 * 0). Writes *path (current 0, sub-target 0, at most 15 nodes from the start)
 * only when the path has more than one node. */
int mu_path_finding2(mu_path_finder *finder, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_client_path *path,
                     float distance, int32_t wall_level, int clear_target_wall);

/* ---- long-distance path (auto move) ----
 *
 * The hero's PATH_t at Character + 0x3194 is larger than the 0x21 bytes
 * PathFinding2 fills (constructor 0x0129e1b9): it also carries an auto-move
 * state and a std::list of tiles. The long-distance helper 0x012b104c fills
 * the list with a whole path (up to 500 nodes); 0x0129cc44 hands it to the
 * follower three nodes at a time. Field offsets are the client's. */
#define MU_PATH_LONG_BUDGET 300000000   /* FindPath pop budget of 0x012b104c */
#define MU_PATH_LONG_MASK 0x1c          /* its passability mask: character tiles do not block */
#define MU_PATH_LONG_LEVEL 4            /* wall level every auto-move caller passes */
#define MU_PATH_SEGMENT_NODES 3         /* nodes per segment taken by 0x0129cc44 */

typedef struct mu_auto_path {
    mu_client_path path;             /* +0x00..+0x20, the follower's PATH_t */
    int32_t mode;                    /* +0x2c: what happens on arrival (1..5; 2 = plain move) */
    int16_t waypoint_x, waypoint_y;  /* +0x30, +0x32: last node of the current segment */
    int32_t flag;                    /* +0x34: 0 idle, 1 armed, 2 walk the list, 3 re-path each step */
    int16_t target_x, target_y;      /* +0x38, +0x3a: destination (the end tile actually found) */
    /* +0x3c std::list<{int16 x, int16 y}>: nodes [list_head, list_head + list_count) */
    int32_t list_head, list_count;
    int16_t list_x[MU_PATH_MAX_STEPS], list_y[MU_PATH_MAX_STEPS];
} mu_auto_path;

/* Results of the auto-move entry points besides their return value. */
typedef struct mu_auto_path_effects {
    uint8_t target_set;              /* TargetX/Y 0x0b449ac0/c4 were set to the waypoint */
    int32_t target[2];
    uint8_t selection_cleared;       /* the six selection globals 0x01cf114c..0x01cf1160 became -1 */
    uint8_t arrived;                 /* the arrival handler 0x0129c8b0 ran (start == target) */
    uint8_t failure_notice;          /* the failure notice of mode 2 was shown (UI, not reproduced) */
} mu_auto_path_effects;

/* Constructor 0x0129e1b9: PATH_t bytes zero, then the reset below. */
void mu_auto_path_init(mu_auto_path *auto_path);
/* Reset 0x0129c4d2: target and waypoint (-1, -1), flag 0, mode 0, list
 * cleared. The follower's PATH_t is left as it is. */
void mu_auto_path_reset(mu_auto_path *auto_path);

/* The long-distance helper 0x012b104c(sx, sy, tx, ty, error_check, path,
 * distance, level): clears the list; refuses a negative target; then
 * FindPath(error_check, level, flag 0, distance, budget 300,000,000, mask
 * 0x1c) on the persistent finder. On success the target becomes the end tile
 * the search reached and the list receives min(nodes, 500) nodes from the
 * start, unless the path has a single node. Returns FindPath's result. A
 * target reached by a path of 500 or more nodes keeps the 499 nodes nearest
 * the start (BuildPath's trimming variant); without error_check an
 * unreachable target gives the path to the explored tile with the smallest
 * heuristic (at most 500 nodes, else failure). */
int mu_path_long(mu_path_finder *finder, int32_t sx, int32_t sy, int32_t tx, int32_t ty, int error_check,
                 mu_auto_path *auto_path, float distance, int32_t wall_level);

/* 0x0129cc44: takes min(list, 3) nodes off the front of the list into the
 * PATH_t (current 0, sub-target 0); the waypoint becomes the last one taken.
 * Returns 0 when the list is empty. (The client also posts a UI notice, text
 * 0x14c3, not reproduced.) */
int mu_auto_path_next(mu_auto_path *auto_path);

/* Start 0x0129c6be(flag, sx, sy, tx, ty, mode, error_check): mode is stored;
 * a start equal to the target runs the arrival handler (effects->arrived;
 * the native layer applies mu_auto_path_arrive) and returns 0. Otherwise the
 * flag and target are stored; flag 1 stops there (returns 0). Then
 * mu_path_long(error_check != 0, distance 0, level 4) and
 * mu_auto_path_next: on success TargetX/Y = waypoint, the selection globals
 * are cleared and 1 is returned; on failure mode 2 shows a notice and the
 * auto path is reset. */
int mu_auto_path_start(mu_auto_path *auto_path, mu_path_finder *finder, int32_t flag, int32_t sx, int32_t sy,
                       int32_t tx, int32_t ty, int32_t mode, int32_t error_check, mu_auto_path_effects *effects);

/* Refresh 0x0129c51d(sx, sy, tx, ty): when the start differs from the
 * target, mu_path_long(error_check 0, distance 0, level 4); on success
 * TargetX/Y = the current waypoint (the list is refilled but no segment is
 * taken) and the selection globals are cleared; on failure reset (mode 2
 * notice). A start equal to the target runs the arrival handler. */
void mu_auto_path_refresh(mu_auto_path *auto_path, mu_path_finder *finder, int32_t sx, int32_t sy, int32_t tx,
                          int32_t ty, mu_auto_path_effects *effects);

/* The part of the arrival handler 0x0129c8b0 that touches the auto path
 * (static reading; its other effects are UI and NPC/quest subsystem calls):
 * modes 4 and 5 leave the state as it is, every other mode resets it. */
void mu_auto_path_arrive(mu_auto_path *auto_path);

/* Angles in degrees (binary32, client compare semantics). */
float mu_path_create_angle(float x1, float y1, float x2, float y2);       /* 0x012aed9e */
float mu_path_angle_difference(float from, float to, int absolute);        /* 0x012af218 */
float mu_path_turn_angle(float from, float to, float step);                /* 0x012aefff */

/* The character fields MovePath reads and writes. */
typedef struct mu_path_mover {
    int32_t tile_x, tile_y;          /* Character + 0x180, + 0x184 */
    float position[3];               /* Object + 0x158 (Character + 0x33ac) */
    float angle[3];                  /* Object + 0x164 */
    mu_client_path path;             /* Character + 0x3194 */
} mu_path_mover;

/* MovePath 0x012b0846: the sub-target is a Catmull-Rom point (t = 0.25,
 * 0.5, 0.75, 1) of the tile centres around the current node; within 30 units
 * the next sub-target is taken; the last node is the arrival (returns 1,
 * position snapped). turn: face the sub-target (snap at 45 degrees or more,
 * otherwise half the difference). The sub-target used is returned through
 * target (may be NULL). */
int mu_path_move(mu_path_mover *mover, int turn, float target[2]);

/* MoveCharacterPosition 0x0137b351, horizontal part: position +=
 * AngleMatrix(angle) * (0, -speed, 0). The height that follows (terrain
 * height plus world offsets) is left to the caller. */
void mu_path_step_position(float position[3], const float angle[3], float speed);

/* MoveCharacters 0x0137a7ce, first loop: every tile with the character bit
 * loses it (wall - 2); then each listed tile gains it (TERRAIN_INDEX_REPEAT,
 * x and y & 255). */
void mu_path_clear_characters(uint16_t *wall, int32_t cells);
void mu_path_stamp_character(uint16_t *wall, int32_t tile_x, int32_t tile_y);

#endif
