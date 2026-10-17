/* Native frame-loop skeleton. See mu_frame.h. */
#include "mu_frame.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

int mu_vk_from_hid(int usage)
{
    if (usage >= 4 && usage <= 29)          /* A..Z */
        return 0x41 + (usage - 4);
    if (usage >= 30 && usage <= 38)         /* 1..9 */
        return 0x31 + (usage - 30);
    if (usage == 39)                        /* 0 */
        return 0x30;
    if (usage >= 58 && usage <= 69)         /* F1..F12 */
        return 0x70 + (usage - 58);
    switch (usage) {
    case 40: return 0x0d;                   /* Return */
    case 41: return 0x1b;                   /* Escape */
    case 42: return 0x08;                   /* Backspace */
    case 43: return 0x09;                   /* Tab */
    case 44: return 0x20;                   /* Space */
    case 47: return 0xdb;                   /* [ */
    case 48: return 0xdd;                   /* ] */
    case 73: return 0x2d;                   /* Insert */
    case 74: return 0x24;                   /* Home */
    case 75: return 0x21;                   /* Page Up */
    case 76: return 0x2e;                   /* Delete */
    case 77: return 0x23;                   /* End */
    case 78: return 0x22;                   /* Page Down */
    case 79: return 0x27;                   /* Right */
    case 80: return 0x25;                   /* Left */
    case 81: return 0x28;                   /* Down */
    case 82: return 0x26;                   /* Up */
    case 224: case 228: return 0x11;        /* Ctrl (the client polls VK_CONTROL) */
    case 225: case 229: return 0x10;        /* Shift */
    case 226: case 230: return 0x12;        /* Alt */
    default: return 0;
    }
}

const char *mu_vk_action(int vk)
{
    switch (vk) {
    case 0x01: return "mouse left: move / attack (MoveHero 0x016a9150)";
    case 0x02: return "mouse right: skill (MoveHero 0x016a9150)";
    case 0x04: return "mouse middle";
    case 0x09: return "Tab: hotkey dispatcher 0x00efbfd0";
    case 0x0d: return "Enter: chat input";
    case 0x10: return "Shift: held modifier (attack in place / no move)";
    case 0x11: return "Ctrl: held modifier";
    case 0x12: return "Alt: held modifier (item names, 0x0107e99a)";
    case 0x1b: return "Esc: close window / game menu";
    case 0x20: return "Space: 0x00efd9ab";
    case 0x51: case 0x57: case 0x45: case 0x52: return "Q/W/E/R: item hotkey slots (0x00efbfd0 ids 0x10-0x13)";
    case 0x70: return "F1: help";
    case 0x25: case 0x26: case 0x27: case 0x28: return "arrows: UI list navigation";
    default:
        if (vk >= 0x30 && vk <= 0x39)
            return "digit: skill hotkey (0x00be808b)";
        if (vk >= 0x41 && vk <= 0x5a)
            return "letter: UI panel toggle (0x00efbfd0)";
        return NULL;
    }
}

static void log_line(mu_frame_world *w, const char *text)
{
    if (w->log_count < MU_FRAME_LOG)
        snprintf(w->log[w->log_count++], sizeof w->log[0], "%s", text);
}

void mu_frame_world_init(mu_frame_world *w, uint32_t window_width, uint32_t window_height, int32_t tile_x,
                         int32_t tile_y)
{
    memset(w, 0, sizeof *w);
    w->view.window_width = window_width;
    w->view.window_height = window_height;
    /* Defaults of the original MU source (CameraFOV 35, near 20) used as
     * placeholders: the per-world FOV comes from world data not decoded here. */
    w->view.fov = 35.0f;
    w->view.view_near = 20.0f;
    w->view.view_far = 2000.0f;
    w->mouse.scale_x = (float)window_width / 640.0f;
    w->mouse.scale_y = (float)window_height / 480.0f;
    w->mouse.x = 320;
    w->mouse.y = 240;
    w->terrain.height = w->heights;
    w->terrain.wall = w->walls;
    w->terrain.water_height = 0.0f;
    w->hero[0] = (float)tile_x * 100.0f + 50.0f;
    w->hero[1] = (float)tile_y * 100.0f + 50.0f;
    w->hero[2] = 0.0f;
    w->target_tile[0] = tile_x;
    w->target_tile[1] = tile_y;
    w->walk_speed = 15.0f;
    mu_world_camera *c = &w->camera;
    c->scene = 6;
    c->world = 0;
    c->world_fov = 35.0f;
    c->far_scale[0] = c->far_scale[1] = c->far_scale[2] = 1.0f;
    c->distance = 1000.0f;
    c->distance_target = 1000.0f;
    c->hero_tile_x = tile_x;
    c->hero_tile_y = tile_y;
    memcpy(c->hero_position, w->hero, sizeof w->hero);
    mu_world_camera_enter(c, &w->view);
    w->view.fov = c->world_fov;
    w->sample.active = 1;
    w->sample.game_foreground = 1;
    w->sample.focus_is_foreground = 1;
    w->clock.accumulator = 40;
}

void mu_frame_world_key(mu_frame_world *w, int vk, int down)
{
    if (vk > 0 && vk < 256)
        w->sample.down[vk] = down ? 1 : 0;
}

void mu_frame_world_message(mu_frame_world *w, uint32_t message, uint32_t wparam, uint32_t lparam)
{
    switch (message) {
    case MU_WM_LBUTTONDOWN: case MU_WM_LBUTTONUP: mu_frame_world_key(w, 0x01, message == MU_WM_LBUTTONDOWN); break;
    case MU_WM_RBUTTONDOWN: case MU_WM_RBUTTONUP: mu_frame_world_key(w, 0x02, message == MU_WM_RBUTTONDOWN); break;
    case MU_WM_MBUTTONDOWN: case MU_WM_MBUTTONUP: mu_frame_world_key(w, 0x04, message == MU_WM_MBUTTONDOWN); break;
    default: break;
    }
    if (message == 0x100 || message == 0x101)  /* WM_KEYDOWN/UP: 0x0bdc5982 */
        w->sample.key_message_down = message == 0x100;
    float zoom = mu_mouse_message(&w->mouse, message, wparam, lparam);
    if (message == MU_WM_MOUSEWHEEL && zoom != 0.0f) {
        if (mu_world_camera_wheel(&w->camera, &w->view, zoom, 0)) {
            char text[64];
            snprintf(text, sizeof text, "wheel: zoom index %d -> fov %.1f", w->camera.zoom_index, (double)w->camera.fov_to);
            log_line(w, text);
        }
    }
}

static void hero_walk(mu_frame_world *w)
{
    if (!w->moving)
        return;
    float dx = w->target[0] - w->hero[0], dy = w->target[1] - w->hero[1];
    float length = sqrtf(dx * dx + dy * dy);
    if (length <= w->walk_speed) {
        w->hero[0] = w->target[0];
        w->hero[1] = w->target[1];
        w->moving = 0;
    } else {
        w->hero[0] += dx / length * w->walk_speed;
        w->hero[1] += dy / length * w->walk_speed;
    }
    if (length > 0.0f)
        w->hero_angle = (float)(atan2((double)dy, (double)dx) * 180.0 / 3.14159265358979323846) + 90.0f;
    int32_t tx = (int32_t)(w->hero[0] / 100.0f), ty = (int32_t)(w->hero[1] / 100.0f);
    if (tx >= 0 && tx < MU_TERRAIN_SIZE && ty >= 0 && ty < MU_TERRAIN_SIZE)
        w->hero[2] = w->heights[ty * MU_TERRAIN_SIZE + tx];
}

void mu_frame_world_step(mu_frame_world *w)
{
    /* 0x00ec5475 runs first in every logic step */
    mu_key_scan(&w->keys, &w->sample);
    for (int vk = 1; vk < 256; ++vk)
        if (mu_key_is(&w->keys, w->sample.active, vk, MU_KEY_PRESS) && vk != 0x01) {
            const char *action = mu_vk_action(vk);
            if (action) {
                char text[64];
                snprintf(text, sizeof text, "vk 0x%02x %s", vk, action);
                log_line(w, text);
            }
        }
    /* MoveHero 0x016a9150: left button pushed (or held), Shift not held ->
     * RenderTerrain(1) pick with the ray of the last render pass. */
    int shift = mu_key_is(&w->keys, w->sample.active, 0x10, MU_KEY_REPEAT);
    if ((w->mouse.left_push || w->mouse.left) && !shift) {
        int32_t tx, ty;
        int32_t hx = (int32_t)(w->hero[0] / 100.0f), hy = (int32_t)(w->hero[1] / 100.0f);
        int32_t r = 24;
        int32_t lo_x = hx - r < 0 ? 0 : hx - r, lo_y = hy - r < 0 ? 0 : hy - r;
        int32_t hi_x = hx + r > MU_TERRAIN_SIZE - 2 ? MU_TERRAIN_SIZE - 2 : hx + r;
        int32_t hi_y = hy + r > MU_TERRAIN_SIZE - 2 ? MU_TERRAIN_SIZE - 2 : hy + r;
        ++w->picks;
        if (mu_terrain_pick(&w->pick, &w->view, &w->terrain, lo_x, lo_y, hi_x, hi_y, &tx, &ty)) {
            ++w->pick_hits;
            w->target_tile[0] = tx;
            w->target_tile[1] = ty;
            memcpy(w->target, w->pick.collision, sizeof w->target);
            w->moving = 1;
            if (w->mouse.left_push) {
                char text[64];
                snprintf(text, sizeof text, "click-to-move: tile %d,%d", tx, ty);
                log_line(w, text);
            }
        }
        w->mouse.left_push = 0;
    }
    hero_walk(w);
}

int32_t mu_frame_world_update(mu_frame_world *w, uint32_t now)
{
    int32_t steps = 0;
    w->now = now;
    mu_frame_begin(&w->clock);
    while (mu_frame_logic_step(&w->clock)) {
        mu_frame_world_step(w);
        ++steps;
    }
    return steps;
}

void mu_frame_world_begin_render(mu_frame_world *w, uint32_t now)
{
    mu_world_camera *c = &w->camera;
    w->now = now;
    mu_frame_render_start(&w->clock, now);
    memcpy(c->hero_position, w->hero, sizeof w->hero);
    c->hero_tile_x = (int32_t)(w->hero[0] / 100.0f);
    c->hero_tile_y = (int32_t)(w->hero[1] / 100.0f);
    c->hero_tile_wall = 0;
    if (c->hero_tile_x >= 0 && c->hero_tile_x < MU_TERRAIN_SIZE && c->hero_tile_y >= 0 && c->hero_tile_y < MU_TERRAIN_SIZE)
        c->hero_tile_wall = w->walls[c->hero_tile_y * MU_TERRAIN_SIZE + c->hero_tile_x];
    /* main render 0x0185916b: MoveMainCamera, BeginOpengl, CreateScreenVector */
    mu_move_main_camera(c, &w->view, w->now);
    mu_view_begin_opengl(&w->view, 0, 0, 640, 480);
    mu_view_create_screen_vector(&w->view, (float)w->mouse.x, (float)w->mouse.y, w->view.mouse_target, 1);
}

int32_t mu_frame_world_end_render(mu_frame_world *w)
{
    return mu_frame_finish(&w->clock);
}

static void corner(const mu_render_backend *b, const float color[3], float x, float y, float z)
{
    const float v[3] = {x, y, z};
    b->sink.color3(b->sink.context, color);
    b->sink.vertex(b->sink.context, v);
}

static long quad(const mu_render_backend *b, const float color[3], const float a[3], const float c[3],
                 const float d[3], const float e[3])
{
    corner(b, color, a[0], a[1], a[2]);
    corner(b, color, c[0], c[1], c[2]);
    corner(b, color, d[0], d[1], d[2]);
    corner(b, color, a[0], a[1], a[2]);
    corner(b, color, d[0], d[1], d[2]);
    corner(b, color, e[0], e[1], e[2]);
    return 2;
}

long mu_frame_draw_world(const mu_frame_world *w, const mu_render_backend *b, int32_t radius, int draw_box)
{
    mu_meshdraw_state state;
    mu_meshdraw_state_defaults(&state);   /* depth test/mask on, blend off (GL_ONE, GL_ZERO) */
    state.cull = 0;
    state.texture = 0;
    long triangles = 0;
    b->prepare(b->context, &state, -1);
    b->begin(b->context);
    int32_t hx = (int32_t)(w->hero[0] / 100.0f), hy = (int32_t)(w->hero[1] / 100.0f);
    for (int32_t y = hy - radius; y <= hy + radius; ++y)
        for (int32_t x = hx - radius; x <= hx + radius; ++x) {
            if (x < 0 || y < 0 || x >= MU_TERRAIN_SIZE - 1 || y >= MU_TERRAIN_SIZE - 1)
                continue;
            float shade = ((x + y) & 1) ? 0.42f : 0.36f;
            float color[3] = {shade * 0.55f, shade, shade * 0.45f};
            if (x % 10 == 0 || y % 10 == 0) {
                color[0] *= 0.6f;
                color[1] *= 0.6f;
                color[2] *= 0.6f;
            }
            const float *h = w->heights;
            float v0[3] = {(float)x * 100.0f, (float)y * 100.0f, h[y * MU_TERRAIN_SIZE + x]};
            float v1[3] = {v0[0] + 100.0f, v0[1], h[y * MU_TERRAIN_SIZE + x + 1]};
            float v2[3] = {v0[0] + 100.0f, v0[1] + 100.0f, h[(y + 1) * MU_TERRAIN_SIZE + x + 1]};
            float v3[3] = {v0[0], v0[1] + 100.0f, h[(y + 1) * MU_TERRAIN_SIZE + x]};
            triangles += quad(b, color, v0, v1, v2, v3);
        }
    if (w->moving) {
        const float red[3] = {0.9f, 0.15f, 0.1f};
        float t[3] = {w->target[0], w->target[1], w->target[2] + 2.0f};
        float a[3] = {t[0], t[1] - 30.0f, t[2]}, c[3] = {t[0] + 30.0f, t[1], t[2]};
        float d[3] = {t[0], t[1] + 30.0f, t[2]}, e[3] = {t[0] - 30.0f, t[1], t[2]};
        triangles += quad(b, red, a, c, d, e);
    }
    if (draw_box) {
        const float s = 35.0f, height = 160.0f;
        const float *p = w->hero;
        float lo[3] = {p[0] - s, p[1] - s, p[2]}, hi[3] = {p[0] + s, p[1] + s, p[2] + height};
        const float side[3] = {0.75f, 0.62f, 0.25f}, top[3] = {0.95f, 0.85f, 0.4f};
        float c000[3] = {lo[0], lo[1], lo[2]}, c100[3] = {hi[0], lo[1], lo[2]}, c110[3] = {hi[0], hi[1], lo[2]};
        float c010[3] = {lo[0], hi[1], lo[2]}, c001[3] = {lo[0], lo[1], hi[2]}, c101[3] = {hi[0], lo[1], hi[2]};
        float c111[3] = {hi[0], hi[1], hi[2]}, c011[3] = {lo[0], hi[1], hi[2]};
        triangles += quad(b, side, c000, c100, c101, c001);
        triangles += quad(b, side, c100, c110, c111, c101);
        triangles += quad(b, side, c110, c010, c011, c111);
        triangles += quad(b, side, c010, c000, c001, c011);
        triangles += quad(b, top, c001, c101, c111, c011);
    }
    b->end(b->context);
    return triangles;
}
