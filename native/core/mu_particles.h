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
#include "mu_joints.h"

/* Owner handle for the hero OBJECT in joint/effect/sprite requests. */
#define MU_WORLD_FX_BOID_BASE 0x7ffffe00
#define MU_WORLD_FX_HERO_OBJECT 0x7fffff00
#include "../../reconstructed/particles/particles.h"
#include "../../reconstructed/combat/skill_fx.h"

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

/* NATIVE-JOINT-001: the module also keeps the world objects' joints and effects (the older effect family's
 * other two pools): CreateJoint/CreateEffect from RenderObjectVisual (Tormenta Island's lightning 0x7f7d and
 * tornado 0x40e) through reconstructed/joints and reconstructed/combat/skill_fx; MoveEffects, MoveJoints and
 * MoveParticles in that order each step; the effect models before the joints, the joints before the sprite
 * section. Viewer choices: these pools are the module's own (the skills keep theirs in mu_combat), the effect
 * models play their first action (frame += speed, looping) and the tornado's PlayBuffer is counted, not played. */
enum { MU_WORLD_PT_BITMAPS = 51, MU_WORLD_PT_CAPACITY = 4096, MU_WORLD_PT_SHADOW_MESHES = 64,
       MU_WORLD_FX_EFFECTS = MU_SFX_EFFECTS, MU_WORLD_FX_MODELS = 11, MU_WORLD_FX_QUADS = 8192,
       MU_WORLD_FX_LIGHTS = MU_JT_JOINTS + MU_SFX_EFFECTS };

typedef struct mu_world_fx_light {
    float x, y, rgb[3];
    int32_t range;
} mu_world_fx_light;

typedef struct mu_world_fx_model {
    int32_t type;
    int loaded;
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
} mu_world_fx_model;

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
    /* NATIVE-JOINT-001 */
    uint64_t joints_created, joints_unsupported, joints_full;
    uint64_t effects_created, effects_unsupported, effects_full, sounds;
    uint32_t live_joints, max_joints, live_effects;
    uint32_t drawn_joint_quads, drawn_effect_models;
    uint32_t drawn_decals;                 /* NATIVE-HELPERS-002: decal fans of the effects (shock ring, paw marks) */
    uint64_t decals_total;
} mu_world_particles_stats;

typedef struct mu_world_particles {
    int32_t world;
    const mu_world *map;
    mu_pt_system list;
    mu_pt_sprites *sprites;
    uint32_t rand_state;
    uint64_t rand_calls;
    mu_textures bitmaps;                   /* slots: 0x7f3c, 0x7f5a, 0x7ef7, 0x7f26, 0x7f2b, 0x7f25, 0x7f67, 0x7f7c,
                                              0x7fd5, 0x7fd3, 0x7fd8, 0x7f89, 0x801a, 0x7f37, 0x7f66, 0x801b,
                                              0x801c, 0x8017, 0x8155, 0x8145, 0x7b78, 0x771c, 0x771d */
    int32_t bitmap_present[MU_WORLD_PT_BITMAPS];
    float camera[12];                      /* CameraMatrix 0x0bdc5918 of the last draw (row-major 3x4) */
    float world_time;
    mu_world_particles_stats stats;
    /* NATIVE-JOINT-001: the world objects' joints and effects */
    struct mu_world_helpers *helpers;      /* helper OBJECTs for mount-owned effects and joints */
    const struct mu_world_actors *actors;  /* NPC-owned joints; actor ids use MU_WORLD_ACTOR_FX_BASE */
    struct mu_world_env *environment;      /* boid-owned particles and joints */
    struct mu_objects *objects;            /* owners and targets (object images), NULL none */
    mu_jt_joint *joints;                   /* MU_JT_JOINTS records */
    mu_sfx_effect *effects;                /* MU_WORLD_FX_EFFECTS records */
    mu_world_fx_model models[MU_WORLD_FX_MODELS];
    const mu_terrain_frustum *frustum; /* current render polygon, optional for standalone hosts */
    float hero_position[3];                /* [0x0a39d754] + 0x33ac (the tornado's sound distance) */
    int has_hero;
    mu_joint_quad *joint_quads;            /* MU_WORLD_FX_QUADS, the last RenderJoints */
    int32_t scene_state;                   /* SceneFlag [0x01d1df70] for the kinds that test it (6 by default) */
    mu_world_fx_light lights[MU_WORLD_FX_LIGHTS];  /* AddTerrainLight calls of the last logic step */
    int32_t light_count;
} mu_world_particles;

enum { MU_WORLD_ACTOR_FX_BASE = 0x08000000 };

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
/* CreateParticle with an owner object (an index into the attached objects; -1 none): the record's owner
 * position is the object's +0x158 with z = RequestTerrainHeight. */
int mu_world_particles_create_owned(mu_world_particles *p, int32_t type, const float position[3],
                                    const float angle[3], const float light[3], int32_t subtype, float scale,
                                    int32_t owner);
/* CreateJoint 0x0153b02c(type, position, target position, angle, subtype, target object, scale, key, skill,
 * byte10, -1, 0, word13, arg14) on the module's joint pool. Returns the record index (< 0: none). */
int32_t mu_world_particles_joint(mu_world_particles *p, int32_t type, const float position[3],
                                 const float target_position[3], const float angle[3], int32_t subtype, int32_t target,
                                 float scale, uint16_t key, uint16_t skill, uint8_t byte10, uint16_t word13,
                                 int32_t arg14, const float *creation_light);
/* CreateEffect 0x013c0f19(type, subtype, position, angle, light, owner object, scale, info) on the module's
 * effect pool. Returns 1 when created. */
int mu_world_particles_effect(mu_world_particles *p, int32_t type, int32_t subtype, const float position[3],
                              const float angle[3], const float light[3], int32_t owner, float scale,
                              const mu_sfx_info *info);
/* The hero's position (the tornado tests its distance for PlayBuffer). */
void mu_world_particles_set_hero(mu_world_particles *p, const float position[3]);
/* Replay after each rendered frame's primary-light copy, like the combat and object light feeds. */
void mu_world_particles_apply_lights(const mu_world_particles *p, mu_world *map);
/* Effect models (RenderEffects -> RenderObject, a static reading): places and poses every live model effect
 * and calls draw with RenderObject's RenderBody options; the callback must draw before returning.
 * NATIVE-CHARSEL-003: the character select's star dragon stardr01 0x5ac is drawn plainly (RenderEffects
 * 0x0151e966); its glint stardr02 0x5ad poses and plays its animation in the render pass, and while its
 * LifeTime is 21..24 creates a Spark04 0x8155 sprite (scale 0.7, light (0.8, 0.8, 1)), takes light 0.6 and
 * scale 0.8 / 0.6 (subtype 0 / 1), else scale 0.5 / 0.3 (0x0151e980, static reading). */
typedef void (*mu_world_particles_model_fn)(void *context, const mu_model *model, const mu_textures *textures,
                                            int32_t slot, const mu_draw_options *options);
int32_t mu_world_particles_draw_models(mu_world_particles *p, mu_world_particles_model_fn draw, void *context);
/* The same through the software rasterizer. */
int32_t mu_world_particles_draw_models_raster(mu_world_particles *p, mu_raster *raster);
/* Live joints and effects. */
int32_t mu_world_particles_live_joints(const mu_world_particles *p);
int32_t mu_world_particles_live_effects(const mu_world_particles *p);

/* CreateSprite 0x01692eb7(bitmap, position, scale, light, owner, rotation,
 * blend, axes, default sheet). */
int32_t mu_world_particles_sprite(mu_world_particles *p, int32_t bitmap, const float position[3], float scale,
                                  const float light[3], int32_t owner, float rotation, int32_t blend, int32_t axes);

/* Kills every live sprite without drawing (a frame rendered without output: RenderSprites' SetLive(0)). */
void mu_world_particles_discard_sprites(mu_world_particles *p);

/* MoveEffects 0x0150ddb1, MoveJoints 0x01589b06 and MoveParticles 0x01616c80, one logic step (frame time
 * 0.1). world_time is the client time 0x06fce370 in ms. */
void mu_world_particles_step(mu_world_particles *p, float world_time);

/* Draw target: the backend for the module's bitmaps (slot = index into
 * p->bitmaps, -1 untextured). Returns 0 when it filled `out`. */
typedef struct mu_world_particles_target {
    void *context;
    int (*backend)(void *context, const mu_world_particles *p, mu_render_backend *out);
} mu_world_particles_target;

/* RenderJoints(0) (NATIVE-JOINT-001), then the sprite section: 0x01692887 (sprites visible),
 * RenderSprites(0) (draws and kills them), RenderParticles(0), with the camera of the GL modelview
 * (column-major). Returns the number of quads drawn. */
long mu_world_particles_draw(mu_world_particles *p, const float modelview[16], const mu_world_particles_target *t);
long mu_world_particles_draw_raster(mu_world_particles *p, mu_raster *raster, const float modelview[16]);

/* RenderBodyShadow 0x012bc07a(-1, -1, -1, -1, 0) of a posed, transformed model
 * (mu_model_vertices, mu_model_origin) through a backend, untextured, with the
 * colour the caller sent (glColor4f) and blend (SRC_ALPHA, ONE_MINUS_SRC_ALPHA)
 * as EnableAlphaTest leaves it. Returns the vertices sent. */
int32_t mu_world_particles_shadow(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd, const float rgba[4],
                                  const mu_render_backend *backend);
/* NATIVE-HELPERS-002: the same over the meshes first..end (RenderBodyShadow(model, -1, -1, first, end, 0): the
 * Dark Horse's and the Divine Horse's second shadow). */
int32_t mu_world_particles_shadow_range(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd,
                                        const float rgba[4], int32_t first, int32_t end,
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
 * RenderObjectVisual after RenderObject, the login world's CreateSprite) and the
 * ambient creatures (CreateParticle, CreateSprite, TransformPosition,
 * RenderBodyShadow). objects/env may be NULL. */
struct mu_objects;
struct mu_world_env;
void mu_world_particles_attach(mu_world_particles *p, struct mu_objects *objects, struct mu_world_env *env);

#endif
