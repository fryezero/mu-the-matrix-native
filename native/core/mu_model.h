#ifndef MU_MODEL_H
#define MU_MODEL_H

#include <stdint.h>

#include "mu_bmd.h"
#include "../../reconstructed/model-codec/skinning.h"

/* Client-memory model for the native viewer.
 *
 * The reconstructed stages (bone-track loop mu_bone_tracks_read, pose builder
 * mu_pose_build, animation tick mu_animation_tick and CPU skinning
 * mu_model_transform) operate on views of 32-bit client address ranges. This
 * module lays a checked mu_bmd out as the client's model object and records,
 * runs the bone-track loop once, and then calls the reconstructed functions
 * unchanged every frame. Nothing here reimplements their arithmetic.
 *
 * Layout choices that are ours (not recovered client facts):
 *   - the window base MU_MODEL_WINDOW and the order of records inside it;
 *   - per-mesh vertex/normal/texcoord/triangle arrays copied from the file
 *     (triangle records are the first 0x24 bytes of each 64-byte polygon,
 *     matching the fields the mesh draw reads: corners, v[4], n[4], t[4]);
 *   - a deterministic bump allocator for the loop's operator-new requests;
 *   - action lock flags (+0xa) copied from the file's lock_positions byte.
 * Output buffers use the client's default wrapper addresses
 * (docs/research/client-skinning.md): bones 0x06fce398, vertices 0x078978a0,
 * normals 0x0812cce0, light 0x06fd0918, secondary light 0x075a9ee8, with the
 * fixed per-mesh strides 0x2bf20/0xea60. Their capacities (200 bones, 50
 * meshes, 15,000 vertices/normals per mesh) are inferences from those
 * addresses; larger models are refused.
 */

#define MU_MODEL_WINDOW 0x10000000u
#define MU_MODEL_BONES 0x06fce398u
#define MU_MODEL_LIGHTS 0x06fd0918u
#define MU_MODEL_VERTICES 0x078978a0u
#define MU_MODEL_NORMALS 0x0812cce0u
#define MU_MODEL_VERTEX_STRIDE 0x2bf20u
#define MU_MODEL_LIGHT_STRIDE 0xea60u
#define MU_MODEL_MAX_BONES 200
#define MU_MODEL_MAX_MESHES 50
#define MU_MODEL_MAX_ENTRIES 15000

/* Inputs a caller of the client routines supplies. Defaults from
 * mu_model_default_params. Fields map to model-object offsets or arguments. */
typedef struct mu_model_params {
    float body_scale;         /* model +0x74 */
    float origin[3];          /* model +0x78 */
    float angles[3];          /* pose builder angles argument (degrees), copied to +0x84 */
    float head_angles[2];     /* pose builder head angles argument */
    float height;             /* model +0x90 */
    float color[3];           /* model +0x54 object colour */
    float light_angles[3];    /* model +0x98 */
    int32_t special_bone;     /* model +0x60, -1 for none */
    int32_t light_skip_mesh;  /* model +0x94: mesh index drawn without per-normal colours */
    uint8_t lighting;         /* model +0x50 */
    uint8_t secondary_light;  /* model +0xcb: 1 selects the secondary light in the colour pass */
    uint8_t pose_translate;   /* pose builder translate argument */
    uint8_t transform_translate; /* transform translate argument */
    float vertex_scale, light_ambient, light_scale, light_minimum; /* transform arguments */
    float bone_scale;         /* global 0x01cf104c */
    uint8_t light_override;   /* global 0x01cf1048 */
    int32_t world;            /* global 0x01cf15fc */
    int32_t scene_state;      /* global 0x01d1df70 */
    int32_t bounds_mode;      /* global 0x0b437bfc */
} mu_model_params;

void mu_model_default_params(mu_model_params *params);

enum { MU_MODEL_REGION_COUNT = 12 };

typedef struct mu_model {
    const mu_bmd *bmd;
    uint8_t *window;
    uint32_t window_size;
    uint32_t model, object, actions, bones, meshes;  /* client addresses inside the window */
    uint32_t heap_cursor, heap_end;
    uint32_t *triangles, *texcoords;                 /* per-mesh client addresses */
    mu_client_image regions[MU_MODEL_REGION_COUNT];
    uint8_t *region_storage[MU_MODEL_REGION_COUNT];
    mu_client_memory memory;
    mu_model_params params;
    int32_t posed;            /* 1 after a successful pose; 0 uses identity bone matrices */
} mu_model;

enum { MU_MODEL_OK = 0, MU_MODEL_ERROR = 1 };

/* Builds the client window and runs the reconstructed bone-track loop. */
int mu_model_init(mu_model *model, const mu_bmd *bmd, const mu_model_params *params, char *error, size_t error_size);
void mu_model_free(mu_model *model);
/* Call after copying a mu_model (and its mu_bmd) by value: re-points the
 * internal region table and the model description. */
void mu_model_relocate(mu_model *model, const mu_bmd *bmd);

/* Writes the parameters into the model object and globals. */
void mu_model_apply_params(mu_model *model, const mu_model_params *params);

/* Animation state held in a caller object inside the window (frame, prior
 * frame, prior action), as the client passes object fields to the tick and
 * the pose builder. */
void mu_model_set_state(mu_model *model, uint16_t action, float frame, float prior_frame, uint16_t prior_action);
uint16_t mu_model_action(const mu_model *model);
float mu_model_frame(const mu_model *model);
float mu_model_prior_frame(const mu_model *model);
uint16_t mu_model_prior_action(const mu_model *model);
int32_t mu_model_action_stop(const mu_model *model, uint16_t action);
void mu_model_set_action_stop(mu_model *model, uint16_t action, uint8_t stop);

/* mu_animation_tick with speed; *loop receives its AL result. */
int mu_model_tick(mu_model *model, float speed, uint8_t *loop);
/* mu_pose_build from the object state (keep_root 0). Models without actions,
 * or whose current/prior action has no keys, get identity bone matrices
 * instead (viewer behaviour; the client would read unrelated memory). */
int mu_model_pose(mu_model *model);
/* mu_model_transform into the output regions. */
int mu_model_transform_all(mu_model *model);
/* tick (when speed != 0 is requested by the caller), pose and transform. */
int mu_model_update(mu_model *model);

/* Host pointers into the output regions and records. */
const float *mu_model_vertices(const mu_model *model, int32_t mesh);
const float *mu_model_normals(const mu_model *model, int32_t mesh);
const float *mu_model_lights(const mu_model *model, int32_t mesh);
const float *mu_model_secondary_lights(const mu_model *model, int32_t mesh);
const float *mu_model_bone_matrices(const mu_model *model);
const uint8_t *mu_model_triangles(const mu_model *model, int32_t mesh);
const float *mu_model_texcoords(const mu_model *model, int32_t mesh);
const float *mu_model_color(const mu_model *model);
const float *mu_model_origin(const mu_model *model);
const float *mu_model_box(const mu_model *model);   /* 12 floats: origin, then three axes */
uint8_t *mu_model_host(const mu_model *model, uint32_t address, uint32_t length);

#endif
