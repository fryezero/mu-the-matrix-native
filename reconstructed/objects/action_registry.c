/* RENDER-WORLDS-AFTER5: the object action registry 0x01ec7d5c (action_registry.h). */
#include "action_registry.h"

#include <math.h>
#include <stddef.h>
#include <string.h>


enum { OBJ_LOOPS = 0x30, OBJ_LIMIT = 0x34 };   /* int counters of the handlers 2, 3 (loops) and 7 (latch) */

uint32_t mu_anim_key(int32_t type, int32_t action)
{
    return 1000u * (uint32_t)action + (uint32_t)type;
}

const mu_anim_entry *mu_anim_find(const mu_anim_inputs *in, int32_t type, int32_t action)
{
    const uint32_t key = mu_anim_key(type, action);
    for (int32_t k = 0; in->entries && k < in->count; ++k)
        if (mu_anim_key(in->entries[k].type, in->entries[k].action) == key)
            return &in->entries[k];
    return NULL;
}

static int32_t back(const mu_anim_entry *e)
{
    return e->extra[e->extra_count - 1];   /* 0x00ce486d */
}

/* ---- SetAction handlers (+0x24), 0x00ce1460.. ---- */
static int set_handler(uint8_t *o, const mu_anim_entry *e, const mu_anim_inputs *in)
{
    switch (e->handler) {
    case 0: case 1: case 4: case 5: case 6: case 7:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, e->speed);
        return MU_ANIM_APPLIED;
    case 2: case 3: {   /* 0x00ce149c, 0x00ce1501: a random first loop limit within [extra[0], extra[1]) */
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, e->speed);
        mu_obj_set_i32(o, OBJ_LOOPS, 0);
        if (e->extra_count < 2 || e->extra[1] == e->extra[0])
            return MU_ANIM_UNSUPPORTED;   /* the client divides by the span */
        const int32_t r = in->rand_fn(in->context);
        mu_obj_set_i32(o, OBJ_LIMIT, e->extra[0] + r % (e->extra[1] - e->extra[0]));
        return MU_ANIM_APPLIED;
    }
    case 8:   /* 0x00ce15de: the alpha rate from extra[6] when the vector has more than six */
        if (e->extra_count > 6)
            mu_obj_set_f32(o, MU_OBJF_ALPHA_RATE, (float)e->extra[6] * 0.00999999978f);
        return MU_ANIM_APPLIED;
    default:
        return MU_ANIM_UNSUPPORTED;
    }
}

int mu_action_set(uint8_t *o, int32_t action, const mu_anim_inputs *in)
{
    if (!o)
        return MU_ANIM_NONE;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    int32_t count = 0;
    int16_t keys = 0;
    uint8_t lock = 0;
    if (!in->model(in->context, type, action, &count, &keys, &lock) || !(action < (int32_t)(int16_t)count))
        return MU_ANIM_NONE;
    if ((int32_t)mu_obj_u16(o, MU_OBJF_ACTION) != action) {
        mu_obj_set_u16(o, MU_OBJF_PRIOR_ACTION, mu_obj_u16(o, MU_OBJF_ACTION));
        mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, mu_obj_f32(o, MU_OBJF_FRAME));
        mu_obj_set_u16(o, MU_OBJF_ACTION, (uint16_t)action);
        mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
    }
    const mu_anim_entry *e = mu_anim_find(in, type, action);
    return e ? set_handler(o, e, in) : MU_ANIM_NONE;
}

/* ---- tick handlers (+0x18), 0x00ce1646.. ---- */

/* The current action's record (model +0x30 + action * 16): keys +8, lock +0xa. The handlers read it unchecked;
 * natively a read without a record is refused. */
typedef struct record {
    int16_t keys;
    uint8_t lock, valid, refused;
} record;

/* The end of the current action: frame +0xd0 >= keys - speed (keys - 1 first when the action locks positions and
 * `locked` asks for it). False for a NaN frame (comiss; jb). */
static int at_end(const uint8_t *o, const mu_anim_entry *e, record *r, int locked)
{
    if (!r->valid) {
        r->refused = 1;
        return 0;
    }
    float limit = (float)r->keys;
    if (locked && r->lock)
        limit = limit - 1.0f;
    return mu_obj_f32(o, MU_OBJF_FRAME) >= limit - e->speed;
}

/* The hero's x/y distance (sqrt 0x00961a07 rounds the root of the widened sum to binary32). */
static float hero_distance(const uint8_t *o, const mu_anim_inputs *in)
{
    const float dx = in->hero[0] - mu_obj_f32(o, MU_OBJF_POSITION);
    const float dy = in->hero[1] - mu_obj_f32(o, MU_OBJF_POSITION + 4);
    const float sum = dx * dx + dy * dy;
    return (float)sqrt((double)sum);
}

/* ---- RENDER-WORLDS-AFTER6: the tick handlers 4, 6 and 8 ----
 *
 * The geometry routines below restate the client's picking primitives in this file (libobjects is built from
 * its own directory). The same routines are ported and compared on their own as mu_pick_segment_obb
 * (reconstructed/npc, validate_npc) and mu_face_normalize / mu_collision_line_face (reconstructed/camera);
 * here they are compared through the handlers (validate_worlds_after6). */

typedef struct box {
    float start[3], x[3], y[3], z[3];   /* the client's OBB: StartPos, XAxis, YAxis, ZAxis */
} box;

/* 0x0184f93f / 0x0184f927 (comiss; jbe: an unordered pair takes the second) and fabs 0x0184f8ff. */
static float larger(float a, float b) { return a > b ? a : b; }
static float smaller(float a, float b) { return a > b ? b : a; }
static float magnitude(float a) { return 0.0f > a ? -a : a; }

/* 0x00cfd21b: ((a.x * b.x + a.y * b.y) + a.z * b.z). */
static float dot(const float a[3], const float b[3])
{
    float sum = a[0] * b[0];
    sum = sum + a[1] * b[1];
    return sum + a[2] * b[2];
}

/* 0x01850d88(axis, p1, p2, obb): the segment's and the box's projections overlap. */
static int overlap(const float axis[3], const float p1[3], const float p2[3], const box *b)
{
    const float d1 = dot(axis, p1), d2 = dot(axis, p2);
    const float hi_segment = larger(d1, d2), lo_segment = smaller(d1, d2);
    const float s = dot(axis, b->start);
    const float e[3] = {dot(axis, b->x), dot(axis, b->y), dot(axis, b->z)};
    float hi = s, lo = s;
    for (int k = 0; k < 3; ++k) {
        if (e[k] > 0.0f)
            hi = hi + e[k];
        else
            lo = lo + e[k];
    }
    return !(lo_segment > hi) && !(lo > hi_segment);
}

/* 0x00cfeff3: a x b. */
static void cross(const float a[3], const float b[3], float out[3])
{
    out[0] = a[1] * b[2] - a[2] * b[1];
    out[1] = a[2] * b[0] - a[0] * b[2];
    out[2] = a[0] * b[1] - a[1] * b[0];
}

/* 0x018500bf(p1, p2, obb): no separating axis among (p2 - p1) x X, Y, Z and X, Y, Z. */
static int segment_box(const float p1[3], const float p2[3], const box *b)
{
    const float d[3] = {p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]};
    float a[3][3];
    cross(d, b->x, a[0]);
    cross(d, b->y, a[1]);
    cross(d, b->z, a[2]);
    return overlap(a[0], p1, p2, b) && overlap(a[1], p1, p2, b) && overlap(a[2], p1, p2, b) &&
           overlap(b->x, p1, p2, b) && overlap(b->y, p1, p2, b) && overlap(b->z, p1, p2, b);
}

/* FaceNormalize 0x00d01206: the cross product of (b - a) and (c - a), divided in binary64 by its length (the
 * sqrt 0x00961a07 rounded to binary32) unless that is 0 (then 0). */
static void face_normal(const float a[3], const float b[3], const float c[3], float n[3])
{
    n[0] = n[1] = n[2] = 0.0f;
    const float nx = (b[1] - a[1]) * (c[2] - a[2]) - (c[1] - a[1]) * (b[2] - a[2]);
    const float ny = (b[2] - a[2]) * (c[0] - a[0]) - (c[2] - a[2]) * (b[0] - a[0]);
    const float nz = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]);
    const float sum = nx * nx + ny * ny + nz * nz;
    const double length = (double)(float)sqrt((double)sum);
    if (length == 0.0)
        return;
    n[0] = (float)((double)nx / length);
    n[1] = (float)((double)ny / length);
    n[2] = (float)((double)nz / length);
}

/* InsideTest 0x018506bc on the plane (p, q): every edge term (v[i][p] - P)(v[j][q] - Q) - (v[j][p] - P)(v[i][q] -
 * Q) above 0 (a sign > 0 flips the test; a NaN term passes). */
static int inside(const float point[3], const float *const v[4], int p, int q, float sign)
{
    for (int i = 0, j = 3; i < 4; j = i, ++i) {
        const float term = (v[i][p] - point[p]) * (v[j][q] - point[q]) - (v[j][p] - point[p]) * (v[i][q] - point[q]);
        if (!(sign > 0.0f) ? 0.0f >= term : term >= 0.0f)
            return 0;
    }
    return 1;
}

/* Inside the segment's range on one axis (comiss; jb: a NaN fails). */
static int within(float x, float o, float t)
{
    return x >= smaller(o, t) && larger(o, t) >= x;
}

/* CollisionDetectLineToFace 0x0184f96c(origin, target, 4, a, b, c, d, normal, 0) after 0x0184f957 set the nearest
 * parameter 0x0bdc58c8 to 9999999: 0 <= t <= 9999999, the hit inside the segment's range on the two axes beside
 * the smallest |dir|, then inside the quad on the plane of the first normal component with |n| >= 0.5. */
static int line_face(const float origin[3], const float target[3], const float *const v[4], const float n[3])
{
    const float dir[3] = {target[0] - origin[0], target[1] - origin[1], target[2] - origin[2]};
    const float t = -(dot(origin, n) - dot(v[0], n)) / dot(dir, n);
    if (!(t >= 0.0f) || !(9999999.0f >= t))
        return 0;
    float x[3];
    for (int k = 0; k < 3; ++k)
        x[k] = dir[k] * t + origin[k];
    const float smallest = smaller(smaller(magnitude(dir[0]), magnitude(dir[1])), magnitude(dir[2]));
    int ok;
    if (smallest == magnitude(dir[0]))
        ok = within(x[1], origin[1], target[1]) && within(x[2], origin[2], target[2]);
    else if (smallest == magnitude(dir[1]))
        ok = within(x[2], origin[2], target[2]) && within(x[0], origin[0], target[0]);
    else
        ok = within(x[0], origin[0], target[0]) && within(x[1], origin[1], target[1]);
    if (!ok)
        return 0;
    if (-0.5f >= n[0] || n[0] >= 0.5f)
        return inside(x, v, 1, 2, n[0]);
    if (-0.5f >= n[1] || n[1] >= 0.5f)
        return inside(x, v, 2, 0, n[1]);
    return inside(x, v, 0, 1, n[2]);
}

/* 0x018500bf(MousePosition, MouseTarget, OBB +0x31c): 1 when the mouse segment meets the object's box, -1 when
 * the caller has no mouse segment. */
static int hover(const uint8_t *o, const mu_anim_inputs *in)
{
    if (!in->mouse_start || !in->mouse_end)
        return -1;
    box b;
    memcpy(&b, o + MU_OBJF_OBB, sizeof b);
    return segment_box(in->mouse_start, in->mouse_end, &b);
}

/* 0x0185c113(out, in, angles): in turned by the angles in degrees (x, y, z), the matrix terms in the client's
 * order, through a copy (out may be in). */
static void turn(float v[3], const float angles[3])
{
    const float k = 0.0174532924f;   /* 0x01a7fd6c */
    const float a = angles[0] * k, b = angles[1] * k, c = angles[2] * k;
    const float ca = (float)cos((double)a), sa = (float)sin((double)a);   /* 0x009fa223, 0x009681bd */
    const float cb = (float)cos((double)b), sb = (float)sin((double)b);
    const float cc = (float)cos((double)c), sc = (float)sin((double)c);
    float out[3];
    out[0] = cc * cb * v[0] + (cc * sb * sa - sc * ca) * v[1] + (cc * sb * ca + sc * sa) * v[2];
    out[1] = sc * cb * v[0] + (sc * sb * sa + cc * ca) * v[1] + (sc * sb * ca - cc * sa) * v[2];
    out[2] = -sb * v[0] + cb * sa * v[1] + cb * ca * v[2];
    memcpy(v, out, sizeof out);
}

/* 0x00ce23ad: the camera -> hero segment against the object's box; +0xd8 (alpha target) 0.1 on a face hit. */
static int camera_fade(uint8_t *o, const mu_anim_entry *e, const mu_anim_inputs *in)
{
    if (e->extra_count != 7)
        return MU_ANIM_APPLIED;
    if (!in->camera)
        return MU_ANIM_UNSUPPORTED;
    float position[3], angles[3];
    for (int k = 0; k < 3; ++k) {
        position[k] = mu_obj_f32(o, MU_OBJF_POSITION + 4u * (uint32_t)k);
        angles[k] = mu_obj_f32(o, MU_OBJF_ANGLE + 4u * (uint32_t)k);
    }
    const float hero[3] = {in->hero[0], in->hero[1], in->hero[2]};
    /* the coarse box: a square of twice the largest size about the position, as high as that size */
    box coarse;
    memset(&coarse, 0, sizeof coarse);
    coarse.z[2] = larger(larger((float)e->extra[0], (float)e->extra[1]), (float)e->extra[2]);
    const float side = 2.0f * coarse.z[2];
    coarse.x[0] = side;
    coarse.y[1] = side;
    memcpy(coarse.start, position, sizeof position);
    coarse.start[0] = coarse.start[0] - coarse.x[0] * 0.5f;
    coarse.start[1] = coarse.start[1] - coarse.y[1] * 0.5f;
    for (int k = 0; k < 3; ++k)
        coarse.start[k] = (float)e->extra[3 + k] + coarse.start[k];
    if (!segment_box(in->camera, hero, &coarse))
        return MU_ANIM_APPLIED;
    /* the turned box: half sizes x, y and the height z, scaled, offset, turned and placed */
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    const float hx = (float)e->extra[0] * scale * 0.5f, hy = (float)e->extra[1] * scale * 0.5f;
    const float hz = (float)e->extra[2] * scale;
    float c[8][3] = {{-hx, -hy, 0.0f}, {hx, -hy, 0.0f}, {-hx, hy, 0.0f}, {hx, hy, 0.0f},
                     {-hx, -hy, hz},   {hx, -hy, hz},   {-hx, hy, hz},   {hx, hy, hz}};
    for (int i = 0; i < 8; ++i) {
        for (int k = 0; k < 3; ++k)
            c[i][k] = (float)e->extra[3 + k] * scale + c[i][k];
        turn(c[i], angles);
        for (int k = 0; k < 3; ++k)
            c[i][k] = c[i][k] + position[k];
    }
    /* the normals from three corners each, then the faces in the client's order and corner lists (the third
     * closes on corner 3, not 2) */
    static const int face[6][4] = {{0, 1, 3, 2}, {4, 5, 7, 6}, {0, 4, 6, 3}, {1, 5, 7, 3}, {2, 3, 7, 6}, {0, 1, 5, 4}};
    static const int normal[6][3] = {{0, 1, 3}, {4, 5, 6}, {0, 4, 6}, {1, 5, 7}, {2, 3, 7}, {0, 1, 5}};
    float n[6][3];
    for (int f = 0; f < 6; ++f)
        face_normal(c[normal[f][0]], c[normal[f][1]], c[normal[f][2]], n[f]);
    int hit = 0;
    for (int f = 0; f < 6 && !hit; ++f) {
        const float *const v[4] = {c[face[f][0]], c[face[f][1]], c[face[f][2]], c[face[f][3]]};
        hit = line_face(in->camera, hero, v, n[f]);
    }
    mu_obj_set_f32(o, MU_OBJF_ALPHA_TARGET, hit ? 0.100000001f : 1.0f);
    return MU_ANIM_APPLIED;
}

static int tick_handler(uint8_t *o, const mu_anim_entry *e, record *r, const mu_anim_inputs *in)
{
    switch (e->handler) {
    case 0:
        return MU_ANIM_APPLIED;
    case 1:   /* 0x00ce165c: the last action of the vector at the end */
        if (at_end(o, e, r, 0)) {
            if (e->extra_count < 1)
                return MU_ANIM_UNSUPPORTED;
            mu_action_set(o, back(e), in);
        }
        return MU_ANIM_APPLIED;
    case 2:   /* 0x00ce1737: after +0x34 loops */
        if (at_end(o, e, r, 0)) {
            if (mu_obj_i32(o, OBJ_LOOPS) >= mu_obj_i32(o, OBJ_LIMIT)) {
                if (e->extra_count < 1)
                    return MU_ANIM_UNSUPPORTED;
                mu_action_set(o, back(e), in);
            }
            mu_obj_set_i32(o, OBJ_LOOPS, mu_obj_i32(o, OBJ_LOOPS) + 1);
        }
        return MU_ANIM_APPLIED;
    case 3:   /* 0x00ce1830: after +0x34 loops, a random action of extra[2..] */
        if (at_end(o, e, r, 0)) {
            if (mu_obj_i32(o, OBJ_LOOPS) >= mu_obj_i32(o, OBJ_LIMIT)) {
                if (e->extra_count <= 2)
                    return MU_ANIM_UNSUPPORTED;   /* the client divides by size - 2 */
                const uint32_t r = (uint32_t)in->rand_fn(in->context);
                mu_action_set(o, e->extra[r % (uint32_t)(e->extra_count - 2) + 2], in);
            }
            mu_obj_set_i32(o, OBJ_LOOPS, mu_obj_i32(o, OBJ_LOOPS) + 1);
        }
        return MU_ANIM_APPLIED;
    case 5:   /* 0x00ce1b61: by the action's own step extra[0] */
    case 7: { /* 0x00ce20c2: the same, with a latch +0x34 */
        if (e->extra_count < 1)
            return MU_ANIM_UNSUPPORTED;
        const int seven = e->handler == 7;
        switch (e->extra[0]) {
        case 0: {   /* the hero comes nearer than param */
            const float d = hero_distance(o, in), p = (float)e->param;
            if (!seven) {
                if (p > d)
                    mu_action_set(o, back(e), in);
            } else if (p > d) {
                if (mu_obj_i32(o, OBJ_LIMIT) == 0)
                    mu_action_set(o, back(e), in);
            } else if (d > p) {
                mu_obj_set_i32(o, OBJ_LIMIT, 0);
            }
            break;
        }
        case 2:
            if (!seven) {   /* the hero leaves param */
                if (hero_distance(o, in) > (float)e->param)
                    mu_action_set(o, back(e), in);
            } else if (at_end(o, e, r, 1)) {
                mu_obj_set_i32(o, OBJ_LIMIT, mu_obj_i32(o, OBJ_LIMIT) + 1);
                mu_action_set(o, back(e), in);
            }
            break;
        case 1: case 3:
            if (at_end(o, e, r, 0))
                mu_action_set(o, back(e), in);
            break;
        default:
            break;
        }
        return MU_ANIM_APPLIED;
    }
    case 4:   /* 0x00ce1947: by extra[0], the mouse over the object's box */
    case 6: { /* 0x00ce1e4b: the same, with a latch +0x34 */
        if (e->extra_count < 1)
            return MU_ANIM_UNSUPPORTED;
        const int six = e->handler == 6;
        switch (e->extra[0]) {
        case 0: {   /* the mouse over the box */
            const int h = hover(o, in);
            if (h < 0)
                return MU_ANIM_UNSUPPORTED;
            if (!six) {
                if (h)
                    mu_action_set(o, back(e), in);
            } else if (h && mu_obj_i32(o, OBJ_LIMIT) == 0) {
                mu_obj_set_i32(o, OBJ_LIMIT, mu_obj_i32(o, OBJ_LIMIT) + 1);
                mu_action_set(o, back(e), in);
            } else {
                mu_obj_set_i32(o, OBJ_LIMIT, 0);
            }
            break;
        }
        case 2:
            if (!six) {   /* the mouse leaves the box */
                const int h = hover(o, in);
                if (h < 0)
                    return MU_ANIM_UNSUPPORTED;
                if (!h)
                    mu_action_set(o, back(e), in);
            } else if (at_end(o, e, r, 1)) {
                mu_action_set(o, back(e), in);
            }
            break;
        case 1: case 3:
            if (at_end(o, e, r, 0))
                mu_action_set(o, back(e), in);
            break;
        default:
            break;
        }
        return MU_ANIM_APPLIED;
    }
    case 8:
        return camera_fade(o, e, in);
    default:
        return MU_ANIM_UNSUPPORTED;
    }
}

int mu_action_tick(uint8_t *o, const mu_anim_inputs *in, int *found)
{
    *found = 0;
    if (!o)
        return MU_ANIM_NONE;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    const int32_t action = (int32_t)mu_obj_u16(o, MU_OBJF_ACTION);
    const mu_anim_entry *e = mu_anim_find(in, type, action);
    if (!e)
        return MU_ANIM_NONE;
    int32_t count = 0;
    int16_t keys = 0;
    uint8_t lock = 0;
    if (!in->model(in->context, type, action, &count, &keys, &lock))
        return MU_ANIM_NONE;
    *found = 1;
    record r = {keys, lock, (uint8_t)(action < (int32_t)(int16_t)count), 0};
    const int status = tick_handler(o, e, &r, in);
    return r.refused ? MU_ANIM_UNSUPPORTED : status;
}

int mu_anim_class_world(int32_t world)
{
    /* world-handler-coverage.md: 57, 58, 62..64, 69..72, 79..82, 91..96, 100, 101, 110..145 */
    return (world >= 57 && world <= 58) || (world >= 62 && world <= 64) || (world >= 69 && world <= 72) ||
           (world >= 79 && world <= 82) || (world >= 91 && world <= 96) || world == 100 || world == 101 ||
           (world >= 110 && world <= 145);
}
