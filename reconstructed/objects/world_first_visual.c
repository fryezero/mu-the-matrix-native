/* RENDER-WORLDS-Q2. The class slot 0x10 that the render pass's draw-first predicate 0x017fcd18 ends with
 * (0x017fe8f7 -> manager wrapper 0x00ea2788): for every world outside the predicate's own cases and its default
 * chain (0x009a645f world 0x27, 0x00e94004 0x3f, 0x00e3068f 0x52..0x5a, 0x016a887a 0x74..0x78, 0x00e1e4b6
 * 0x7b..0x7f, 0x016a8325 0x80..0x82) the answer is the current class's slot 0x10. The base 0x00d5cbc9 answers
 * no; the overrides of worlds 134..145 draw their listed types first when TestFrustrum2D(x / 100, y / 100,
 * range) holds; Twisted Karutan's (0x00e67005) first sets the range to -800. 137 (0x00e08c53), 139 (0x00d9c11b)
 * and 140 (0x00d99f69) answer no. */
#include "world_visual_internal.h"
#include "../terrain/terrain.h"

static const int16_t first_134[] = {1, 3, 4, 6, 7, 8, 9, 12, 16, 17, 18, 19, 21, 22, 24, 26, 31, 33, 34, 35, 36, 37,
                                    39, 42, 45, 46, 50, 55, 62, 64, 69, 92, 109, 113, 133, -1};
static const int16_t first_135[] = {23, 38, 59, 90, 102, 106, -1};
static const int16_t first_136[] = {2, 23, 24, 38, 59, 90, 102, 106, 134, 135, 179, -1};
static const int16_t first_138[] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 16, 17, 29, 30, 59, 95, 153, 157, 171,
                                    173, -1};
static const int16_t first_141[] = {0, 1, 33, 38, 39, 125, 127, 128, 199, -1};
static const int16_t first_142[] = {0, 1, 2, 5, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 30, 43, 59, 60,
                                    61, 65, 70, 72, 74, 75, 77, 84, 85, 89, 91, 95, 98, 102, 107, 117, 119, 130, 139,
                                    140, 141, 142, 143, 144, 148, 153, 154, 158, 160, 161, 165, -1};
static const int16_t first_143[] = {0, 1, 2, 3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 26, 27, 30, 33, 34, 35, 36,
                                    37, 42, 54, 55, 57, 72, 73, 74, 75, 76, 77, 78, 88, 89, 95, 97, 100, 109, 110,
                                    113, 115, 121, 122, 124, 125, 128, 131, 132, 134, 139, 140, 142, 143, 145, 146,
                                    147, 150, 151, 152, 156, 166, 168, -1};
static const int16_t first_144[] = {4, 6, 10, 13, 16, 18, 21, 23, 24, 25, 26, 27, 28, 31, 33, 34, 35, 36, 37, 38, 39,
                                    43, 54, 55, 57, 59, 64, 66, 67, 73, 74, 77, 78, 79, 82, 90, 91, 94, 106, 107,
                                    109, 110, 111, 112, 113, 116, 120, 121, 122, 125, 126, 127, 129, 130, 131, 132,
                                    140, 141, 142, 144, 145, 146, 147, 148, 153, 181, 183, 200, -1};
static const int16_t first_145[] = {0, 2, 3, 7, 8, 9, 10, 12, 15, 16, 51, 55, 56, 58, 59, 62, 64, 65, 67, 68, 69, 71,
                                    76, 77, 79, 80, 81, 82, 90, 95, 96, 97, 99, 100, 105, 108, 109, 113, 114, 119,
                                    120, 124, 131, 137, 143, 148, 160, 161, 165, 166, -1};

static const int16_t *first_types(int32_t world)
{
    switch (world) {
    case 134: return first_134;   /* 0x00d83dd1 */
    case 135: return first_135;   /* 0x00e3a304 */
    case 136: return first_136;   /* 0x00d935b4 */
    case 138: return first_138;   /* 0x00e05882 */
    case 141: return first_141;   /* 0x00e4beaa */
    case 142: return first_142;   /* 0x00e67005 */
    case 143: return first_143;   /* 0x00e0e1fa */
    case 144: return first_144;   /* 0x00e46042 */
    case 145: return first_145;   /* 0x00d752ad: live objects only */
    default: return NULL;
    }
}

int mu_class_first_owned(int32_t world)
{
    return world >= 134 && world <= 145;
}

int mu_class_first(uint8_t *o, int32_t world, const float x2d[4], const float y2d[4], int32_t scene_state)
{
    const int16_t *list = first_types(world);
    if (!list || (world == 145 && !o[MU_OBJF_LIVE]))
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    int listed = 0;
    for (int k = 0; list[k] >= 0 && !listed; ++k)
        listed = t == list[k];
    if (!listed)
        return 0;
    if (world == 142)
        mu_obj_set_f32(o, MU_OBJF_RANGE, -800.0f);
    const float x = mu_obj_f32(o, MU_OBJF_POSITION) * 0.01f, y = mu_obj_f32(o, MU_OBJF_POSITION + 4) * 0.01f;
    return mu_terrain_test_frustum_2d(x2d, y2d, scene_state, x, y, mu_obj_f32(o, MU_OBJF_RANGE)) ? 1 : 0;
}
