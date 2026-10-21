#ifndef MU_ENV_NATIVE_H
#define MU_ENV_NATIVE_H

#include <stddef.h>
#include <stdint.h>

#include "mu_bmd.h"
#include "mu_model.h"
#include "mu_raster.h"
#include "mu_scene.h"
#include "mu_terrain.h"
#include "mu_textures.h"
#include "../../reconstructed/environment/env.h"

/* The client's ambient world life and weather in the native session
 * (NATIVE-ENV-001, docs/research/client-environment.md).
 *
 * Runs reconstructed/environment (MoveLeaves, MoveBoids, MoveFishs and the
 * three render routines, compared with the client in Unicorn) over the
 * session's terrain and hero, and draws what the render routines ask for:
 *
 *   - the ambient models (Bird01, Bat01, Butterfly01, Fish01, Rat01, the Atlans
 *     Fish02..09, Crow01) through mu_model and the mesh-draw port, posed from
 *     each object's animation state, which the host advances with the
 *     reconstructed animation tick (the client's model getter + 0x012b4dd3);
 *   - the weather particles as RenderPlane3D quads or RenderSprite billboards
 *     with the world's leaf/rain bitmaps (the 0x01829e21 loading rule: the
 *     .jpg load replaces the .tga one, so worlds without leaf01.OZJ have no
 *     leaf bitmap and RenderLeaves skips every particle).
 *
 * The body colour is RenderObject's body light 0x017ec3d8 (NATIVE-FIDELITY-001,
 * verified, mu_env_body_light): lighting flag = object +5, colour = the frame
 * light at the position + the object light, light terms 0.4/0.8/0.2.
 * Viewer choices (not client readings): RenderObject 0x016d4fe4's body
 * pass is drawn with the default render flags; billboards are drawn in the world pass (the client draws them
 * in its BeginSprite pass). With a particle module attached (`particles`,
 * NATIVE-PARTICLE-001) the blob shadows (RenderBodyShadow 0x012bc07a), the
 * butterfly and crow glow sprites (CreateSprite, crow eyes at bone 1 through
 * TransformPosition) and the rain splash particles (CreateParticle) are
 * created and drawn; without one they are counted. */

struct mu_world_particles;

enum { MU_WORLD_ENV_MODELS = 12, MU_WORLD_ENV_BITMAPS = 5 };

typedef struct mu_world_env_model {
    int32_t type;
    int loaded;
    char path[1024];
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
} mu_world_env_model;

typedef struct mu_world_env_stats {
    uint32_t steps, leaf_steps;
    uint32_t sounds, sound_bird, sound_bat, sound_rat, sound_other;
    uint32_t particles, effects, kills, inits;
    uint32_t live_boids, live_fishs, live_leaves;          /* now */
    uint32_t max_boids, max_fishs, max_leaves;             /* over the session */
    uint32_t drawn_objects, drawn_leaves, skipped_leaves;  /* last draw */
    uint32_t shadows, sprites;                             /* last draw, not drawn */
} mu_world_env_stats;

typedef struct mu_world_env {
    mu_env env;
    int32_t world;
    mu_env_world_info info;
    const mu_world *map;
    int32_t model_count;
    mu_world_env_model models[MU_WORLD_ENV_MODELS];
    mu_textures bitmaps;                 /* slots 0..4: 0x771f, 0x7720, 0x7721, 0x771c, 0x771d */
    int32_t bitmap_present[MU_WORLD_ENV_BITMAPS];
    int tga_leaves;                      /* viewer option: load leaf01.OZT when leaf01.OZJ is missing */
    void (*sound)(void *context, int32_t id);
    void *sound_context;
    mu_env_inputs inputs;
    float camera[3][4];                  /* CameraMatrix of the last draw */
    int32_t blend;                       /* RenderLeaves state: 0 alpha test, 1 additive */
    int32_t slot;                        /* bound bitmap slot */
    float shadow_rgba[4];                /* glColor4f before RenderBodyShadow */
    struct mu_world_particles *particles; /* NATIVE-PARTICLE-001 (NULL: counted only) */
    mu_world_env_stats stats;
} mu_world_env;

typedef struct mu_world_env_hero {
    float position[3];        /* hero +0x33ac */
    int32_t tile[2];          /* hero +0x180 / +0x184 */
    uint16_t action;          /* hero object +0x2a */
    uint8_t safe_zone;        /* hero +4 */
    int32_t hero_tile;        /* HeroTile 0x0b437c10 (the MoveLeaves guard) */
} mu_world_env_hero;

/* Loads the world's ambient models and weather bitmaps (no_assets: none,
 * for headless logic runs) and seeds the module's rand(). Returns 0, or 1
 * with a message. */
int mu_world_env_open(mu_world_env *e, const char *game_root, const mu_world *map, int32_t world, uint32_t seed,
                      int no_assets, int tga_leaves, char *error, size_t error_size);
void mu_world_env_close(mu_world_env *e);

/* One 40 ms logic step in the tick's order: MoveLeaves (when the tick's guard
 * calls it), MoveBoids, MoveFishs. camera is CameraPosition, world_time the
 * client time 0x06fce370 in ms. */
void mu_world_env_step(mu_world_env *e, const mu_world_env_hero *hero, const float camera[3], float world_time);

/* Draw target: a backend for model slot (0..model_count-1) or, for slot -1,
 * for the weather bitmaps. Returns 0 when it filled `out`. */
typedef struct mu_world_env_target {
    void *context;
    int (*backend)(void *context, const mu_world_env *e, int32_t slot, mu_render_backend *out);
} mu_world_env_target;

/* RenderBoids(0), RenderFishs, RenderLeaves, RenderBoids(1) with the camera
 * of the GL modelview (column-major, as the frame leaves it). frustum gives
 * TestFrustrum2D's polygon (NULL: every object counts as visible). Returns
 * the number of models and particles drawn. */
long mu_world_env_draw(mu_world_env *e, const float modelview[16], const mu_terrain_frustum *frustum,
                       const mu_world_env_target *target);
long mu_world_env_draw_raster(mu_world_env *e, mu_raster *raster, const float modelview[16],
                              const mu_terrain_frustum *frustum);

/* The clear colour of the render scene as RGBA8. */
void mu_world_env_clear(const mu_world_env *e, uint8_t rgba[4]);

#endif
