/* Character picking (NATIVE-NPC-001); see npc_pick.h.  Binary32 in the
 * client's operation order: build with -ffp-contract=off. */
#include "npc_pick.h"

#include <stddef.h>
#include <string.h>

#include "character_box_table.h"

void mu_pick_cross(const float a[3], const float b[3], float out[3])
{
    out[0] = a[1] * b[2] - a[2] * b[1];
    out[1] = a[2] * b[0] - a[0] * b[2];
    out[2] = a[0] * b[1] - a[1] * b[0];
}

static float dot3(const float a[3], const float b[3])
{
    float s = a[0] * b[0] + a[1] * b[1];
    return s + a[2] * b[2];
}

/* 0x0184f93f / 0x0184f927 (comiss: an unordered pair takes the second). */
static float fmax_client(float a, float b) { return a > b ? a : b; }
static float fmin_client(float a, float b) { return a > b ? b : a; }

int mu_pick_axis_overlap(const float axis[3], const float p1[3], const float p2[3], const mu_obb *obb)
{
    float d1 = dot3(axis, p1), d2 = dot3(axis, p2);
    float hi_seg = fmax_client(d1, d2), lo_seg = fmin_client(d1, d2);
    float s = dot3(axis, obb->start);
    float px = dot3(axis, obb->x), py = dot3(axis, obb->y), pz = dot3(axis, obb->z);
    float hi = s, lo = s;
    if (px > 0.0f)
        hi += px;
    else
        lo += px;
    if (py > 0.0f)
        hi += py;
    else
        lo += py;
    if (pz > 0.0f)
        hi += pz;
    else
        lo += pz;
#ifdef MU_MUT_AXIS_STRICT
    if (lo_seg >= hi)   /* planted mistake */
        return 0;
#else
    if (lo_seg > hi)
        return 0;
#endif
    if (lo > hi_seg)
        return 0;
    return 1;
}

int mu_pick_segment_obb(const float p1[3], const float p2[3], const mu_obb *obb)
{
    float d[3] = {p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]};
    float cx[3], cy[3], cz[3];
    mu_pick_cross(d, obb->x, cx);
    mu_pick_cross(d, obb->y, cy);
    mu_pick_cross(d, obb->z, cz);
    return mu_pick_axis_overlap(cx, p1, p2, obb) && mu_pick_axis_overlap(cy, p1, p2, obb) &&
           mu_pick_axis_overlap(cz, p1, p2, obb) && mu_pick_axis_overlap(obb->x, p1, p2, obb) &&
           mu_pick_axis_overlap(obb->y, p1, p2, obb) && mu_pick_axis_overlap(obb->z, p1, p2, obb);
}

static int kind_matches(uint8_t mask, uint8_t kind)
{
    return (uint8_t)(mask & kind) == kind;
}

static void set_light(mu_pick_character *c, float r, float g, float b)
{
    c->light[0] = r;
    c->light[1] = g;
    c->light[2] = b;
    c->light_set = 1;
}

/* cvttss2si: out of range or NaN gives the integer indefinite value. */
static int32_t truncate_f32(float v)
{
    if (!(v > -2147483904.0f && v < 2147483648.0f))
        return (int32_t)0x80000000u;
    return (int32_t)v;
}

int32_t mu_npc_pick(mu_pick_character *characters, int32_t count, uint8_t kind, const mu_pick_scene *scene)
{
    if (count > MU_PICK_CHARACTERS)
        count = MU_PICK_CHARACTERS;
    int skip_hero = scene->scene != 5;
    for (int32_t i = 0; i < count; i++) {
        mu_pick_character *c = &characters[i];
        if (!kind_matches(kind, c->kind) || !c->live || !c->visible || !(c->alpha > 0.0f))
            continue;
        c->marked = 1;
        switch (c->highlight) {
        case 0: set_light(c, 0.2f, 0.2f, 0.2f); break;
        case 1: set_light(c, -0.4f, -0.4f, -0.4f); break;
        case 2: set_light(c, 0.2f, -0.6f, -0.6f); break;
        case 3: set_light(c, 1.5f, 1.5f, 1.5f); break;
        case 4: set_light(c, 0.3f, 0.2f, -0.5f); break;
        default: break;
        }
        if (c->c1f >= 6)
            set_light(c, -0.4f, -0.4f, -0.4f);
    }
    int32_t best = -1;
    float best_distance = 999999995904.0f;
    for (int32_t i = 0; i < count; i++) {
        mu_pick_character *c = &characters[i];
        if (!c->live || !c->visible || !(c->alpha > 0.0f) || c->dead || c->buff_1b)
            continue;
        if (skip_hero && c->is_hero)
            continue;
        if (!c->c10 || !kind_matches(kind, c->kind))
            continue;
        mu_obb *b = &c->obb;
        if (c->type == 0xa40) {
            b->start[2] += 300.0f;
        } else if (c->type == 0x81b || c->type == 0x81c) {
            b->start[2] += 200.0f;
        } else if (c->type == 0xa3e) {
            b->start[0] -= 100.0f;
            b->start[2] += 100.0f;
            b->x[0] += 100.0f;
            b->z[2] += 100.0f;
        } else if (scene->world == 0x5d) {
            b->z[2] += 100.0f;
        } else if (c->type == 0xa64) {
            b->x[0] += 100.0f;
            b->z[2] += 100.0f;
        }
        if (!mu_pick_segment_obb(scene->ray_start, scene->ray_end, b))
            continue;
        float d[3] = {c->position[0] - scene->camera[0], c->position[1] - scene->camera[1],
                      c->position[2] - scene->camera[2]};
#ifdef MU_MUT_PICK_DISTANCE
        float distance = d[0] * d[0] + d[1] * d[1];   /* planted mistake: no height term */
#else
        float distance = d[0] * d[0] + d[1] * d[1];
        distance = distance + d[2] * d[2];
#endif
        if (!(best_distance > distance))
            continue;
        int ok = 1;
        if ((scene->world == 0 || scene->world == 2) && scene->map) {
            /* esi = (int)y / 100; shl esi, 8; add esi, (int)x / 100 (idiv truncates) */
            int32_t index = (int32_t)(((uint32_t)(truncate_f32(c->position[1]) / 100) << 8) +
                                      (uint32_t)(truncate_f32(c->position[0]) / 100));
            uint8_t v = index >= 0 && index < 65536 ? scene->map[index] : 0;
            int marked = (scene->world == 0 && v == 4) || (scene->world == 2 && v == 3);
            if (marked && v != scene->map_value && scene->world == 2 && scene->map_value != 0xb)
                ok = 0;
        }
        if (ok) {
            best = i;
            best_distance = distance;
        }
    }
    return best;
}

void mu_character_box(int32_t type, float min[3], float max[3])
{
    static const float DEFAULT_MIN[3] = {-60.0f, -60.0f, 0.0f}, DEFAULT_MAX[3] = {50.0f, 50.0f, 150.0f};
    memcpy(min, DEFAULT_MIN, sizeof DEFAULT_MIN);
    memcpy(max, DEFAULT_MAX, sizeof DEFAULT_MAX);
#ifdef MU_MUT_BOX_DEFAULT
    return;   /* planted mistake: every type keeps the default box */
#endif
    for (size_t i = 0; i < sizeof MU_CHARACTER_BOXES / sizeof MU_CHARACTER_BOXES[0]; i++)
        if (MU_CHARACTER_BOXES[i].type == type) {
            memcpy(min, MU_CHARACTER_BOXES[i].min, sizeof DEFAULT_MIN);
            memcpy(max, MU_CHARACTER_BOXES[i].max, sizeof DEFAULT_MAX);
            return;
        }
}

void mu_character_obb(const float min[3], const float max[3], const float origin[3], mu_obb *obb)
{
    memset(obb, 0, sizeof *obb);
    for (int k = 0; k < 3; k++)
        obb->start[k] = min[k] + origin[k];
    obb->x[0] = max[0] - min[0];
    obb->y[1] = max[1] - min[1];
    obb->z[2] = max[2] - min[2];
}
