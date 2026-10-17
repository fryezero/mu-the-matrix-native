/* Per-mesh draw driver. See mu_scene.h. */
#include "mu_scene.h"

#include <stdlib.h>
#include <string.h>

void mu_draw_default_options(mu_draw_options *o)
{
    memset(o, 0, sizeof *o);
    o->mode = 2;
    o->alpha = 1.0f;
    o->uv_offset_mesh = -1;
    o->cull = -1;
}

int mu_scene_draw_model(const mu_model *model, const mu_draw_options *options, const mu_render_backend *backend,
                        mu_draw_stats *stats)
{
    const mu_bmd *b = model->bmd;
    const mu_model_params *p = &model->params;
    int32_t most = 1;
    for (int32_t i = 0; i < b->mesh_count; ++i)
        if (b->meshes[i].normal_count > most)
            most = b->meshes[i].normal_count;
    float *colours = malloc(sizeof(float) * 3 * (size_t)most);
    float *table = malloc(sizeof(float) * 2 * (size_t)most);
    if (!colours || !table) {
        free(colours);
        free(table);
        return 1;
    }
    const float *colour = mu_model_color(model);
    for (int32_t i = 0; i < b->mesh_count; ++i) {
        const mu_bmd_mesh *mesh = &b->meshes[i];
        mu_meshdraw_mesh view;
        memset(&view, 0, sizeof view);
        view.triangles = mu_model_triangles(model, i);
        view.triangle_count = mesh->polygon_count;
        view.texcoords = mu_model_texcoords(model, i);
        view.texcoord_count = mesh->uv_count;
        view.vertices = mu_model_vertices(model, i);
        view.vertex_count = mesh->vertex_count;
        view.normal_count = mesh->normal_count;
        view.light_colors = colours;
        view.normal_texcoords = table;
        view.model_color = colour;
        view.origin = mu_model_origin(model);

        mu_meshdraw_params params;
        memset(&params, 0, sizeof params);
        params.mode = options->mode;
        params.flags = options->flags;
        params.alpha = options->alpha;
        params.u_offset = options->u_offset;
        params.v_offset = options->v_offset;
        params.apply_uv_offset = i == options->uv_offset_mesh;
        params.light_colors = p->lighting && i != p->light_skip_mesh;

        /* 1. pre-loop colour */
        mu_meshdraw_pre_color(p->lighting, colour, options->alpha, &backend->sink);
        /* 2. per-normal colour pass */
        if (params.light_colors)
            mu_meshdraw_light_colors(mu_model_lights(model, i), mu_model_secondary_lights(model, i),
                                     mesh->normal_count, colour, p->secondary_light, colours);
        if (options->mode == 4 || options->mode == 0x1000 || options->mode == 0x80000 || options->mode == 0x100000) {
            /* Substitute for the unrecovered 0x072acfd8 writer (viewer placeholder). */
            const float *normals = mu_model_normals(model, i);
            for (int32_t n = 0; n < mesh->normal_count; ++n) {
                table[2 * n] = 0.5f + 0.5f * normals[3 * n];
                table[2 * n + 1] = 0.5f + 0.5f * normals[3 * n + 1];
            }
        }
        /* 3. state and texture */
        mu_meshdraw_state state;
        mu_meshdraw_state_for(options->flags, options->alpha, &state);
        if (options->alpha_test)
            state.alpha_test = 1;
        if (options->cull >= 0)
            state.cull = (uint8_t)options->cull;
        backend->prepare(backend->context, &state, i);
        /* 4-6. one GL_TRIANGLES block with the ported corner loop */
        backend->begin(backend->context);
        long corners = 0;
        int status = mu_meshdraw_corners(&view, &params, &backend->sink, &corners);
        backend->end(backend->context);
        if (stats) {
            stats->meshes++;
            stats->corners += corners;
            if (status != MU_MESHDRAW_OK)
                stats->refused++;
        }
    }
    free(colours);
    free(table);
    return 0;
}
