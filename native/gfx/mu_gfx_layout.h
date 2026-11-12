/* APP-POLISH-009: bounded native-window adaptation after the original movie layout.
 * Original placement remains in MUComponent.SetWindowSize. This fit is needed when
 * the client's fixed 83/90/95 percent scales exceed a resizable native viewport. */
#ifndef MU_GFX_LAYOUT_H
#define MU_GFX_LAYOUT_H
#include <math.h>

typedef struct mu_gfx_fit {
    double x, y, scale;
} mu_gfx_fit;

static inline mu_gfx_fit mu_gfx_fit_window(double x, double y, double w, double h,
                                           double available_w, double available_h)
{
    mu_gfx_fit out = {x, y, 1.0};
    if (!(w > 0 && h > 0 && available_w > 0 && available_h > 0))
        return out;
    out.scale = fmin(1.0, fmin(available_w / w, available_h / h));
    out.x = fmax(0.0, fmin(x, available_w - w * out.scale));
    out.y = fmax(0.0, fmin(y, available_h - h * out.scale));
    return out;
}

/* Only called when the original HUD is wider than the viewport. Width is
 * already scaled; the background height is local to Frame.Main. */
static inline mu_gfx_fit mu_gfx_fit_bar(double bar_width, double background_height, double original_scale,
                                       double viewport_width, double viewport_height)
{
    mu_gfx_fit out = {0, 0, original_scale * viewport_width / bar_width};
    out.y = floor(viewport_height - background_height * out.scale / 100.0);
    return out;
}
#endif
