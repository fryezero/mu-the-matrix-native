#include "link_selector.h"
#include <stddef.h>

/* The cases of 0x0137eefc (jump table 0x0137f5f9 for 0x7a5..0x7ed, then the
 * compare chain) and of its first default helper 0x00df230b. Each row is the
 * pair of immediates the case stores; mask 1 means the case stores slot 0 only. */
static const struct { uint16_t type; uint8_t bone[2], mask; } LINKS[] = {
    {0x7a5, {42, 33}, 3},
    {0x7a6, {19, 14}, 3},
    {0x7a8, {26, 36}, 3},
    {0x7a9, {41, 32}, 3},
    {0x7aa, {41, 32}, 3},
    {0x7ad, {29, 38}, 3},
    {0x7af, {41, 32}, 3},
    {0x7b0, {30, 39}, 3},
    {0x7b5, {30, 39}, 3},
    {0x7b7, {26, 35}, 3},
    {0x7b8, {31, 22}, 3},
    {0x7ba, {24, 19}, 3},
    {0x7bb, {25, 16}, 3},
    {0x7bd, {39, 30}, 3},
    {0x7bf, {16, 25}, 3},
    {0x7c0, {17, 28}, 3},
    {0x7c2, {30, 39}, 3},
    {0x7c3, {42, 33}, 3},
    {0x7c7, {30, 39}, 3},
    {0x7c8, {30, 39}, 3},
    {0x7c9, {52, 65}, 3},
    {0x7cd, {20, 33}, 3},
    {0x7ce, {23, 0}, 1},
    {0x7cf, {43, 0}, 1},
    {0x7d1, {55, 70}, 3},
    {0x7d3, {39, 39}, 3},
    {0x7d4, {27, 38}, 3},
    {0x7d5, {32, 43}, 3},
    {0x7d9, {36, 45}, 3},
    {0x7da, {30, 39}, 3},
    {0x7dc, {27, 18}, 3},
    {0x7de, {30, 39}, 3},
    {0x7e0, {33, 20}, 3},
    {0x7e1, {1, 1}, 3},
    {0x7e5, {29, 49}, 3},   /* 0x00df230b */
    {0x7e7, {13, 14}, 3},   /* 0x00df230b */
    {0x7e8, {56, 42}, 3},   /* 0x00df230b */
    {0x7e9, {60, 60}, 3},   /* 0x00df230b */
    {0x7ea, {41, 51}, 3},   /* 0x00df230b */
    {0x7eb, {33, 42}, 3},
    {0x7ec, {33, 42}, 3},
    {0x7ed, {33, 42}, 3},
    {0x8e0, {41, 32}, 3},
    {0x8e2, {19, 14}, 3},
    {0x8e3, {29, 38}, 3},
    {0x8e4, {41, 32}, 3},
    {0x8e5, {42, 33}, 3},
    {0x8e6, {26, 36}, 3},
    {0x8e7, {30, 39}, 3},
    {0x912, {36, 45}, 3},
    {0x914, {36, 45}, 3},
    {0x915, {30, 39}, 3},
    {0x917, {27, 18}, 3},
    {0x94f, {32, 68}, 3},
    {0x950, {43, 0}, 1},
};

int mu_link_bones(int32_t type, uint8_t bones[2])
{
    for (size_t i = 0; i < sizeof LINKS / sizeof LINKS[0]; ++i)
        if (LINKS[i].type == type) {
            if (LINKS[i].mask & MU_LINK_SLOT0) bones[0] = LINKS[i].bone[0];
            if (LINKS[i].mask & MU_LINK_SLOT1) bones[1] = LINKS[i].bone[1];
            return LINKS[i].mask;
        }
    if (type == 0x7ee || type == 0xa2f) return MU_LINK_OTHER;   /* 0x00d9013e's two compares */
    bones[0] = 33; bones[1] = 42;                               /* 0x0137f5d9, 0x0137f5ec */
    return MU_LINK_SLOT0 | MU_LINK_SLOT1;
}

int mu_link_index(int32_t model, int32_t action)
{
    return model == 0xa91 && (action == 0x73 || action == 0x74);
}
