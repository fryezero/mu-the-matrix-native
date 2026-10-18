#ifndef MU_CLIENT_PATH_H
#define MU_CLIENT_PATH_H

/* The client's path finder (NATIVE-WORLD-001): PathFinding2 0x012b0e85 and the
 * path object's FindPath 0x012b1c45 with its helpers (0x012b2515 reset,
 * 0x012b1ae7 touched range, 0x012b1b67 step cost, 0x012b1bcf heuristic,
 * 0x012b198d / 0x012b240a open queue, 0x012b21c6 path build). Authored names.
 *
 * The search, as the client runs it on the 256 x 256 TerrainWall grid:
 *   - the start cell is opened with priority 0; each step pops the open cell
 *     of lowest priority (a binary tree keyed by priority, equal keys to the
 *     right, the leftmost popped: earliest insertion first among equals);
 *   - the popped cell's cost is the minimum over its closed neighbours of
 *     neighbour cost + 5 (straight) or 7 (diagonal), and that neighbour
 *     becomes its parent (the start costs 0);
 *   - the cell is closed; if it is a target cell the path is built;
 *   - every in-bounds neighbour not yet opened whose (attribute & mask) is
 *     below the wall mode is opened with priority heuristic(target) + the
 *     popped cell's cost, parent = the popped cell; cells flagged in the
 *     object grid 0x0b7b5420 open only when they are the target;
 *   - without the error check the cell closest to the target by the
 *     heuristic is remembered and the path goes there when the search ends
 *     (open list empty or max_iterations pops).
 * The neighbour order is the client's direction table at 0x01cf1640, which
 * lies in the packed data section of the executable; callers pass it. */

#include <stdint.h>

#include "client_movement.h"

#define MU_PATH_FINDER_CELLS 65536
#define MU_PATH_FINDER_LENGTH 500

typedef struct mu_path_node {
    int32_t index, priority;
    uint32_t sequence;
} mu_path_node;

typedef struct mu_path_finder {
    int32_t width, height, size;            /* +0x00 .. +0x08 */
    uint16_t *map;                          /* +0x0c TerrainWall (written when flag == 1) */
    int32_t length;                         /* +0x10 */
    uint8_t x[MU_PATH_FINDER_LENGTH];       /* +0x14, filled from the end */
    uint8_t y[MU_PATH_FINDER_LENGTH];       /* +0x208 */
    int16_t end_x, end_y;                   /* +0x3fc */
    uint8_t state[MU_PATH_FINDER_CELLS];    /* +0x400: 1 opened, 2 closed, 4 target */
    int32_t touched_low, touched_high;      /* +0x404, +0x408 */
    int32_t cost[MU_PATH_FINDER_CELLS];     /* +0x40c */
    int32_t previous_x[MU_PATH_FINDER_CELLS], previous_y[MU_PATH_FINDER_CELLS]; /* +0x410, +0x414 */
    mu_path_node open[MU_PATH_FINDER_CELLS];/* +0x418 tree, as a stable priority queue */
    int32_t open_count;
    uint32_t sequence;
} mu_path_finder;

/* sizeof(mu_path_finder), for callers that allocate it (ctypes tests). */
uint32_t mu_path_finder_bytes(void);
/* Path object constructor plus 0x012b281e (256 x 256 over map). */
void mu_path_finder_init(mu_path_finder *finder, uint16_t *map);

/* FindPath 0x012b1c45(sx, sy, tx, ty, error_check, wall, flag, distance,
 * max_iterations, mask). Only distance == 0 (a single target cell) is
 * ported; other distances return -1. directions[d] = {dx, dy}. objects is
 * the 0x0b7b5420 grid (NULL = all clear). Returns 1 with the path in
 * finder->x/y (last length entries), 0 when the client returns 0. */
int mu_find_path(mu_path_finder *finder, int32_t sx, int32_t sy, int32_t tx, int32_t ty, uint8_t error_check,
                 int32_t wall, uint8_t flag, float distance, int32_t max_iterations, int32_t mask,
                 const int32_t directions[8][2], const uint32_t *objects);

/* PathFinding2 0x012b0e85(sx, sy, tx, ty, path, distance, wall) with the
 * event predicate (flag) as an input: FindPath with the error check; on
 * failure, wall 4 when the start is a safe-zone cell or the target is a
 * safe cell without a character, and FindPath without the error check (the
 * closest reachable cell). A result of more than one cell is copied into
 * path (at most 15 cells from the start), current = sub-step = 0; returns 1.
 * Otherwise returns 0 and leaves path unchanged. */
int mu_path_finding2(mu_path_finder *finder, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_path *path,
                     float distance, int32_t wall, uint8_t flag, const int32_t directions[8][2],
                     const uint32_t *objects);

#endif
