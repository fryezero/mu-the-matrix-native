#include "../charsel_rt_internal.h"

static void draw_soft(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    mu_raster *raster = d->raster;
    if (s->has_particles)   /* RenderEffects 0x015181fa: the effect models */
        mu_world_particles_draw_models_raster(&s->particles, raster);
}

#ifndef MU_CHARSEL_NO_GL
static void particle_model_gl(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                              const mu_draw_options *draw_options)
{
    mu_charsel_rt *a = context;
    mu_gl_backend *gl = &a->effects.models[slot];
    if (!gl->textures)
        mu_gl_upload(gl, textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(model, draw_options, &backend, &ds);
}
static void draw_gl(mu_charsel_rt *a, mu_charsel_draw *d)
{
    (void)d;
    mu_charsel_session *s = a->s;
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    if (s->has_particles)   /* RenderEffects 0x015181fa: the effect models */
        mu_world_particles_draw_models(&s->particles, particle_model_gl, a);
}

static void gl_setup(mu_charsel_rt *a)
{
    memset(&a->effects.bitmaps, 0, sizeof a->effects.bitmaps);
    memset(a->effects.models, 0, sizeof a->effects.models);
    if (a->s->has_particles)   /* NATIVE-CHARSEL-002 */
        mu_gl_upload(&a->effects.bitmaps, &a->s->particles.bitmaps, 0);
}

static void gl_teardown(mu_charsel_rt *a)
{
    if (a->effects.bitmaps.textures)
        mu_gl_release(&a->effects.bitmaps);
    for (int i = 0; i < MU_WORLD_FX_MODELS; ++i)
        if (a->effects.models[i].textures)
            mu_gl_release(&a->effects.models[i]);
}
#endif

const mu_charsel_part_ops mu_charsel_effects_part = {
    .draw_soft = draw_soft,
#ifndef MU_CHARSEL_NO_GL
    .draw_gl = draw_gl,
    .gl_setup = gl_setup,
    .gl_teardown = gl_teardown,
#endif
};
