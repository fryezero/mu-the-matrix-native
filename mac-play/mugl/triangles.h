/* SPDX-License-Identifier: MIT */
#ifndef MUGL_TRIANGLES_H
#define MUGL_TRIANGLES_H
#include <stddef.h>
/* OpenGL 1.1 enum values; no GL/Windows dependency for host-side tests. */
enum { MUGL_TRIANGLE_STRIP = 5, MUGL_TRIANGLE_FAN = 6,
       MUGL_QUADS = 7, MUGL_QUAD_STRIP = 8, MUGL_POLYGON = 9 };
size_t mugl_triangle_count(unsigned mode, size_t vertices);
/* Returns 0 for an out-of-range triangle, without touching out. */
int mugl_triangle(unsigned mode, size_t vertices, size_t triangle, size_t out[3]);
#endif
