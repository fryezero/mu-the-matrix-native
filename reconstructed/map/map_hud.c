/* The map overlay's game side: the hudMap window object of the client
 * (NATIVE-MAP-001).  See map.h; addresses are the pinned capture's. */
#include "map.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

/* Planted mistakes for scripts/validate_map.py --mutations (0: none). */
#ifndef MU_MAP_MUTATION
#define MU_MAP_MUTATION 0
#endif

int mu_map_navimap_name(int32_t world, char *out, size_t cap)
{
    /* 0x00c6b116: eax = [0x01cf15fc] + 1; sprintf through a std::string formatter "navimap%02d.ozp" */
    return snprintf(out, cap, "navimap%02d.ozp", (int)(world + 1));
}

float mu_map_px_x(float tile_x)
{
    volatile float v = tile_x * 2.0f;       /* 0x00c6ba5c: mulss [0x01a7e474] (2.0) */
    return v;
}

float mu_map_px_y(float tile_y)
{
    volatile float v = (256.0f - tile_y) * 2.0f;   /* 0x00c6ba7d: [0x01a7fb20] (256.0) - v, * 2.0 */
    return v;
}

/* ucomiss a, b; lahf; test ah, 0x44; jnp: the "same value" test (ordered and equal). */
static int same(float a, float b)
{
    return !isnan(a) && !isnan(b) && a == b;
}

void mu_map_hud_update(mu_map_hud *h, int hero_valid, int map_valid, const float hero_pos[2], float hero_angle_z,
                       mu_map_hud_frame *out)
{
    memset(out, 0, sizeof *out);
    if (!h->shown)
        return;
    if (hero_valid) {
        volatile float r = -hero_angle_z;       /* xorps with the sign mask, then addss 225.0 [0x01a9d460] */
        r = r + (MU_MAP_MUTATION == 1 ? 224.0f : 225.0f);
        if (!same(h->last_rotation, r)) {
            h->last_rotation = r;
            out->set_rotation = 1;
            out->rotation = (double)h->last_rotation;
        }
    }
    if (map_valid) {
        if (!same(h->last_x, hero_pos[0]) || !same(h->last_y, hero_pos[1])) {
            h->last_x = hero_pos[0];
            h->last_y = hero_pos[1];
            volatile float x = h->last_x / 100.0f;     /* divss [0x01a7dec4] (100.0) */
            volatile float y = h->last_y / 100.0f;
            volatile float px = mu_map_px_x(x), py = mu_map_px_y(y);
            out->set_position = 1;
            out->map_x = (double)(-px);
            out->map_y = (double)(-py);
        }
    }
}

void mu_map_unit_make(int32_t type, int32_t key, int32_t state, const char *text, int32_t tile_x, int32_t tile_y,
                      mu_map_unit *out)
{
    memset(out, 0, sizeof *out);
    out->type = type;
    out->key = key;
    out->state = state;
    out->x = mu_map_px_x((float)tile_x);   /* cvtsi2ss */
    out->y = mu_map_px_y((float)tile_y);
    if (text)
        snprintf(out->text, sizeof out->text, "%s", text);
}

int mu_map_unit_packet(const uint8_t *p, size_t length, int with_name, mu_map_unit *out)
{
    memset(out, 0, sizeof *out);
    if (length < 10)
        return MU_MAP_UNIT_NONE;
    if (p[7] == 1) {          /* delUnit(type [5], key [4]) */
        out->type = p[5];
        out->key = p[4];
        return MU_MAP_UNIT_DEL;
    }
    if (p[7] != 0)
        return MU_MAP_UNIT_NONE;
    char name[64] = "";
    if (with_name) {          /* the name at [10] (a NUL-terminated string; bounded here by the packet) */
        size_t n = 0;
        while (10 + n < length && p[10 + n] && n + 1 < sizeof name) {
            name[n] = (char)p[10 + n];
            n++;
        }
        name[n] = 0;
    }
    if (MU_MAP_MUTATION == 2)
        mu_map_unit_make(p[4], p[5], p[6], name, p[8], p[9], out);
    else
        mu_map_unit_make(p[5], p[4], p[6], name, p[8], p[9], out);
    return MU_MAP_UNIT_ADD;
}

void mu_map_detected_unit(int32_t index, int32_t kind, int32_t tile_x, int32_t tile_y, mu_map_unit *out)
{
    mu_map_unit_make(MU_MAP_MUTATION == 3 ? kind : kind + 1, index, 0, "", tile_x, tile_y, out);
}

static int in(int32_t v, int32_t lo, int32_t hi)   /* 0x0095c61f(v, lo, hi) */
{
    return v >= lo && v <= hi;
}

int mu_map_blocked(int32_t world, int32_t x, int32_t y, int *notice)
{
    *notice = 0;
    if (world == 0x72) {
        if ((in(x, 0xe8, 0xf9) && in(y, 0xe7, 0xf6)) || (in(x, 0x6d, 0x7f) && in(y, 0xe7, 0xf7)) ||
            (in(x, 0xb6, 0xb6) && in(y, 0xe2, 0xfc))) {
            *notice = 1;
            return 1;
        }
        return 0;
    }
    if (world == 0x73)
        return 1;
    if (world == 0x4f) {
        if ((in(x, 0x10, 0x24) && in(y, 0xe2, 0xf6)) || (in(x, 0x34, 0x4b) && in(y, 0xe4, 0xfa))) {
            *notice = 1;
            return 1;
        }
    }
    return 0;
}

void mu_map_show(mu_map_hud *h, int show, int32_t world, int32_t x, int32_t y, mu_map_show_result *out)
{
    memset(out, 0, sizeof *out);
    uint8_t b = (uint8_t)(show != 0);
    if (b == 1) {
        int notice = 0;
        if (mu_map_blocked(world, x, y, &notice)) {
            out->ignored = 1;
            out->notice = notice;
            return;
        }
        if (!h->available) {
            out->notice = 1;
            return;
        }
    }
    h->shown = b;
    out->set_show = 1;
    out->shown = b;
    out->packet[0] = 0xc1;
    out->packet[1] = 4;
    out->packet[2] = 0xe7;
    out->packet[3] = b == 1 ? 1 : (MU_MAP_MUTATION == 4 ? 0 : 2);
    out->packet_length = 4;
}

const char *const mu_map_init_members[10] = {"txAlphaControl", "txAlphaDownKey", "txAlphaDownText", "txAlphaUpKey",
                                             "txAlphaUpText",  "txSizeControl",  "txSizeDownKey",   "txSizeDownText",
                                             "txSizeUpKey",    "txSizeUpText"};
const int32_t mu_map_init_text[10] = {0x106b, 0x106c, 0x106d, 0x106e, 0x1070, 0x1071, 0x1072, 0x1073, 0x1074, 0x1075};
