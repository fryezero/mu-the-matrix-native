#ifndef MU_EDGE_H
#define MU_EDGE_H

#include <stdint.h>

#include "mu_meshdraw.h"

/* Client-memory view of a mesh whose triangle records index past their arrays
 * (MODEL-EDGE, docs/research/model-edge.md).
 *
 * The client's mesh draw 0x012b8d1d bounds no corner index. Executed on the
 * installed records it reads, for an index past its array:
 *   texcoord  the heap past the mesh's texcoord block (mesh +0x14 + 8*index);
 *   colour    &colour_table[mesh][index], passed to glColor3fv: the persistent
 *             per-mesh table 0x089c2120 + mesh*0x2bf20, or (negative index) the
 *             memory before it, which is the transform's normal buffer;
 *   normal    the per-normal texcoord table 0x072acfd8 (modes 4/0x1000/...);
 *   vertex    the transform's per-mesh vertex slot past the model's vertices.
 * All of these hold whatever earlier draws, transforms or allocations left.
 * mu_meshdraw_corners refuses such a mesh; the client draws it. This module
 * reproduces the client's corner stream for the state of a freshly loaded
 * client in which nothing has been written past the model's own entries: each
 * out-of-range index is redirected to an appended zero entry (the zero-filled
 * uninitialized data of the third image section). For the heap texcoord no
 * client state is known; zero is a labelled substitute. In-range corners are
 * untouched, so the stream is the client's stream except at those values. */

typedef struct mu_edge_view {
    uint8_t *triangles;      /* remapped copy of the 0x24-byte records */
    float *texcoords;        /* original entries followed by the zero substitutes */
    float *light_colors;
    float *normal_texcoords;
    float *vertices;
    int32_t redirected;      /* corner fields redirected */
} mu_edge_view;

/* Returns 1 and fills *out (a copy of *in pointing at the view's arrays) when a
 * corner index of an active corner (0..min(corners,4)-1) lies outside its
 * array; 0 when the mesh needs no view (out = *in); -1 when out of memory. */
int mu_edge_mesh_view(const mu_meshdraw_mesh *in, mu_meshdraw_mesh *out, mu_edge_view *view);
void mu_edge_view_free(mu_edge_view *view);

#endif
