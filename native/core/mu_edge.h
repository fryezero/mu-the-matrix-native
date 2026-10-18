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
 * The mesh-draw port refuses such a mesh (its authored index check); the
 * client draws it. This module reproduces the client's corner stream for the
 * state of a freshly loaded client in which nothing has been written past the
 * model's own entries: each out-of-range index is redirected to an appended
 * zero entry (the zero-filled uninitialized data of the third image section).
 * For the heap texcoord no client state is known; zero is a labelled
 * substitute. In-range corners are untouched, so the stream is the client's
 * stream except at those values.
 *
 * Appended normals extend the mesh's normal count, so the port's colour pass
 * and normal-texcoord table also run over them; mu_edge_zero_tables (from the
 * scratch `tables` hook, after the tables are written and before the corner
 * loop) resets those entries to the fresh-client zeros. */

typedef struct mu_edge_view {
    uint8_t *triangles;      /* remapped copy of the 0x24-byte records */
    float *texcoords;        /* original entries followed by the zero substitutes */
    float *vertices, *normals, *lights, *secondary;
    int32_t normal_count;    /* the mesh's own normals; entries from here on are appended */
    int32_t extended_count;  /* normal count of the view */
    int32_t redirected;      /* corner fields redirected */
} mu_edge_view;

/* Returns 1 and fills *out (a copy of *in pointing at the view's arrays) when a
 * corner index lies outside its array (normal/texcoord fields of the active
 * corners, vertex fields of corners 0..max(corners,3)-1, as the port checks);
 * 0 when the mesh needs no view (out = *in); -1 when out of memory or when the
 * extended counts exceed the port's limits. */
int mu_edge_mesh_view(const mu_meshdraw_mesh *in, mu_meshdraw_mesh *out, mu_edge_view *view);
void mu_edge_view_free(mu_edge_view *view);

/* Zeroes the appended entries of the port's colour table (3 floats per normal)
 * and normal-texcoord table (2 floats per normal) for a mesh drawn through `view`. */
void mu_edge_zero_tables(const mu_edge_view *view, float *light_colors, float *normal_texcoords);

#endif
