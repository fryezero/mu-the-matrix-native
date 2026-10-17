#ifndef MU_MESHDRAW_CASE_H
#define MU_MESHDRAW_CASE_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "mu_meshdraw.h"

/* A self-contained mesh-draw case: every input the routine reads (model
 * fields, meshes, transform outputs, bitmaps, globals, GL caches) plus a list
 * of calls. `mu-render corners --case-out` writes the case it drew;
 * scripts/validate_meshdraw.py builds the same client memory from it, runs the
 * actual routine under Unicorn and compares the GL stream with `mu-render
 * corners` / `mu-render replay`. Format (little endian), version 1:
 *
 *   "MUMC" u32 version
 *   globals   f32 time, f32 env[3], i32 skin_base
 *   cache     u8 depth_test, cull, depth_mask, alpha_test, texture, fog; i32 blend, bound
 *   model     i16 mesh_count, i32 hide_typed, f32 alt[3], u8 lighting, f32 color[3], f32 origin[3],
 *             i8 light_mesh, i8 skin_shift, u8 a5, a6, alt_on_skin, secondary; u32 slots,
 *             i32 texture_index[slots], i32 texture_type[slots]
 *   meshes    per mesh: u8 flag, i16 slot, i32 vertices, normals, texcoords, triangles, u8 has_sub, u8 sub[5],
 *             f32 texcoords[2t], u8 triangles[0x24 n], f32 V[3v], f32 N[3n], f32 L[n], f32 S[n]
 *   bitmaps   u32 count; per bitmap: i32 index, i8 components, u32 name, f32 width, f32 height,
 *             u32 pixel bytes, bytes
 *   calls     u32 count; per call: u8 kind (0 body, 1 mesh), i32 mesh or skip, u32 flags, f32 alpha,
 *             i32 select, f32 scale, f32 u, f32 v, i32 texture
 * Records of the GL stream: u32 op, u32 words[4] (20 bytes). */

typedef struct mu_meshdraw_call {
    uint8_t kind;      /* 0 body, 1 single mesh */
    int32_t target;    /* skip mesh (body) or mesh index */
    mu_meshdraw_args args;
} mu_meshdraw_call;

typedef struct mu_meshdraw_case {
    mu_meshdraw_globals globals;
    mu_gl_cache cache;
    mu_meshdraw_model model;
    mu_meshdraw_mesh *meshes;
    int32_t *texture_index, *texture_type;
    uint8_t (*subs)[5];
    mu_bitmap *bitmaps;
    int32_t *bitmap_index;
    int32_t bitmap_count;
    mu_meshdraw_call *calls;
    int32_t call_count;
    uint8_t *storage;  /* owned buffer the mesh arrays point into */
} mu_meshdraw_case;

int mu_meshdraw_case_write(FILE *file, const mu_meshdraw_globals *globals, const mu_gl_cache *cache,
                           const mu_meshdraw_model *model, const mu_bitmap *bitmaps, const int32_t *bitmap_index,
                           int32_t bitmap_count, const mu_meshdraw_call *calls, int32_t call_count);
int mu_meshdraw_case_read(const uint8_t *data, size_t size, mu_meshdraw_case *out);
void mu_meshdraw_case_free(mu_meshdraw_case *c);

/* Runs every call in order on the case's state. `sink` receives the GL calls;
 * `scratch->tables` (optional) receives the tables each mesh draw wrote. */
void mu_meshdraw_case_run(mu_meshdraw_case *c, const mu_gl_sink *sink, mu_meshdraw_scratch *scratch,
                          mu_meshdraw_counts *counts);

#endif
