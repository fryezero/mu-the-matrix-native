/* Compare direct corner delivery with the literal stream and scratch tables.
 * The render backend maps both Color3f and Color3fv to the same color3 call. */
#include "../core/mu_meshdraw_case.h"
#include "../core/mu_perf_mesh.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef PERF_MUTANT
#define PERF_MUTANT 0
#endif
static uint32_t bits(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static void record(void *ctx, uint32_t op, const uint32_t words[4])
{
    (void)ctx;
    uint32_t out[5] = {op == MU_GL_OP_COLOR3F ? MU_GL_OP_COLOR3FV : op,
                       words[0], words[1], words[2], words[3]};
    fwrite(out, sizeof out, 1, stdout);
}
static void texcoord(void *c, float s, float t)
{
    uint32_t w[4] = {bits(s), bits(t), 0, 0}; record(c, MU_GL_OP_TEXCOORD2F, w);
}
static void color3(void *c, const float v[3])
{
    uint32_t w[4] = {bits(v[0]), bits(v[1]), bits(v[2]), 0}; record(c, MU_GL_OP_COLOR3FV, w);
}
static void color4(void *c, float r, float g, float b, float a)
{
    if (PERF_MUTANT == 2) a = 1.0f;
    uint32_t w[4] = {bits(r), bits(g), bits(b), bits(a)}; record(c, MU_GL_OP_COLOR4F, w);
}
static void vertex(void *c, const float v[3])
{
    if (PERF_MUTANT == 1) return;
    uint32_t w[4] = {bits(v[0]), bits(v[1]), bits(v[2]), 0}; record(c, MU_GL_OP_VERTEX3FV, w);
}
static const mu_bitmap *bitmap(void *ctx, int32_t index)
{
    const mu_meshdraw_case *c = ctx;
    for (int32_t i = 0; i < c->bitmap_count; ++i)
        if (c->bitmap_index[i] == index) return &c->bitmaps[i];
    return NULL;
}
int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    FILE *f = fopen(argv[2], "rb");
    if (!f) return 2;
    fseek(f, 0, SEEK_END); long size = ftell(f); rewind(f);
    if (size <= 0) return 2;
    uint8_t *bytes = malloc((size_t)size);
    if (!bytes || fread(bytes, 1, (size_t)size, f) != (size_t)size) return 2;
    fclose(f);
    mu_meshdraw_case c;
    if (mu_meshdraw_case_read(bytes, (size_t)size, &c)) return 2;
    free(bytes);
    float colors[3 * MU_MESHDRAW_MAX_ENTRIES] = {0};
    float table[2 * (MU_MESHDRAW_MAX_ENTRIES + 1)] = {0};
    mu_meshdraw_scratch scratch = {colors, table, NULL, NULL};
    mu_gl_sink sink = {NULL, record};
    mu_meshdraw_sink direct = {NULL, texcoord, color3, color4, vertex};
    mu_meshdraw_env env = {&c.model, &c.globals, &c.cache, &sink, bitmap, &c, &scratch,
                           atoi(argv[1]) ? &direct : NULL};
    mu_meshdraw_counts counts = {0};
    int validated = atoi(argv[1]) == 2;
    mu_perf_mesh_cache *cache = mu_perf_mesh_new(c.model.mesh_count);
    for (int32_t i = 0; i < c.call_count; ++i) {
        mu_meshdraw_call *call = &c.calls[i];
        int status;
        uint64_t regular = 0;
        if (validated)
            for (int32_t m = 0; m < c.model.mesh_count && m < 64; ++m)
                if (mu_perf_mesh_regular(cache, m, &c.model.meshes[m])) regular |= UINT64_C(1) << m;
        if (call->kind == 0) status = mu_meshdraw_body_validated(&env, &call->args, call->target, &counts, regular);
        else {
            long corners;
            int m = call->target;
            status = m >= 0 && m < 64 && (regular & (UINT64_C(1) << m))
                ? mu_meshdraw_mesh_draw_validated(&env, m, &call->args, &corners)
                : mu_meshdraw_mesh_draw(&env, m, &call->args, &corners);
        }
        uint32_t w[4] = {(uint32_t)status, 0, 0, 0}; record(NULL, 0, w);
        if (status == MU_MESHDRAW_FAULT) break;
    }
    fwrite(colors, sizeof colors, 1, stdout);
    fwrite(table, sizeof table, 1, stdout);
    mu_perf_mesh_free(cache);
    mu_meshdraw_case_free(&c);
    return ferror(stdout) ? 1 : 0;
}
