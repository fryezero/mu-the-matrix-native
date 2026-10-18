#include "client_path.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "../record-math/record_math.h"

/* 0x01cf1640 (8 int pairs; values from the unpacked data section, see the
 * finding). */
const int32_t mu_path_directions[8][2] = {
    {-1, -1}, {0, -1}, {1, -1}, {-1, 0}, {1, 0}, {-1, 1}, {0, 1}, {1, 1},
};

/* ---- priority queue: (cost, insertion order) ---- */

static int queue_less(const mu_path_queue_entry *a, const mu_path_queue_entry *b)
{
    return a->cost < b->cost || (a->cost == b->cost && a->sequence < b->sequence);
}

static int queue_push(mu_path_finder *f, int32_t index, int32_t cost)
{
    if (f->queue_count == f->queue_capacity) {
        int32_t capacity = f->queue_capacity ? f->queue_capacity * 2 : 1024;
        mu_path_queue_entry *grown = realloc(f->queue, (size_t)capacity * sizeof *grown);
        if (!grown)
            return -1;
        f->queue = grown;
        f->queue_capacity = capacity;
    }
    mu_path_queue_entry entry = {index, cost, f->queue_sequence++};
    int32_t i = f->queue_count++;
    while (i > 0) {
        int32_t parent = (i - 1) / 2;
        if (!queue_less(&entry, &f->queue[parent]))
            break;
        f->queue[i] = f->queue[parent];
        i = parent;
    }
    f->queue[i] = entry;
    f->pushes++;
    return 0;
}

static int32_t queue_pop(mu_path_finder *f)
{
    int32_t index = f->queue[0].index;
    mu_path_queue_entry last = f->queue[--f->queue_count];
    int32_t i = 0;
    for (;;) {
        int32_t child = 2 * i + 1;
        if (child >= f->queue_count)
            break;
        if (child + 1 < f->queue_count && queue_less(&f->queue[child + 1], &f->queue[child]))
            child++;
        if (!queue_less(&f->queue[child], &last))
            break;
        f->queue[i] = f->queue[child];
        i = child;
    }
    if (f->queue_count > 0)
        f->queue[i] = last;
    f->pops++;
    return index;
}

static void queue_clear(mu_path_finder *f)
{
    f->queue_count = 0;
    f->queue_sequence = 0;
}

/* ---- object ---- */

int mu_path_finder_init(mu_path_finder *f, int32_t width, int32_t height, uint16_t *wall,
                        const uint32_t *object_flags)
{
    memset(f, 0, sizeof *f);
    f->width = width;
    f->height = height;
    f->size = width * height;
    f->wall = wall;
    f->object_flags = object_flags;
    size_t n = (size_t)f->size;
    f->mark = calloc(n, 1);
    f->cost = calloc(n, sizeof *f->cost);
    f->parent_x = calloc(n, sizeof *f->parent_x);
    f->parent_y = calloc(n, sizeof *f->parent_y);
    f->touched_min = MU_PATH_INFINITE;
    f->touched_max = -1;
    if (!f->mark || !f->cost || !f->parent_x || !f->parent_y) {
        mu_path_finder_free(f);
        return -1;
    }
    return 0;
}

void mu_path_finder_free(mu_path_finder *f)
{
    free(f->mark);
    free(f->cost);
    free(f->parent_x);
    free(f->parent_y);
    free(f->queue);
    f->mark = NULL;
    f->cost = f->parent_x = f->parent_y = NULL;
    f->queue = NULL;
    f->queue_count = f->queue_capacity = 0;
}

static void set_end(mu_path_finder *f, int32_t x, int32_t y)
{
    f->end_x = (int16_t)x;   /* 0x0121304e stores the low words */
    f->end_y = (int16_t)y;
}

void mu_path_finder_reset(mu_path_finder *f)
{
    if (f->touched_min == MU_PATH_INFINITE)
        return;
    memset(f->mark + f->touched_min, 0, (size_t)(f->touched_max - f->touched_min + 1));
    f->touched_min = MU_PATH_INFINITE;
    f->touched_max = -1;
    set_end(f, 0, 0);
}

/* 0x012b23de: y * width + x, no range check. */
static int32_t tile_index(const mu_path_finder *f, int32_t x, int32_t y)
{
    return y * f->width + x;
}

/* 0x012b1ae7: range check and touched-range update. */
static int touch(mu_path_finder *f, int32_t index)
{
    if (index < 0 || index >= f->size)
        return 0;
    if (index < f->touched_min)
        f->touched_min = index;
    if (index > f->touched_max)
        f->touched_max = index;
    return 1;
}

/* 0x012b1b92 */
static int in_map(const mu_path_finder *f, int32_t x, int32_t y)
{
    return x >= 0 && y >= 0 && x < f->width && y < f->height;
}

int32_t mu_path_heuristic(int32_t tx, int32_t ty, int32_t x, int32_t y)
{
    int32_t dx = abs(x - tx), dy = abs(y - ty);
    int32_t m = dx < dy ? dx : dy;
    return (abs(dx - dy) * 5 + m * 7 + 1) * 3 / 4;
}

int32_t mu_path_step_cost(int32_t dx, int32_t dy)
{
    return dx != 0 && dy != 0 ? 7 : 5;
}

/* Square root through the client's float wrapper 0x00961a07: double sqrt,
 * rounded to binary32. */
static float client_sqrtf(float x)
{
    return (float)sqrt((double)x);
}

/* 0x012b2584: mark the target tiles within `distance` of (tx, ty). */
static void mark_targets(mu_path_finder *f, int error_check, int32_t wall_level, int32_t tx, int32_t ty,
                         float distance)
{
    int32_t d = (int32_t)distance;
    for (int32_t i = -d; i <= d; i++) {
        int32_t r = d - abs(i);
        for (int32_t j = -r; j <= 0; j++) {
            int32_t pair[2] = {tx + j, tx - j};
            for (int k = 0; k < 2; k++) {
                int32_t index = tile_index(f, pair[k], ty + i);
                if (index >= 0 && index < f->size) {
                    if (!error_check || wall_level > (int32_t)f->wall[index]) {
                        f->mark[index] = MU_PATH_TARGET;
                        touch(f, index);
                    }
                } else {
                    f->index_errors++;   /* client: log line via 0x01206598 */
                }
            }
        }
        for (int32_t k = -d; k < -r; k++) {
            float s = client_sqrtf((float)(k * k + i * i));
            if (!(distance > s))
                continue;
            int32_t pair[2] = {tx + k, tx - k};
            for (int m = 0; m < 2; m++) {
                int32_t index = tile_index(f, pair[m], ty + i);
                if (index >= 0 && index < f->size) {
                    if (!error_check || wall_level > (int32_t)f->wall[index]) {
                        f->mark[index] = MU_PATH_TARGET;
                        touch(f, index);
                    }
                } else {
                    f->index_errors++;
                }
            }
        }
    }
}

/* 0x012b21c6 with flag 0 (the trimming variant for budgets above 500 is used
 * only by the long-distance helper path 0x012b104c, not ported). */
static int build_path(mu_path_finder *f, int32_t sx, int32_t sy, int32_t ex, int32_t ey)
{
    int32_t cx = ex, cy = ey;
    set_end(f, ex, ey);
    for (f->count = 0; f->count < MU_PATH_MAX_STEPS; f->count++) {
        f->path_x[MU_PATH_MAX_STEPS - 1 - f->count] = (uint8_t)cx;
        f->path_y[MU_PATH_MAX_STEPS - 1 - f->count] = (uint8_t)cy;
        if (cx == sx && cy == sy) {
            f->count++;
            return 1;
        }
        int32_t index = tile_index(f, cx, cy);
        cx = f->parent_x[index];
        cy = f->parent_y[index];
    }
    return 0;
}

int mu_path_find(mu_path_finder *f, int32_t sx, int32_t sy, int32_t tx, int32_t ty, int error_check,
                 int32_t wall_level, int clear_target_wall, float distance, int32_t max_pops, int32_t wall_mask)
{
    f->pops = f->pushes = 0;
    mu_path_finder_reset(f);
    if (sx == 0 || sy == 0)
        return 0;
    set_end(f, -1, -1);
    if (distance == 0.0f) {
        int32_t target = tile_index(f, tx, ty);
        if (target < 0 || target >= f->size)
            return 0;
        if (clear_target_wall == 1)
            f->wall[target] = 0;
        if (error_check && wall_level <= (int32_t)f->wall[target] &&
            !(f->wall[tile_index(f, tx, ty)] & MU_TW_ACTION))
            return 0;
        f->mark[target] = MU_PATH_TARGET;
        if (!touch(f, target))
            return 0;
    } else {
        mark_targets(f, error_check, wall_level, tx, ty, distance);
    }

    int32_t best = MU_PATH_INFINITE, best_x = sx, best_y = sy;
    int32_t start = tile_index(f, sx, sy);
    if (start < 0 || start >= f->size)
        return 0;
    if (queue_push(f, start, 0))
        return 0;
    f->mark[start] |= MU_PATH_OPEN;
    if (!touch(f, start))
        return 0;

    for (int32_t budget = max_pops; f->queue_count > 0 && budget > 0; budget--) {
        int32_t current = queue_pop(f);
        int32_t x = current % f->width, y = current / f->width;   /* 0x012b24ee (idiv) */
        f->cost[current] = budget == max_pops ? 0 : MU_PATH_INFINITE;
        for (int d = 0; d < 8; d++) {
            int32_t nx = x + mu_path_directions[d][0], ny = y + mu_path_directions[d][1];
            if (!in_map(f, nx, ny))
                continue;
            int32_t n = tile_index(f, nx, ny);
            if (!(f->mark[n] & MU_PATH_CLOSED))
                continue;
            int32_t g = mu_path_step_cost(mu_path_directions[d][0], mu_path_directions[d][1]) + f->cost[n];
            if (g < f->cost[current]) {
                f->cost[current] = g;
                f->parent_x[current] = nx;
                f->parent_y[current] = ny;
            }
        }
        f->mark[current] |= MU_PATH_CLOSED;
        if (f->mark[current] & MU_PATH_TARGET) {
            queue_clear(f);
            return build_path(f, sx, sy, x, y);
        }
        for (int d = 0; d < 8; d++) {
            int32_t nx = x + mu_path_directions[d][0], ny = y + mu_path_directions[d][1];
            if (!in_map(f, nx, ny))
                continue;
            int32_t n = tile_index(f, nx, ny);
            int32_t w = (int32_t)f->wall[n] & wall_mask;
            if (f->mark[n] & MU_PATH_OPEN)
                continue;
            if (!(wall_level > w))
                continue;
            if (f->object_flags && (f->object_flags[n] & 1u) && tile_index(f, tx, ty) != n)
                continue;
            if (queue_push(f, n, mu_path_heuristic(tx, ty, nx, ny) + f->cost[current]))
                return 0;
            f->mark[n] |= MU_PATH_OPEN;
            if (!touch(f, n))
                return 0;
            f->parent_x[n] = x;
            f->parent_y[n] = y;
        }
        if (!error_check) {
            int32_t h = mu_path_heuristic(tx, ty, x, y);
            if (h < best) {
                best = h;
                best_x = x;
                best_y = y;
            }
        }
    }
    queue_clear(f);
    if (!error_check)
        return build_path(f, sx, sy, best_x, best_y);
    return 0;
}

int32_t mu_path_finder_nodes(const mu_path_finder *f)
{
    return f->count < MU_PATH_CLIENT_NODES ? f->count : MU_PATH_CLIENT_NODES;
}

const uint8_t *mu_path_finder_x(const mu_path_finder *f)
{
    return f->path_x + MU_PATH_MAX_STEPS - f->count;
}

const uint8_t *mu_path_finder_y(const mu_path_finder *f)
{
    return f->path_y + MU_PATH_MAX_STEPS - f->count;
}

/* TERRAIN_INDEX_REPEAT 0x016d34db over the 256 x 256 TerrainWall. */
static uint16_t wall_repeat(const mu_path_finder *f, int32_t x, int32_t y)
{
    return f->wall[((y & 255) << 8) + (x & 255)];
}

int mu_path_finding2(mu_path_finder *f, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_client_path *path,
                     float distance, int32_t wall_level, int clear_target_wall)
{
    int32_t wall = wall_level;
    int found = mu_path_find(f, sx, sy, tx, ty, 1, wall, clear_target_wall, distance, MU_PATH_MAX_STEPS,
                             MU_PATH_WALL_MASK);
    if (!found) {
        if (((wall_repeat(f, sx, sy) & MU_TW_SAFEZONE) || (wall_repeat(f, tx, ty) & MU_TW_SAFEZONE)) &&
            !(wall_repeat(f, tx, ty) & MU_TW_CHARACTER))
            wall = 4;
        found = mu_path_find(f, sx, sy, tx, ty, 0, wall, clear_target_wall, distance, MU_PATH_MAX_STEPS,
                             MU_PATH_WALL_MASK);
    }
    if (!found)
        return 0;
    int32_t nodes = mu_path_finder_nodes(f);
    if (nodes <= 1)
        return 0;
    path->count = (uint8_t)nodes;
    const uint8_t *xs = mu_path_finder_x(f), *ys = mu_path_finder_y(f);
    for (int32_t i = 0; i < path->count; i++) {
        path->x[i] = xs[i];
        path->y[i] = ys[i];
    }
    path->current = 0;
    path->current_float = 0;
    return 1;
}

/* ---- angles ---- */

/* 0x0184f8ff: 0 > x ? -x : x (sign flip, NaN kept). */
static float client_fabsf(float x)
{
    return 0.0f > x ? -x : x;
}

float mu_path_create_angle(float x1, float y1, float x2, float y2)
{
    float nx = x2 - x1, ny = y2 - y1;
    if (0.0001f > client_fabsf(nx))
        return 0.0f > ny ? 0.0f : 180.0f;
    if (0.0001f > client_fabsf(ny))
        return 0.0f > nx ? 270.0f : 90.0f;
    float a = (float)atan((double)(ny / nx));   /* 0x012b2bca -> CRT atan, rounded to binary32 */
    a = a / 3.14159274f;                        /* 0x40490fdb */
    a = a * 180.0f;
    a = a + 90.0f;
    if (0.0f > nx && ny >= 0.0f)
        return a + 180.0f;
    if (0.0f > nx && 0.0f > ny)
        return a + 180.0f;
    return a;   /* nx >= 0 && 0 > ny, and every other case */
}

float mu_path_angle_difference(float a, float b, int absolute)
{
    if (0.0f > a)
        a = a + 360.0f;
    if (0.0f > b)
        b = b + 360.0f;
    float d = b - a;
    if (180.0f > a) {
        if (b >= a + 180.0f)
            d = (360.0f - b) + a;
    } else if (a - 180.0f > b) {
        d = (360.0f - a) + b;
    }
    if (absolute == 1 && 0.0f > d)
        d = -d;
    return d;
}

float mu_path_turn_angle(float a, float b, float step)
{
    if (0.0f > a)
        a = a + 360.0f;
    if (0.0f > b)
        b = b + 360.0f;
    if (180.0f > a) {
        float lo = a - step;
        if (b >= a + step && a + 180.0f > b)
            return a + step;
        if (lo >= 0.0f && (b >= a + 180.0f || lo > b))
            return a - step;
        if (0.0f > lo && b >= a + 180.0f && lo + 360.0f > b)
            return (a - step) + 360.0f;
        return b;
    }
    float hi = a + step;
    if (a - step > b && b >= a - 180.0f)
        return a - step;
    if (360.0f > hi && (a - 180.0f > b || b >= hi))
        return a + step;
    if (hi >= 360.0f && a - 180.0f > b && b >= hi - 360.0f)
        return (a + step) - 360.0f;
    return b;
}

/* ---- following ---- */

static const float spline_weights[3][4] = {
    {-0.0703125f, 0.8671875f, 0.2265625f, -0.0234375f},
    {-0.0625f, 0.5625f, 0.5625f, -0.0625f},
    {-0.0234375f, 0.2265625f, 0.8671875f, -0.0703125f},
};

int mu_path_move(mu_path_mover *m, int turn, float target[2])
{
    mu_client_path *p = &m->path;
    int arrived = 0;
    if (!(p->current < p->count))
        return 0;
    if (p->current_float == 0) {
        int32_t i = p->current + 1;
        if (i > p->count - 1)
            i = p->count - 1;
        m->tile_x = p->x[i];
        m->tile_y = p->y[i];
    }
    float xs[4], ys[4];
    for (int k = 0; k < 4; k++) {
        int32_t j = p->current + k - 1;
        if (j < 0)
            j = 0;
        else if (j > p->count - 1)
            j = p->count - 1;
        xs[k] = ((float)p->x[j] + 0.5f) * 100.0f;
        ys[k] = ((float)p->y[j] + 0.5f) * 100.0f;
    }
    float tx = 0.0f, ty = 0.0f;
    if (p->current_float < 3) {
        const float *w = spline_weights[p->current_float];
        tx = xs[0] * w[0] + xs[1] * w[1];
        tx = tx + xs[2] * w[2];
        tx = tx + xs[3] * w[3];
        ty = ys[0] * w[0] + ys[1] * w[1];
        ty = ty + ys[2] * w[2];
        ty = ty + ys[3] * w[3];
    } else if (p->current_float == 3) {
        tx = xs[2];
        ty = ys[2];
    }
    if (target) {
        target[0] = tx;
        target[1] = ty;
    }
    float dx = m->position[0] - tx, dy = m->position[1] - ty;
    float distance = client_sqrtf(dx * dx + dy * dy);
    /* cvttss2si: NaN and out-of-range values give INT32_MIN */
    int32_t whole = (distance >= -2147483648.0f && distance < 2147483648.0f) ? (int32_t)distance : INT32_MIN;
    if (whole <= 30) {
        p->current_float = (uint8_t)(p->current_float + 1);
        if (p->current_float > 3) {
            p->current_float = 0;
            p->current = (uint8_t)(p->current + 1);
            if (p->current >= p->count - 1) {
                p->current = (uint8_t)(p->count - 1);
                m->tile_x = p->x[p->current];
                m->tile_y = p->y[p->current];
                m->position[0] = tx;
                m->position[1] = ty;
                arrived = 1;
            }
        }
    }
    if (!arrived && turn) {
        float angle = mu_path_create_angle(m->position[0], m->position[1], tx, ty);
        float difference = mu_path_angle_difference(m->angle[2], angle, 1);
        if (difference >= 45.0f)
            m->angle[2] = angle;
        else
            m->angle[2] = mu_path_turn_angle(m->angle[2], angle, difference * 0.5f);
    }
    return arrived;
}

void mu_path_step_position(float position[3], const float angle[3], float speed)
{
    float matrix[3][4], velocity[3] = {0.0f, -speed, 0.0f}, delta[3];
    mu_angle_matrix(angle, matrix);
    mu_vector_rotate(velocity, matrix, delta);
    position[0] = position[0] + delta[0];
    position[1] = position[1] + delta[1];
    position[2] = position[2] + delta[2];
}

void mu_path_clear_characters(uint16_t *wall, int32_t cells)
{
    for (int32_t i = 0; i < cells; i++)
        if (wall[i] & MU_TW_CHARACTER)
            wall[i] = (uint16_t)(wall[i] - 2);
}

void mu_path_stamp_character(uint16_t *wall, int32_t tile_x, int32_t tile_y)
{
    int32_t index = ((tile_y & 255) << 8) + (tile_x & 255);
    wall[index] = (uint16_t)(wall[index] | MU_TW_CHARACTER);
}
