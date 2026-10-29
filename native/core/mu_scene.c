/* Per-model draw driver over the mesh-draw port. See mu_scene.h. */
#include "mu_scene.h"

#include "mu_edge.h"
#include "mu_perf_mesh.h"

#include <stdlib.h>
#include <string.h>

void mu_draw_default_options(mu_draw_options *o)
{
    memset(o, 0, sizeof *o);
    o->flags = 2;
    o->alpha = 1.0f;
    o->select = -1;
    o->color_scale = 1.0f;
    o->skip_mesh = -1;
    o->texture = -1;
    o->cull = -1;
}

const mu_bitmap *mu_scene_bitmap(void *context, int32_t index)
{
    const mu_scene_inputs *in = context;
    for (int32_t k = 0; k < in->bitmap_count; ++k)
        if (in->bitmap_index[k] == index)
            return &in->bitmaps[k];
    return NULL;
}

void mu_scene_inputs_free(mu_scene_inputs *in)
{
    free(in->meshes);
    free(in->texture_index);
    free(in->texture_type);
    free(in->bitmaps);
    free(in->bitmap_index);
    free(in->subs);
    memset(in, 0, sizeof *in);
}

static int inputs_fill(const mu_model *model, const mu_draw_options *o, mu_scene_inputs *in)
{
    const mu_bmd *b = model->bmd;
    const mu_model_params *p = &model->params;
    const int32_t count = b->mesh_count;
    const int32_t extras = o->textures ? o->textures->extra_count : 0;
    for (int32_t i = 0; i < count; ++i) {
        const mu_bmd_mesh *bm = &b->meshes[i];
        mu_meshdraw_mesh *m = &in->meshes[i];
        m->flag = 0;  /* the loader writes 0 (0x012b3edd) */
        m->texture_slot = (int16_t)bm->texture_index;
        m->normal_count = (int16_t)bm->normal_count;
        m->triangle_count = (int16_t)bm->polygon_count;
        m->texcoords = mu_model_texcoords(model, i);
        m->triangles = mu_model_triangles(model, i);
        /* +0x1c from the texture name, as the loader 0x012b409a..0x012b4130 */
        m->sub = mu_meshdraw_sub_from_name((const uint8_t *)bm->texture, in->subs[i]) ? in->subs[i] : NULL;
        m->vertex_count = bm->vertex_count;
        m->texcoord_count = bm->uv_count;
        m->vertices = mu_model_vertices(model, i);
        m->normals = mu_model_normals(model, i);
        m->lights = mu_model_lights(model, i);
        m->secondary = mu_model_secondary_lights(model, i);
        /* a special mesh name keeps the client's index (RENDER-ITEMS-TEX-001), so the substitutions apply */
        in->texture_index[i] = o->textures && o->textures->client_index && i < o->textures->model_count &&
                                       o->textures->client_index[i] ? o->textures->client_index[i]
                                                                    : MU_SCENE_TEXTURE_BASE + i;
        /* RENDER-ITEMS-TEX-002: the item loader's TextureType (0x012b3e2e writes 0 for other loaders) */
        in->texture_type[i] = o->textures && o->textures->texture_type && i < o->textures->model_count
                                  ? o->textures->texture_type[i] : 0;
    }
    const mu_textures *t = o->textures;
    int32_t n = 0;
    for (int32_t k = 0; k < count; ++k, ++n) {
        mu_bitmap *bm = &in->bitmaps[n];
        in->bitmap_index[n] = MU_SCENE_TEXTURE_BASE + k;
        const mu_image *image = (t && k < t->model_count) ? t->slots[k] : NULL;
        bm->components = (t && k < t->model_count) ? t->components[k] : 3;
        if (bm->components == 0)
            bm->components = 3;  /* missing: the client binds its error bitmap; drawn untextured here */
        bm->name = image ? (uint32_t)k + 1 : 0;
        bm->width = image ? (float)image->width : 0.0f;
        bm->height = image ? (float)image->height : 0.0f;
        bm->pixels = NULL;  /* freed by the client's loaders after the upload */
        bm->pixel_bytes = 0;
    }
    for (int32_t k = 0; k < MU_TEXTURE_SPECIAL_COUNT; ++k, ++n) {
        mu_bitmap *bm = &in->bitmaps[n];
        in->bitmap_index[n] = mu_texture_specials[k].index;
        const int32_t s = t ? t->model_count + k : -1;
        const mu_image *image = (t && s < t->count) ? t->slots[s] : NULL;
        bm->components = 3;
        bm->name = image ? (uint32_t)count + 1 + (uint32_t)k : 0;
        bm->width = image ? (float)image->width : 0.0f;
        bm->height = image ? (float)image->height : 0.0f;
        bm->pixels = NULL;  /* none of these indices keeps its pixels in the client */
        bm->pixel_bytes = 0;
    }
    for (int32_t j = 0; j < extras; ++j, ++n) {   /* NATIVE-HELPERS-002: the model passes' extra bitmaps */
        mu_bitmap *bm = &in->bitmaps[n];
        in->bitmap_index[n] = t->extra_index[j];
        const int32_t s = t->model_count + MU_TEXTURE_SPECIAL_COUNT + j;
        const mu_image *image = s < t->count ? t->slots[s] : NULL;
        bm->components = image && t->components[s] ? t->components[s] : 3;
        bm->name = image ? (uint32_t)s + 1 : 0;
        bm->width = image ? (float)image->width : 0.0f;
        bm->height = image ? (float)image->height : 0.0f;
        bm->pixels = NULL;
        bm->pixel_bytes = 0;
    }
    in->bitmap_count = n;

    mu_meshdraw_model *M = &in->model;
    M->mesh_count = (int16_t)count;
    M->meshes = in->meshes;
    M->texture_index = in->texture_index;
    M->texture_type = in->texture_type;
    M->texture_count = count;
    M->lighting = p->lighting;
    memcpy(M->color, p->color, sizeof M->color);
    memcpy(M->origin, p->origin, sizeof M->origin);
    M->light_mesh = (int8_t)p->light_skip_mesh;
    M->secondary_light = p->secondary_light;
    if (o->textures) {   /* RENDER-ITEMS-TEX-002: model +0xa4 (wearer skin index) and +0xa6 (field_ name) */
        M->skin_shift = o->textures->skin_shift;
        M->flag_a6 = o->textures->field;
    }
    if (o->fields) {
        const mu_draw_model_fields *f = o->fields;
        memcpy(M->color, f->color, sizeof M->color);
        M->hide_typed = f->hide_typed;
        memcpy(M->alt_color, f->alt_color, sizeof M->alt_color);
        M->alt_on_skin = f->alt_on_skin;
        M->flag_a5 = f->flag_a5;
        if (f->light_mesh_set)
            M->light_mesh = f->light_mesh;
    }

    in->globals.time = o->time;
    memcpy(in->globals.env_vector, o->env_vector, sizeof in->globals.env_vector);
    in->args.flags = o->flags;
    in->args.alpha = o->alpha;
    in->args.select = o->select;
    in->args.color_scale = o->color_scale;
    in->args.u_offset = o->u_offset;
    in->args.v_offset = o->v_offset;
    in->args.texture = o->texture;
    in->skip = o->skip_mesh;
    mu_gl_cache_scene_defaults(&in->cache);
    return 0;
}

int mu_scene_inputs_build(const mu_model *model, const mu_draw_options *o, mu_scene_inputs *in)
{
    memset(in, 0, sizeof *in);
    const mu_bmd *b = model->bmd;
    const int32_t count = b->mesh_count;
    const int32_t slots = count > 0 ? count : 1;
    in->meshes = calloc((size_t)slots, sizeof *in->meshes);
    in->texture_index = calloc((size_t)slots, sizeof *in->texture_index);
    in->texture_type = calloc((size_t)slots, sizeof *in->texture_type);
    const int32_t extras = o->textures ? o->textures->extra_count : 0;   /* NATIVE-HELPERS-002 */
    in->bitmaps = calloc((size_t)(slots + MU_TEXTURE_SPECIAL_COUNT + extras), sizeof *in->bitmaps);
    in->bitmap_index = calloc((size_t)(slots + MU_TEXTURE_SPECIAL_COUNT + extras), sizeof *in->bitmap_index);
    in->subs = calloc((size_t)slots, sizeof *in->subs);
    if (!in->meshes || !in->texture_index || !in->texture_type || !in->bitmaps || !in->bitmap_index || !in->subs) {
        mu_scene_inputs_free(in);
        return 1;
    }
    return inputs_fill(model, o, in);
}

/* Per-draw storage, rebuilt from all current model/texture inputs each call.
 * Larger models and auxiliary bitmap lists retain the allocating path. */
enum { LOCAL_MESHES = 16, LOCAL_EXTRAS = 16,
       LOCAL_BITMAPS = LOCAL_MESHES + MU_TEXTURE_SPECIAL_COUNT + LOCAL_EXTRAS };
typedef struct scene_storage {
    mu_meshdraw_mesh meshes[LOCAL_MESHES];
    int32_t texture_index[LOCAL_MESHES], texture_type[LOCAL_MESHES];
    uint8_t subs[LOCAL_MESHES][5];
    mu_bitmap bitmaps[LOCAL_BITMAPS];
    int32_t bitmap_index[LOCAL_BITMAPS];
} scene_storage;

/* Adapter: literal GL calls -> backend (effective state before each glBegin). */
typedef struct adapter {
    const mu_render_backend *backend;
    const mu_draw_options *options;
    int32_t model_count;
    mu_meshdraw_state state;
    int open;  /* inside glBegin/glEnd */
} adapter;

static void adapter_call(void *context, uint32_t op, const uint32_t w[4])
{
    adapter *a = context;
    const mu_render_backend *b = a->backend;
    if (b->gl)
        b->gl->call(b->gl->context, op, w);
    if (op >= MU_GL_OP_ENABLE && mu_meshdraw_state_apply(&a->state, op, w))
        return;
    float f[4];
    memcpy(f, w, sizeof f);
    switch (op) {
    case MU_GL_OP_BEGIN: {
        mu_meshdraw_state s = a->state;
        if (a->options->alpha_test)
            s.alpha_test = 1;
        if (a->options->cull >= 0)
            s.cull = (uint8_t)a->options->cull;
        const int32_t texture = (s.texture_name >= 1) ? (int32_t)s.texture_name - 1 : -1;
        if (b->prepare)
            b->prepare(b->context, &s, texture);
        if (b->begin)
            b->begin(b->context);
        a->open = 1;
        break;
    }
    case MU_GL_OP_END:
        a->open = 0;
        if (b->end)
            b->end(b->context);
        break;
    case MU_GL_OP_TEXCOORD2F:
        b->sink.texcoord(b->sink.context, f[0], f[1]);
        break;
    case MU_GL_OP_COLOR3F:
    case MU_GL_OP_COLOR3FV:
        b->sink.color3(b->sink.context, f);
        break;
    case MU_GL_OP_COLOR4F:
        b->sink.color4(b->sink.context, f[0], f[1], f[2], f[3]);
        break;
    case MU_GL_OP_VERTEX3FV:
        b->sink.vertex(b->sink.context, f);
        break;
    default:
        break;  /* push/pop matrix: no matrix call between them */
    }
}

/* MODEL-EDGE: meshes whose corner indices leave their arrays are drawn through
 * a client-memory view (mu_edge.h) instead of being refused by the port. */
typedef struct edge_views {
    mu_edge_view *views;   /* per mesh; triangles == NULL when the mesh needs none */
    float *colours, *table;
} edge_views;

static void edge_tables(void *context, int32_t mesh, int32_t light_count, const float *light_colors,
                        int32_t texcoord_count, const float *normal_texcoords)
{
    (void)light_count;
    (void)light_colors;
    (void)texcoord_count;
    (void)normal_texcoords;
    edge_views *e = context;
    if (e->views && e->views[mesh].triangles)
        mu_edge_zero_tables(&e->views[mesh], e->colours, e->table);
}

static void edge_free(edge_views *e, int32_t count)
{
    if (!e->views)
        return;
    for (int32_t i = 0; i < count; ++i)
        mu_edge_view_free(&e->views[i]);
    free(e->views);
    e->views = NULL;
}

/* Returns 0, or 1 when out of memory. A view that cannot be built leaves the
 * mesh as it is (the port refuses it). */
static int edge_apply(mu_scene_inputs *in, edge_views *e, uint64_t regular)
{
    const int32_t count = in->model.mesh_count;
    /* A fully proved model needs no edge storage, even for glow passes. */
    if (count > 0 && count <= 64 && regular == (UINT64_MAX >> (64 - count)))
        return 0;
    e->views = calloc((size_t)(count > 0 ? count : 1), sizeof *e->views);
    if (!e->views)
        return 1;
    for (int32_t i = 0; i < count; ++i) {
        if (i < 64 && (regular & (UINT64_C(1) << i))) continue;
        mu_meshdraw_mesh view;
        int status = mu_edge_mesh_view(&in->meshes[i], &view, &e->views[i]);
        if (status == 1)
            in->meshes[i] = view;
    }
    return 0;
}

int mu_scene_draw_model(const mu_model *model, const mu_draw_options *o, const mu_render_backend *backend,
                        mu_draw_stats *stats)
{
    mu_scene_inputs in = {0};
    scene_storage storage = {0};
    const char *baseline003 = getenv("MU_PERF_003_BASELINE");
    int extras = o->textures ? o->textures->extra_count : 0;
    int local = !(baseline003 && baseline003[0] == '1') &&
                model->bmd->mesh_count >= 0 && model->bmd->mesh_count <= LOCAL_MESHES &&
                extras >= 0 && extras <= LOCAL_EXTRAS;
    if (local) {
        in.meshes = storage.meshes;
        in.texture_index = storage.texture_index;
        in.texture_type = storage.texture_type;
        in.subs = storage.subs;
        in.bitmaps = storage.bitmaps;
        in.bitmap_index = storage.bitmap_index;
        inputs_fill(model, o, &in);
    } else if (mu_scene_inputs_build(model, o, &in)) {
        return 1;
    }
    /* Draws are sequential; these tables need no heap allocation per glow
     * pass. Each routine writes exactly the entries it reads, as before. */
    float local_colours[3 * MU_MESHDRAW_MAX_ENTRIES];
    float local_table[2 * (MU_MESHDRAW_MAX_ENTRIES + 1)];
    const char *baseline = getenv("MU_PERF_002_BASELINE");
    int old_alloc = baseline && atoi(baseline);
    float *colours = old_alloc ? malloc(sizeof local_colours) : local_colours;
    float *table = old_alloc ? malloc(sizeof local_table) : local_table;
    if (!colours || !table) {
        if (old_alloc) { free(colours); free(table); }
        if (!local) mu_scene_inputs_free(&in);
        return 1;
    }
    edge_views edge = {NULL, colours, table};
    uint64_t regular = 0;
    const char *reference004 = getenv("MU_PERF_004_BASELINE");
    if (!(reference004 && reference004[0] == '1'))
        for (int32_t i = 0; i < in.model.mesh_count && i < 64; ++i)
            if (mu_perf_mesh_regular(model->draw_topology, i, &in.meshes[i]))
                regular |= UINT64_C(1) << i;
    if (edge_apply(&in, &edge, regular)) {
        if (old_alloc) { free(colours); free(table); }
        if (!local) mu_scene_inputs_free(&in);
        return 1;
    }
    adapter a = {backend, o, in.model.mesh_count, {0}, 0};
    mu_meshdraw_state_defaults(&a.state);
    mu_gl_sink sink = {&a, adapter_call};
    mu_meshdraw_scratch scratch = {colours, table, &edge, edge_tables};
    mu_meshdraw_env env = {&in.model, &in.globals, &in.cache, &sink, mu_scene_bitmap, &in, &scratch,
                           !old_alloc && !backend->gl ? &backend->sink : NULL};
    mu_meshdraw_counts counts = {0, 0, 0, 0, 0};
    if (o->mesh_plus_one > 0) {
        long corners = 0;
        int32_t mesh = o->mesh_plus_one - 1;
        int checked = mesh < 64 && (regular & (UINT64_C(1) << mesh)) != 0;
        int r = mesh < in.model.mesh_count
                    ? (checked ? mu_meshdraw_mesh_draw_validated(&env, mesh, &in.args, &corners)
                               : mu_meshdraw_mesh_draw(&env, mesh, &in.args, &corners)) : MU_MESHDRAW_RETURNED;
        counts.corners += corners;
        if (r == MU_MESHDRAW_DRAWN) counts.drawn++;
        else if (r == MU_MESHDRAW_RETURNED) counts.returned++;
        else if (r == MU_MESHDRAW_REFUSED) counts.refused++;
        else counts.faulted++;
    } else {
        mu_meshdraw_body_validated(&env, &in.args, in.skip, &counts, regular);
    }
    /* A fault stops where the client would crash; close the open primitive
     * for the backend (the client issues no glEnd). */
    if (a.open && backend->end)
        backend->end(backend->context);
    if (stats) {
        stats->meshes += counts.drawn + counts.returned + counts.refused + counts.faulted;
        stats->corners += counts.corners;
        stats->refused += counts.refused;
        stats->faulted += counts.faulted;
    }
    edge_free(&edge, in.model.mesh_count);
    if (old_alloc) { free(colours); free(table); }
    if (!local) mu_scene_inputs_free(&in);
    return 0;
}
