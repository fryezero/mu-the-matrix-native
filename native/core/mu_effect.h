#ifndef MU_EFFECT_H
#define MU_EFFECT_H

#include <stdint.h>

#include "mu_image.h"
#include "mu_raster.h"
#include "../../reconstructed/effects/effects.h"

/* Native effect instance (NATIVE-FX-001): a Data/Effect .ein particle system or
 * billboard run by the reconstructed effect module (reconstructed/effects),
 * with its texture and a software-raster draw that applies the client's draw
 * state (docs/research/client-effects.md):
 *   - blending: none, alpha (SRC_ALPHA, ONE_MINUS_SRC_ALPHA), particle additive
 *     (ONE, ONE), billboard additive (SRC_COLOR, ONE), multiply (DST_COLOR, ZERO);
 *   - depth test kept, depth writes off, alpha test off (EffectManager render
 *     0x00a7a30e);
 *   - texture GL_MODULATE, GL_LINEAR, GL_REPEAT, no mipmaps (0x00a90987);
 *   - GL_QUADS split into triangles (0,1,2) and (0,2,3).
 * Culling for particle systems is left off: the particle draw does not set it
 * and the state left by earlier passes was not recovered. */

typedef struct mu_effect {
    mu_fx_effect fx;
    mu_fx_rng rng;
    mu_image texture;
    int texture_loaded;
    char texture_path[4096];
    mu_fx_vertex *vertices;
    uint32_t vertex_capacity;
    uint32_t frame;
} mu_effect;

enum { MU_EFFECT_OK = 0, MU_EFFECT_ERROR = 1 };

/* Loads an .ein file. `game_root` (may be NULL) is the installation root the
 * "Texture" path is relative to; when NULL it is derived from a path of the
 * form ROOT/Data/Effect/name.ein. A missing texture is reported in
 * texture_loaded and the effect still runs (the client then disables
 * GL_TEXTURE_2D). */
int mu_effect_load_file(mu_effect *effect, const char *path, const char *game_root, uint32_t seed, char *error,
                        unsigned long error_size);
int mu_effect_load_text(mu_effect *effect, const char *text, unsigned long length, uint32_t seed, char *error,
                        unsigned long error_size);
void mu_effect_free(mu_effect *effect);

/* One rendered frame of the client's main render: effect update with the
 * per-frame step (the client passes the constant 0x01cf103c = 0.1). The
 * terrain collider sees flat ground at z = 0 (no world is loaded). */
void mu_effect_update(mu_effect *effect, float dt);

/* Camera for the effect fill from an eye position and a target, Z up. */
void mu_effect_camera(mu_fx_camera *camera, const float eye[3], const float target[3]);

/* Fills the effect's quads and rasterizes them. Returns the vertex count. */
uint32_t mu_effect_draw(mu_effect *effect, const mu_fx_camera *camera, mu_raster *raster);

/* Case-insensitive resolution of a client path ("Data\\Effect\\x.OZJ") under
 * root. Returns 1 and fills out when the file exists. */
int mu_effect_resolve_path(const char *root, const char *client_path, char *out, unsigned long out_size);

#endif
