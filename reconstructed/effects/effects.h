#ifndef MU_EFFECTS_H
#define MU_EFFECTS_H

/* Reconstructed JSON effect system ("EffectManager" effects, Data/Effect .ein files).
 *
 * Two effect types are reconstructed:
 *   type 0  particle system  (client vtable 0x01a81d0c, 0x158-byte object)
 *   type 1  billboard sprite (client vtable 0x01a80844, 0x170-byte object)
 * Names are investigator choices; the client's RTTI names were not captured.
 * Field comments give the client object offset each value mirrors.
 *
 * Arithmetic follows the client's scalar SSE binary32 code in source order;
 * build with -ffp-contract=off. Trigonometry and square roots go through the
 * client's CRT wrappers, i.e. (float)cos((double)x), (float)sin((double)x) and
 * (float)sqrt((double)x); this module uses the host libm for those three.
 * Random numbers come from the MSVC CRT rand() the client calls (0x01989721);
 * mu_fx_rand implements the same linear congruential generator. */

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- random numbers (MSVC rand) ---- */
typedef struct mu_fx_rng {
    uint32_t state;
    uint64_t calls;
} mu_fx_rng;
void mu_fx_rng_seed(mu_fx_rng *rng, uint32_t seed);
int32_t mu_fx_rand(mu_fx_rng *rng);

/* ---- keyed curves and gradients ---- */
typedef struct mu_fx_curve_key { float time, value, tangent; } mu_fx_curve_key;   /* 12 bytes */
typedef struct mu_fx_curve { mu_fx_curve_key *keys; uint32_t count; } mu_fx_curve;
typedef struct mu_fx_grad1_key { float time, value; } mu_fx_grad1_key;            /* 8 bytes */
typedef struct mu_fx_grad1 { mu_fx_grad1_key *keys; uint32_t count; } mu_fx_grad1;
typedef struct mu_fx_grad3_key { float time, rgb[3]; } mu_fx_grad3_key;           /* 16 bytes */
typedef struct mu_fx_grad3 { mu_fx_grad3_key *keys; uint32_t count; } mu_fx_grad3;

/* 0x00a74a3f: cubic Hermite with unscaled tangents; returns 0 and leaves *out
 * untouched when the curve has no keys. */
int mu_fx_curve_eval(const mu_fx_curve *curve, float *out, float t);
/* 0x00a73b41 / 0x00a73ca4: piecewise linear. */
int mu_fx_grad1_eval(const mu_fx_grad1 *gradient, float *out, float t);
int mu_fx_grad3_eval(const mu_fx_grad3 *gradient, float out[3], float t);

/* ---- particle (0x88 bytes; field order and size match the client record) ---- */
typedef struct mu_fx_particle {
    float position[3];        /* +0x00 */
    float direction[3];       /* +0x0c */
    float force[3];           /* +0x18 force-over-lifetime velocity */
    float velocity[3];        /* +0x24 direction*speed + force (set each update) */
    float start_life;         /* +0x30 */
    float life;               /* +0x34 remaining */
    float start_size;         /* +0x38 */
    float size;               /* +0x3c */
    float start_speed;        /* +0x40 */
    float speed;              /* +0x44 */
    float angular_velocity;   /* +0x48 */
    float angle;              /* +0x4c */
    float start_color[4];     /* +0x50 */
    float color[4];           /* +0x60 */
    float brightness;         /* +0x70 */
    float bounce;             /* +0x74 terrain-collider restitution product */
    float uv0[2];             /* +0x78 */
    float uv1[2];             /* +0x80 */
} mu_fx_particle;

/* Vertex record of both effect VBOs: 36 bytes, glVertexPointer(3,0),
 * glTexCoordPointer(2,12), glColorPointer(4,20). */
typedef struct mu_fx_vertex {
    float position[3];
    float texcoord[2];
    float color[4];
} mu_fx_vertex;

/* Camera record the effect fill routines read (client object 0x0bdc5ae8,
 * filled by 0x00a8d821): eye position, view direction, right = forward x up,
 * up. */
typedef struct mu_fx_camera {
    float position[3];        /* +0x00 */
    float forward[3];         /* +0x0c */
    float right[3];           /* +0x18 */
    float up[3];              /* +0x24 */
} mu_fx_camera;
void mu_fx_camera_set(mu_fx_camera *camera, const float position[3], const float forward[3], const float up[3]);

enum { MU_FX_BLEND_NONE, MU_FX_BLEND_ALPHA, MU_FX_BLEND_ADDITIVE, MU_FX_BLEND_MULTIPLY };
enum { MU_FX_BILLBOARD_EYELINE, MU_FX_BILLBOARD_HORIZONTAL, MU_FX_BILLBOARD_DIRECTIONAL,
       MU_FX_BILLBOARD_VERTICAL, MU_FX_BILLBOARD_LOCAL_PLANE };
enum { MU_FX_SHAPE_BOX, MU_FX_SHAPE_CONE, MU_FX_SHAPE_HEMISPHERE, MU_FX_SHAPE_POINT, MU_FX_SHAPE_SPHERE };

/* ---- emitter sub-components (emitter slots 0..5, by "Type") ---- */
typedef struct mu_fx_shape {
    uint8_t present;
    int32_t shape;            /* MU_FX_SHAPE_* */
    float size[3];            /* box +0x04 */
    float tangent, radius, height;   /* cone +0x04/+0x08/+0x0c; sphere radius +0x04 */
    uint8_t cylinder;         /* cone +0x10 */
    uint8_t emit_from_shell;  /* box +0x10, cone +0x11, spheres +0x08 */
    uint8_t random_direction; /* box +0x11, cone +0x12, spheres +0x09 */
} mu_fx_shape;

typedef struct mu_fx_start_color {
    uint8_t present;
    float min_color[4], max_color[4];  /* +0x04, +0x14 */
    float min_brightness, max_brightness; /* +0x24, +0x28 */
    mu_fx_grad3 color;        /* +0x2c */
    mu_fx_grad1 alpha;        /* +0x38 */
    mu_fx_grad1 brightness;   /* +0x44 */
} mu_fx_start_color;

typedef struct mu_fx_range {  /* StartLifetime / StartRotationAngle / StartSize / StartSpeed */
    uint8_t present;
    float min, max;           /* +0x04, +0x08 */
    mu_fx_curve curve;        /* +0x0c (unused by StartRotationAngle) */
} mu_fx_range;

typedef struct mu_fx_burst { float time; int32_t count; } mu_fx_burst;

typedef struct mu_fx_emitter {         /* particle component type 0, 0x64 bytes */
    uint8_t present;
    float delay;              /* +0x04 */
    float delay_left;         /* +0x08 */
    uint32_t frequency;       /* +0x0c: emits only when rand() % frequency == 0 */
    int32_t min_count, max_count;  /* +0x10, +0x14 */
    mu_fx_curve count_curve;  /* +0x18 CurveEmissionCount */
    float accumulated;        /* +0x24 */
    mu_fx_burst *bursts;      /* +0x28 */
    uint32_t burst_count;
    mu_fx_shape shape;        /* slot 0 */
    mu_fx_start_color color;  /* slot 1 */
    mu_fx_range lifetime;     /* slot 2 */
    mu_fx_range rotation;     /* slot 3 */
    mu_fx_range size;         /* slot 4 */
    mu_fx_range speed;        /* slot 5 */
} mu_fx_emitter;

typedef struct mu_fx_color_lifetime { uint8_t present; mu_fx_grad3 color; mu_fx_grad1 alpha; } mu_fx_color_lifetime;
typedef struct mu_fx_force_lifetime {
    uint8_t present;
    float constant[3];        /* +0x04 */
    mu_fx_curve curve[3];     /* +0x10, +0x1c, +0x28 */
    float offset[3];          /* billboard variant only: +0x34 accumulated displacement */
} mu_fx_force_lifetime;
typedef struct mu_fx_rotation_lifetime {
    uint8_t present;
    float min, max;           /* particle variant: random angular velocity */
    float constant;           /* billboard variant: +0x04 */
    mu_fx_curve curve;
} mu_fx_rotation_lifetime;
typedef struct mu_fx_curve_component { uint8_t present; mu_fx_curve curve; } mu_fx_curve_component;
typedef struct mu_fx_texcoord_animation {
    uint8_t present;
    uint32_t horizontal, vertical;   /* +0x04, +0x08 */
    int32_t min_tile, max_tile;      /* particle variant +0x0c, +0x10 */
    mu_fx_curve tiles;               /* particle +0x14, billboard +0x0c */
} mu_fx_texcoord_animation;
typedef struct mu_fx_terrain_collider { uint8_t present; float bounding; } mu_fx_terrain_collider;

/* Terrain queries used by the particle terrain collider (client 0x016cc9e2
 * height, 0x016ccbb6 normal). Without a terrain the collider is skipped. */
typedef struct mu_fx_terrain {
    void *context;
    float (*height)(void *context, float x, float y);
    void (*normal)(void *context, float x, float y, float out[3]);
} mu_fx_terrain;

enum { MU_FX_PARTICLE_SYSTEM = 0, MU_FX_BILLBOARD = 1 };

/* Fields of the client's world object (characters, monsters, map objects)
 * that the effect code reads through the effect's owner pointer (+0xd8). */
typedef struct mu_fx_owner {
    uint8_t flag5, flag6;     /* object +5, +6: the owner tint needs both set */
    uint16_t action;          /* +0x2a current action */
    uint8_t visible;          /* +0x38: both draws return before any GL call when 0 */
    float frame;              /* +0xd0 animation frame */
    float tint[3];            /* +0x1e8 colour that replaces the effect colour when tinting */
} mu_fx_owner;

struct mu_fx_octree_node;

/* Common effect node fields (base class, client constructor 0x00a76b51). */
typedef struct mu_fx_effect {
    int32_t type;
    char name[64];
    char texture[260];        /* "Texture" path as written in the .ein */
    float position[3];        /* +0x2c local */
    float world_position[3];  /* +0x38 */
    float rotation[3];        /* +0x44 radians, applied Z then Y then X */
    float scale;              /* +0x50 */
    float world_scale;        /* +0x54 */
    float matrix[16];         /* +0x58 column-major world matrix */
    uint8_t playing;          /* +0xd4 */
    uint8_t random_duration;  /* +0xdd */
    uint8_t parent_duration;  /* +0xde (needs a parent; unsupported here, treated as false) */
    uint8_t looping;          /* +0xdf */
    float min_duration, max_duration; /* +0xe0, +0xe4 */
    float duration;           /* +0xe8 */
    float time_left;          /* +0xec */
    int32_t blending;         /* PS +0x104, BB +0x138 */
    int32_t billboarding;     /* PS +0x108, BB +0x13c */
    uint8_t drawn;            /* PS +0x114, BB +0x144: set by draw, required by update */
    uint8_t faulted;          /* emitter hit rand() % 0 (client: integer divide fault) */

    /* particle system */
    uint8_t space_is_local;   /* +0xf0 */
    uint32_t count;           /* +0xf4 live particles */
    uint32_t capacity;        /* MaxParticle */
    mu_fx_particle *particles;/* +0xf8 */
    float length_scale;       /* +0x10c */
    float speed_scale;        /* +0x110 */
    mu_fx_emitter emitter;                 /* slot 0 */
    mu_fx_color_lifetime color_lifetime;   /* slot 1 */
    mu_fx_force_lifetime force_lifetime;   /* slot 2 */
    mu_fx_rotation_lifetime rotation_lifetime; /* slot 3 */
    mu_fx_curve_component size_lifetime;   /* slot 4 */
    mu_fx_curve_component speed_lifetime;  /* slot 5 */
    mu_fx_texcoord_animation texcoord;     /* slot 6 */
    mu_fx_terrain_collider collider;       /* slot 7 */

    /* billboard */
    float base_color[4];      /* +0xf0 */
    float color[4];           /* +0x100 */
    float base_width, width;  /* +0x110, +0x114 */
    float base_height, height;/* +0x118, +0x11c */
    float base_angle, angle;  /* +0x120, +0x124 */
    float uv0[2], uv1[2];     /* +0x128, +0x130 */
    float brightness;         /* +0x140 */
    mu_fx_color_lifetime bb_color;          /* slot 0 */
    mu_fx_rotation_lifetime bb_rotation;    /* slot 1 */
    mu_fx_curve_component bb_size;          /* slot 2 */
    mu_fx_texcoord_animation bb_texcoord;   /* slot 3 */
    mu_fx_force_lifetime bb_force;          /* slot 4 */

    /* node tree, owner and EffectManager links (NATIVE-FX-002, effects_tree.c) */
    struct mu_fx_effect *parent;            /* +0x24 */
    struct mu_fx_effect **children;         /* +0xb4 std::list of shared pointers, push_back order */
    uint32_t child_count, child_capacity;
    uint8_t managed;          /* +0x28 != NULL: created for the EffectManager, kept in its octree */
    float bbox[6];            /* +0x98 axis-aligned box: min xyz, max xyz (type routine vtable +0x0c) */
    struct mu_fx_octree_node *cell;         /* +0xb0 octree node holding this effect */
    int32_t *actions;         /* +0xc4 std::vector<int> of owner actions that gate playing */
    uint32_t action_count;
    float start_frame;        /* +0xd0 owner frame at which a gated effect starts */
    const mu_fx_owner *owner; /* +0xd8 */
    uint8_t owner_tint;       /* +0xdc: replace the colour by the owner tint while filling */
} mu_fx_effect;

/* ---- loading (.ein JSON, see effects_json.c) ---- */
enum { MU_FX_OK = 0, MU_FX_ERROR_PARSE = 1, MU_FX_ERROR_TYPE = 2, MU_FX_ERROR_MEMORY = 3 };
int mu_fx_load_json(mu_fx_effect *effect, const char *text, size_t length, char *error, size_t error_size);
void mu_fx_free(mu_fx_effect *effect);

/* ---- simulation ---- */
/* Restart (0x00a76898): time_left = duration, reset counters and components. */
void mu_fx_restart(mu_fx_effect *effect);
/* World transform (0x00a76dfe) for a top-level effect (no parent). */
void mu_fx_update_transform(mu_fx_effect *effect);
/* One node update (0x00a75708 for a top-level node without parent or manager):
 * transform, type update (PS 0x00a88443 / BB 0x00a6ea2c) and, for particle
 * systems, the bounding box (0x00a88970). */
void mu_fx_update(mu_fx_effect *effect, float dt, mu_fx_rng *rng, const mu_fx_terrain *terrain);

/* ---- drawing ---- */
/* Draw-call state of one effect draw (PS 0x00a88720, BB 0x00a6ebd1). */
typedef struct mu_fx_draw_state {
    uint8_t visible;          /* 0: the client returns before any GL call */
    uint8_t blend;            /* GL_BLEND enabled */
    uint32_t src, dst;        /* glBlendFunc factors (GL enums) */
    uint8_t texture;          /* GL_TEXTURE_2D enabled (texture loaded) */
    uint8_t multiply_matrix;  /* PS with SpaceIsLocal: glMultMatrixf(matrix) around the draw */
    uint8_t disable_cull;     /* BB: glDisable(GL_CULL_FACE) through the client's cached wrapper */
    uint32_t vertex_count;    /* glDrawArrays(GL_QUADS, 0, vertex_count) */
} mu_fx_draw_state;

/* Marks the effect drawn and fills its vertices (4 per particle; 4 for a
 * billboard). `vertices` needs 4 * capacity (PS) or 4 (BB) records. The
 * particle fill (0x00a8a55c) may write the owner tint back into particles,
 * which is not modelled (no owner). Returns the vertex count. */
uint32_t mu_fx_draw(mu_fx_effect *effect, const mu_fx_camera *camera, int texture_loaded, mu_fx_vertex *vertices,
                    mu_fx_draw_state *state);

/* ---- effect tree, owner and EffectManager (NATIVE-FX-002, effects_tree.c) ----
 *
 * mu_fx_load_json builds the whole tree: the client's base load 0x00a760b2
 * reads "Children" after the node's own keys, its type load and restart; each
 * child of Type 0 or 1 is constructed (children of other types are skipped),
 * loaded by the same routine and appended to the parent (0x00a75542).
 * mu_fx_free releases the children. */

/* World transform 0x00a76dfe: M = R(z, y, x) * scale, T = position; then
 * M = external * M when `external` is given and not the identity, otherwise
 * M = parent.M * M (world scale times the parent's) when the parent's matrix
 * is not the identity. */
void mu_fx_transform(mu_fx_effect *effect, const float *external);

/* Node update 0x00a75708(dt, external, owner): transform, owner action gate,
 * type update, bounding box, octree maintenance (when `tree` is given and the
 * effect is managed), then every child with (dt, NULL, owner). Stops at the
 * first node whose emitter faults (the client's integer divide exception);
 * returns 0 then. */
int mu_fx_node_update(mu_fx_effect *effect, float dt, const float *external, const mu_fx_owner *owner,
                      mu_fx_rng *rng, const mu_fx_terrain *terrain, struct mu_fx_octree_node *tree);

/* Bounding box, type routine vtable +0x0c (particles 0x00a88970, billboard
 * 0x00a6ed9b). */
void mu_fx_bounding_box(mu_fx_effect *effect);

/* Owner of the effect and its children (0x00a76a30). */
void mu_fx_set_owner(mu_fx_effect *effect, const mu_fx_owner *owner);

/* Number of nodes in the tree and the node at pre-order index `index`. */
uint32_t mu_fx_tree_count(const mu_fx_effect *effect);
mu_fx_effect *mu_fx_tree_node(mu_fx_effect *effect, uint32_t index);

/* Instance of a template (0x00a75934 with the type clone, vtable +0x18):
 * the template's loaded parameters with a new position, rotation and scale;
 * children are cloned with their own transforms and the same gate and tint
 * settings. `actions` may be NULL when action_count is 0 (no gate). */
int mu_fx_clone(mu_fx_effect *out, const mu_fx_effect *source, const float position[3], const float rotation[3],
                float scale, int owner_tint, const int32_t *actions, uint32_t action_count, float start_frame);

/* View frustum record (client camera object 0x0bdc5ae8, 0x90 bytes): the
 * camera fields the fills read, then six planes (normal, d), filled by
 * 0x00a8d821. */
typedef struct mu_fx_frustum {
    mu_fx_camera camera;
    float planes[6][4];       /* +0x30: near, far, left, top, right, bottom */
} mu_fx_frustum;
/* 0x00a8d821(eye, forward, up, fov, aspect, near, far); fov in radians. */
void mu_fx_frustum_set(mu_fx_frustum *frustum, const float eye[3], const float forward[3], const float up[3],
                       float fov, float aspect, float near_plane, float far_plane);
/* 0x00a8d7c8: 0 when the sphere is entirely behind one plane. The client
 * passes the squared half diagonal of a box as `radius_squared`. */
int mu_fx_frustum_sphere(const mu_fx_frustum *frustum, const float center[3], float radius_squared);

/* EffectManager octree (node 0x44 bytes: box, depth, 8 children, std::list of
 * effects). The root spans (-12750, -12750, -25500)..(38250, 38250, 25500)
 * (EffectManager init 0x00a79534); nodes split to depth 6. */
typedef struct mu_fx_octree_node {
    float bbox[6];
    uint32_t depth;
    struct mu_fx_octree_node *child[8];
    mu_fx_effect **items;
    uint32_t count, capacity;
} mu_fx_octree_node;
extern const float MU_FX_OCTREE_ROOT[6];
mu_fx_octree_node *mu_fx_octree_create(const float bbox[6], uint32_t depth);
void mu_fx_octree_free(mu_fx_octree_node *node);
int mu_fx_octree_insert(mu_fx_octree_node *node, mu_fx_effect *effect);   /* 0x00a8df54 */
void mu_fx_octree_remove(mu_fx_octree_node *node, mu_fx_effect *effect);  /* 0x00a8e4d7 */
/* 0x00a8e59f: visible effects in the client's order (node list, then the
 * eight children). Returns the number found; at most `capacity` are stored. */
uint32_t mu_fx_octree_query(const mu_fx_octree_node *node, const mu_fx_frustum *frustum, mu_fx_effect **out,
                            uint32_t capacity);

/* EffectManager render 0x00a7a30e: the GL state around the effect draws.
 * Given the state before the pass, describes what the client does: it queries
 * GL_ALPHA_TEST, GL_TEXTURE_2D, GL_BLEND, the blend factors and the depth
 * write mask, turns depth writes and alpha test off when they were on, draws
 * every visible effect, binds texture 0 and restores all of them. Depth test
 * and the depth function are not touched. With no visible effect it returns
 * before any GL call. */
typedef struct mu_fx_gl_state {
    uint8_t alpha_test, texture_2d, blend, depth_mask;
    uint32_t blend_src, blend_dst;
} mu_fx_gl_state;
typedef struct mu_fx_gl_call { uint32_t op, a, b; } mu_fx_gl_call;
enum { MU_FX_GL_GET_BOOLEAN = 1, MU_FX_GL_GET_INTEGER, MU_FX_GL_DEPTH_MASK, MU_FX_GL_ENABLE, MU_FX_GL_DISABLE,
       MU_FX_GL_BIND_TEXTURE, MU_FX_GL_BLEND_FUNC, MU_FX_GL_DRAW_EFFECTS, MU_FX_GL_GEN_TEXTURES,
       MU_FX_GL_TEX_PARAMETER, MU_FX_GL_TEX_ENV, MU_FX_GL_BUILD_MIPMAPS, MU_FX_GL_TEX_IMAGE };
enum { MU_FX_GL_NEW_TEXTURE = 0xffffffffu };   /* stands for the name glGenTextures returned */
/* Writes the call sequence (at most 24 entries); MU_FX_GL_DRAW_EFFECTS marks
 * where the effect draws happen. Returns the number of calls. */
uint32_t mu_fx_manager_render_calls(const mu_fx_gl_state *before, uint32_t visible, mu_fx_gl_call out[24]);

/* Effect texture upload 0x00a90987(pixels, width, height, format, filter,
 * wrap, mipmap): nothing without pixels or with a zero size; otherwise a new
 * texture name, wrap S/T, GL_MODULATE, then either filters and glTexImage2D
 * or (mipmap) a *_MIPMAP_NEAREST minification filter and gluBuild2DMipmaps.
 * The effect base load requests GL_LINEAR, GL_REPEAT and no mipmaps
 * (0x00a7620a). Writes at most 12 calls; returns the count. */
uint32_t mu_fx_texture_upload_calls(int has_pixels, int32_t width, int32_t height, uint32_t format, uint32_t filter,
                                    uint32_t wrap, int mipmap, mu_fx_gl_call out[12]);

/* ---- matrix helpers used above (exposed for tests) ---- */
void mu_fx_rotation_matrix(float out[16], float rz, float ry, float rx);       /* 0x00cef49d */
int mu_fx_affine_inverse(float out[16], const float m[16]);                    /* 0x00cee8cd, 0: singular */
float mu_fx_random_range(mu_fx_rng *rng, float lo, float hi);                  /* 0x00a7ebb0 */

#ifdef __cplusplus
}
#endif

#endif
