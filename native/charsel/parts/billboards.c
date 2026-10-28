#include "../charsel_rt_internal.h"

static void draw_soft(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    mu_raster *raster = d->raster;
    const mu_client_view *v = &s->frame.view;
    if (s->has_particles) {   /* RenderJoints(0), RenderSprites(0), RenderParticles(0) */
        s->frame_sprites = (int32_t)(s->particles.stats.sprites_created - d->sprites);
        s->billboards = mu_world_particles_draw_raster(&s->particles, raster, v->modelview);
    }
}

#ifndef MU_CHARSEL_NO_GL
static int particle_gl_backend(void *context, const mu_world_particles *p, mu_render_backend *out)
{
    mu_charsel_rt *a = context;
    (void)p;
    mu_gl_backend_bind(&a->effects.bitmaps, out);
    return 0;
}
static void draw_gl(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    const mu_client_view *v = &s->frame.view;
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    if (s->has_particles) {   /* RenderJoints(0), RenderSprites(0), RenderParticles(0) */
        s->frame_sprites = (int32_t)(s->particles.stats.sprites_created - d->sprites);
        mu_world_particles_target target = {a, particle_gl_backend};
        s->billboards = mu_world_particles_draw(&s->particles, v->modelview, &target);
        glBindTexture(GL_TEXTURE_2D, 0);
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
        glDisable(GL_ALPHA_TEST);
    }
}
#endif

const mu_charsel_part_ops mu_charsel_billboards_part = {
    .draw_soft = draw_soft,
#ifndef MU_CHARSEL_NO_GL
    .draw_gl = draw_gl,
#endif
};
