#ifndef MU_CHARSEL_PART_H
#define MU_CHARSEL_PART_H
#include "mu_charsel_rt.h"
#include "../core/mu_terrain.h"

typedef struct mu_charsel_draw {
    mu_raster *raster;
    mu_render_backend backend;
    mu_terrain_frustum frustum;
    int linear;
    uint64_t sprites;
    long faces;
} mu_charsel_draw;

typedef struct mu_charsel_part_ops {
    int (*open)(mu_charsel_rt *rt);
    void (*close)(mu_charsel_rt *rt);
    void (*draw_soft)(mu_charsel_rt *rt, mu_charsel_draw *draw);
#ifndef MU_CHARSEL_NO_GL
    void (*gl_setup)(mu_charsel_rt *rt);
    void (*gl_teardown)(mu_charsel_rt *rt);
    void (*draw_gl)(mu_charsel_rt *rt, mu_charsel_draw *draw);
#endif
} mu_charsel_part_ops;
#endif
