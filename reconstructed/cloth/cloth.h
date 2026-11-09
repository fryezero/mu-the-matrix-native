#ifndef MU_CLOTH_H
#define MU_CLOTH_H
/* RENDER-ITEMS-CLOAK / CLOAK-002: the client's physics cloth (the capes of CreateCloth's wing cases).
 * docs/research/client-render-items.md parts 25 and 27.
 *
 * The client draws these capes as a CPhysicsCloth-style mass-spring grid, not as a mesh of the item model:
 *  - RenderCharacter 0x01363260 steps every cloth of its object (MoveCloth 0x01362f24, at 0x0136ab80) and, when its
 *    cloth flag [ebp-0x4d] is set, calls RenderCloth 0x01363098 (at 0x0136aba2) with its light [ebp-0xc8];
 *  - RenderCloth creates the wing's cloths once (CreateCloth 0x01357ccc: a switch on CHARACTER +0x21a4), steps them
 *    again on the creation frame and renders each one (virtual slot 8, 0x00fd8bc2);
 *  - the cloth object is 0xe8 bytes (vtable 0x01ab2780, constructor 0x00fd6c22), with a vertex array of 0x3c-byte
 *    records (+0x38), a spring array of 16-byte records (+0x40) and a list of collision spheres (+0xdc).
 *
 * Arithmetic contract: every value is binary32 and every expression keeps the client's SSE scalar order (build with
 * -ffp-contract=off). Sine/cosine are the CRT wrappers 0x009681bd / 0x009fa223 (float widened, double sin/cos,
 * rounded to float) through host libm, AngleMatrix 0x00cff32a through mu_angle_matrix (record-math), as the other
 * reconstructed units. The struct below is our layout; the offsets name the client field each one mirrors. */
#include <stdint.h>

enum {
    MU_CLOTH_MAX_VERTICES = 256,
    MU_CLOTH_MAX_SPRINGS = 1024,
    MU_CLOTH_MAX_SPHERES = 8,
    MU_CLOTH_WINGS_MAX = 3          /* cloths per wing (0x230e, 0x2318, 0x23ec, 0x2488, 0x239e make three) */
};

/* CPhysicsVertex (0x3c bytes, vtable 0x01ab2758). */
typedef struct mu_cloth_vertex {
    float force[3];                 /* +0x04 */
    float velocity[3];              /* +0x10 */
    float position[3];              /* +0x1c */
    uint8_t flags;                  /* +0x28: 1 = fixed (set by SetPosition 0x00fd5985 with a non-zero argument) */
    int32_t count;                  /* +0x2c: displacements gathered since the last apply */
    float delta[3];                 /* +0x30: their sum */
} mu_cloth_vertex;

/* Spring record (16 bytes, SetSpring 0x00fd8192). */
typedef struct mu_cloth_spring {
    int16_t v0, v1;                 /* +0x00, +0x02 */
    float min_length;               /* +0x04: 0.8 x the rest length */
    float length;                   /* +0x08: the rest length (distance at creation) */
    uint8_t flags;                  /* +0x0c: 1 constrain, 2 force, 4 stretch */
} mu_cloth_spring;

/* Collision sphere (0x24 bytes, vtable 0x01ab2770; AddCollisionSphere 0x00fd9ded). */
typedef struct mu_cloth_sphere {
    float offset[3];                /* +0x04: local offset on the bone (x, y, z as passed) */
    int32_t bone;                   /* +0x10 */
    float center[3];                /* +0x14: world centre, refreshed every step */
    float radius;                   /* +0x20 */
} mu_cloth_sphere;

typedef struct mu_cloth {
    int32_t owner;                  /* +0x04: the OBJECT (0 = none; Move refuses without one) */
    int32_t bone;                   /* +0x08: the OBJECT bone the top row hangs from */
    int32_t texture_front;          /* +0x0c: bitmap index */
    int32_t texture_back;           /* +0x10 */
    uint32_t type;                  /* +0x14: flags (or-ed in by Create) */
    float origin[3];                /* +0x18 */
    float width, height;            /* +0x24, +0x28 */
    int32_t columns, rows;          /* +0x2c, +0x30 */
    int32_t vertex_count;           /* +0x34 */
    int32_t spring_count;           /* +0x3c */
    uint8_t custom;                 /* +0x44: 1 = the angle-matrix Create variant (slot 1 0x00fd77dc) */
    float matrix[12];               /* +0x48: its AngleMatrix (SetFixed slot 5 0x00fd7d2a rotates the top row by it) */
    float alpha;                    /* +0x78 */
    uint8_t alpha_from_object;      /* +0x7c: Render copies the OBJECT alpha into +0x78 */
    float uv_scale[2];              /* +0x80, +0x84 (setter 0x013bb4a2) */
    float uv_offset[2];             /* +0x88, +0x8c (setter 0x013bb477) */
    float wind;                     /* +0x90: this step's wind */
    uint8_t wind_range, wind_base;  /* +0x94, +0x95 */
    float push[2];                  /* +0x98, +0x9c: sideways force (setter 0x013bb44c) */
    int32_t glow_texture;           /* +0xa0: -1 = no glow pass (SetGlow 0x00fd9f50, pass 0x00fd9663) */
    float glow[3];                  /* +0xa4 pulse speed, +0xa8 minimum, +0xac maximum brightness */
    int32_t mesh;                   /* +0xc0: -1 = no mesh passes */
    int32_t mesh_level;             /* +0xc4 */
    float mesh_color[3];            /* +0xc8 */
    int32_t glow2_texture;          /* +0xb0: the level >= 9 glow */
    float glow2[3];                 /* +0xb4, +0xb8, +0xbc */
    float step[2];                  /* +0xd4, +0xd8: width / (columns - 1), height / (rows - 1) */
    int32_t sphere_count;           /* the +0xdc list, in insertion order */
    mu_cloth_sphere spheres[MU_CLOTH_MAX_SPHERES];
    mu_cloth_vertex vertices[MU_CLOTH_MAX_VERTICES];
    mu_cloth_spring springs[MU_CLOTH_MAX_SPRINGS];
} mu_cloth;

/* What the cloth reads from its OBJECT and the OBJECT's model (Models[OBJECT +0x5c]). */
typedef struct mu_cloth_host {
    const float *bones;             /* OBJECT +0x318: bone matrices, 12 floats (3x4 row-major) each; NULL = none */
    int32_t bone_count;             /* the model's bone count (BMD +0x22), the range test of 0x0129f12c */
    int32_t has_model;              /* 1 = the model lookup 0x00eaa8cf finds Models[OBJECT +0x5c] */
    float body_scale;               /* model +0x74 (TransformPosition 0x012b6ef1) */
    float body_origin[3];           /* model +0x78 */
    float angles[3];                /* OBJECT +0x164 */
    float alpha;                    /* OBJECT +0xdc */
    /* SetFixed (slots 4 and 5) transforms the top row with Models[OBJECT +0x60] when that sub-type is 0x5bc or 0x5bd,
     * else with Models[OBJECT +0x5c] (the fields above). */
    int32_t subtype;                /* OBJECT +0x60 */
    int32_t sub_has_model;          /* the lookup finds Models[subtype] */
    float sub_body_scale;           /* its +0x74 */
    float sub_body_origin[3];       /* its +0x78 */
} mu_cloth_host;

/* Client globals the cloth reads or writes. */
typedef struct mu_cloth_globals {
    float time;                     /* 0x06fce370 */
    int32_t logic_steps;            /* 0x0bdc5eb0 (the frame driver's logic-step counter) */
    int32_t world;                  /* 0x01cf15fc */
    float wind;                     /* 0x01ec981c (the physics manager's wind, MoveWind 0x00fdad7b) */
    float wind_vector[3];           /* 0x01ec9820 (x, y written by every step; z is never written) */
    float gravity[3];               /* 0x01cf0eb0 = 9.8, 0x01cf0eb4 = 0.0025, 0x01cf0eb8 = 400 (captured section) */
    uint32_t rand_seed;             /* rand() 0x01989721 (MSVC): the wind walk; types 0x200 / 0x8 / world 0x37 */
    int32_t quality;               /* graphics options +0xc: cloth level passes, native 5 */
    uint8_t stretch_hold;           /* the singleton test 0x00aae6f9 in the stretch limit (0 = the step stops) */
} mu_cloth_globals;

void mu_cloth_default_globals(mu_cloth_globals *g);

/* The GL calls of Render 0x00fd8bc2, in order. */
enum {
    MU_CLOTH_STATE_BLEND_OFF = 1,   /* DisableAlphaBlend 0x0184a7f3 (type & 0x3000 == 0) */
    MU_CLOTH_STATE_ALPHA_TEST = 2,  /* EnableAlphaTest(1) 0x0184a990 (0x1000) */
    MU_CLOTH_STATE_BLEND_ONE = 3    /* EnableAlphaBlend 0x0184aa2b (0x2000; the glow pass) */
};
typedef struct mu_cloth_sink {
    void *context;
    void (*state)(void *context, int32_t wrapper);
    void (*bind)(void *context, int32_t bitmap);                 /* BindTexture 0x0184acf6 */
    void (*color4)(void *context, float r, float g, float b, float a);
    void (*begin)(void *context, uint32_t mode);                 /* glBegin(GL_QUADS = 7) */
    void (*texcoord)(void *context, float s, float t);
    void (*vertex)(void *context, float x, float y, float z);    /* glVertex3f */
    void (*end)(void *context);
    /* CreateSprite(0x7ef7, position, scale, light, NULL, 0, 0, 4), queued for RenderSprites. */
    void (*sprite)(void *context, int32_t bitmap, const float position[3], float scale, const float light[3]);
} mu_cloth_sink;

enum { MU_CLOTH_OK = 1, MU_CLOTH_FAILED = 0, MU_CLOTH_UNSUPPORTED = -1 };

/* The constructor 0x00fd6c22 and its defaults 0x00fd6ca4 (empty sphere list). */
void mu_cloth_init(mu_cloth *c);
/* Create (virtual slot 2, 0x00fd6e60), argument order as the client's. 1 = created, 0 = the client's failure
 * returns (no bone matrix, no model; the grid keeps what was written), -1 = a grid larger than our arrays or the
 * custom variant. */
int mu_cloth_create(mu_cloth *c, const mu_cloth_host *h, int32_t bone, float x, float y, float z, int32_t columns,
                    int32_t rows, float width, float height, int32_t texture_front, int32_t texture_back,
                    uint32_t type);
/* The angle-matrix variant (virtual slot 1, 0x00fd77dc): Create, then on success AngleMatrix(angles) into +0x48 and
 * custom = 1 (later SetFixed calls take slot 5). */
int mu_cloth_create_angles(mu_cloth *c, const mu_cloth_host *h, int32_t bone, float x, float y, float z,
                           const float angles[3], int32_t columns, int32_t rows, float width, float height,
                           int32_t texture_front, int32_t texture_back, uint32_t type);
/* SetGlow 0x00fd9f50(texture, speed, minimum, maximum). */
void mu_cloth_set_glow(mu_cloth *c, int32_t texture, float speed, float minimum, float maximum);
/* AddCollisionSphere 0x00fd9ded(x, y, z, radius, bone). -1 when the list is full. */
int mu_cloth_add_sphere(mu_cloth *c, float x, float y, float z, float radius, int32_t bone);
/* Move2 0x00fd821e(time, count): count steps 0x00fd825f. 0 when a step refuses (no owner). */
int mu_cloth_move2(mu_cloth *c, const mu_cloth_host *h, mu_cloth_globals *g, float time, int32_t count);
/* Render (virtual slot 8, 0x00fd8bc2(light, 0)); light may be NULL (white): the front face, the back face, then the
 * glow and mesh passes, with flare sprites queued through sink->sprite. */
int mu_cloth_render(mu_cloth *c, const mu_cloth_host *h, const mu_cloth_globals *g, const float *light,
                    const mu_cloth_sink *sink);

/* MoveWind (the wind walk of the physics manager's step 0x00fdad7b, called five times per logic step by the frame
 * driver 0x01851d39 at 0x01851f01): wind += (rand() % 200 - 100) * 0.001, clamped to [-0.2, 1]. */
void mu_cloth_wind_step(mu_cloth_globals *g);

/* ---- the character side (RenderCharacter's cloth calls) ---- */

/* What CreateCloth 0x01357ccc reads besides the OBJECT. */
typedef struct mu_cloth_wing_in {
    int16_t wing_type;              /* CHARACTER +0x21a4 (-1 = none) */
    int8_t wing_level;              /* CHARACTER +0x21a6 (the level glows of 0x2396 (>= 9) and 0x239e.. (>= 11)) */
    uint8_t arg4;                   /* RenderCharacter's [ebp-0x128]: 1 = the robe cloth whatever the wing */
    int32_t scene;                  /* SceneFlag 0x01d1df70 (5 = character select: 0x23ec's scale / 1.2, else / 0.9) */
    float object_scale;             /* OBJECT +0xa0 (CHARACTER +0x32f4) */
} mu_cloth_wing_in;
/* How many cloths CreateCloth makes (0 = none: no case). */
int mu_cloth_wing_cloths(const mu_cloth_wing_in *in);
/* CreateCloth's case: out[0..n-1] constructed, created and given their spheres and setters. Returns n (the
 * client's bool is n > 0). */
int mu_cloth_wing_create(mu_cloth out[MU_CLOTH_WINGS_MAX], const mu_cloth_wing_in *in, const mu_cloth_host *h);

/* The inputs of RenderCharacter's cloth block 0x01366edf..0x01367530 that this unit reads. */
typedef struct mu_cloth_gate_in {
    uint8_t class_byte;             /* CHARACTER +0x12 */
    uint8_t c_0e;                   /* CHARACTER +0x0e */
    uint8_t pk;                     /* CHARACTER +0x1f (6 = the red light) */
    int16_t wing_type;              /* CHARACTER +0x21a4 */
    int16_t class_index;            /* CHARACTER +0x146 */
    int32_t object_type;            /* the passed OBJECT's +0x5c */
    int32_t own_type;               /* CHARACTER +0x32b0 (its own OBJECT's type) */
    int32_t world;                  /* 0x01cf15fc */
} mu_cloth_gate_in;
typedef struct mu_cloth_gate_out {
    uint8_t render;                 /* [ebp-0x4d]: RenderCloth is called */
    uint8_t arg4;                   /* [ebp-0x128] (always 0 here: the guild / duel branches need event flags) */
    float light[3];                 /* [ebp-0xc8] */
} mu_cloth_gate_out;
/* The block with the guild-war flags 0x06fca13d / 0x06fca13f clear, no duel (0x01d1e028) and no hiding buff
 * (0x009c104e(c, 2, 1)): the native world has none of them. */
void mu_cloth_gate(const mu_cloth_gate_in *in, mu_cloth_gate_out *out);
/* RenderCloth's draw tests 0x01362e1d and 0x01362e87 with no buff 0x12 (0x01295ade): the sub-types (CHARACTER
 * +0x32b4 = OBJECT +0x60) 0x431 / 0x432 hide; the actions (OBJECT +0x2a and +0x2c both 0xe4) hide; 0x009a0989 hides
 * a class of skin 3 under the sub-types 0x3e9, 0x3ed, 0x429, 0x541, 0x552, 0x5ba..0x5bf, 0x5c4, 0x5c5, 0xa5e; the
 * class index 0x271 / 0x272 hides. */
int mu_cloth_draw_allowed(uint8_t class_byte, int32_t subtype, uint16_t action, uint16_t prior_action,
                          int16_t class_index);

/* CreateClothArmour 0x0135ea29, the second OBJECT list (+0x48, count +0x3e).
 * Armour is CHARACTER slot 2 (+0x9bc), pants slot 3 (+0xdb8). Fixture equipment only. */
typedef struct mu_cloth_armour_in {
    uint8_t class_byte, enabled;    /* OBJECT +0x3b must be 1 */
    int16_t armour_type, pants_type, wing_type, class_index;
    int8_t pants_level;
    float mesh_color[3];            /* EnchantEffect lookup, host supplies table/default colour */
} mu_cloth_armour_in;
int mu_cloth_armour_cloths(const mu_cloth_armour_in *in);
int mu_cloth_armour_create(mu_cloth out[MU_CLOTH_WINGS_MAX], const mu_cloth_armour_in *in,
                           const mu_cloth_host *h);
/* Existing-list branch, before RenderCloth's second MoveCloth. Returns that call's boolean. */
int mu_cloth_armour_update(mu_cloth out[MU_CLOTH_WINGS_MAX], int count, const mu_cloth_armour_in *in,
                           const mu_cloth_host *h);
/* Mesh index for the colour lookup (-1 when none); 0x1d99 uses 1, 0x1d9e uses 2. */
int mu_cloth_armour_color_mesh(int16_t pants_type);
/* RenderCloth's armour-list test 0x01362edc, no buff 0x12. */
int mu_cloth_armour_draw_allowed(uint8_t class_byte, int32_t subtype);
/* NPC/monster second-list constructor 0x01362755, called after armour creation declines.
 * The caller owns the existing-list guard. Counts remain allocated even if Create lacks a model/bones. */
/* Model/scale overrides from the creation processors, -1 means use the generic class table. */
int mu_cloth_npc_model(int16_t class_index, int32_t world, float *scale);
int mu_cloth_npc_cloths(int16_t class_index);
int mu_cloth_npc_create(mu_cloth out[MU_CLOTH_WINGS_MAX], int16_t class_index, const mu_cloth_host *h);
#endif
