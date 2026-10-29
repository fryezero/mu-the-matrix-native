#ifndef MU_EFFECT_SCENE_H
#define MU_EFFECT_SCENE_H

#include <stdint.h>

#include "mu_effect.h"
#include "mu_raster.h"
#include "mu_terrain.h"

/* Scenes of several effects run like the client's EffectManager
 * (NATIVE-FX-002, docs/research/client-effect-manager.md):
 *
 *   - creation by name (factory 0x00a797a0): the first request for a path loads
 *     the .ein tree into a template cache keyed by the path; every request
 *     returns an instance cloned from the template (0x00a75934) with its own
 *     position, rotation, scale, owner-tint flag, action list and start frame;
 *   - instances attached to a world object get the object's matrix as the
 *     external matrix of the node update (0x0129f4cb/0x0129f671: object scale
 *     and position, or a bone matrix);
 *   - every frame: node update of every instance (transform, owner gate, type
 *     update, bounding box, octree maintenance, children), then the render
 *     pass 0x00a7a30e: frustum (0x00a8d821) query of the octree and the draws
 *     of the visible effects in octree order with depth writes and alpha test
 *     off.
 *
 * The terrain collider queries the loaded world when one is set (viewer
 * height/normal helpers, not the client's 0x016cc9e2/0x016ccbb6), else flat
 * ground z = 0. */

typedef struct mu_effect_instance {
    mu_fx_effect fx;               /* clone of the template tree */
    uint32_t template_index;
    float external[16];
    int has_external;
    mu_fx_owner owner;
} mu_effect_instance;

typedef struct mu_effect_scene {
    char root[4096];
    mu_effect *templates;          /* loaded trees with their textures (never updated, like the client's) */
    char (*template_keys)[256];
    uint32_t template_count, template_capacity;
    mu_effect_instance *instances;
    uint32_t instance_count, instance_capacity;
    mu_fx_rng rng;
    mu_fx_octree_node *tree;
    const mu_world *world;
    mu_fx_terrain terrain;
    mu_fx_frustum frustum;
    mu_fx_vertex *vertices;
    uint32_t vertex_capacity;
    /* statistics of the last render */
    uint32_t visible, vertices_drawn;
} mu_effect_scene;

int mu_effect_scene_init(mu_effect_scene *scene, const char *game_root, uint32_t seed);
void mu_effect_scene_free(mu_effect_scene *scene);

/* Collider ground from a loaded world (NULL: flat ground z = 0). */
void mu_effect_scene_set_world(mu_effect_scene *scene, const mu_world *world);

/* Factory: instance of the effect at client_path ("Data\\Effect\\x.ein").
 * use_template_transform takes the template's own position, rotation and
 * scale instead of the given ones. Returns the instance index or -1. */
int mu_effect_scene_create(mu_effect_scene *scene, const char *client_path, const float position[3],
                           const float rotation[3], float scale, int use_template_transform, int owner_tint,
                           const int32_t *actions, uint32_t action_count, float start_frame, char *error,
                           unsigned long error_size);

/* RENDER-EFFECTS-006: the factory's template load alone (index, or -1 with a message): whether a request for
 * client_path returns a valid effect. */
int mu_effect_scene_template(mu_effect_scene *scene, const char *client_path, char *error, unsigned long error_size);

/* RENDER-EFFECTS-006: one instance's node update (0x0129f671 updates the effects of one world object). */
void mu_effect_scene_update_one(mu_effect_scene *scene, uint32_t instance, float dt);

/* Owner path: the object's world matrix becomes the external matrix. */
void mu_effect_scene_attach(mu_effect_scene *scene, uint32_t instance, const float matrix[16]);

/* Object matrix of 0x0129f4cb without a bone: uniform scale, then translation. */
void mu_effect_object_matrix(float out[16], const float position[3], float scale);

void mu_effect_scene_update(mu_effect_scene *scene, float dt);

/* Render pass for a camera (eye, target, Z up; fov in degrees as the viewer
 * camera). The raster's view/projection must match. Returns the number of
 * visible effects drawn. */
uint32_t mu_effect_scene_render(mu_effect_scene *scene, const float eye[3], const float target[3], float fov_degrees,
                                float aspect, float near_plane, float far_plane, mu_raster *raster);

/* The same render pass with a caller draw (e.g. OpenGL): for each visible
 * effect in octree order, its filled quads, draw state, texture and the
 * SpaceIsLocal matrix (NULL when none). draw may be NULL (fill only). */
typedef void (*mu_effect_draw_fn)(void *context, const mu_fx_vertex *vertices, uint32_t count,
                                  const mu_fx_draw_state *state, const mu_image *texture, const float *matrix);
uint32_t mu_effect_scene_render_to(mu_effect_scene *scene, const float eye[3], const float target[3],
                                   float fov_degrees, float aspect, float near_plane, float far_plane,
                                   mu_effect_draw_fn draw, void *context);

#endif
