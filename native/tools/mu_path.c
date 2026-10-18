/* mu-path: click-to-move demonstrator of the native path module (NATIVE-PATH-001).
 *
 *   mu-path find   SOURCE --from X,Y --to X,Y [--repath]      JSON: client path, search, walk
 *   mu-path render SOURCE --from X,Y --to X,Y --out PNG [--size N] [--margin T] [--no-terrain] [--repath]
 *   mu-path batch  SOURCE --count N --out-dir DIR [--seed S] [--size N]   random clicks, one PNG each
 *   mu-path att    ROOT --world W --out FILE|-                 the loaded 256 x 256 attribute cells (u16 LE)
 *
 * SOURCE is either `ROOT --world W` (the game directory containing Data/, read-only) or
 * `--synthetic open|noise|rooms|maze|safezone [--seed S]` (no client data).
 *
 * The search is the client's PathFinding2 with the hero click arguments (distance 0, level
 * TW_CHARACTER); the walk runs the client's 40 ms hero step (MovePath with turning, then
 * MoveCharacterPosition at the player base speed). --repath clicks the same target again
 * whenever the walker stops short of it (a demo choice: the client gets a new click from
 * the player). Nothing is sent anywhere: the network boundary is only counted ("sent").
 */
#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "../core/mu_path.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_terrain.h"

typedef struct args {
    const char *command, *root, *out, *synthetic, *out_dir;
    int32_t world, size, margin, count;
    int32_t from[2], to[2];
    int have_from, have_to, terrain, repath, run;
    uint32_t seed;
} args;

static int parse_pair(const char *v, int32_t out[2])
{
    return v && sscanf(v, "%d,%d", &out[0], &out[1]) == 2 ? 0 : 1;
}

static int parse(args *a, int argc, char **argv)
{
    memset(a, 0, sizeof *a);
    a->size = 768;
    a->margin = 6;
    a->terrain = 1;
    a->seed = 1;
    a->count = 8;
    if (argc < 2)
        return 1;
    a->command = argv[1];
    int i = 2;
    if (i < argc && argv[i][0] != '-')
        a->root = argv[i++];
    for (; i < argc; ++i) {
        const char *k = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(k, "--no-terrain")) {
            a->terrain = 0;
            continue;
        }
        if (!strcmp(k, "--repath")) {
            a->repath = 1;
            continue;
        }
        if (!strcmp(k, "--run")) {
            a->run = 1;
            continue;
        }
        if (!v)
            return 1;
        ++i;
        if (!strcmp(k, "--world"))
            a->world = atoi(v);
        else if (!strcmp(k, "--out"))
            a->out = v;
        else if (!strcmp(k, "--out-dir"))
            a->out_dir = v;
        else if (!strcmp(k, "--synthetic"))
            a->synthetic = v;
        else if (!strcmp(k, "--seed"))
            a->seed = (uint32_t)strtoul(v, NULL, 0);
        else if (!strcmp(k, "--size"))
            a->size = atoi(v);
        else if (!strcmp(k, "--margin"))
            a->margin = atoi(v);
        else if (!strcmp(k, "--count"))
            a->count = atoi(v);
        else if (!strcmp(k, "--from")) {
            if (parse_pair(v, a->from))
                return 1;
            a->have_from = 1;
        } else if (!strcmp(k, "--to")) {
            if (parse_pair(v, a->to))
                return 1;
            a->have_to = 1;
        } else
            return 1;
    }
    return (!a->root && !a->synthetic) || a->size < 64 || a->size > 8192;
}

/* ---- synthetic attribute maps (deterministic LCG; no client data) ---- */

static uint32_t lcg(uint32_t *s)
{
    *s = *s * 1103515245u + 12345u;
    return (*s >> 8) & 0xffffffu;
}

static int synthesize(const char *kind, uint32_t seed, uint16_t *grid)
{
    uint32_t s = seed ? seed : 1;
    if (!strcmp(kind, "open")) {
        memset(grid, 0, MU_PATH_CELLS * sizeof *grid);
    } else if (!strcmp(kind, "noise")) {
        for (int i = 0; i < MU_PATH_CELLS; i++)
            grid[i] = (lcg(&s) % 100) < 28 ? MU_TW_NOMOVE : 0;
    } else if (!strcmp(kind, "safezone")) {
        for (int i = 0; i < MU_PATH_CELLS; i++)
            grid[i] = (uint16_t)(MU_TW_SAFEZONE | ((lcg(&s) % 100) < 30 ? MU_TW_CHARACTER : 0));
    } else if (!strcmp(kind, "rooms")) {
        memset(grid, 0, MU_PATH_CELLS * sizeof *grid);
        for (int r = 0; r < 140; r++) {
            int x0 = (int)(lcg(&s) % 250), y0 = (int)(lcg(&s) % 250);
            int w = 3 + (int)(lcg(&s) % 26), h = 3 + (int)(lcg(&s) % 26);
            for (int y = y0; y < y0 + h && y < 256; y++)
                for (int x = x0; x < x0 + w && x < 256; x++)
                    if (x == x0 || y == y0 || x == x0 + w - 1 || y == y0 + h - 1)
                        grid[y * 256 + x] = MU_TW_NOMOVE;
            if (x0 + w / 2 < 256)
                grid[y0 * 256 + x0 + w / 2] = 0;   /* door */
        }
    } else if (!strcmp(kind, "maze")) {
        enum { CELLS = 64 };
        static uint8_t seen[CELLS * CELLS];
        static int16_t stack[CELLS * CELLS * 2];
        memset(seen, 0, sizeof seen);
        for (int i = 0; i < MU_PATH_CELLS; i++)
            grid[i] = MU_TW_NOMOVE;
        int top = 0;
        stack[top++] = (int16_t)(lcg(&s) % CELLS);
        stack[top++] = (int16_t)(lcg(&s) % CELLS);
        while (top) {
            int cx = stack[top - 2], cy = stack[top - 1];
            seen[cy * CELLS + cx] = 1;
            for (int o = 1; o <= 2; o++)
                for (int p = 1; p <= 2; p++)
                    grid[(cy * 4 + o) * 256 + cx * 4 + p] = 0;
            int options[4][2], n = 0;
            static const int d[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
            for (int k = 0; k < 4; k++) {
                int nx = cx + d[k][0], ny = cy + d[k][1];
                if (nx >= 0 && ny >= 0 && nx < CELLS && ny < CELLS && !seen[ny * CELLS + nx]) {
                    options[n][0] = d[k][0];
                    options[n][1] = d[k][1];
                    n++;
                }
            }
            if (!n) {
                top -= 2;
                continue;
            }
            int k = (int)(lcg(&s) % (uint32_t)n), dx = options[k][0], dy = options[k][1];
            for (int step = 1; step <= 3; step++)
                for (int o = 1; o <= 2; o++) {
                    if (dx)
                        grid[(cy * 4 + o) * 256 + cx * 4 + (dx > 0 ? 2 : 1) + dx * step] = 0;
                    else
                        grid[(cy * 4 + (dy > 0 ? 2 : 1) + dy * step) * 256 + cx * 4 + o] = 0;
                }
            stack[top++] = (int16_t)(cx + dx);
            stack[top++] = (int16_t)(cy + dy);
        }
    } else {
        return 1;
    }
    return 0;
}

/* ---- source ---- */

typedef struct source {
    mu_world *world;            /* NULL for synthetic maps */
    uint16_t attributes[MU_PATH_CELLS];
    char label[64];
} source;

static int load_source(const args *a, source *src, int textures)
{
    memset(src, 0, sizeof *src);
    if (a->synthetic) {
        if (synthesize(a->synthetic, a->seed, src->attributes)) {
            fprintf(stderr, "unknown synthetic map %s\n", a->synthetic);
            return 1;
        }
        snprintf(src->label, sizeof src->label, "synthetic-%s-%u", a->synthetic, a->seed);
        return 0;
    }
    char error[512];
    src->world = mu_world_load(a->root, a->world, 1, textures, error, sizeof error);
    if (!src->world) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    memcpy(src->attributes, src->world->attributes, sizeof src->attributes);
    snprintf(src->label, sizeof src->label, "world%d", a->world);
    return 0;
}

/* ---- search and walk ---- */

#define MAX_TRACE 20000

typedef struct run {
    int found, clicks;
    mu_client_path path;            /* first click */
    int32_t full_count;             /* nodes of the full BuildPath result (before the 15-node cap) */
    uint8_t full_x[MU_PATH_MAX_STEPS], full_y[MU_PATH_MAX_STEPS];
    int32_t pops, closed;
    uint8_t *closed_map;            /* explored tiles of the first search */
    float trace[MAX_TRACE][2];
    int32_t trace_count, steps, arrivals;
    int32_t end_tile[2];
    float end_angle;
    uint32_t sent;
} run;

static void simulate(const args *a, mu_pathing *pathing, run *r)
{
    mu_walker hero;
    mu_walker_place(&hero, a->from[0], a->from[1], 0.0f);
    r->closed_map = calloc(MU_PATH_CELLS, 1);
    r->trace[0][0] = hero.mover.position[0];
    r->trace[0][1] = hero.mover.position[1];
    r->trace_count = 1;
    int max_clicks = a->repath ? 40 : 1;
    for (int click = 0; click < max_clicks; click++) {
        int started = mu_walker_click(&hero, pathing, a->to[0], a->to[1]);
        if (click == 0) {
            mu_path_finder *f = &pathing->finder;
            r->found = started;
            r->path = hero.mover.path;
            r->pops = f->pops;
            r->full_count = started ? f->count : 0;
            if (started) {
                memcpy(r->full_x, mu_path_finder_x(f), (size_t)f->count);
                memcpy(r->full_y, mu_path_finder_y(f), (size_t)f->count);
            }
            for (int i = 0; i < MU_PATH_CELLS; i++)
                if (f->mark[i] & MU_PATH_CLOSED) {
                    r->closed_map[i] = 1;
                    r->closed++;
                }
        }
        if (!started)
            break;
        r->clicks++;
        for (int step = 0; step < 4000 && hero.moving; step++) {
            r->arrivals += mu_walker_step(&hero, a->run);
            r->steps++;
            if (r->trace_count < MAX_TRACE) {
                r->trace[r->trace_count][0] = hero.mover.position[0];
                r->trace[r->trace_count][1] = hero.mover.position[1];
                r->trace_count++;
            }
        }
        if (hero.mover.tile_x == (a->to[0] & 255) && hero.mover.tile_y == (a->to[1] & 255))
            break;
    }
    r->end_tile[0] = hero.mover.tile_x;
    r->end_tile[1] = hero.mover.tile_y;
    r->end_angle = hero.mover.angle[2];
    r->sent = hero.sent;
}

static void print_json(FILE *out, const args *a, const source *src, const run *r)
{
    fprintf(out, "{\"map\": \"%s\", \"from\": [%d, %d], \"to\": [%d, %d], \"found\": %d, ", src->label, a->from[0],
            a->from[1], a->to[0], a->to[1], r->found);
    fprintf(out, "\"path\": [");
    for (int i = 0; r->found && i < r->path.count; i++)
        fprintf(out, "%s[%u, %u]", i ? ", " : "", r->path.x[i], r->path.y[i]);
    fprintf(out, "], \"full_path_nodes\": %d, \"pops\": %d, \"explored\": %d, ", r->full_count, r->pops, r->closed);
    fprintf(out, "\"clicks\": %d, \"sent\": %u, \"steps\": %d, \"arrivals\": %d, \"end_tile\": [%d, %d], ", r->clicks,
            r->sent, r->steps, r->arrivals, r->end_tile[0], r->end_tile[1]);
    fprintf(out, "\"end_position\": [%.9g, %.9g], \"end_angle\": %.9g, \"reached\": %d}\n",
            (double)r->trace[r->trace_count - 1][0], (double)r->trace[r->trace_count - 1][1], (double)r->end_angle,
            r->end_tile[0] == (a->to[0] & 255) && r->end_tile[1] == (a->to[1] & 255));
}

/* ---- render ---- */

typedef struct canvas {
    uint8_t *rgba;
    int32_t size;
    float x0, y0, scale;   /* world units at pixel 0, pixels per world unit */
} canvas;

static void blend(canvas *c, int32_t px, int32_t py, const uint8_t rgb[3], float alpha)
{
    if (px < 0 || py < 0 || px >= c->size || py >= c->size)
        return;
    uint8_t *p = c->rgba + ((size_t)py * (size_t)c->size + (size_t)px) * 4;
    for (int k = 0; k < 3; k++)
        p[k] = (uint8_t)lrintf((float)p[k] * (1.0f - alpha) + (float)rgb[k] * alpha);
    p[3] = 255;
}

static void tile_rect(canvas *c, int32_t tx, int32_t ty, const uint8_t rgb[3], float alpha, int outline)
{
    int32_t x0 = (int32_t)floorf(((float)tx * 100.0f - c->x0) * c->scale);
    int32_t y0 = (int32_t)floorf(((float)ty * 100.0f - c->y0) * c->scale);
    int32_t x1 = (int32_t)floorf(((float)(tx + 1) * 100.0f - c->x0) * c->scale);
    int32_t y1 = (int32_t)floorf(((float)(ty + 1) * 100.0f - c->y0) * c->scale);
    for (int32_t y = y0; y < y1; y++)
        for (int32_t x = x0; x < x1; x++)
            if (!outline || x < x0 + 2 || y < y0 + 2 || x >= x1 - 2 || y >= y1 - 2)
                blend(c, x, y, rgb, alpha);
}

static void dot(canvas *c, float wx, float wy, float radius, const uint8_t rgb[3], float alpha)
{
    float cx = (wx - c->x0) * c->scale, cy = (wy - c->y0) * c->scale;
    for (int32_t y = (int32_t)(cy - radius) - 1; y <= (int32_t)(cy + radius) + 1; y++)
        for (int32_t x = (int32_t)(cx - radius) - 1; x <= (int32_t)(cx + radius) + 1; x++) {
            float dx = (float)x + 0.5f - cx, dy = (float)y + 0.5f - cy;
            if (dx * dx + dy * dy <= radius * radius)
                blend(c, x, y, rgb, alpha);
        }
}

static void line(canvas *c, float ax, float ay, float bx, float by, float width, const uint8_t rgb[3], float alpha)
{
    float length = hypotf(bx - ax, by - ay) * c->scale;
    int n = (int)length + 1;
    for (int i = 0; i <= n; i++) {
        float t = (float)i / (float)n;
        dot(c, ax + (bx - ax) * t, ay + (by - ay) * t, width, rgb, alpha);
    }
}

static int render(const args *a, source *src, mu_pathing *pathing, const run *r, const char *out)
{
    /* box: from, to, path, explored tiles, plus a margin, square, inside 0..254 */
    int32_t bx0 = a->from[0] < a->to[0] ? a->from[0] : a->to[0], bx1 = a->from[0] < a->to[0] ? a->to[0] : a->from[0];
    int32_t by0 = a->from[1] < a->to[1] ? a->from[1] : a->to[1], by1 = a->from[1] < a->to[1] ? a->to[1] : a->from[1];
    for (int i = 0; i < MU_PATH_CELLS; i++)
        if (r->closed_map[i]) {
            int32_t x = i % 256, y = i / 256;
            if (x < bx0) bx0 = x;
            if (x > bx1) bx1 = x;
            if (y < by0) by0 = y;
            if (y > by1) by1 = y;
        }
    bx0 -= a->margin; by0 -= a->margin; bx1 += a->margin; by1 += a->margin;
    int32_t span = (bx1 - bx0 > by1 - by0 ? bx1 - bx0 : by1 - by0) + 1;
    if (span > 255)
        span = 255;
    int32_t cx = (bx0 + bx1) / 2, cy = (by0 + by1) / 2;
    bx0 = cx - span / 2;
    by0 = cy - span / 2;
    if (bx0 < 0) bx0 = 0;
    if (by0 < 0) by0 = 0;
    if (bx0 + span > 255) bx0 = 255 - span;
    if (by0 + span > 255) by0 = 255 - span;
    bx1 = bx0 + span - 1;
    by1 = by0 + span - 1;

    canvas c = {calloc((size_t)a->size * (size_t)a->size, 4), a->size, (float)bx0 * 100.0f, (float)by0 * 100.0f,
                (float)a->size / ((float)span * 100.0f)};
    if (!c.rgba)
        return 1;
    if (src->world && a->terrain) {
        mu_raster raster;
        if (mu_raster_init(&raster, a->size, a->size)) {
            free(c.rgba);
            return 1;
        }
        mu_world_frame(src->world, 0.0f);
        /* top-down orthographic view: x right, y down, higher z nearer */
        float wx0 = c.x0, wx1 = c.x0 + (float)span * 100.0f, wy0 = c.y0, wy1 = c.y0 + (float)span * 100.0f;
        memset(raster.view, 0, sizeof raster.view);
        raster.view[0] = raster.view[5] = raster.view[10] = raster.view[15] = 1.0f;
        memset(raster.projection, 0, sizeof raster.projection);
        raster.projection[0] = 2.0f / (wx1 - wx0);
        raster.projection[12] = -(wx1 + wx0) / (wx1 - wx0);
        raster.projection[5] = -2.0f / (wy1 - wy0);
        raster.projection[13] = (wy1 + wy0) / (wy1 - wy0);
        raster.projection[10] = -1.0f / 20000.0f;
        raster.projection[14] = 0.0f;
        raster.projection[15] = 1.0f;
        raster.front_ccw = 0;
        static const uint8_t background[4] = {0, 0, 0, 255};
        mu_raster_clear(&raster, background);
        mu_world_draw_stats stats;
        int32_t dx1 = bx1 < 254 ? bx1 : 254, dy1 = by1 < 254 ? by1 : 254;
        mu_world_draw_raster(src->world, &raster, bx0, by0, dx1, dy1, &stats);
        memcpy(c.rgba, raster.color, (size_t)a->size * (size_t)a->size * 4);
        mu_raster_free(&raster);
    } else {
        for (int32_t y = 0; y < a->size; y++)
            for (int32_t x = 0; x < a->size; x++) {
                uint8_t *p = c.rgba + ((size_t)y * (size_t)a->size + (size_t)x) * 4;
                p[0] = 92;
                p[1] = 104;
                p[2] = 84;
                p[3] = 255;
            }
    }
    static const uint8_t red[3] = {220, 40, 30}, blue[3] = {60, 120, 255}, dark[3] = {10, 10, 10},
                         yellow[3] = {255, 220, 60}, cyan[3] = {40, 230, 255}, grey[3] = {200, 200, 200},
                         white[3] = {255, 255, 255}, orange[3] = {255, 140, 0}, green[3] = {40, 255, 80},
                         magenta[3] = {255, 60, 220};
    for (int32_t ty = by0; ty <= by1; ty++)
        for (int32_t tx = bx0; tx <= bx1; tx++) {
            uint16_t w = pathing->wall[ty * 256 + tx];
            if (w & MU_TW_NOGROUND)
                tile_rect(&c, tx, ty, dark, 0.55f, 0);
            else if ((w & MU_PATH_WALL_MASK) >= MU_TW_CHARACTER)
                tile_rect(&c, tx, ty, red, 0.38f, 0);
            if (w & MU_TW_SAFEZONE)
                tile_rect(&c, tx, ty, blue, 0.22f, 0);
            if (r->closed_map[ty * 256 + tx])
                tile_rect(&c, tx, ty, yellow, 0.22f, 0);
        }
    for (int i = r->path.count; r->found && i < r->full_count; i++)
        tile_rect(&c, r->full_x[i], r->full_y[i], grey, 0.8f, 1);
    for (int i = 0; r->found && i < r->path.count; i++)
        tile_rect(&c, r->path.x[i], r->path.y[i], cyan, 0.9f, 1);
    float width = c.scale * 7.0f < 1.0f ? 1.0f : c.scale * 7.0f;
    for (int i = 1; i < r->trace_count; i++)
        line(&c, r->trace[i - 1][0], r->trace[i - 1][1], r->trace[i][0], r->trace[i][1], width, white, 0.9f);
    for (int i = 0; i < r->trace_count; i++)
        dot(&c, r->trace[i][0], r->trace[i][1], width * 1.4f, orange, 1.0f);
    dot(&c, ((float)a->from[0] + 0.5f) * 100.0f, ((float)a->from[1] + 0.5f) * 100.0f, c.scale * 35.0f, green, 1.0f);
    float tx = ((float)a->to[0] + 0.5f) * 100.0f, ty = ((float)a->to[1] + 0.5f) * 100.0f;
    line(&c, tx - 35.0f, ty - 35.0f, tx + 35.0f, ty + 35.0f, width * 1.5f, magenta, 1.0f);
    line(&c, tx - 35.0f, ty + 35.0f, tx + 35.0f, ty - 35.0f, width * 1.5f, magenta, 1.0f);
    int failed = mu_png_write(out, c.rgba, a->size, a->size);
    char hash[65];
    mu_sha256_hex(c.rgba, (uint64_t)a->size * (uint64_t)a->size * 4, hash);
    fprintf(stderr, "%s: box %d,%d-%d,%d sha256 %s\n", out, bx0, by0, bx1, by1, hash);
    free(c.rgba);
    return failed;
}

/* ---- commands ---- */

static int pick_endpoints(args *a, const mu_pathing *pathing, uint32_t *s)
{
    for (int tries = 0; tries < 100000; tries++) {
        int32_t x = 1 + (int32_t)(lcg(s) % 254), y = 1 + (int32_t)(lcg(s) % 254);
        if (!mu_pathing_walkable(pathing, x, y))
            continue;
        int32_t span = 6 + (int32_t)(lcg(s) % 30);
        int32_t tx = x - span + (int32_t)(lcg(s) % (uint32_t)(2 * span + 1));
        int32_t ty = y - span + (int32_t)(lcg(s) % (uint32_t)(2 * span + 1));
        if (tx < 1 || ty < 1 || tx > 254 || ty > 254)
            continue;
        if ((lcg(s) % 5) && !mu_pathing_walkable(pathing, tx, ty))
            continue;
        a->from[0] = x;
        a->from[1] = y;
        a->to[0] = tx;
        a->to[1] = ty;
        return 0;
    }
    return 1;
}

static int command_att(const args *a)
{
    source *src = malloc(sizeof *src);
    if (!src || load_source(a, src, 0)) {
        free(src);
        return 1;
    }
    FILE *f = (!a->out || !strcmp(a->out, "-")) ? stdout : fopen(a->out, "wb");
    int failed = !f;
    for (int i = 0; f && i < MU_PATH_CELLS; i++) {
        uint8_t b[2] = {(uint8_t)(src->attributes[i] & 0xff), (uint8_t)(src->attributes[i] >> 8)};
        failed |= fwrite(b, 1, 2, f) != 2;
    }
    if (f && f != stdout)
        fclose(f);
    if (src->world)
        mu_world_free(src->world);
    free(src);
    return failed;
}

static int command_run(args *a, int draw)
{
    source *src = malloc(sizeof *src);
    mu_pathing *pathing = malloc(sizeof *pathing);
    run *r = calloc(1, sizeof *r);
    int status = 1;
    if (!src || !pathing || !r || load_source(a, src, draw && a->terrain))
        goto done;
    if (mu_pathing_init(pathing, src->attributes))
        goto done;
    if (!strcmp(a->command, "batch")) {
        if (!a->out_dir) {
            fprintf(stderr, "batch needs --out-dir\n");
            goto done_pathing;
        }
        mkdir(a->out_dir, 0755);
        uint32_t s = a->seed * 2654435761u + 7u;
        status = 0;
        for (int k = 0; k < a->count; k++) {
            if (pick_endpoints(a, pathing, &s))
                break;
            memset(r, 0, sizeof *r);
            simulate(a, pathing, r);
            print_json(stdout, a, src, r);
            char name[1024];
            snprintf(name, sizeof name, "%s/%s-%03d-%d_%d-to-%d_%d.png", a->out_dir, src->label, k, a->from[0],
                     a->from[1], a->to[0], a->to[1]);
            status |= render(a, src, pathing, r, name);
            free(r->closed_map);
            r->closed_map = NULL;
        }
        goto done_pathing;
    }
    if (!a->have_from || !a->have_to) {
        fprintf(stderr, "--from X,Y and --to X,Y are required\n");
        goto done_pathing;
    }
    simulate(a, pathing, r);
    print_json(stdout, a, src, r);
    status = 0;
    if (draw) {
        if (!a->out) {
            fprintf(stderr, "render needs --out\n");
            status = 1;
        } else {
            status = render(a, src, pathing, r, a->out);
        }
    }
    free(r->closed_map);
done_pathing:
    mu_pathing_free(pathing);
done:
    if (src && src->world)
        mu_world_free(src->world);
    free(src);
    free(pathing);
    free(r);
    return status;
}

int main(int argc, char **argv)
{
    args a;
    if (parse(&a, argc, argv)) {
        fprintf(stderr,
                "usage: mu-path find|render|batch (ROOT --world W | --synthetic open|noise|rooms|maze|safezone"
                " [--seed S])\n"
                "               [--from X,Y --to X,Y] [--out PNG] [--out-dir DIR --count N] [--size N]"
                " [--margin T]\n"
                "               [--no-terrain] [--repath] [--run]\n"
                "       mu-path att ROOT --world W --out FILE|-\n");
        return 2;
    }
    if (!strcmp(a.command, "att"))
        return command_att(&a);
    if (!strcmp(a.command, "find"))
        return command_run(&a, 0);
    if (!strcmp(a.command, "render") || !strcmp(a.command, "batch"))
        return command_run(&a, 1);
    fprintf(stderr, "unknown command %s\n", a.command);
    return 2;
}
