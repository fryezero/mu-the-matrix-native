#ifndef MU_CHARSEL_RT_H
#define MU_CHARSEL_RT_H

/* CHARSEL-RT-001: scene 5 shared by the shell and the standalone tools.
 * The caller owns the GL context and calls gl_teardown before closing it.
 * Options strings and list must remain valid until close. */
#include <stddef.h>
#include <stdint.h>
#include "../core/mu_charsel.h"
#include "../core/mu_raster.h"

typedef struct mu_charsel_rt mu_charsel_rt;
typedef struct mu_charsel_rt_options {
    const char *root, *list_path, *objects_dir;
    const mu_charsel_list *list; /* overrides list_path; NULL uses file or built-in list */
    int32_t width, height, slot;
    int marker_given;
    float marker[3];
    int no_ui; /* the shell owns its 2D layer; standalone headless tools may open one */
    const char *font, *tip;
} mu_charsel_rt_options;

void mu_charsel_rt_default_options(mu_charsel_rt_options *options);
mu_charsel_rt *mu_charsel_rt_open(const mu_charsel_rt_options *options, char *error, size_t error_size);
void mu_charsel_rt_close(mu_charsel_rt *rt);
mu_charsel_session *mu_charsel_rt_session(mu_charsel_rt *rt);
void mu_charsel_rt_select_next(mu_charsel_rt *rt, int step);
void mu_charsel_rt_resize(mu_charsel_rt *rt, int32_t width, int32_t height);
long mu_charsel_rt_draw_soft(mu_charsel_rt *rt, mu_raster *raster);
#ifndef MU_CHARSEL_NO_GL
int mu_charsel_rt_gl_setup(mu_charsel_rt *rt);
void mu_charsel_rt_gl_teardown(mu_charsel_rt *rt);
long mu_charsel_rt_draw_gl(mu_charsel_rt *rt, int32_t width, int32_t height);
#endif
#endif
