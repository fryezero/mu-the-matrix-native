#include "mu_path.h"

#include <stdlib.h>
#include <string.h>

int mu_pathing_init(mu_pathing *p, const uint16_t *attributes)
{
    memset(p, 0, sizeof *p);
    if (attributes)
        memcpy(p->wall, attributes, sizeof p->wall);
    return mu_path_finder_init(&p->finder, 256, 256, p->wall, p->objects);
}

void mu_pathing_free(mu_pathing *p)
{
    mu_path_finder_free(&p->finder);
}

void mu_pathing_set_characters(mu_pathing *p, const int32_t *tiles, int32_t count)
{
    mu_path_clear_characters(p->wall, MU_PATH_CELLS);
    for (int32_t i = 0; i < count; i++)
        mu_path_stamp_character(p->wall, tiles[2 * i], tiles[2 * i + 1]);
}

int mu_pathing_find(mu_pathing *p, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_client_path *path)
{
    return mu_path_finding2(&p->finder, sx, sy, tx, ty, path, 0.0f, (int32_t)MU_TW_CHARACTER, 0);
}

int mu_pathing_walkable(const mu_pathing *p, int32_t x, int32_t y)
{
    if (x < 0 || y < 0 || x > 255 || y > 255)
        return 0;
    return (p->wall[y * 256 + x] & MU_PATH_WALL_MASK) < MU_TW_CHARACTER;
}

void mu_walker_place(mu_walker *w, int32_t tile_x, int32_t tile_y, float angle)
{
    memset(w, 0, sizeof *w);
    w->mover.tile_x = tile_x;
    w->mover.tile_y = tile_y;
    w->mover.position[0] = ((float)tile_x + 0.5f) * 100.0f;
    w->mover.position[1] = ((float)tile_y + 0.5f) * 100.0f;
    w->mover.angle[2] = angle;
}

/* (int)(position * 0.01f), the object tile computed at 0x016ac5bb. */
static int32_t object_tile(float coordinate)
{
    float t = 0.01f * coordinate;
    return (t >= -2147483648.0f && t < 2147483648.0f) ? (int32_t)t : INT32_MIN;
}

int mu_walker_click(mu_walker *w, mu_pathing *p, int32_t target_x, int32_t target_y)
{
    mu_path_mover *m = &w->mover;
    target_x &= 255;   /* TargetX/Y are stored as (uint8_t)(CollisionPosition / 100) */
    target_y &= 255;
    if (w->moving && (abs(m->tile_x - object_tile(m->position[0])) >= 2 ||
                      abs(m->tile_y - object_tile(m->position[1])) >= 2))
        return 0;
    if (m->tile_x == target_x && m->tile_y == target_y && w->moving)
        return 0;
    mu_client_path path;
    if (!mu_path_finding2(&p->finder, m->tile_x, m->tile_y, target_x, target_y, &path, 0.0f,
                          (int32_t)MU_TW_CHARACTER, 0))
        return 0;
    m->path = path;
    /* SendMove 0x016b5cd0 (network boundary): sets Character+0x38 = 1. */
    w->moving = 1;
    w->sent++;
    return 1;
}

float mu_walker_base_speed(const mu_walker *w)
{
    return w->run < 40 ? 12.0f : 15.0f;
}

int mu_walker_step(mu_walker *w, int can_run)
{
    if (!w->moving)
        return 0;
    if (can_run && w->run < 40)
        w->run = (uint8_t)(w->run + 1);
    w->steps++;
    if (mu_path_move(&w->mover, 1, NULL)) {
        w->moving = 0;
        w->run = 0;
        return 1;
    }
    w->speed = mu_walker_base_speed(w);
    mu_path_step_position(w->mover.position, w->mover.angle, w->speed);
    return 0;
}
