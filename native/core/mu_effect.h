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
    mu_image texture;          /* root node (node 0) */
    int texture_loaded;
    char texture_path[4096];
    mu_fx_vertex *vertices;    /* sized for the largest node */
    uint32_t vertex_capacity;
    uint32_t frame;
    /* NATIVE-FX-002: the whole tree ("Children"), nodes in pre-order. */
    uint32_t node_count;
    mu_image *node_textures;   /* node_textures[i] for node i >= 1 */
    uint8_t *node_texture_loaded;
    const mu_fx_terrain *terrain; /* collider ground; NULL = flat ground z = 0 */
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

/* One rendered frame of the client's main render: node update of the whole
 * tree (0x00a75708) with the per-frame step (the client passes the constant
 * 0x01cf103c = 0.1). The terrain collider sees effect->terrain, or flat ground
 * at z = 0 when it is NULL. */
void mu_effect_update(mu_effect *effect, float dt);

/* Camera for the effect fill from an eye position and a target, Z up. */
void mu_effect_camera(mu_fx_camera *camera, const float eye[3], const float target[3]);

/* Fills the quads of every node and rasterizes them (raster may be NULL: fill
 * only, which still marks the nodes drawn). Returns the vertex count. */
uint32_t mu_effect_draw(mu_effect *effect, const mu_fx_camera *camera, mu_raster *raster);

/* One node (pre-order index): fill into effect->vertices, rasterize when
 * raster is given. Returns the node's vertex count. */
uint32_t mu_effect_draw_node(mu_effect *effect, uint32_t node, const mu_fx_camera *camera, mu_raster *raster);

/* Texture of node i (NULL when not loaded). */
const mu_image *mu_effect_node_texture(const mu_effect *effect, uint32_t node);

/* Rasterizes filled effect quads with the client's effect draw state (blend
 * factors from the draw state, depth test on, depth writes off, no culling,
 * no alpha test; `matrix` multiplies the view for SpaceIsLocal particles). */
void mu_effect_raster_quads(mu_raster *raster, const mu_fx_vertex *vertices, uint32_t count,
                            const mu_fx_draw_state *state, const mu_image *texture, const float *matrix);

/* Case-insensitive resolution of a client path ("Data\\Effect\\x.OZJ") under
 * root. Returns 1 and fills out when the file exists. */
int mu_effect_resolve_path(const char *root, const char *client_path, char *out, unsigned long out_size);

#endif
