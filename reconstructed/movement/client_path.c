/* The client's path finder. See client_path.h. */
#include "client_path.h"

#include <string.h>

#define FAR_COST 0x743aa380

static int32_t cell(const mu_path_finder *f, int32_t x, int32_t y)
{
    return y * f->width + x;   /* 0x012b23de */
}

static int inside(const mu_path_finder *f, int32_t x, int32_t y)
{
    return x >= 0 && y >= 0 && x < f->width && y < f->height;   /* 0x012b1b92 */
}

/* 0x012b1ae7: widens the range of touched state bytes. */
static int touch(mu_path_finder *f, int32_t index)
{
    if (index < 0 || index >= f->size)
        return 0;
    if (index < f->touched_low)
        f->touched_low = index;
    if (index > f->touched_high)
        f->touched_high = index;
    return 1;
}

/* 0x012b2515: clears the touched state bytes and the end marker. */
static void reset(mu_path_finder *f)
{
    if (f->touched_low == FAR_COST)
        return;
    memset(f->state + f->touched_low, 0, (size_t)(f->touched_high - f->touched_low + 1));
    f->touched_low = FAR_COST;
    f->touched_high = -1;
    f->end_x = 0;
    f->end_y = 0;
}

static int32_t absolute(int32_t v)
{
    return v < 0 ? -v : v;   /* CRT abs 0x01983135 */
}

/* 0x012b1bcf: ((|a - b| * 5 + min(a, b) * 7 + 1) * 3) / 4, a = |x - tx|, b = |y - ty|. */
static int32_t heuristic(int32_t tx, int32_t ty, int32_t x, int32_t y)
{
    int32_t a = absolute(x - tx), b = absolute(y - ty);
    int32_t m = a < b ? a : b;
    int32_t value = absolute(a - b) * 5 + m * 7 + 1;
    return value * 3 / 4;
}

/* 0x012b1b67 */
static int32_t step_cost(int32_t dx, int32_t dy)
{
    return dx != 0 && dy != 0 ? 7 : 5;
}

/* ---- open queue: the client's binary tree (equal keys to the right, the
 * leftmost popped) behaves as a priority queue that is first-in first-out
 * among equal priorities; a binary heap on (priority, insertion order). ---- */

static int before(const mu_path_node *a, const mu_path_node *b)
{
    return a->priority < b->priority || (a->priority == b->priority && a->sequence < b->sequence);
}

static void push(mu_path_finder *f, int32_t index, int32_t priority)
{
    int32_t i = f->open_count++;
    mu_path_node node = {index, priority, f->sequence++};
    while (i > 0) {
        int32_t parent = (i - 1) / 2;
        if (!before(&node, &f->open[parent]))
            break;
        f->open[i] = f->open[parent];
        i = parent;
    }
    f->open[i] = node;
}

static int32_t pop(mu_path_finder *f)
{
    int32_t result = f->open[0].index;
    mu_path_node last = f->open[--f->open_count];
    int32_t i = 0;
    for (;;) {
        int32_t child = 2 * i + 1;
        if (child >= f->open_count)
            break;
        if (child + 1 < f->open_count && before(&f->open[child + 1], &f->open[child]))
            ++child;
        if (!before(&f->open[child], &last))
            break;
        f->open[i] = f->open[child];
        i = child;
    }
    if (f->open_count > 0)
        f->open[i] = last;
    return result;
}

uint32_t mu_path_finder_bytes(void)
{
    return (uint32_t)sizeof(mu_path_finder);
}

void mu_path_finder_init(mu_path_finder *f, uint16_t *map)
{
    memset(f, 0, sizeof *f);
    f->width = 256;
    f->height = 256;
    f->size = f->width * f->height;
    f->map = map;
    f->touched_low = FAR_COST;
    f->touched_high = -1;
}

/* 0x012b21c6 (the long-search branch never runs: max_iterations 500 keeps
 * its flag 0): walks the parents from the end back to the start. */
static int build(mu_path_finder *f, int32_t sx, int32_t sy, int32_t ex, int32_t ey)
{
    f->end_x = (int16_t)ex;
    f->end_y = (int16_t)ey;
    int32_t x = ex, y = ey;
    for (f->length = 0; f->length < MU_PATH_FINDER_LENGTH; ) {
        f->x[MU_PATH_FINDER_LENGTH - 1 - f->length] = (uint8_t)x;
        f->y[MU_PATH_FINDER_LENGTH - 1 - f->length] = (uint8_t)y;
        if (x == sx && y == sy) {
            ++f->length;
            return 1;
        }
        int32_t i = cell(f, x, y);
        x = f->previous_x[i];
        y = f->previous_y[i];
        ++f->length;
    }
    return 0;
}

int mu_find_path(mu_path_finder *f, int32_t sx, int32_t sy, int32_t tx, int32_t ty, uint8_t error_check,
                 int32_t wall, uint8_t flag, float distance, int32_t max_iterations, int32_t mask,
                 const int32_t directions[8][2], const uint32_t *objects)
{
    reset(f);
    if (sx == 0 || sy == 0)
        return 0;
    f->end_x = -1;
    f->end_y = -1;
    if (!(distance == 0.0f))
        return -1;   /* the target-area branch 0x012b2584 is not ported */
    int32_t target = cell(f, tx, ty);
    if (target < 0 || target >= f->size)
        return 0;
    if (flag == 1)
        f->map[target] = 0;
    if (error_check && !(wall > (int32_t)f->map[target]) && !(f->map[target] & 0x20))
        return 0;
    f->state[target] = 4;
    if (!touch(f, target))
        return 0;
    int32_t best = FAR_COST, best_x = sx, best_y = sy;
    int32_t start = cell(f, sx, sy);
    if (start < 0 || start >= f->size)
        return 0;
    f->open_count = 0;
    f->sequence = 0;
    push(f, start, 0);
    f->state[start] |= 1;
    if (!touch(f, start))
        return 0;
    for (int32_t left = max_iterations; f->open_count > 0 && left > 0; --left) {
        int32_t c = pop(f);
        int32_t x = c % f->width, y = c / f->width;   /* 0x012b24ee */
        f->cost[c] = left == max_iterations ? 0 : FAR_COST;
        for (int d = 0; d < 8; ++d) {
            int32_t nx = x + directions[d][0], ny = y + directions[d][1];
            if (!inside(f, nx, ny))
                continue;
            int32_t n = cell(f, nx, ny);
            if (!(f->state[n] & 2))
                continue;
            int32_t candidate = step_cost(directions[d][0], directions[d][1]) + f->cost[n];
            if (candidate < f->cost[c]) {
                f->cost[c] = candidate;
                f->previous_x[c] = nx;
                f->previous_y[c] = ny;
            }
        }
        f->state[c] |= 2;
        if (f->state[c] & 4) {
            f->open_count = 0;
            return build(f, sx, sy, x, y);
        }
        for (int d = 0; d < 8; ++d) {
            int32_t nx = x + directions[d][0], ny = y + directions[d][1];
            if (!inside(f, nx, ny))
                continue;
            int32_t n = cell(f, nx, ny);
            int32_t value = (int32_t)(f->map[n] & (uint32_t)mask);
            if ((f->state[n] & 1) || !(wall > value))
                continue;
            if (objects && (objects[n] & 1) && cell(f, tx, ty) != n)
                continue;
            int32_t priority = heuristic(tx, ty, nx, ny) + f->cost[c];
            push(f, n, priority);
            f->state[n] |= 1;
            if (!touch(f, n))
                return 0;
            f->previous_x[n] = x;
            f->previous_y[n] = y;
        }
        if (!error_check) {
            int32_t h = heuristic(tx, ty, x, y);
            if (h < best) {
                best = h;
                best_x = x;
                best_y = y;
            }
        }
    }
    f->open_count = 0;
    if (!error_check)
        return build(f, sx, sy, best_x, best_y);
    return 0;
}

static int32_t repeat_index(int32_t x, int32_t y)
{
    return (int32_t)(((uint32_t)y & 0xffu) << 8) + (int32_t)((uint32_t)x & 0xffu);   /* 0x016d34db */
}

int mu_path_finding2(mu_path_finder *f, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_path *path,
                     float distance, int32_t wall, uint8_t flag, const int32_t directions[8][2],
                     const uint32_t *objects)
{
    int found = mu_find_path(f, sx, sy, tx, ty, 1, wall, flag, distance, 500, 0x1e, directions, objects);
    if (found < 0)
        return found;
    if (!found) {
        uint16_t start = f->map[repeat_index(sx, sy)], goal = f->map[repeat_index(tx, ty)];
        if ((start & 1) || ((goal & 1) && !(goal & 2)))
            wall = 4;
        found = mu_find_path(f, sx, sy, tx, ty, 0, wall, flag, distance, 500, 0x1e, directions, objects);
        if (found < 0)
            return found;
    }
    if (!found)
        return 0;
    int32_t count = f->length < MU_PATH_CELLS ? f->length : MU_PATH_CELLS;   /* 0x012b2489 */
    if (count <= 1)
        return 0;
    path->count = (uint8_t)count;
    const uint8_t *xs = f->x + MU_PATH_FINDER_LENGTH - f->length;   /* 0x012b24b1 */
    const uint8_t *ys = f->y + MU_PATH_FINDER_LENGTH - f->length;   /* 0x012b24c8 */
    for (int32_t i = 0; i < count; ++i) {
        path->x[i] = xs[i];
        path->y[i] = ys[i];
    }
    path->current = 0;
    path->current_float = 0;
    return 1;
}
