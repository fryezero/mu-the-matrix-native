/* RENDER-WORLDS-AFTER4. The render pass's draw-first predicate 0x017fcd18 for every world: an object answered
 * yes is drawn before RenderObjects' frustum test (object_render.c). The predicate switches on the world
 * ([0x01cf15fc]); a world case that answers no, and every world without a case, falls through to the default
 * chain at 0x017fe2a8, whose last step is the class slot 0x10 (mu_class_first, RENDER-WORLDS-Q2).
 *
 * Own cases (a type list, sometimes the live byte +0 through 0x0095f977, then TestFrustrum2D 0x016ccce7 at
 * (x / 100, y / 100) with the object's range +0xc0 or a constant):
 *   0 (0x017fd66f), 0x21 (0x017fd733), 0x4a (0x017fd24d): listed types answer yes with no frustum test;
 *   0x33 (live == 1, -400), 0x38 (live, -1500), 0x39/0x3a (-600), 0x70 (live == 1, range), 0x85 (range, then
 *   live), the others with the range;
 *   0x49 (0x017fce36): a fade by the camera distance d = |[0x0bdc5ab4] - position| in x/y (sqrt 0x00961a07):
 *     types 0x7a..0x7c, 0x7e, 0x7f, 0x81, 0x9f inside TestFrustrum2D(-500) and 4000 > d raise +0xa8 and +0xd8
 *     by 0.03 (or set 1 once they reach it) and answer yes; any type <= 300 inside TestFrustrum2D(-500) and
 *     2000 > d raises +0xd8 and answers yes; otherwise d > 2000 with +0xd8 != 0 clears +0xa8, +0xdc, +0xd8.
 * Default chain:
 *   0x009a645f on (0x009a6ef3() + 0x78): world 0x27 and its state +4 not 3, 4 or 5 -> types 0 and 0x4bc;
 *   0x00e94004 (world 0x3f) and 0x00e3068f (0x52..0x5a): types 0x10, 0x43, 0x44 (0x3f also 0x45), -600;
 *   0x016a887a (0x74..0x78): every object whose range is <= -400, with its range;
 *   0x00e1e4b6 (0x7b..0x7f): a type list, range;
 *   0x016a8325 (0x80..0x82): the live byte, a type list, range;
 *   then the class slot 0x10 through the manager 0x00ea594b / 0x00ea2788. */
#include <math.h>

#include "world_visual_internal.h"
#include "../terrain/terrain.h"

#define END (-1)

static const int32_t w0[] = {0x3c, 0x37, END};
static const int32_t w2[] = {0x7a, 0x7b, END};
static const int32_t w21[] = {0x21, 0x23, END};
static const int32_t w25[] = {0x4b, 0x20, 0x7c, 0x75, 0x55, 0x38, END};
static const int32_t w33[] = {4, 0x81, 0x73, 0x39, 0xa6, 0xa7, 0x7e, 0x5b, 0x26, 0x20, 0x1e, 0x80, END};  /* + 5..0xe, 0x57..0x58 */
static const int32_t w38[] = {0x10, 0x27, 0x33, 0x38, 0x46, 0x4c, 0x55, END};
static const int32_t w39[] = {0x1e, 0x1f, END};
static const int32_t w4a[] = {0x81, 0x62, END};
static const int32_t w5b[] = {0x1d, 0x1b, 0x3c, END};
static const int32_t w64[] = {0x14, 0x1d, 0x21, 0x22, 0x23, 0x27, 0x36, 0x37, 0x38, 0x60, 0x61, END};
static const int32_t w6e[] = {0, 8, 9, 0x13, 0x1c, 0xc, 0xb, 6, 0x23, 0x24, 0x25, 0x26, 0x3c, 0x40, 0x9a, END};
static const int32_t w70[] = {0xa, 0x12, 0x16, 0x1a, 0x1d, 0x1f, 0x22, 0x25, 0x3c, 0x41, 0x54, 0x61, 0x62, 0x6a, 0x72,
                              0x7e, 0x7f, 0x89, 0x98, 0x99, 0x9a, END};
static const int32_t w71[] = {0, 1, 2, 3, 7, 8, 0xa, 0xb, 0x17, 0x21, 0x33, 0x34, 0x46, 0x47, 0x4e, 0x50, 0x54, 0x55,
                              0x63, 0x66, 0x6a, 0x73, 0x76, 0x80, 0x82, 0x85, 0x92, 0x96, 0x9d, 0x9f, END};
static const int32_t w7a[] = {0, 1, 2, 3, 8, 9, 0xe, 0xf, 0x10, 0x11, 0x13, 0x1b, 0x1e, 0x21, 0x24, 0x30, 0x31, 0x32,
                              0x33, 0x35, 0x3a, 0x3d, 0x3f, 0x40, 0x44, 0x4a, 0x4b, 0x4e, 0x58, 0x5c, 0x5d, 0x5e, 0x5f,
                              0x64, 0x67, 0x69, 0x6d, 0x6e, 0x6f, 0x71, 0x74, 0x75, 0x7c, 0x83, 0x84, 0x85, 0xad, 0xae,
                              END};
static const int32_t w83[] = {0xc, 0x16, 0x19, 0x1a, 0x1c, 0x22, 0x26, 0x27, 0x2c, 0x2d, 0x32, 0x3b, 0x3c, 0x3d, 0x3f,
                              0x43, 0x52, 0x53, 0x54, 0x55, 0x58, 0x5f, 0x60, 0x62, 0x6a, 0x72, 0x77, 0x78, 0x79, 0x7f,
                              0x80, 0x83, 0x85, 0x8d, 0x98, 0x9a, 0x9b, 0xac, 0xad, 0, 2, 3, 5, 8, 0xa, 0x46, 0x4b,
                              0x4e, END};
static const int32_t w84[] = {0x1e, END};
static const int32_t w85[] = {1, 2, 3, 5, 7, 8, 0xa, 0xb, 0x10, 0x11, 0x16, 0x17, 0x1d, 0x1e, 0x1f, 0x3d, 0x40, 0x41,
                              0x42, 0x43, 0x4b, 0x50, 0x51, 0x73, 0x7e, 0x80, 0x81, 0x85, 0x88, 0x89, 0x91, 0x94, 0x9d,
                              0xac, END};
static const int32_t w49_near[] = {0x7a, 0x7b, 0x7c, 0x9f, 0x7e, 0x81, 0x7f, END};
static const int32_t c_tower[] = {0, 0x4bc, END};
static const int32_t c_3f[] = {0x10, 0x43, 0x44, 0x45, END};
static const int32_t c_52[] = {0x10, 0x43, 0x44, END};
static const int32_t c_7b[] = {0, 1, 0x17, 0x23, 0x25, 0x2b, 0x2c, 0x2d, 0x40, 0x4f, 0x51, 0x55, 0x5d, 0x60, 0x67, 0x6b,
                               0x6f, 0x7d, 0x86, 0x91, 0x9a, 0x9e, END};
static const int32_t c_80[] = {1, 4, 5, 6, 8, 7, 9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf, 0x10, 0x11, 0x12, 0x13, 0x14, 0x18,
                               0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x2a, 0x2d, 0x31,
                               0x33, 0x34, 0x38, 0x39, 0x3a, 0x3c, 0x3e, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
                               END};

static int listed(int32_t t, const int32_t *list)
{
    for (int32_t k = 0; list[k] != END; ++k)
        if (t == list[k])
            return 1;
    return 0;
}

static int frustum(const uint8_t *o, const mu_draw_first_inputs *in, float range)
{
    const float x = mu_obj_f32(o, MU_OBJF_POSITION) * 0.01f, y = mu_obj_f32(o, MU_OBJF_POSITION + 4) * 0.01f;
    return mu_terrain_test_frustum_2d(in->x2d, in->y2d, in->scene_state, x, y, range) ? 1 : 0;
}

static float range_of(const uint8_t *o)
{
    return mu_obj_f32(o, MU_OBJF_RANGE);
}

static void fade_in(uint8_t *o, uint32_t field)   /* 1.0 > v ? v + 0.03 : 1.0 (unordered sets 1) */
{
    const float v = mu_obj_f32(o, field);
    mu_obj_set_f32(o, field, 1.0f > v ? v + 0.0299999993f : 1.0f);
}

/* 0x017fce36: world 0x49. */
static int world_49(uint8_t *o, int32_t t, const mu_draw_first_inputs *in)
{
    const float dx = in->eye[0] - mu_obj_f32(o, MU_OBJF_POSITION);
    const float dy = in->eye[1] - mu_obj_f32(o, MU_OBJF_POSITION + 4);
    const float sum = dx * dx + dy * dy;
    const float d = (float)sqrt((double)sum);
    const float r = 2000.0f;
    if (listed(t, w49_near) && frustum(o, in, -500.0f) && r * 2.0f > d) {
        fade_in(o, MU_OBJF_BLEND_LIGHT);
        fade_in(o, MU_OBJF_ALPHA_TARGET);
        return 1;
    }
    if (frustum(o, in, -500.0f) && r > d && t <= 300) {
        fade_in(o, MU_OBJF_ALPHA_TARGET);
        return 1;
    }
    const float target = mu_obj_f32(o, MU_OBJF_ALPHA_TARGET);
    if (!(target == 0.0f) && d > r) {
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, 0.0f);
        mu_obj_set_f32(o, MU_OBJF_ALPHA, 0.0f);
        mu_obj_set_f32(o, MU_OBJF_ALPHA_TARGET, 0.0f);
    }
    return 0;
}

/* The world switch 0x017fcd27..0x017fe2a3; 0 continues with the default chain. */
static int own_case(uint8_t *o, int32_t world, int32_t t, const mu_draw_first_inputs *in)
{
    const uint8_t live = o[MU_OBJF_LIVE];
    switch (world) {
    case 0: return listed(t, w0);
    case 0x21: return listed(t, w21);
    case 0x4a: return listed(t, w4a);
    case 2: return listed(t, w2) && frustum(o, in, range_of(o));
    case 0x25: return listed(t, w25) && frustum(o, in, range_of(o));
    case 0x33:
        return ((t >= 5 && t <= 0xe) || (t >= 0x57 && t <= 0x58) || listed(t, w33)) && live == 1 &&
               frustum(o, in, -400.0f);
    case 0x38: return listed(t, w38) && live && frustum(o, in, -1500.0f);
    case 0x39: case 0x3a: return listed(t, w39) && frustum(o, in, -600.0f);
    case 0x49: return world_49(o, t, in);
    case 0x5b: case 0x5c: return listed(t, w5b) && frustum(o, in, range_of(o));
    case 0x64: case 0x65: return listed(t, w64) && frustum(o, in, range_of(o));
    case 0x6e: case 0x6f: return listed(t, w6e) && frustum(o, in, range_of(o));
    case 0x70: return listed(t, w70) && live == 1 && frustum(o, in, range_of(o));
    case 0x71: return listed(t, w71) && frustum(o, in, range_of(o));
    case 0x7a: return listed(t, w7a) && frustum(o, in, range_of(o));
    case 0x83: return listed(t, w83) && frustum(o, in, range_of(o));
    case 0x84: return listed(t, w84) && frustum(o, in, range_of(o));
    case 0x85: return listed(t, w85) && frustum(o, in, range_of(o)) && live;
    default: return 0;
    }
}

/* The default chain 0x017fe2a8..0x017fe8f5 (each step's world test, then its type list and frustum test). */
static int chain(uint8_t *o, int32_t world, int32_t t, const mu_draw_first_inputs *in)
{
    if (world == 0x27 && in->tower_state != 3 && in->tower_state != 4 && in->tower_state != 5 && listed(t, c_tower))
        return 1;
    if (world == 0x3f && listed(t, c_3f) && frustum(o, in, -600.0f))
        return 1;
    if (world >= 0x52 && world <= 0x5a && listed(t, c_52) && frustum(o, in, -600.0f))
        return 1;
    if (world >= 0x74 && world <= 0x78 && -400.0f >= range_of(o) && frustum(o, in, range_of(o)))
        return 1;
    if (world >= 0x7b && world <= 0x7f && listed(t, c_7b) && frustum(o, in, range_of(o)))
        return 1;
    if (world >= 0x80 && world <= 0x82 && o[MU_OBJF_LIVE] && listed(t, c_80) && frustum(o, in, range_of(o)))
        return 1;
    return mu_class_first_owned(world) ? mu_class_first(o, world, in->x2d, in->y2d, in->scene_state) : 0;
}

int mu_draw_first(uint8_t *o, int32_t world, const mu_draw_first_inputs *in)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    return own_case(o, world, t, in) || chain(o, world, t, in);
}
