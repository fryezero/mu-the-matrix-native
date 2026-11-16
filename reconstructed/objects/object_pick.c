#include "object_pick.h"

#include <string.h>

/* RENDER-WORLDS-PICK-001: the box write of BMD::Transform 0x012b5bde as RenderObject's setup calls it for a
 * map object (object_pick.h). All arithmetic is binary32 in the client's order. */

void mu_obj_vertex_bounds_begin(float minimum[3], float maximum[3])
{
    for (int k = 0; k < 3; ++k) {
        minimum[k] = 999999.0f;    /* 0x01ac8da0 */
        maximum[k] = -999999.0f;   /* 0x01ac8da4 */
    }
}

void mu_obj_vertex_bounds_add(float minimum[3], float maximum[3], const float vertex[3])
{
    for (int k = 0; k < 3; ++k) {
        if (minimum[k] > vertex[k])
            memcpy(&minimum[k], &vertex[k], 4);
        if (vertex[k] > maximum[k])
            memcpy(&maximum[k], &vertex[k], 4);
    }
}

void mu_obj_obb_write(uint8_t *o, const float body_origin[3], int32_t bounds_mode, const float vertex_minimum[3],
                      const float vertex_maximum[3])
{
    float low[3], high[3];
    if (bounds_mode == 2) {
        memcpy(low, vertex_minimum, sizeof low);
        memcpy(high, vertex_maximum, sizeof high);
    } else {
        memcpy(low, o + MU_OBJF_BOX_MIN, sizeof low);
        memcpy(high, o + MU_OBJF_BOX_MAX, sizeof high);
    }
    mu_obj_obb box;
    memcpy(box.start, low, sizeof low);   /* the minimum's bits; a NaN keeps its payload until the add */
    const float extent[3] = {high[0] - low[0], high[1] - low[1], high[2] - low[2]};
    for (int k = 0; k < 3; ++k)
        box.start[k] = box.start[k] + body_origin[k];
    box.x[0] = extent[0];
    box.x[1] = 0.0f;
    box.x[2] = 0.0f;
    box.y[0] = 0.0f;
    box.y[1] = extent[1];
    box.y[2] = 0.0f;
    box.z[0] = 0.0f;
    box.z[1] = 0.0f;
    box.z[2] = extent[2];
    memcpy(o + MU_OBJF_OBB, &box, sizeof box);
}
