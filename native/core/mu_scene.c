/* Per-model draw driver over the mesh-draw port. See mu_scene.h. */
#include "mu_scene.h"

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

int mu_scene_inputs_build(const mu_model *model, const mu_draw_options *o, mu_scene_inputs *in)
{
    memset(in, 0, sizeof *in);
    const mu_bmd *b = model->bmd;
    const mu_model_params *p = &model->params;
    const int32_t count = b->mesh_count;
    const int32_t slots = count > 0 ? count : 1;
    in->meshes = calloc((size_t)slots, sizeof *in->meshes);
    in->texture_index = calloc((size_t)slots, sizeof *in->texture_index);
    in->texture_type = calloc((size_t)slots, sizeof *in->texture_type);
    in->bitmaps = calloc((size_t)(slots + MU_TEXTURE_SPECIAL_COUNT), sizeof *in->bitmaps);
    in->bitmap_index = calloc((size_t)(slots + MU_TEXTURE_SPECIAL_COUNT), sizeof *in->bitmap_index);
    in->subs = calloc((size_t)slots, sizeof *in->subs);
    if (!in->meshes || !in->texture_index || !in->texture_type || !in->bitmaps || !in->bitmap_index || !in->subs) {
        mu_scene_inputs_free(in);
        return 1;
    }
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
        in->texture_index[i] = MU_SCENE_TEXTURE_BASE + i;
        in->texture_type[i] = 0;
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
    if (mu_meshdraw_state_apply(&a->state, op, w))
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

int mu_scene_draw_model(const mu_model *model, const mu_draw_options *o, const mu_render_backend *backend,
                        mu_draw_stats *stats)
{
    mu_scene_inputs in;
    if (mu_scene_inputs_build(model, o, &in))
        return 1;
    float *colours = malloc(sizeof(float) * 3 * MU_MESHDRAW_MAX_ENTRIES);
    float *table = malloc(sizeof(float) * 2 * (MU_MESHDRAW_MAX_ENTRIES + 1));
    if (!colours || !table) {
        free(colours);
        free(table);
        mu_scene_inputs_free(&in);
        return 1;
    }
    adapter a = {backend, o, in.model.mesh_count, {0}, 0};
    mu_meshdraw_state_defaults(&a.state);
    mu_gl_sink sink = {&a, adapter_call};
    mu_meshdraw_scratch scratch = {colours, table, NULL, NULL};
    mu_meshdraw_env env = {&in.model, &in.globals, &in.cache, &sink, mu_scene_bitmap, &in, &scratch};
    mu_meshdraw_counts counts = {0, 0, 0, 0, 0};
    mu_meshdraw_body(&env, &in.args, in.skip, &counts);
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
    free(colours);
    free(table);
    mu_scene_inputs_free(&in);
    return 0;
}
