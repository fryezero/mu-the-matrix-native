#ifndef MU_OBJECT_PICK_H
#define MU_OBJECT_PICK_H

#include <stdint.h>

#include "object_render.h"

/* RENDER-WORLDS-PICK-001: the map object's box OBJECT +0x31c (docs/research/client-worlds-pick.md).
 *
 * RenderObject's setup 0x017ec896 ends with BMD::Transform through the wrapper 0x00966ea5
 * (0x017edc95 / 0x017edd08): Transform(bones, o + 0x128, o + 0x134, o + 0x31c, translate, 0, 0.4, +0xe4, +0xe8)
 * on the model whose body origin +0x78 the setup copied from the object's position +0x158. The transform
 * 0x012b5bde ends with the box write 0x012b6479..0x012b678a:
 *
 *   bounds mode 0x0b437bfc != 2:  start = the box minimum (o + 0x128), X.x, Y.y, Z.z = maximum - minimum;
 *   bounds mode == 2:             the same from the running bounds of the transformed vertices
 *                                 (start 999999 / -999999 at 0x012b5da3, per vertex at 0x012b6164);
 *   then start += the body origin, and the six off-diagonal axis terms = 0.
 *
 * The box is therefore axis-aligned whatever the object's angle and scale: neither enters the mode != 2
 * write, and mode 2 only sees them through the posed vertices. The client text holds nine references to
 * 0x0b437bfc, all compares, and the address lies outside the initialised image data: the mode stays 0 for
 * the process (static), so mode 2 is the editor's branch. Both are compared with the original instructions
 * by scripts/validate_worlds_pick.py. The object's initialiser 0x0129ef45 zeroes the box. */

/* The box as the client stores it: StartPos, XAxis, YAxis, ZAxis (12 binary32). */
typedef struct mu_obj_obb {
    float start[3], x[3], y[3], z[3];
} mu_obj_obb;

/* 0x012b5da3: the running bounds before the first vertex (mode 2). */
void mu_obj_vertex_bounds_begin(float minimum[3], float maximum[3]);
/* 0x012b6164: one transformed vertex (comiss; jbe: a NaN component changes neither bound). */
void mu_obj_vertex_bounds_add(float minimum[3], float maximum[3], const float vertex[3]);

/* The box write for object o. body_origin is the model's +0x78 (the object's position after the setup).
 * vertex_minimum / vertex_maximum are read only in mode 2. */
void mu_obj_obb_write(uint8_t *object, const float body_origin[3], int32_t bounds_mode,
                      const float vertex_minimum[3], const float vertex_maximum[3]);

/* 0x018500bf(p1, p2, object + 0x31c): 1 when no axis among (p2 - p1) x X, Y, Z and X, Y, Z separates the
 * segment from the box (action_registry.c, the tick handlers 4 and 6 call it with the mouse segment
 * MousePosition 0x0bdc5984 -> MouseTarget 0x0bdc5990). */
int mu_obj_segment_obb(const uint8_t *object, const float p1[3], const float p2[3]);

#endif
