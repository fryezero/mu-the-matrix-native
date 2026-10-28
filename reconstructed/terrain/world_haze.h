#ifndef MU_WORLD_HAZE_H
#define MU_WORLD_HAZE_H
#include "terrain.h"
/* RENDER-WORLDS-F: RenderBitmapUV and the Tarkan/Raklion screen passes.
 * Coordinates use the client's bottom-origin orthographic pixel space. The
 * caller establishes the full-window viewport and disables depth testing.
 * Other worlds emit no calls. Time conversion follows CVTTSS2SI, including
 * negative remainders. No Fog.OZJ or terrain-light adjustment is involved. */
void mu_world_haze_quad(int32_t texture, float x, float y, float width, float height,
                        float u, float v, float du, float dv, uint32_t screen_width,
                        uint32_t screen_height, const mu_terrain_sink *sink);
void mu_world_haze_draw(int32_t world, float time, uint32_t width, uint32_t height,
                        const mu_terrain_sink *sink);
/* Relative client texture names, slot 0 = 0x7f21, slot 1 = 0x7f22. */
const char *mu_world_haze_texture(int32_t world, int slot);
#endif
