#include "../charsel_rt_internal.h"

static void soft_bind(mu_raster *raster, const mu_object_model *m)
{
    raster->textures = m ? m->textures.slots : NULL;
    raster->texture_count = m ? m->textures.count : 0;
    raster->texture_filter = m ? m->textures.filter : NULL;
    raster->texture_wrap = m ? m->textures.wrap : NULL;
}

static void draw_soft(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    mu_raster *raster = d->raster;
    if (s->has_objects) {   /* RenderObjects 0x016d5020 with CGMCharacterScene_Ex (NATIVE-CHARSEL-002) */
        mu_objects *o = s->objects;
        raster->linear = 1;
        mu_objects_visibility(o, &d->frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.draw_count; ++k) {
            mu_draw_options options;
            mu_object_model *m = mu_objects_prepare(o, k, s->map, MU_CHARSEL_SCENE, &options);
            if (!m)
                continue;
            soft_bind(raster, m);
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &options, &d->backend, &ds))
                ++s->objects_drawn;
        }
        soft_bind(raster, NULL);
        a->objects_drawn = s->objects_drawn;
    } else if (a->has_objects) {
        a->objects_drawn = mu_objects_draw_raster(&a->objects, s->map, raster, 0, 0, 255, 255);
    }
}

#ifndef MU_CHARSEL_NO_GL
static void draw_gl(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    if (s->has_objects) {   /* RenderObjects 0x016d5020 with CGMCharacterScene_Ex (NATIVE-CHARSEL-002) */
        mu_objects *o = s->objects;
        if (a->terrain.batch)
            mu_gl_batch_session_begin(a->terrain.batch);
        mu_objects_visibility(o, &d->frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.draw_count; ++k) {
            mu_draw_options options;
            mu_object_model *m = mu_objects_prepare(o, k, s->map, MU_CHARSEL_SCENE, &options);
            if (!m)
                continue;
            mu_gl_backend_bind(a->terrain.batch ? &a->object_render.batched[m->type] : &a->object_render.models[m->type], &d->backend);
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &options, &d->backend, &ds))
                ++s->objects_drawn;
        }
        if (a->terrain.batch)
            mu_gl_batch_session_end(a->terrain.batch);
        a->objects_drawn = s->objects_drawn;
    } else if (a->has_objects) {   /* static placement (the lifecycle did not start) */
        mu_draw_options options;
        mu_draw_default_options(&options);
        for (int32_t i = 0; i < a->objects.count; ++i) {
            mu_object_model *m = mu_objects_place(&a->objects, i, s->map);
            if (!m)
                continue;
            mu_gl_backend_bind(&a->object_render.models[m->type], &d->backend);
            options.textures = &m->textures;
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &options, &d->backend, &ds))
                ++a->objects_drawn;
        }
    }
}

static void gl_setup(mu_charsel_rt *a)
{
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t) {
        memset(&a->object_render.models[t], 0, sizeof a->object_render.models[t]);
        if (a->has_objects && a->objects.models[t] && a->objects.models[t]->loaded)
            mu_gl_upload(&a->object_render.models[t], &a->objects.models[t]->textures, 0);
    }
    memset(a->object_render.batched, 0, sizeof a->object_render.batched);
    for (int32_t t = 0; a->terrain.batch && t < MU_OBJECT_TYPES; ++t) {   /* the first objects pass only */
        a->object_render.batched[t] = a->object_render.models[t];
        a->object_render.batched[t].batch = a->terrain.batch;
    }
}

static void gl_teardown(mu_charsel_rt *a)
{
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t)
        if (a->object_render.models[t].textures)
            mu_gl_release(&a->object_render.models[t]);
}
#endif

const mu_charsel_part_ops mu_charsel_objects_part = {
    .draw_soft = draw_soft,
#ifndef MU_CHARSEL_NO_GL
    .draw_gl = draw_gl,
    .gl_setup = gl_setup,
    .gl_teardown = gl_teardown,
#endif
};
