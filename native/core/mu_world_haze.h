#ifndef MU_NATIVE_WORLD_HAZE_H
#define MU_NATIVE_WORLD_HAZE_H
#include "mu_raster.h"
#include "../../reconstructed/terrain/world_haze.h"
typedef struct mu_world_haze {
    int32_t world;
    mu_image images[2];
} mu_world_haze;
/* Native resource boundary: missing textures skip their draw. Failed image
 * loads are reported on stderr. The client assumes loaded resources. */
void mu_world_haze_open(mu_world_haze *haze, const char *root, int32_t world);
void mu_world_haze_close(mu_world_haze *haze);
void mu_world_haze_draw_raster(const mu_world_haze *haze, float time, mu_raster *raster);
#endif
