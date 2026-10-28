#include "../charsel_rt_internal.h"

static void draw_soft(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    mu_raster *raster = d->raster;
    raster->linear = d->linear;
    for (int32_t i = 0; i < s->decal_count; ++i) {
        const mu_charsel_decal *d = &s->decals[i];
        /* EnableAlphaBlend 0x0184aa2b, then RenderTerrainAlphaBitmap(0x8036, x, y, size, size, light,
         * rotation, 1, 5, 1, 0) */
        mu_world_decal_raster(s->map, raster, 0x8036, d->x, d->y, d->size, d->size, d->light, d->rotation, 1.0f, 5.0f,
                              1, 0, MU_TERRAIN_STATE_ADDITIVE);
    }
}

#ifndef MU_CHARSEL_NO_GL
static void draw_gl(mu_charsel_rt *a, mu_charsel_draw *d)
{
    (void)d;
    mu_charsel_session *s = a->s;
    mu_terrain_scene scene;
    mu_world_scene(s->map, &scene);
    mu_terrain_sink sink;
    charsel_terrain_sink(a, &sink);
    for (int32_t i = 0; i < s->decal_count; ++i) {
        const mu_charsel_decal *d = &s->decals[i];
        charsel_gl_state(a, MU_TERRAIN_STATE_ADDITIVE, 1);
        mu_terrain_decal(&scene, 0x8036, d->x, d->y, d->size, d->size, d->light, d->rotation, 1.0f, 5.0f, 1, 0, &sink);
    }
}
#endif

const mu_charsel_part_ops mu_charsel_decals_part = {
    .draw_soft = draw_soft,
#ifndef MU_CHARSEL_NO_GL
    .draw_gl = draw_gl,
#endif
};
