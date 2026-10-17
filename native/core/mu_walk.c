/* Walk-around session. See mu_walk.h. */
#include "mu_walk.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- camera record ---- */

static int same_text(const char *a, const char *b, size_t n)
{
    for (size_t i = 0; i < n; ++i)
        if (tolower((unsigned char)a[i]) != tolower((unsigned char)b[i]))
            return 0;
    return 1;
}

/* GetPrivateProfileStringA on an in-memory INI: case-insensitive section and
 * key, surrounding blanks dropped, at most size - 1 characters copied,
 * default "" when absent. */
static void profile_string(const char *text, size_t length, const char *section, const char *key, char *out,
                           size_t size)
{
    out[0] = 0;
    int in_section = 0;
    size_t i = 0;
    while (i < length) {
        size_t end = i;
        while (end < length && text[end] != '\n' && text[end] != '\r')
            ++end;
        size_t a = i, b = end;
        while (a < b && isspace((unsigned char)text[a]))
            ++a;
        while (b > a && isspace((unsigned char)text[b - 1]))
            --b;
        if (a < b && text[a] == '[') {
            size_t close = a + 1;
            while (close < b && text[close] != ']')
                ++close;
            size_t n = close - (a + 1);
            in_section = n == strlen(section) && same_text(text + a + 1, section, n);
        } else if (in_section && a < b) {
            size_t eq = a;
            while (eq < b && text[eq] != '=')
                ++eq;
            if (eq < b) {
                size_t ke = eq;
                while (ke > a && isspace((unsigned char)text[ke - 1]))
                    --ke;
                if (ke - a == strlen(key) && same_text(text + a, key, ke - a)) {
                    size_t v = eq + 1;
                    while (v < b && isspace((unsigned char)text[v]))
                        ++v;
                    size_t n = b - v;
                    if (n > size - 1)
                        n = size - 1;
                    memcpy(out, text + v, n);
                    out[n] = 0;
                    return;
                }
            }
        }
        i = end + 1;
    }
}

static float profile_float(const char *text, size_t length, const char *section, const char *key, size_t size)
{
    char value[64];
    profile_string(text, length, section, key, value, size);
    return (float)strtod(value, NULL);   /* CRT atof 0x01985654, then fstp dword */
}

void mu_camera_info_parse(const char *text, size_t size, mu_camera_info *info)
{
    /* 0x0098b27b..0x0098b476: buffer sizes 0xb (angles, distances, FOV) and 0x1e (positions) */
    info->angle[0] = profile_float(text, size, "CAMERA ANGLE", "Angle X", 0xb);
    info->angle[1] = profile_float(text, size, "CAMERA ANGLE", "Angle Y", 0xb);
    info->angle[2] = profile_float(text, size, "CAMERA ANGLE", "Angle Z", 0xb);
    info->position[0] = profile_float(text, size, "CAMERA POSITION", "Position X", 0x1e);
    info->position[1] = profile_float(text, size, "CAMERA POSITION", "Position Y", 0x1e);
    info->position[2] = profile_float(text, size, "CAMERA POSITION", "Position Z", 0x1e);
    info->distance = profile_float(text, size, "CAMERA DISTANCE", "Distance", 0xb);
    info->z_distance = profile_float(text, size, "CAMERA DISTANCE", "Z_Distance", 0xb);
    info->fov = profile_float(text, size, "CAMERA FOV", "FOV", 0xb);
}

static uint8_t *read_file(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *data = n > 0 ? malloc((size_t)n) : NULL;
    if (data && fread(data, 1, (size_t)n, f) != (size_t)n) {
        free(data);
        data = NULL;
    }
    fclose(f);
    *size = data ? (size_t)n : 0;
    return data;
}

static int load_record(const char *path, mu_camera_info *info, char *error, size_t error_size)
{
    size_t size = 0;
    uint8_t *file = read_file(path, &size);
    if (!file)
        return 1;
    size_t plain_size = 0;
    uint8_t *plain = mu_world_decrypt(file, size, "MAP\x01", &plain_size, error, error_size);
    free(file);
    if (!plain)
        return 2;
    mu_camera_info_parse((const char *)plain, plain_size, info);
    free(plain);
    return 0;
}

int mu_camera_info_load(const char *root, int32_t folder, mu_camera_info *info, char *error, size_t error_size)
{
    char path[4096];
    memset(info, 0, sizeof *info);
    /* 0x0098b55e: the record keyed by the folder number, else key 0 */
    snprintf(path, sizeof path, "%s/Data/World%d/Camera_Angle_Position.bmd", root, folder);
    int status = load_record(path, info, error, error_size);
    if (status == 0) {
        info->key = folder;
        return 0;
    }
    if (status == 2)
        return 1;
    snprintf(path, sizeof path, "%s/Data/G_Camera_Angle_Position.bmd", root);
    status = load_record(path, info, error, error_size);
    if (status == 1)
        snprintf(error, error_size, "%s: missing", path);
    info->key = 0;
    return status ? 1 : 0;
}

/* ---- placeholder path ---- */

static int32_t cell_index(int32_t x, int32_t y)
{
    return (int32_t)(((uint32_t)y & 0xffu) << 8) + (int32_t)((uint32_t)x & 0xffu);
}

static int blocked(const uint16_t *attributes, int32_t x, int32_t y, int32_t wall_mode)
{
    if (x < 0 || y < 0 || x > 255 || y > 255)
        return 1;
    return (int32_t)attributes[cell_index(x, y)] >= wall_mode;   /* 0x012b2584: map value >= wall blocks */
}

static int32_t sign(int32_t v)
{
    return v > 0 ? 1 : v < 0 ? -1 : 0;
}

int32_t mu_walk_straight_path(const uint16_t *attributes, int32_t sx, int32_t sy, int32_t tx, int32_t ty,
                              int32_t wall_mode, mu_path *path)
{
    memset(path, 0, sizeof *path);
    int32_t x = sx, y = sy, n = 0;
    path->x[n] = (uint8_t)x;
    path->y[n++] = (uint8_t)y;
    while (n < MU_PATH_CELLS && (x != tx || y != ty)) {
        int32_t dx = sign(tx - x), dy = sign(ty - y);
        if (!blocked(attributes, x + dx, y + dy, wall_mode)) {
            x += dx;
            y += dy;
        } else if (dx && dy && !blocked(attributes, x + dx, y, wall_mode)) {
            x += dx;
        } else if (dx && dy && !blocked(attributes, x, y + dy, wall_mode)) {
            y += dy;
        } else {
            break;
        }
        path->x[n] = (uint8_t)x;
        path->y[n++] = (uint8_t)y;
    }
    path->count = (uint8_t)n;
    return n;
}

/* ---- session ---- */

static void log_line(mu_walk *w, const char *text)
{
    if (w->log_count < MU_WALK_LOG)
        snprintf(w->log[w->log_count++], sizeof w->log[0], "%s", text);
}

static float ground(const mu_walk *w, float x, float y)
{
    /* RequestTerrainHeight 0x016cc9e2 in scene 6 */
    return mu_request_terrain_height(w->map->height, w->map->attributes, w->map->water_height, 6, x, y);
}

static void set_action(mu_walk *w, int32_t action, float speed)
{
    mu_hero *h = &w->hero;
    if (mu_set_action(&h->action, &h->prior_action, &h->frame, &h->prior_frame, w->action_count, action))
        h->action_changed = 1;
    h->play_speed = speed;
}

void mu_walk_init(mu_walk *w, mu_world *map, const mu_camera_info *info, uint32_t window_width,
                  uint32_t window_height, int32_t tile_x, int32_t tile_y, float angle_z, uint8_t class_byte,
                  int32_t action_count, float near_plane)
{
    memset(w, 0, sizeof *w);
    mu_frame_world *f = &w->frame;
    mu_frame_world_init(f, window_width, window_height, tile_x, tile_y);
    memcpy(f->heights, map->height, sizeof f->heights);
    memcpy(f->walls, map->attributes, sizeof f->walls);
    f->terrain.water_height = map->water_height;
    w->map = map;
    w->world = map->world;
    w->camera_info = *info;
    w->action_count = action_count;
    /* OpenWorld 0x0182876e: CameraFOV = world FOV (0x0098c5d6), zoom index 2;
     * MoveMainCamera's far = 2000 * Distance * Z_Distance * scale (0x0098ac45),
     * scale (+0x10) = 1 outside the FOV-65 camera mode. */
    mu_world_camera *c = &f->camera;
    c->world = map->world;
    c->world_fov = info->fov;
    c->far_scale[0] = info->distance;
    c->far_scale[1] = info->z_distance;
    c->far_scale[2] = 1.0f;
    f->view.fov = info->fov;
    f->view.view_near = near_plane;
    mu_world_camera_enter(c, &f->view);
    mu_hero *h = &w->hero;
    h->class_byte = class_byte;
    h->tile[0] = tile_x;
    h->tile[1] = tile_y;
    h->position[0] = (float)tile_x * 100.0f + 50.0f;
    h->position[1] = (float)tile_y * 100.0f + 50.0f;
    h->position[2] = ground(w, h->position[0], h->position[1]);
    h->angle[2] = angle_z;
    h->action = (uint16_t)mu_player_stop_action(class_byte);
    h->prior_action = h->action;
    h->play_speed = mu_player_stop_speed(h->action);
    h->safe_zone = (uint8_t)(map->attributes[cell_index(tile_x, tile_y)] & 1);
    memcpy(f->hero, h->position, sizeof f->hero);
    w->target[0] = tile_x;
    w->target[1] = tile_y;
}

void mu_walk_message(mu_walk *w, uint32_t message, uint32_t wparam, uint32_t lparam)
{
    mu_frame_world_message(&w->frame, message, wparam, lparam);
}

void mu_walk_key(mu_walk *w, int vk, int down)
{
    mu_frame_world_key(&w->frame, vk, down);
}

/* The hero branch of MoveHero for Movement set and movement type 0
 * (0x016a9a74..0x016a9cf2, no buff or auto-move state). */
static void hero_walk(mu_walk *w)
{
    mu_hero *h = &w->hero;
    if (!h->movement)
        return;
    /* SetPlayerWalk 0x0139002a: run counter, walk action and its PlaySpeed */
    h->run = mu_player_walk_run(h->class_byte, h->safe_zone, w->world, h->run);
    float speed;
    int32_t action = mu_player_walk_action(h->class_byte, h->run, &speed);
    set_action(w, action, speed);
    if (mu_move_path(&h->path, h->tile, h->position, h->angle, 1)) {
        /* 0x016a8904(c, 1): stop position packet, Movement = 0; then
         * SetPlayerStop 0x0138fe69: run counter 0, stand action */
        h->movement = 0;
        h->run = 0;
        action = mu_player_stop_action(h->class_byte);
        set_action(w, action, mu_player_stop_speed(action));
        ++w->arrivals;
        char text[80];
        snprintf(text, sizeof text, "arrived: tile %d,%d", h->tile[0], h->tile[1]);
        log_line(w, text);
        return;
    }
    /* MoveCharacterPosition 0x0137b351 with CharacterMoveSpeed 0x013957b5 */
    mu_move_speed_input in;
    memset(&in, 0, sizeof in);
    in.object_type = 0xa91;      /* Player */
    in.object_kind = 1;
    in.helper_type = 0xffff;     /* no pet or mount */
    in.mount_type = 0xffff;
    in.safe_zone = h->safe_zone;
    in.wing_type = -1;
    int32_t world = w->world;    /* 0x009dacb8: the Chaos Castle group forces run speed */
    in.world_runs = (uint8_t)((world >= 0x12 && world <= 0x17) || world == 0x35 || world == 0x61);
    mu_position_input p;
    memset(&p, 0, sizeof p);
    p.speed = mu_character_move_speed(&in, &h->run);
    p.world = world;
    p.helper_type = 0xffff;
    p.safe_zone = h->safe_zone;
    p.object_type = 0xa91;
    p.height = w->map->height;
    p.wall = w->map->attributes;
    p.special_height = w->map->water_height;
    p.scene_state = 6;
    float before[2] = {h->position[0], h->position[1]};
    mu_move_character_position(&p, h->position, h->angle, &h->timer);
    double dx = (double)h->position[0] - (double)before[0], dy = (double)h->position[1] - (double)before[1];
    w->position_distance += sqrt(dx * dx + dy * dy);
    ++w->position_steps;
}

/* The click start of MoveHero (0x016ac4b4..0x016ace4f, plain terrain click). */
static void hero_click(mu_walk *w)
{
    mu_frame_world *f = &w->frame;
    mu_hero *h = &w->hero;
    int shift = mu_key_is(&f->keys, f->sample.active, 0x10, MU_KEY_REPEAT);
    if (!(f->mouse.left_push || f->mouse.left) || shift)
        return;
    int pushed = f->mouse.left_push;
    f->mouse.left_push = 0;
    int32_t hx = (int32_t)(h->position[0] / 100.0f), hy = (int32_t)(h->position[1] / 100.0f);
    const int32_t r = 30;   /* viewer box around the hero (the client walks its visible box) */
    int32_t lo_x = hx - r < 0 ? 0 : hx - r, lo_y = hy - r < 0 ? 0 : hy - r;
    int32_t hi_x = hx + r > MU_TERRAIN_SIZE - 2 ? MU_TERRAIN_SIZE - 2 : hx + r;
    int32_t hi_y = hy + r > MU_TERRAIN_SIZE - 2 ? MU_TERRAIN_SIZE - 2 : hy + r;
    int32_t tx, ty;
    ++f->picks;
    if (!mu_terrain_pick(&f->pick, &f->view, &f->terrain, lo_x, lo_y, hi_x, hi_y, &tx, &ty))
        return;
    ++f->pick_hits;
    /* 0x016ac544: TargetX/Y = (uint8)(int)(CollisionPosition / 100) */
    w->target[0] = mu_cvtt(f->pick.collision[0] / 100.0f) & 0xff;
    w->target[1] = mu_cvtt(f->pick.collision[1] / 100.0f) & 0xff;
    memcpy(f->target, f->pick.collision, sizeof f->target);
    /* 0x016acce8: while moving, re-path only within one tile of the position */
    if (h->movement) {
        int32_t px = mu_cvtt(h->position[0] * 0.01f), py = mu_cvtt(h->position[1] * 0.01f);
        if (abs(h->tile[0] - px) >= 2 || abs(h->tile[1] - py) >= 2)
            return;
    }
    if (h->tile[0] == w->target[0] && h->tile[1] == w->target[1] && h->movement)
        return;
    /* PathFinding2 0x012b0e85(PositionX, PositionY, TargetX, TargetY, &Path, 0, 2):
     * placeholder straight path; wall mode 4 when the start tile is a safe
     * zone or the target is a safe tile without a character (0x012b0f2c). */
    mu_path path;
    int32_t n = mu_walk_straight_path(w->map->attributes, h->tile[0], h->tile[1], w->target[0], w->target[1], 2, &path);
    if (n <= 1) {
        uint16_t start = w->map->attributes[cell_index(h->tile[0], h->tile[1])];
        uint16_t goal = w->map->attributes[cell_index(w->target[0], w->target[1])];
        if ((start & 1) || ((goal & 1) && !(goal & 2)))
            n = mu_walk_straight_path(w->map->attributes, h->tile[0], h->tile[1], w->target[0], w->target[1], 4,
                                      &path);
    }
    if (n <= 1) {
        ++w->path_refused;
        return;
    }
    h->path = path;      /* current = 0, sub-step 0 */
    h->movement = 1;     /* SendMove 0x016b5cd0: Movement = 1 */
    ++w->moves;
    if (pushed) {
        char text[80];
        snprintf(text, sizeof text, "click-to-move: tile %d,%d (%d cells)", w->target[0], w->target[1], n);
        log_line(w, text);
    }
}

int mu_walk_animate(mu_walk *w, mu_character *character)
{
    mu_hero *h = &w->hero;
    mu_model *player = &character->player;
    if (h->action_changed) {
        /* SetAction 0x012affa4 on the object: prior = current, frame 0 */
        uint16_t prior = mu_model_action(player);
        float prior_frame = mu_model_frame(player);
        mu_character_set_state(character, h->action, 0.0f, prior_frame, prior);
        h->action_changed = 0;
    }
    uint8_t loop = 0;
    int status = mu_character_tick(character, h->play_speed, &loop);
    h->frame = mu_model_frame(player);
    h->prior_frame = mu_model_prior_frame(player);
    return status;
}

int mu_walk_place(const mu_walk *w, mu_character *character)
{
    for (int k = 0; k < 3; ++k) {
        character->params.position[k] = w->hero.position[k];
        character->params.angles[k] = w->hero.angle[k];
    }
    return mu_character_update(character);
}

void mu_walk_step(mu_walk *w, mu_character *character)
{
    mu_frame_world *f = &w->frame;
    /* 0x00ec5475 runs first in every logic step */
    mu_key_scan(&f->keys, &f->sample);
    /* MoveHero 0x016a9150 (in-world tick 0x01856d3a): walk, then click */
    hero_walk(w);
    hero_click(w);
    /* MoveCharacters 0x0137a7ce (0x01856eca): the character animation step */
    if (character)
        mu_walk_animate(w, character);
    ++w->steps;
}

int32_t mu_walk_update(mu_walk *w, uint32_t now, mu_character *character)
{
    int32_t steps = 0;
    w->frame.now = now;
    mu_frame_begin(&w->frame.clock);
    while (mu_frame_logic_step(&w->frame.clock)) {
        mu_walk_step(w, character);
        ++steps;
    }
    return steps;
}

void mu_walk_begin_render(mu_walk *w, uint32_t now)
{
    mu_frame_world *f = &w->frame;
    mu_world_camera *c = &f->camera;
    mu_hero *h = &w->hero;
    f->now = now;
    mu_frame_render_start(&f->clock, now);
    /* RenderCharacter 0x013b23f8 (visible characters): SafeZone = TerrainWall[tile] & 1 */
    h->safe_zone = (uint8_t)(w->map->attributes[cell_index(h->tile[0], h->tile[1])] & 1);
    memcpy(f->hero, h->position, sizeof f->hero);
    memcpy(c->hero_position, h->position, sizeof c->hero_position);
    c->hero_tile_x = h->tile[0];   /* Hero + 0x180 / + 0x184 */
    c->hero_tile_y = h->tile[1];
    c->hero_tile_wall = w->map->attributes[cell_index(h->tile[0], h->tile[1])];
    c->hero_byte4 = h->safe_zone;
    /* main render 0x0185916b: MoveMainCamera, BeginOpengl, CreateScreenVector */
    mu_move_main_camera(c, &f->view, now);
    mu_view_begin_opengl(&f->view, 0, 0, 640, 480);
    mu_view_create_screen_vector(&f->view, (float)f->mouse.x, (float)f->mouse.y, f->view.mouse_target, 1);
}

int32_t mu_walk_end_render(mu_walk *w)
{
    return mu_frame_finish(&w->frame.clock);
}
