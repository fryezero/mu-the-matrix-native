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
    mu_path_clear_characters(p->wall, MU_PATHING_CELLS);
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

void mu_walker_gear_default(mu_walker *w, uint8_t class_byte, int32_t world)
{
    memset(&w->gear, 0, sizeof w->gear);
    w->gear.class_byte = class_byte;
    w->gear.world = world;
    w->gear.gloves_type = -1;
    w->gear.boots_type = -1;
}

void mu_walker_gear_boots(mu_walker *w, int8_t level)
{
    w->gear.boots_type = 0x0c00;   /* any boots item: the rule reads only "present" and the level */
    w->gear.boots_level = level;
}

void mu_walker_place(mu_walker *w, int32_t tile_x, int32_t tile_y, float angle)
{
    memset(w, 0, sizeof *w);
    w->mover.tile_x = tile_x;
    w->mover.tile_y = tile_y;
    w->mover.position[0] = ((float)tile_x + 0.5f) * 100.0f;
    w->mover.position[1] = ((float)tile_y + 0.5f) * 100.0f;
    w->mover.angle[2] = angle;
    mu_walker_gear_default(w, 0, 0);
    mu_auto_path_init(&w->auto_path);
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

/* CharacterMoveSpeed's input for the walker (a Player without helper or wing). */
static float walker_speed(const mu_walker *w, uint8_t *run)
{
    mu_speed_fields f;
    memset(&f, 0, sizeof f);
    f.object_type = 0xa91;
    f.object_kind = 1;
    f.helper_type = 0xffff;
    f.wing_type = -1;
    f.safe_zone = w->gear.safe_zone;
    f.subtype = w->gear.subtype;
    f.mounted_item = w->gear.mounted_item;
    f.world = w->gear.world;
    f.buffs = w->gear.buffs;
    mu_move_speed_input in;
    mu_move_speed_input_from(&f, &in);
    return mu_character_move_speed(&in, run);
}

float mu_walker_base_speed(const mu_walker *w)
{
    uint8_t run = w->run;
    return walker_speed(w, &run);
}

/* SendMove 0x016b5cd0 (network boundary): Character + 0x38 = 1. */
static void send_move(mu_walker *w)
{
    w->moving = 1;
    w->sent++;
}

/* The auto move's PATH_t is the hero's PATH_t: the follower state lives in mover.path. */
static void take_segment(mu_walker *w)
{
    w->mover.path = w->auto_path.path;
    w->segments++;
    send_move(w);
}

int mu_walker_auto_move(mu_walker *w, mu_pathing *p, int32_t target_x, int32_t target_y)
{
    mu_auto_path_effects e;
    w->auto_path.path = w->mover.path;
    int started = mu_auto_path_start(&w->auto_path, &p->finder, 2, w->mover.tile_x, w->mover.tile_y, target_x,
                                     target_y, 2, 0, &e);
    if (e.arrived)
        mu_auto_path_arrive(&w->auto_path);
    if (started)
        take_segment(w);
    /* 0x016ad0a1: a destination on a safe-zone tile drops the auto move */
    if (w->auto_path.target_x >= 0 && w->auto_path.target_y >= 0 &&
        (p->wall[((w->auto_path.target_y & 255) << 8) + (w->auto_path.target_x & 255)] & MU_TW_SAFEZONE))
        mu_auto_path_reset(&w->auto_path);
    return started;
}

int mu_walker_step(mu_walker *w, mu_pathing *p)
{
    mu_auto_path *a = &w->auto_path;
    /* 0x016a9976: flag 2 and stopped: walk on toward the auto-move target */
    if (a->flag == 2 && !w->moving && p) {
        if (a->target_x != -1 && a->target_y != -1) {
            mu_auto_path_effects e;
            a->path = w->mover.path;
            if (mu_auto_path_start(a, &p->finder, 2, w->mover.tile_x, w->mover.tile_y, a->target_x, a->target_y,
                                   a->mode, 0, &e))
                take_segment(w);
            else if (e.arrived)
                mu_auto_path_arrive(a);
        } else {
            mu_auto_path_reset(a);
        }
    }
    if (!w->moving)
        return 0;
    if (p)   /* RenderCharacter: SafeZone = TerrainWall[tile] & 1 */
        w->gear.safe_zone = (uint8_t)(p->wall[((w->mover.tile_y & 255) << 8) + (w->mover.tile_x & 255)] & 1);
    w->run = mu_player_run_counter(&w->gear, w->run);
    /* 0x016a9c0a: flag 2 and the logical tile on the waypoint: the next segment */
    if (a->flag == 2 && w->mover.tile_x == a->waypoint_x && w->mover.tile_y == a->waypoint_y) {
        a->path = w->mover.path;
        if (mu_auto_path_next(a))
            take_segment(w);
    }
    w->steps++;
    if (mu_path_move(&w->mover, 1, NULL)) {
        w->moving = 0;
        w->run = mu_player_stop_run_counter(0, w->run);
        return 1;
    }
    w->speed = walker_speed(w, &w->run);
    mu_path_step_position(w->mover.position, w->mover.angle, w->speed);
    return 0;
}
