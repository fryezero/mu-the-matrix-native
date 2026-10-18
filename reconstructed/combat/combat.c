/* Client-side combat visuals and timing (NATIVE-COMBAT-001). See combat.h and
 * docs/research/client-combat.md. Build with -ffp-contract=off. */
#include "combat.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static float mu_f32(uint32_t bits)
{
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

#include "attack_speed_table.h"

/* ---------------------------------------------------------------- points */

int32_t mu_point_create(mu_point *points, const float position[3], int32_t value, const float color[3], float scale,
                        uint8_t move, uint8_t floor_test, float render_arg, int32_t extra, mu_height_fn height,
                        void *context)
{
    for (int32_t i = 0; i < MU_POINTS; ++i) {
        mu_point *p = &points[i];
        if (p->live)
            continue;
        p->live = 1;
        p->value = value;
        p->extra = extra;
        p->position[0] = position[0];
        p->position[1] = position[1];
        p->position[2] = position[2];
        p->position[2] = p->position[2] + 140.0f;
        p->color[0] = color[0];
        p->color[1] = color[1];
        p->color[2] = color[2];
        p->floor_test = floor_test;
        float h = height ? height(context, p->position[0], p->position[1]) : 0.0f;
        p->floor = h + 140.0f;
        p->render_arg = render_arg;
        p->gravity = 10.0f;
        p->scale = scale;
        p->delay = 0;
        p->move = move;
        return i;
    }
    return -1;
}

void mu_points_move(mu_point *points)
{
    for (int32_t i = 0; i < MU_POINTS; ++i) {
        mu_point *p = &points[i];
        if (!p->live)
            continue;
        p->delay = (int32_t)((uint32_t)p->delay - 1u);
        if (p->delay >= 0)
            continue;
        if (p->move)
            p->position[2] = p->position[2] + p->gravity;
        p->gravity = p->gravity - mu_f32(0x3e99999au);   /* 0.3 */
        if (0.0f >= p->gravity)
            p->live = 0;
        if (p->value == MU_POINT_HIT)
            continue;
        p->scale = p->scale - 5.0f;
        if (15.0f > p->scale)
            p->scale = 15.0f;
    }
}

int32_t mu_points_render(const mu_point *points, uint8_t mode, mu_number_call *calls, int32_t max)
{
    int32_t n = 0;
    for (int32_t i = 0; i < MU_POINTS; ++i) {
        const mu_point *p = &points[i];
        if (!p->live)
            continue;
        if (mode == 1) {
            if (p->position[2] > 350.0f)
                continue;
        } else if (mode == 2) {
            if (300.0f >= p->position[2])
                continue;
        } else if (p->floor_test) {
            if (p->floor >= p->position[2])
                continue;
        }
        if (n < max && calls) {
            mu_number_call *c = &calls[n];
            c->index = i;
            memcpy(c->position, p->position, sizeof c->position);
            c->value = p->value;
            memcpy(c->color, p->color, sizeof c->color);
            c->alpha = p->gravity * mu_f32(0x3ecccccdu);   /* 0.4 */
            c->scale = p->scale;
            c->render_arg = p->render_arg;
        }
        ++n;
    }
    return n;
}

/* ---------------------------------------------------------------- RenderNumber */

int32_t mu_format_thousands(int32_t value, char *out, size_t size)
{
    uint32_t v = (uint32_t)value;
    char groups[16][4];
    int count = 0;
    char lead[16];
    while (v / 1000u > 0 && count < 16) {
        snprintf(groups[count], sizeof groups[count], "%03u", v % 1000u);
        ++count;
        v /= 1000u;
    }
    snprintf(lead, sizeof lead, "%u", v);
    size_t n = 0;
    out[0] = 0;
    for (const char *s = lead; *s && n + 1 < size; ++s)
        out[n++] = *s;
    for (int g = count - 1; g >= 0; --g) {
        if (n + 1 < size)
            out[n++] = ',';
        for (int k = 0; k < 3 && n + 1 < size; ++k)
            out[n++] = groups[g][k];
    }
    if (size)
        out[n < size ? n : size - 1] = 0;
    return (int32_t)n;
}

static void sprite(mu_sprite_call *sprites, int32_t max, int32_t *count, int32_t bitmap, const float p[3], float width,
                   float height, const float uv[4][2], const float color[3], float alpha, float skew)
{
    if (*count < max && sprites) {
        mu_sprite_call *s = &sprites[*count];
        s->bitmap = bitmap;
        memcpy(s->position, p, sizeof s->position);
        s->width = width;
        s->height = height;
        memcpy(s->uv, uv, sizeof s->uv);
        for (int k = 0; k < 4; ++k)
            memcpy(s->light[k], color, sizeof s->light[k]);
        s->alpha = alpha;
        s->skew = skew;
    }
    ++*count;
}

/* Bitmap, width and height factors of the special values -11..-1 (jump table
 * 0x0184d877 of RenderNumber). */
static const struct { int32_t bitmap; uint32_t w, h; } special[11] = {
    {0x7df9, 0x404ccccdu, 0x3fcccccdu},  /* -11 stun   3.2 x 1.6 */
    {0x7dfa, 0x40cccccdu, 0x3fcccccdu},  /* -10 toxic  6.4 x 1.6 */
    {0x7dfb, 0x404ccccdu, 0x3fcccccdu},  /*  -9 slow   3.2 x 1.6 */
    {0x7dfc, 0x404ccccdu, 0x3fcccccdu},  /*  -8 bind   3.2 x 1.6 */
    {0x7dfd, 0x40cccccdu, 0x3fcccccdu},  /*  -7 bleed  6.4 x 1.6 */
    {0x7df8, 0x40accccdu, 0x3fd9999au},  /*  -6 absorb 5.4 x 1.7 */
    {0x7df7, 0x40accccdu, 0x3fd9999au},  /*  -5 parry  5.4 x 1.7 */
    {0x7df6, 0x40accccdu, 0x3fd9999au},  /*  -4 block  5.4 x 1.7 */
    {0x7df5, 0x40accccdu, 0x3fd9999au},  /*  -3 resist 5.4 x 1.7 */
    {0x7df3, 0x4059999au, 0x3fd9999au},  /*  -2 hit    3.4 x 1.7 */
    {0x7df4, 0x4059999au, 0x3fd9999au},  /*  -1 miss   3.4 x 1.7 */
};

int32_t mu_render_number(const float position[3], int32_t value, const float color[3], float alpha, float scale,
                         float arg6, mu_sprite_call *sprites, int32_t max)
{
    float p[3] = {position[0], position[1], position[2]};
    float uv[4][2] = {{0.0f, 1.0f}, {1.0f, 1.0f}, {1.0f, 0.0f}, {0.0f, 0.0f}};
    int32_t count = 0;
    uint32_t k = (uint32_t)value + 11u;
    if (k <= 10u) {
        sprite(sprites, max, &count, special[k].bitmap, p, scale * mu_f32(special[k].w), scale * mu_f32(special[k].h),
               uv, color, alpha, 0.0f);
        return count;
    }
    char text[64];
    mu_format_thousands(value, text, sizeof text);
    uint32_t length = (uint32_t)strlen(text);
    float l = (float)(double)length;
    p[0] = p[0] - l * 5.0f;
    p[0] = p[0] - l * scale * 0.125f;
    p[1] = p[1] - l * scale * 0.125f;
    const float du = mu_f32(0x3dba2e8cu);   /* 0.0909091 = 1/11 */
    for (uint32_t i = 0; i < length; ++i) {
        if (text[i] == ',') {
            float cuv[4][2] = {{0.0f, 1.0f}, {1.0f, 1.0f}, {1.0f, 0.0f}, {0.0f, 0.0f}};
            p[0] = p[0] - l * scale * mu_f32(0x3ccccccdu);   /* 0.025 */
            p[1] = p[1] - l * scale * mu_f32(0x3ccccccdu);
            sprite(sprites, max, &count, 0x7dfe, p, scale * 0.375f, scale * 1.5f, cuv, color, alpha, arg6);
            p[0] = scale * mu_f32(0x3eb33333u) + p[0];   /* 0.35 */
            p[1] = scale * mu_f32(0x3eb33333u) + p[1];
            continue;
        }
        float u = (float)((int32_t)(signed char)text[i] - 0x30) * du;
        float duv[4][2] = {{u, 1.0f}, {u + du, 1.0f}, {u + du, 0.0f}, {u, 0.0f}};
        sprite(sprites, max, &count, MU_BITMAP_FONT_DAMAGE, p, scale, scale * 1.5f, duv, color, alpha, arg6);
        p[0] = scale * 0.5f + p[0];
        p[1] = scale * 0.5f + p[1];
    }
    return count;
}

void mu_sprite_corners(const float camera[12], const float position[3], float width, float height, float skew,
                       float corners[4][3])
{
    float e[3];
    for (int r = 0; r < 3; ++r)
        e[r] = camera[4 * r + 0] * position[0] + camera[4 * r + 1] * position[1] + camera[4 * r + 2] * position[2] +
               camera[4 * r + 3];
    float w = width * 0.5f, h = height * 0.5f;
    corners[0][0] = e[0] - w - skew;
    corners[0][1] = e[1] - h;
    corners[1][0] = e[0] + w - skew;
    corners[1][1] = e[1] - h;
    corners[2][0] = e[0] + w + skew;
    corners[2][1] = e[1] + h;
    corners[3][0] = e[0] - w + skew;
    corners[3][1] = e[1] + h;
    for (int k = 0; k < 4; ++k)
        corners[k][2] = e[2];
}

/* ---------------------------------------------------------------- damage text */

static void set3(float c[3], uint32_t r, uint32_t g, uint32_t b)
{
    c[0] = mu_f32(r);
    c[1] = mu_f32(g);
    c[2] = mu_f32(b);
}

#define F1 0x3f800000u
#define F0 0x00000000u

void mu_damage_color(int32_t type, int32_t key, int32_t hero_key, uint8_t flag_a, uint8_t flag_b, float color[3])
{
    if (flag_a == 1) {
        if (flag_b)
            set3(color, 0x3f7d70a4u, 0x3f63d70au, 0x3f7ae148u);   /* 0.99 0.89 0.98 */
        else
            set3(color, F1, F1, F0);
        return;
    }
    if (flag_b) {
        if (type == 2)
            set3(color, 0x3f7851ecu, 0x3f147ae1u, 0x3f6e147bu);   /* 0.97 0.58 0.93 */
        else if (type == 3)
            set3(color, F1, 0x3f75c28fu, 0x3f170a3du);            /* 1 0.96 0.59 */
        else
            set3(color, 0x3f7d70a4u, 0x3f63d70au, 0x3f7ae148u);
        return;
    }
    switch (type) {
    case 0:
        if (key == hero_key)
            set3(color, F1, F0, F0);
        else
            set3(color, F1, 0x3f19999au, F0);   /* 1 0.6 0 */
        break;
    case 1: set3(color, F0, F1, F1); break;
    case 2: set3(color, F0, F1, 0x3f19999au); break;
    case 3: set3(color, F0, 0x3f19999au, F1); break;
    case 4: set3(color, F1, F0, F1); break;
    case 5: set3(color, F0, F1, F0); break;
    case 6: set3(color, 0x3f333333u, 0x3ecccccdu, F1); break;   /* 0.7 0.4 1 */
    case 11: set3(color, 0x3f000000u, 0x3f000000u, 0x3f400000u); break;   /* 0.5 0.5 0.75 */
    default: set3(color, F1, F1, F1); break;
    }
}

float mu_damage_scale(int32_t type)
{
    switch (type) {
    case 1: case 2: case 3: return 50.0f;
    case 11: return 80.0f;
    default: return 15.0f;
    }
}

int32_t mu_show_damage(mu_point *points, int32_t key, int32_t hero_key, const float position[3], float color[3],
                       float scale, const mu_damage_info *info, mu_height_fn height, void *context)
{
    int32_t made = 0;
#define POINT(pos, col, sc, mv, fl, arg) \
    made += mu_point_create(points, pos, info->damage, col, sc, mv, fl, arg, 0, height, context) >= 0
    if (info->damage == 0) {
        int32_t v;
        if (key == hero_key)
            set3(color, F1, F1, F1);
        else
            set3(color, 0x3f000000u, 0x3f000000u, 0x3f000000u);
        switch (info->type) {
        case 7: v = MU_POINT_RESIST; break;
        case 8: v = MU_POINT_BLOCK; break;
        case 9: v = MU_POINT_PARRY; break;
        case 10: v = MU_POINT_ABSORB; break;
        case 12: return 0;
        default: v = MU_POINT_MISS; break;
        }
        return mu_point_create(points, position, v, color, 1.0f, 1, 1, 0.0f, 0, height, context) >= 0;
    }
    float p[3] = {position[0], position[1], position[2]};
    if (info->flag_b)
        scale = scale * 1.5f;
    float s = scale;
    if (info->flag_c) {
        p[0] = p[0] - 35.0f;
        p[1] = p[1] - 35.0f;
        p[2] = p[2] + 25.0f;
        if (info->flag_b) {
            p[0] = p[0] - 35.0f;
            p[1] = p[1] - 35.0f;
            p[2] = p[2] + 12.0f;
        }
    } else if (info->flag_b) {
        p[0] = p[0] + 8.0f;
        p[1] = p[1] + 8.0f;
        p[2] = p[2] - 10.0f;
    }
    if (info->type == 5)
        p[2] = p[2] - 25.0f;
    float c2[3];
    const float k04 = mu_f32(0x3ecccccdu), k02 = mu_f32(0x3e4ccccdu);   /* 0.4, 0.2 */
    if (info->flag8) {
        for (int k = 0; k < 3; ++k)
            c2[k] = color[k] - k04;
        POINT(p, c2, s, 1, 0, 3.0f);
        p[2] = p[2] + 7.0f;
        for (int k = 0; k < 3; ++k)
            c2[k] = color[k] - k02;
        POINT(p, c2, s + 15.0f, 1, 0, 3.0f);
        p[2] = p[2] + 7.0f;
        POINT(p, c2, s + 25.0f, 1, 0, 3.0f);
    } else if (info->flag_a) {
        POINT(p, color, s, 1, 0, 0.0f);
        p[2] = p[2] + 7.0f;
        for (int k = 0; k < 3; ++k)
            c2[k] = color[k] + k02;
        POINT(p, c2, s + 15.0f, 1, 0, 0.0f);
        p[2] = p[2] + 7.0f;
        for (int k = 0; k < 3; ++k)
            c2[k] = color[k] + k04;
        POINT(p, c2, s + 25.0f, 1, 1, 0.0f);
    } else if (info->flag9) {
        for (int k = 0; k < 3; ++k)
            c2[k] = color[k] - k02;
        POINT(p, c2, s, 1, 0, 0.0f);
        p[2] = p[2] + 7.0f;
        POINT(p, color, s + 20.0f, 1, 1, 0.0f);
    } else {
        POINT(p, color, s, 1, 1, 0.0f);
    }
#undef POINT
    return made;
}

/* ---------------------------------------------------------------- attack speed */

void mu_set_attack_speed(float attack_speed, float magic_speed, float *speeds)
{
    mu_attack_speed_body(attack_speed, magic_speed, speeds);
}

int mu_attack_speed_writes(int32_t action)
{
    static float probe[MU_PLAYER_ACTIONS];
    if (action < 0 || action >= MU_PLAYER_ACTIONS)
        return 0;
    for (int i = 0; i < MU_PLAYER_ACTIONS; ++i)
        probe[i] = -12345.0f;
    mu_attack_speed_body(100.0f, 100.0f, probe);
    return probe[action] != -12345.0f;
}

/* ---------------------------------------------------------------- attack actions */

static int32_t next_rand(const mu_attack_input *in, mu_attack_result *r)
{
    if (r->rand_used >= in->rand_count) {
        r->fault = 1;
        ++r->rand_used;
        return 0;
    }
    return in->rand_values[r->rand_used++];
}

static int in_group(int32_t item, int32_t low, int32_t high)
{
    return item >= low && item < high;
}

void mu_player_attack_action(const mu_attack_input *in, mu_attack_result *r)
{
    memset(r, 0, sizeof *r);
    r->action = -1;
    if (in->object_type != 0xa91)
        return;
    r->speed_update = 1;
    if (!in->safe_zone)
        r->attack_start = 1;
    int32_t w0 = in->weapon[0], w1 = in->weapon[1];
    int32_t cls = in->class_byte & 15;
    int32_t counter = in->counter;
    if (w0 == -1 && w1 == -1) {
        r->action = (cls == 7 || cls == 8 || cls == 9 || cls == 12 || cls == 14) ? 0x70 : 0x6f;
    } else if (in_group(w0, 0xae6, 0x10e6)) {
        if (in->attr_present[0] && !in->two_handed) {
            if (cls == 9)
                r->action = 0x82;
            else if (in_group(w1, 0xae6, 0x10e6)) {
                static const int32_t four[4] = {0x71, 0x73, 0x72, 0x74};
                r->action = four[counter % 4];
            } else {
                r->action = 0x71 + counter % 2;
            }
        } else if (w0 == 0xafb || w0 == 0xb05 || w0 == 0xafd || w0 == 0xaff) {
            r->action = 0x78;
        } else {
            r->action = 0x75 + counter % 3;
        }
    } else if (in_group(w1, 0xae6, 0x10e6)) {
        r->action = 0x73 + next_rand(in, r) % 2;
    } else if (in_group(w0, 0x14e6, 0x16e6)) {
        if (in->attr_present[0] && !in->two_handed) {
            if (cls == 12)
                r->action = 0x70;
            else if (in->state_72)
                r->action = 0x88;
            else
                r->action = 0x71 + next_rand(in, r) % 2;
        } else {
            r->action = 0xa3 + next_rand(in, r) % 2;
        }
    } else if (w0 == 0x10e7 || w0 == 0x10e8) {
        r->action = 0x79;
    } else if (in_group(w0, 0x10e6, 0x12e6)) {
        r->action = cls == 7 ? 0x7a : 0x7b + counter % 3;
    } else if (in->bow_kind == 1) {
        r->action = in->wing != -1 ? 0x80 : 0x7e;
    } else if (in->bow_kind == 2) {
        r->action = in->wing != -1 ? 0x81 : 0x7f;
    } else if (in->dual) {
        if (in->wing != -1) {
            if (in->attr_present[0] && in->attr_present[1])
                r->action = 0x85 + next_rand(in, r) % 2;
            else if (in->attr_present[0])
                r->action = 0x86;
        } else {
            if (in->attr_present[0] && in->attr_present[1])
                r->action = 0x83 + (next_rand(in, r) % 10 == 0);
            else if (in->attr_present[0])
                r->action = 0x84;
        }
    } else if (w0 == -1 && in->state_72) {
        r->action = 0x87;
    } else {
        r->action = 0x6f;
    }
}

int32_t mu_monster_attack_action(uint8_t counter, int special_blocks)
{
    if (special_blocks)
        return -1;
    return counter % 3 == 0 ? 3 : 4;
}

int32_t mu_player_magic_action(uint8_t class_byte, int class_check, int32_t rand_value)
{
    if (class_check)
        return (class_byte & 15) == 14 ? 0x10e : 0xa5;
    return 0xa1 + rand_value % 2;
}

/* ---------------------------------------------------------------- hero, shock, death */

int mu_in_range(int32_t tile_x, int32_t tile_y, int32_t x, int32_t y, float range)
{
    float dx = (float)(int32_t)((uint32_t)tile_x - (uint32_t)x);
    float dy = (float)(int32_t)((uint32_t)tile_y - (uint32_t)y);
    float s = dx * dx + dy * dy;
    float d = (float)sqrt((double)s);
    return range >= d;
}

float mu_hero_attack_range(int32_t weapon_item, int bow, int item_flag_54, int16_t class_word)
{
    float range = 1.0f;
    if (weapon_item >= 0x600 && weapon_item < 0x800)
        range = 2.0f;
    if (bow)
        range = 6.0f;
    if (item_flag_54)
        range = 8.0f;
    if (class_word == 9)
        range = 7.0f;
    return range;
}

/* cvttss2si: truncation, 0x80000000 for NaN and out-of-range values. */
static int32_t cvtt(float v)
{
    if (!(v > -2147483904.0f && v < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)v;
}

uint8_t mu_attack_direction(float angle_z)
{
    float v = (angle_z + 22.5f) / 360.0f * 8.0f + 1.0f;
    int32_t i = cvtt(v);
    int32_t b = (uint8_t)i;
    return (uint8_t)(b % 8);
}

int mu_monster_shock_allowed(int32_t monster_class, int32_t action)
{
    if (monster_class == 0x2fb)
        return !(action >= 8 || action == 4);
    return !(action == 3 || action == 4);
}

int32_t mu_shock_action(uint8_t dead, int32_t object_type, int32_t action, int32_t monster_class, int32_t damage,
                        int32_t type)
{
    static const int32_t skip[] = {0x8f, 0x9c, 0x9f, 0xe2, 0xe3, 0xdc, 0xe0, 0xe1, 0x11d, 0x126, 0x127};
    if (dead)
        return -1;
    for (size_t i = 0; i < sizeof skip / sizeof skip[0]; ++i)
        if (action == skip[i])
            return -1;
    if (type != 12 && type != 15 && damage <= 0)
        return -1;
    if (object_type == 0xa91)
        return -1;   /* Player hit actions 0x134..0x13a: not reduced here */
    return mu_monster_shock_allowed(monster_class, action) ? 5 : -1;
}

uint8_t mu_dead_step(uint8_t dead, int *die)
{
    *die = 0;
    if (dead == 0)
        return dead;
    dead = (uint8_t)(dead + 1);
    if (dead >= 15)
        *die = 1;
    return dead;
}

void mu_dead_fade(uint8_t dead, mu_fade_state *s)
{
    if (dead == 0)
        return;
    if (s->model == 0x7c5 && s->world == 7)
        s->timer = s->timer + mu_f32(0x3d4ccccdu);   /* 0.05 */
    else if (s->model == 0x7e5 || s->model == 0x940)
        s->timer = s->timer + (s->o6c >= 100 ? mu_f32(0x3c23d70au) : mu_f32(0x3ca3d70au));   /* 0.01 / 0.02 */
    else
        s->timer = s->timer + mu_f32(0x3ca3d70au);
    float one = 1.0f;
    if (!(s->timer >= one))
        return;
    if (s->model != 0x819)
        s->alpha = 1.0f - (s->timer - one);
    if (s->alpha >= mu_f32(0x3c23d70au))
        s->z = s->z - mu_f32(0x3ecccccdu);   /* 0.4 */
    else if (!s->is_hero)
        s->removed = 1;
}

int mu_attack_time_step(uint8_t *attack_time, int32_t limit)
{
    if (*attack_time == 0)
        return 0;
    *attack_time = (uint8_t)(*attack_time + 1);
    if ((int32_t)*attack_time >= limit) {
        *attack_time = 0;
        return 1;
    }
    return 0;
}

/* ---------------------------------------------------------------- skills */

static const mu_skill_visual skills[] = {
    /* skill, name, receive, action, effect, subtype, count, arrows, sound, end sound */
    {0, "normal attack (bow: arrow)", MU_SKILL_RECEIVE_ATTACK, -1, -1, 0, 0, 1, -1, -1},
    {1, "Poison", MU_SKILL_RECEIVE_MAGIC, -1, 0x414, 0, 1, 0, 0x34d, 0x22},
    {2, "Meteorite", MU_SKILL_RECEIVE_MAGIC, -1, 0x413, 0, 1, 0, 0x34d, 0x42},
    {4, "Fire Ball", MU_SKILL_RECEIVE_MAGIC, -1, 0x413, 1, 1, 0, 0x34d, 0x42},
    {7, "Ice", MU_SKILL_RECEIVE_MAGIC, -1, 0x412, 0, 1, 0, 0x34d, 0x78},
    {9, "Evil Spirit", MU_SKILL_RECEIVE_MAGIC, -1, 0x7fd3, 0, 8, 0, 0x34d, 0x75},
    {10, "Hellfire", MU_SKILL_RECEIVE_AREA, 0xa9, 0x41c, 0, 2, 0, -1, 0x77},
    {11, "Power Wave", MU_SKILL_RECEIVE_MAGIC, -1, 0x41f, 0, 3, 0, 0x34d, 0x76},
    {12, "Aqua Beam", MU_SKILL_RECEIVE_AREA, 0xa7, 0x7f4e, 0, 1, 0, -1, 0x7a},
    {14, "Inferno", MU_SKILL_RECEIVE_AREA, 0xa8, 0x457, 0, 1, 0, -1, -1},
    {17, "Energy Ball", MU_SKILL_RECEIVE_MAGIC, -1, 0x437, 0, 1, 0, 0x34d, -1},
    {19, "Falling Slash", MU_SKILL_RECEIVE_MAGIC, 0x89, -1, 0, 0, 0, 0x70, -1},
    {20, "Lunge", MU_SKILL_RECEIVE_MAGIC, 0x8a, -1, 0, 0, 0, 0x71, -1},
    {21, "Uppercut", MU_SKILL_RECEIVE_MAGIC, 0x8b, -1, 0, 0, 0, 0x72, -1},
    {22, "Cyclone", MU_SKILL_RECEIVE_MAGIC, 0x8c, -1, 0, 0, 0, 0x73, -1},
    {23, "Slash", MU_SKILL_RECEIVE_MAGIC, 0x8d, -1, 0, 0, 0, 0x73, -1},
    {24, "Triple Shot", MU_SKILL_RECEIVE_AREA, -1, -1, 0, 0, 2, -1, -1},
    {26, "Heal", MU_SKILL_RECEIVE_MAGIC, -1, 0x7f84, 0, 1, 0, 0x6f, -1},
    {27, "Greater Defense", MU_SKILL_RECEIVE_MAGIC, -1, -1, 0, 0, 0, 0x6f, -1},
    {28, "Greater Damage", MU_SKILL_RECEIVE_MAGIC, -1, -1, 0, 0, 0, 0x6f, -1},
    {41, "Twisting Slash", MU_SKILL_RECEIVE_AREA, 0x8e, 0x453, 0, 1, 0, -1, 0x73},
    {42, "Rageful Blow", MU_SKILL_RECEIVE_AREA, 0x8f, 0x461, 0, 1, 0, -1, 0x95},
    {43, "Death Stab", MU_SKILL_RECEIVE_AREA, 0x9e, -1, 0, 0, 0, -1, -1},
};

const mu_skill_visual *mu_skill_visual_find(int32_t skill)
{
    for (size_t i = 0; i < sizeof skills / sizeof skills[0]; ++i)
        if (skills[i].skill == skill)
            return &skills[i];
    return NULL;
}

const mu_skill_visual *mu_skill_visual_at(int32_t index)
{
    if (index < 0 || index >= (int32_t)(sizeof skills / sizeof skills[0]))
        return NULL;
    return &skills[index];
}

int32_t mu_skill_visual_count(void)
{
    return (int32_t)(sizeof skills / sizeof skills[0]);
}
