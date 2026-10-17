/* SPDX-License-Identifier: MIT */
#include "triangles.h"
size_t mugl_triangle_count(unsigned mode, size_t n)
{
    switch (mode) {
    case MUGL_TRIANGLE_FAN: case MUGL_TRIANGLE_STRIP: case MUGL_POLYGON:
        return n < 3 ? 0 : n - 2;
    case MUGL_QUADS: return (n / 4) * 2;
    case MUGL_QUAD_STRIP: return n < 4 ? 0 : (n / 2 - 1) * 2;
    default: return 0;
    }
}
int mugl_triangle(unsigned mode, size_t n, size_t t, size_t out[3])
{
    if (t >= mugl_triangle_count(mode, n)) return 0;
    switch (mode) {
    case MUGL_TRIANGLE_FAN: case MUGL_POLYGON:
        out[0] = 0; out[1] = t + 1; out[2] = t + 2; break;
    case MUGL_TRIANGLE_STRIP:
        out[0] = t + (t & 1); out[1] = t + 1 - (t & 1); out[2] = t + 2; break;
    case MUGL_QUADS: {
        size_t i = (t / 2) * 4;
        out[0] = i; out[1] = i + 1 + (t & 1); out[2] = i + 2 + (t & 1); break;
    }
    case MUGL_QUAD_STRIP: {
        size_t i = (t / 2) * 2;
        out[0] = i; out[1] = i + ((t & 1) ? 3 : 1); out[2] = i + ((t & 1) ? 2 : 3); break;
    }
    default: return 0;
    }
    return 1;
}
