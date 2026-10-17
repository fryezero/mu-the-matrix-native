/* Mesh-draw case files. See mu_meshdraw_case.h. */
#include "mu_meshdraw_case.h"

#include <stdlib.h>
#include <string.h>

/* ---- writing ---- */

static void w8(FILE *f, uint8_t v) { fputc(v, f); }
static void w16(FILE *f, int16_t v) { uint8_t b[2] = {(uint8_t)v, (uint8_t)((uint16_t)v >> 8)}; fwrite(b, 1, 2, f); }
static void w32(FILE *f, uint32_t v)
{
    uint8_t b[4] = {(uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16), (uint8_t)(v >> 24)};
    fwrite(b, 1, 4, f);
}
static void wf(FILE *f, float v) { uint32_t u; memcpy(&u, &v, 4); w32(f, u); }
static void wfloats(FILE *f, const float *v, size_t n) { for (size_t k = 0; k < n; ++k) wf(f, v ? v[k] : 0.0f); }

int mu_meshdraw_case_write(FILE *f, const mu_meshdraw_globals *g, const mu_gl_cache *c, const mu_meshdraw_model *m,
                           const mu_bitmap *bitmaps, const int32_t *bitmap_index, int32_t bitmap_count,
                           const mu_meshdraw_call *calls, int32_t call_count)
{
    fwrite("MUMC", 1, 4, f);
    w32(f, 1);
    wf(f, g->time);
    wfloats(f, g->env_vector, 3);
    w32(f, (uint32_t)g->skin_base);
    w8(f, c->depth_test); w8(f, c->cull); w8(f, c->depth_mask); w8(f, c->alpha_test); w8(f, c->texture); w8(f, c->fog);
    w32(f, (uint32_t)c->blend);
    w32(f, (uint32_t)c->bound);
    w16(f, m->mesh_count);
    w32(f, (uint32_t)m->hide_typed);
    wfloats(f, m->alt_color, 3);
    w8(f, m->lighting);
    wfloats(f, m->color, 3);
    wfloats(f, m->origin, 3);
    w8(f, (uint8_t)m->light_mesh); w8(f, (uint8_t)m->skin_shift); w8(f, m->flag_a5); w8(f, m->flag_a6);
    w8(f, m->alt_on_skin); w8(f, m->secondary_light);
    w32(f, (uint32_t)m->texture_count);
    for (int32_t k = 0; k < m->texture_count; ++k)
        w32(f, (uint32_t)m->texture_index[k]);
    for (int32_t k = 0; k < m->texture_count; ++k)
        w32(f, (uint32_t)m->texture_type[k]);
    for (int32_t i = 0; i < m->mesh_count; ++i) {
        const mu_meshdraw_mesh *x = &m->meshes[i];
        w8(f, x->flag);
        w16(f, x->texture_slot);
        w32(f, (uint32_t)x->vertex_count);
        w32(f, (uint32_t)x->normal_count);
        w32(f, (uint32_t)x->texcoord_count);
        w32(f, (uint32_t)x->triangle_count);
        w8(f, x->sub != NULL);
        for (int k = 0; k < 5; ++k)
            w8(f, x->sub ? x->sub[k] : 0);
        wfloats(f, x->texcoords, 2 * (size_t)x->texcoord_count);
        fwrite(x->triangles, 0x24, (size_t)x->triangle_count, f);
        wfloats(f, x->vertices, 3 * (size_t)x->vertex_count);
        wfloats(f, x->normals, 3 * (size_t)x->normal_count);
        wfloats(f, x->lights, (size_t)x->normal_count);
        wfloats(f, x->secondary, (size_t)x->normal_count);
    }
    w32(f, (uint32_t)bitmap_count);
    for (int32_t k = 0; k < bitmap_count; ++k) {
        const mu_bitmap *b = &bitmaps[k];
        w32(f, (uint32_t)bitmap_index[k]);
        w8(f, (uint8_t)b->components);
        w32(f, b->name);
        wf(f, b->width);
        wf(f, b->height);
        w32(f, b->pixels ? b->pixel_bytes : 0);
        if (b->pixels && b->pixel_bytes)
            fwrite(b->pixels, 1, b->pixel_bytes, f);
    }
    w32(f, (uint32_t)call_count);
    for (int32_t k = 0; k < call_count; ++k) {
        const mu_meshdraw_call *x = &calls[k];
        w8(f, x->kind);
        w32(f, (uint32_t)x->target);
        w32(f, x->args.flags);
        wf(f, x->args.alpha);
        w32(f, (uint32_t)x->args.select);
        wf(f, x->args.color_scale);
        wf(f, x->args.u_offset);
        wf(f, x->args.v_offset);
        w32(f, (uint32_t)x->args.texture);
    }
    return ferror(f) ? 1 : 0;
}

/* ---- reading ---- */

typedef struct reader {
    const uint8_t *p, *end;
    int bad;
} reader;

static const uint8_t *take(reader *r, size_t n)
{
    if (r->bad || (size_t)(r->end - r->p) < n) {
        r->bad = 1;
        return NULL;
    }
    const uint8_t *q = r->p;
    r->p += n;
    return q;
}
static uint8_t r8(reader *r) { const uint8_t *q = take(r, 1); return q ? q[0] : 0; }
static int16_t r16(reader *r) { const uint8_t *q = take(r, 2); return q ? (int16_t)(uint16_t)(q[0] | q[1] << 8) : 0; }
static uint32_t r32(reader *r)
{
    const uint8_t *q = take(r, 4);
    return q ? (uint32_t)q[0] | (uint32_t)q[1] << 8 | (uint32_t)q[2] << 16 | (uint32_t)q[3] << 24 : 0;
}
static float rf(reader *r) { uint32_t u = r32(r); float v; memcpy(&v, &u, 4); return v; }

/* Arrays are copied into one aligned buffer so float pointers are aligned. */
typedef struct arena {
    uint8_t *base;
    size_t used, size;
} arena;
static void *place(arena *a, const void *src, size_t n)
{
    size_t at = (a->used + 15) & ~(size_t)15;
    if (at + n > a->size)
        return NULL;
    if (n)
        memcpy(a->base + at, src, n);
    a->used = at + n;
    return a->base + at;
}

void mu_meshdraw_case_free(mu_meshdraw_case *c)
{
    free(c->meshes);
    free(c->texture_index);
    free(c->texture_type);
    free(c->subs);
    free(c->bitmaps);
    free(c->bitmap_index);
    free(c->calls);
    free(c->storage);
    memset(c, 0, sizeof *c);
}

int mu_meshdraw_case_read(const uint8_t *data, size_t size, mu_meshdraw_case *c)
{
    memset(c, 0, sizeof *c);
    reader r = {data, data + size, 0};
    const uint8_t *magic = take(&r, 4);
    if (!magic || memcmp(magic, "MUMC", 4) != 0 || r32(&r) != 1)
        return 1;
    arena a = {malloc(size * 2 + 4096), 0, size * 2 + 4096};
    c->storage = a.base;
    if (!a.base)
        return 1;
    c->globals.time = rf(&r);
    for (int k = 0; k < 3; ++k) c->globals.env_vector[k] = rf(&r);
    c->globals.skin_base = (int32_t)r32(&r);
    c->cache.depth_test = r8(&r); c->cache.cull = r8(&r); c->cache.depth_mask = r8(&r);
    c->cache.alpha_test = r8(&r); c->cache.texture = r8(&r); c->cache.fog = r8(&r);
    c->cache.blend = (int32_t)r32(&r);
    c->cache.bound = (int32_t)r32(&r);
    mu_meshdraw_model *m = &c->model;
    m->mesh_count = r16(&r);
    m->hide_typed = (int32_t)r32(&r);
    for (int k = 0; k < 3; ++k) m->alt_color[k] = rf(&r);
    m->lighting = r8(&r);
    for (int k = 0; k < 3; ++k) m->color[k] = rf(&r);
    for (int k = 0; k < 3; ++k) m->origin[k] = rf(&r);
    m->light_mesh = (int8_t)r8(&r); m->skin_shift = (int8_t)r8(&r); m->flag_a5 = r8(&r); m->flag_a6 = r8(&r);
    m->alt_on_skin = r8(&r); m->secondary_light = r8(&r);
    m->texture_count = (int32_t)r32(&r);
    if (r.bad || m->mesh_count < 0 || m->texture_count < 0 || m->texture_count > 4096)
        goto fail;
    c->texture_index = calloc((size_t)m->texture_count + 1, sizeof(int32_t));
    c->texture_type = calloc((size_t)m->texture_count + 1, sizeof(int32_t));
    c->meshes = calloc((size_t)m->mesh_count + 1, sizeof *c->meshes);
    c->subs = calloc((size_t)m->mesh_count + 1, sizeof *c->subs);
    if (!c->texture_index || !c->texture_type || !c->meshes || !c->subs)
        goto fail;
    for (int32_t k = 0; k < m->texture_count; ++k) c->texture_index[k] = (int32_t)r32(&r);
    for (int32_t k = 0; k < m->texture_count; ++k) c->texture_type[k] = (int32_t)r32(&r);
    m->texture_index = c->texture_index;
    m->texture_type = c->texture_type;
    m->meshes = c->meshes;
    for (int32_t i = 0; i < m->mesh_count; ++i) {
        mu_meshdraw_mesh *x = &c->meshes[i];
        x->flag = r8(&r);
        x->texture_slot = r16(&r);
        x->vertex_count = (int32_t)r32(&r);
        int32_t normals = (int32_t)r32(&r);
        x->texcoord_count = (int32_t)r32(&r);
        int32_t triangles = (int32_t)r32(&r);
        if (r.bad || x->vertex_count < 0 || normals < 0 || normals > 32767 || x->texcoord_count < 0 || triangles < 0 ||
            triangles > 32767)
            goto fail;
        x->normal_count = (int16_t)normals;
        x->triangle_count = (int16_t)triangles;
        const uint8_t has_sub = r8(&r);
        for (int k = 0; k < 5; ++k)
            c->subs[i][k] = r8(&r);
        x->sub = has_sub ? c->subs[i] : NULL;
        const size_t tc = 8 * (size_t)x->texcoord_count, tr = 0x24 * (size_t)triangles,
                     vb = 12 * (size_t)x->vertex_count, nb = 12 * (size_t)normals, lb = 4 * (size_t)normals;
        const uint8_t *q;
        if (!(q = take(&r, tc)) || !(x->texcoords = place(&a, q, tc))) goto fail;
        if (!(q = take(&r, tr)) || !(x->triangles = place(&a, q, tr))) goto fail;
        if (!(q = take(&r, vb)) || !(x->vertices = place(&a, q, vb))) goto fail;
        if (!(q = take(&r, nb)) || !(x->normals = place(&a, q, nb))) goto fail;
        if (!(q = take(&r, lb)) || !(x->lights = place(&a, q, lb))) goto fail;
        if (!(q = take(&r, lb)) || !(x->secondary = place(&a, q, lb))) goto fail;
    }
    c->bitmap_count = (int32_t)r32(&r);
    if (r.bad || c->bitmap_count < 0 || c->bitmap_count > 4096)
        goto fail;
    c->bitmaps = calloc((size_t)c->bitmap_count + 1, sizeof *c->bitmaps);
    c->bitmap_index = calloc((size_t)c->bitmap_count + 1, sizeof *c->bitmap_index);
    if (!c->bitmaps || !c->bitmap_index)
        goto fail;
    for (int32_t k = 0; k < c->bitmap_count; ++k) {
        mu_bitmap *b = &c->bitmaps[k];
        c->bitmap_index[k] = (int32_t)r32(&r);
        b->components = (int8_t)r8(&r);
        b->name = r32(&r);
        b->width = rf(&r);
        b->height = rf(&r);
        b->pixel_bytes = r32(&r);
        const uint8_t *q = take(&r, b->pixel_bytes);
        if (!q || !(b->pixels = place(&a, q, b->pixel_bytes)))
            goto fail;
    }
    c->call_count = (int32_t)r32(&r);
    if (r.bad || c->call_count < 0 || c->call_count > 100000)
        goto fail;
    c->calls = calloc((size_t)c->call_count + 1, sizeof *c->calls);
    if (!c->calls)
        goto fail;
    for (int32_t k = 0; k < c->call_count; ++k) {
        mu_meshdraw_call *x = &c->calls[k];
        x->kind = r8(&r);
        x->target = (int32_t)r32(&r);
        x->args.flags = r32(&r);
        x->args.alpha = rf(&r);
        x->args.select = (int32_t)r32(&r);
        x->args.color_scale = rf(&r);
        x->args.u_offset = rf(&r);
        x->args.v_offset = rf(&r);
        x->args.texture = (int32_t)r32(&r);
    }
    if (r.bad || r.p != r.end)
        goto fail;
    return 0;
fail:
    mu_meshdraw_case_free(c);
    return 1;
}

static const mu_bitmap *case_bitmap(void *context, int32_t index)
{
    const mu_meshdraw_case *c = context;
    for (int32_t k = 0; k < c->bitmap_count; ++k)
        if (c->bitmap_index[k] == index)
            return &c->bitmaps[k];
    return NULL;
}

int mu_meshdraw_case_run(mu_meshdraw_case *c, const mu_gl_sink *sink, mu_meshdraw_scratch *scratch,
                         mu_meshdraw_counts *counts)
{
    mu_meshdraw_env env = {&c->model, &c->globals, &c->cache, sink, case_bitmap, c, scratch};
    for (int32_t k = 0; k < c->call_count; ++k) {
        const mu_meshdraw_call *x = &c->calls[k];
        int status;
        if (x->kind == 0) {
            status = mu_meshdraw_body(&env, &x->args, x->target, counts);
        } else {
            long corners = 0;
            status = mu_meshdraw_mesh_draw(&env, x->target, &x->args, &corners);
            if (counts) {
                if (status == MU_MESHDRAW_DRAWN) counts->drawn++;
                else if (status == MU_MESHDRAW_RETURNED) counts->returned++;
                else if (status == MU_MESHDRAW_REFUSED) counts->refused++;
                else counts->faulted++;
                counts->corners += corners;
            }
        }
        if (status == MU_MESHDRAW_FAULT)
            return MU_MESHDRAW_FAULT;
    }
    return 0;
}
