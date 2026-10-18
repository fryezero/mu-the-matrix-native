#ifndef MU_PARTICLES_NATIVE_H
#define MU_PARTICLES_NATIVE_H

#include <stddef.h>
#include <stdint.h>

#include "mu_bmd.h"
#include "mu_model.h"
#include "mu_raster.h"
#include "mu_scene.h"
#include "mu_terrain.h"
#include "mu_textures.h"
#include "../../reconstructed/particles/particles.h"

/* The client's legacy particles, sprites and blob shadows in the native
 * session (NATIVE-PARTICLE-001, docs/research/client-particles.md).
 *
 * Runs reconstructed/particles (compared with the client in Unicorn) for the
 * walk-around world:
 *   - CreateParticle from the object move pass (CreateFire's fire and smoke),
 *     RenderObjectVisual (the Waterspout smoke) and the weather (rain
 *     splashes); MoveParticles once per logic step after the other movers, as
 *     the in-world tick orders them;
 *   - CreateSprite from RenderObjectVisual (MerchantAnimal flares) and the
 *     ambient creatures (butterfly glow, crow eyes); the sprite section of the
 *     render scene draws RenderSprites(0) and then RenderParticles(0);
 *   - RenderBodyShadow for the ambient creatures (their RenderBoids/RenderFishs
 *     call).
 * The GL stream the reconstructed routines emit (state wrappers, BindTexture,
 * GL_QUADS in view space under BeginSprite's identity modelview) goes through
 * the session's render backend: view-space corners are taken back to world
 * space with the camera matrix (the backend applies the modelview), quads are
 * drawn as two triangles.
 *
 * Viewer choices (not client readings): the module has its own MSVC rand()
 * state (the client shares one with everything); the list keeps at most
 * MU_WORLD_PT_CAPACITY particles (the client's is unbounded); bone positions
 * use the native pose (bones without the origin, TransformPosition with
 * translate) where the client's static-object pose folds the origin into the
 * bones. */

enum { MU_WORLD_PT_BITMAPS = 9, MU_WORLD_PT_CAPACITY = 4096, MU_WORLD_PT_SHADOW_MESHES = 64 };

typedef struct mu_world_particles_stats {
    uint64_t created, dropped, unsupported, overflow;
    uint64_t sprites_created, sprites_full;
    uint64_t joints, effects;              /* CreateJoint / CreateEffect requests (the older effect pools) */
    uint32_t steps;
    uint32_t live, max_live;               /* particles in the list now / over the session */
    uint32_t drawn_particles, drawn_sprites;   /* last draw */
    uint32_t shadows, shadow_vertices;     /* drawn in the frame of the last particle draw */
    uint32_t pending_shadows, pending_shadow_vertices;
    uint64_t shadows_total;
    uint32_t visuals;                      /* RenderObjectVisual calls handled */
} mu_world_particles_stats;

typedef struct mu_world_particles {
    int32_t world;
    const mu_world *map;
    mu_pt_system list;
    mu_pt_sprites *sprites;
    uint32_t rand_state;
    uint64_t rand_calls;
    mu_textures bitmaps;                   /* slots: 0x7f3c, 0x7f5a, 0x7ef7, 0x7f26, 0x7f2b, 0x7f25, 0x7f67, 0x771c, 0x771d */
    int32_t bitmap_present[MU_WORLD_PT_BITMAPS];
    float camera[12];                      /* CameraMatrix 0x0bdc5918 of the last draw (row-major 3x4) */
    float world_time;
    mu_world_particles_stats stats;
} mu_world_particles;

/* Loads the effect bitmaps (Data/Effect, the world's rain02/rain03) unless
 * no_assets, seeds rand(). Returns 0, or 1 with a message. */
int mu_world_particles_open(mu_world_particles *p, const char *game_root, const mu_world *map, int32_t world,
                            uint32_t seed, int no_assets, char *error, size_t error_size);
void mu_world_particles_close(mu_world_particles *p);

/* The module's rand() (MSVC LCG). */
int32_t mu_world_particles_rand(mu_world_particles *p);

/* CreateParticle 0x0168fafd(type, position, angle, light, subtype, scale,
 * owner NULL, 0). Returns 1 when kept. */
int mu_world_particles_create(mu_world_particles *p, int32_t type, const float position[3], const float angle[3],
                              const float light[3], int32_t subtype, float scale);
/* CreateSprite 0x01692eb7(bitmap, position, scale, light, owner, rotation,
 * blend, axes, default sheet). */
int32_t mu_world_particles_sprite(mu_world_particles *p, int32_t bitmap, const float position[3], float scale,
                                  const float light[3], int32_t owner, float rotation, int32_t blend, int32_t axes);

/* MoveParticles 0x01616c80, one logic step (frame time 0.1). world_time is
 * the client time 0x06fce370 in ms. */
void mu_world_particles_step(mu_world_particles *p, float world_time);

/* Draw target: the backend for the module's bitmaps (slot = index into
 * p->bitmaps, -1 untextured). Returns 0 when it filled `out`. */
typedef struct mu_world_particles_target {
    void *context;
    int (*backend)(void *context, const mu_world_particles *p, mu_render_backend *out);
} mu_world_particles_target;

/* The sprite section: 0x01692887 (sprites visible), RenderSprites(0) (draws
 * and kills them), RenderParticles(0), with the camera of the GL modelview
 * (column-major). Returns the number of quads drawn. */
long mu_world_particles_draw(mu_world_particles *p, const float modelview[16], const mu_world_particles_target *t);
long mu_world_particles_draw_raster(mu_world_particles *p, mu_raster *raster, const float modelview[16]);

/* RenderBodyShadow 0x012bc07a(-1, -1, -1, -1, 0) of a posed, transformed model
 * (mu_model_vertices, mu_model_origin) through a backend, untextured, with the
 * colour the caller sent (glColor4f) and blend (SRC_ALPHA, ONE_MINUS_SRC_ALPHA)
 * as EnableAlphaTest leaves it. Returns the vertices sent. */
int32_t mu_world_particles_shadow(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd, const float rgba[4],
                                  const mu_render_backend *backend);

/* The character part shadow of the item render 0x0176ce74 (its shadow block,
 * a static reading): RenderBodyShadow of a posed, transformed part model,
 * opaque black after DisableAlphaBlend 0x0184a7f3 (glColor3f(0, 0, 0)), or
 * EnableAlphaTest(1) and glColor4f(0, 0, 0, 0.2) in Atlans (worlds 7,
 * 0x80..0x82); none in the worlds 0x18..0x1d, 0x24, 0xa and 0x84; z offset 5
 * in world 0x8f. The client's further conditions (the object's shadow flag
 * +3, +0x44 != 3, the buff 0x12 and an option singleton) are taken as
 * allowing it for the hero. Returns the vertices sent. */
int32_t mu_world_particles_character_shadow(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd,
                                            const mu_render_backend *backend);

/* TransformPosition 0x012b6ef1 on a posed native model: bone `bone`'s matrix
 * (mu_model_bone_matrices), with the body scale and origin of the model's
 * parameters (translate). Returns 0 when the bone does not exist. */
int mu_world_particles_bone_position(const mu_model *model, int32_t bone, const float in[3], float out[3]);
/* The same with the bone looked up by name (0x0129f18a's test on the BMD bone
 * names). */
int mu_world_particles_named_bone_position(const mu_model *model, const mu_bmd *bmd, const char *name,
                                           const float in[3], float out[3]);

/* RenderObjectVisual 0x017f9758 for an object of the world (Lorencia and
 * Tormenta Island; other worlds do nothing). has_model: the model getter's
 * answer; model/bmd: the posed model for the bone positions (NULL when the
 * object was not posed: the bone helpers then leave their output alone).
 * Writes back BlendMeshLight / v scroll and the light the visual sets.
 * Returns 1 when handled. */
int mu_world_particles_object_visual(mu_world_particles *p, mu_pt_visual_object *object, int has_model,
                                     const mu_model *model, const mu_bmd *bmd);

/* Hooks the module into the object runtime (CreateParticle of the move pass,
 * RenderObjectVisual after RenderObject) and the ambient creatures
 * (CreateParticle, CreateSprite, TransformPosition, RenderBodyShadow).
 * objects/env may be NULL. */
struct mu_objects;
struct mu_world_env;
void mu_world_particles_attach(mu_world_particles *p, struct mu_objects *objects, struct mu_world_env *env);

#endif
