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
    if (s->has_objects) {   /* RenderObjects_AfterCharacter 0x016d6949 */
        mu_objects *o = s->objects;
        mu_objects_after_visibility(o, &d->frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.after_count; ++k) {
            mu_object_mesh meshes[MU_CHARSEL_AFTER_MESHES];
            int32_t count = 0;
            mu_object_model *m = mu_objects_prepare_after(o, k, s->map, MU_CHARSEL_SCENE, meshes,
                                                          MU_CHARSEL_AFTER_MESHES, &count);
            if (!m)
                continue;
            soft_bind(raster, m);
            for (int32_t j = 0; j < count; ++j) {
                meshes[j].options.fields = &meshes[j].fields;
                mu_draw_stats ds = {0, 0, 0, 0};
                if (!mu_scene_draw_model(&m->model, &meshes[j].options, &d->backend, &ds))
                    ++s->after_meshes;
            }
        }
        soft_bind(raster, NULL);
    }
}

#ifndef MU_CHARSEL_NO_GL
static void draw_gl(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    if (s->has_objects) {   /* RenderObjects_AfterCharacter 0x016d6949 */
        mu_objects *o = s->objects;
        mu_objects_after_visibility(o, &d->frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.after_count; ++k) {
            mu_object_mesh meshes[MU_CHARSEL_AFTER_MESHES];
            int32_t count = 0;
            mu_object_model *m = mu_objects_prepare_after(o, k, s->map, MU_CHARSEL_SCENE, meshes,
                                                          MU_CHARSEL_AFTER_MESHES, &count);
            if (!m)
                continue;
            mu_gl_backend_bind(&a->object_render.models[m->type], &d->backend);
            for (int32_t j = 0; j < count; ++j) {
                meshes[j].options.fields = &meshes[j].fields;
                mu_draw_stats ds = {0, 0, 0, 0};
                if (!mu_scene_draw_model(&m->model, &meshes[j].options, &d->backend, &ds))
                    ++s->after_meshes;
            }
        }
    }
}
#endif

const mu_charsel_part_ops mu_charsel_objects_after_part = {
    .draw_soft = draw_soft,
#ifndef MU_CHARSEL_NO_GL
    .draw_gl = draw_gl,
#endif
};
