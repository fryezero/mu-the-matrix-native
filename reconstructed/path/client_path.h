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
 *   FindPath             0x012b1c45 (thiscall, 10 arguments)
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

#define MU_PATH_MAX_STEPS 500       /* BuildPath limit and FindPath pop budget used by PathFinding2 */
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
