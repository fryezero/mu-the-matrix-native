#ifndef MU_PARTICLES_H
#define MU_PARTICLES_H

/* The client's legacy particle and sprite system, the blob shadow and the
 * bone-position helpers that objects, ambient creatures and characters use to
 * place them (NATIVE-PARTICLE-001, docs/research/client-particles.md).
 *
 *   - particles: CreateParticle 0x0168fafd (wrapper) -> 0x015ae7b0 (core) into
 *     a std::list of shared 0xb4-byte records (list object 0x0a3a9adc),
 *     MoveParticles 0x01616c80 once per logic step, RenderParticles
 *     0x0159123f in the sprite section of the render scene;
 *   - sprites: CreateSprite 0x01692eb7 -> 0x01692508 into 1000 OBJECT records
 *     at 0x0a3da070, drawn and killed by RenderSprites 0x0169270e every frame;
 *   - RenderSprite 0x0184c39c, the camera-facing quad both draw with;
 *   - RenderBodyShadow 0x012bc07a, the blob shadow (the posed mesh flattened
 *     onto the terrain);
 *   - the bone helpers: the bone-matrix lookup by name 0x0129f18a and
 *     TransformPosition 0x012b6ef1;
 *   - the object visuals that call them: RenderObjectVisual 0x017f9758
 *     (Lorencia) and the Tormenta Island handler's slot 0x34 0x00e4ef4b.
 *
 * Authored C ports. Every client operation is binary32 SSE: build with
 * -ffp-contract=off. The functions say whether they were compared with the
 * client's instructions in Unicorn (scripts/validate_particles.py, "verified")
 * or are static readings. Client offsets are in the comments. Only the kinds
 * listed by mu_pt_kind_supported are reconstructed: the client's per-kind
 * switches cover several hundred bitmaps (the create routine alone spans
 * 0x015ae7b0..0x01615f39). */

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* LoadBitmap indices (Data\Effect\..., the loader 0x0185baac; rain02/rain03
 * are the world's World<n>\rain02.tga / rain03.tga, 0x01829e21). */
enum {
    MU_PT_BITMAP_RAIN_SPLASH = 0x771c,  /* rain02 */
    MU_PT_BITMAP_RAIN_RING = 0x771d,    /* rain03 */
    MU_PT_BITMAP_FLARE = 0x7ef7,        /* Effect\flare01.jpg */
    MU_PT_BITMAP_SPARK2 = 0x7f25,       /* Effect\Spark02.jpg */
    MU_PT_BITMAP_SPARK3 = 0x7f26,       /* Effect\Spark03.jpg */
    MU_PT_BITMAP_SHINY2 = 0x7f67,       /* Effect\Shiny02.jpg (sprites) */
    MU_PT_BITMAP_THUNDER = 0x7f2b,      /* Effect\Thunder01.jpg */
    MU_PT_BITMAP_FIRE = 0x7f3c,         /* Effect\Fire01.jpg (a strip of four cells) */
    MU_PT_BITMAP_SMOKE = 0x7f5a,        /* Effect\smoke01.jpg */
    MU_PT_BITMAP_CLOUDS = 0x7f89,       /* Effect\clouds.jpg (the login scene's mist, NATIVE-JOINT-001) */
    MU_PT_BITMAP_SHINY1 = 0x7f66,       /* Effect\Shiny01.jpg (Noria's lamp sparkles) */
    MU_PT_BITMAP_LIGHTNING2 = 0x7f37,   /* Effect\lightning2.jpg (sprites of Dungeon, Devias, Noria) */
    MU_PT_BITMAP_WATERFALL1 = 0x801a,   /* Effect\WATERFALL1.jpg (the login scene's spray) */
    /* NATIVE-CHARSEL-002: the character-select scene (World94) */
    MU_PT_BITMAP_WATERFALL2 = 0x801b,   /* Effect\WATERFALL2.jpg (the falls' spray, object type 0x38) */
    MU_PT_BITMAP_WATERFALL3 = 0x801c,   /* Effect\WATERFALL3.jpg (the falls' mist, object type 0x37) */
    MU_PT_BITMAP_FANTA_B = 0x8017,      /* Effect\fantaB.jpg (the lamps' sparks, object type 0x49) */
    MU_PT_BITMAP_CHASELLIGHT = 0x8022,  /* Logo\chasellight.jpg (the selection light, RenderCharacterScene) */
    MU_PT_BITMAP_IMPACK03 = 0x7b78,     /* Effect\Impack03.jpg (drawn by 0x8022 subtype 5) */
    MU_PT_BITMAP_SPARK04 = 0x8155,      /* Effect\Spark04.jpg (sprites of object type 0x1f) */
    MU_PT_BITMAP_MAGIC_GROUND13 = 0x8145, /* Effect\magic_ground1_3.jpg (sprites of object type 0x49) */
    /* NATIVE-HELPERS-002: the helpers' kinds */
    MU_PT_BITMAP_SMOKE2 = 0x7f5b,       /* Effect\smoke02.tga (the mounts' dust outside world 2) */
    MU_PT_BITMAP_DROP = 0x7fcd          /* Object8\drop01.jpg (Atlans; the Dark Horse's dust there), a 3x3 sheet */
};

/* GL state wrappers the render routines call, by client address. */
enum {
    MU_PT_STATE_ADD = 0x0184aa2b,       /* EnableAlphaBlend: blend (ONE, ONE), depth mask off, alpha test off */
    MU_PT_STATE_ALPHA = 0x0184a990,     /* EnableAlphaTest(arg): (SRC_ALPHA, ONE_MINUS_SRC_ALPHA), alpha test on */
    MU_PT_STATE_SUBTRACT = 0x0184aab7,  /* EnableAlphaBlendMinus: (ZERO, ONE_MINUS_SRC_COLOR), depth mask off */
    MU_PT_STATE_ADD_INVERSE = 0x0184ab46, /* (ONE_MINUS_SRC_COLOR, ONE), depth mask off */
    MU_PT_STATE_OPAQUE = 0x0184a7f3,    /* DisableAlphaBlend: blend off, depth mask on (sprite blend 4: then EnableAlphaTest(1)) */
    MU_PT_STATE_6B7 = 0x0184a6b7,       /* extra wrappers of two kinds not ported (flare 6, 0x7f54 5) */
    MU_PT_STATE_6DA = 0x0184a6da,
    MU_PT_STATE_UNTEXTURED = 0x0184a783, /* DisableAlphaBlend-like (arg 0): depth mask on, alpha test off, texture off */
    MU_PT_STATE_DEPTH_OFF = 0x0184a763, /* cached glDepthMask(0) */
    MU_PT_STATE_DEPTH_ON = 0x0184a743,  /* cached glDepthMask(1) */
    MU_PT_STATE_BLEND = 0x0184abd5      /* (SRC_ALPHA, ONE_MINUS_SRC_ALPHA), depth mask off, alpha test off (smoke02) */
};

#define MU_PT_RECORD_BYTES 0xb4
#define MU_PT_NO_OWNER (-1)

/* One particle record, the fields the ported kinds use (client offsets). The
 * client allocates records from a pool (0x0a63f040) and reuses freed ones, so
 * a field CreateParticle does not write keeps an earlier particle's value. */
typedef struct mu_pt_particle {
    uint8_t live;            /* +0x08 */
    int32_t type;            /* +0x0c bitmap index, the kind */
    int32_t tex_type;        /* +0x10 bitmap drawn */
    int32_t subtype;         /* +0x14 */
    float scale;             /* +0x18 */
    float position[3];       /* +0x20 */
    float angle[3];          /* +0x2c */
    float light[3];          /* +0x38 */
    float alpha;             /* +0x44 (clouds: the light's factor; CreateParticle leaves it to the record) */
    int32_t lifetime;        /* +0x48 */
    int32_t owner;           /* +0x50 OBJECT pointer in the client; here an index, MU_PT_NO_OWNER for NULL */
    float owner_position[3]; /* +0x54 */
    float rotation;          /* +0x60 degrees */
    int32_t frame;           /* +0x64 sprite-strip cell */
    uint8_t moving;          /* +0x68 position += VectorRotate(velocity, AngleMatrix(angle)) each step */
    float gravity;           /* +0x6c */
    float velocity[3];       /* +0x70 */
    float field_7c;          /* +0x7c (clouds: a spin rate) */
    float start[3];          /* +0x88 (clouds: [1] a rotation offset, [2] the starting height) */
    float start_angle[3];    /* +0x94 */
    float time;              /* +0xac */
    int32_t arg8;            /* +0xb0 CreateParticle's last argument */
    int32_t initial_lifetime; /* +0x4c, the Shining Tail's fades */
    float initial_scale;     /* +0x1c */
    float field_80, field_84; /* +0x80 / +0x84, colour saved beside +0x7c */
} mu_pt_particle;

/* The client state the routines read. */
typedef struct mu_pt_host {
    void *context;
    int32_t (*rand)(void *context);                               /* rand() 0x01989721 */
    float (*terrain_height)(void *context, float x, float y);    /* RequestTerrainHeight 0x016cc9e2 */
    void (*owner_position)(void *context, int32_t owner, float out[3]); /* the owner OBJECT's +0x158 */
    int32_t world;           /* [0x01cf15fc] */
    float world_time;        /* [0x06fce370], ms */
    float frame_time;        /* [0x01cf103c], 0.1 in game */
    int32_t drop_divisor;    /* [0x0a39d768], the wrapper's drop rate in world 0x8b */
    int32_t scene_state;     /* SceneFlag [0x01d1df70] (0x009b0bc1): WATERFALL2 tests scene 5 (NATIVE-CHARSEL-002) */
    /* NATIVE-HELPERS-002: the bitmap record's height +0x208 through the getter 0x00ebbec8(bitmaps 0x0bdc5f00,
     * index) (smoke02 sits on the terrain by half its size; NULL: 0) */
    float (*bitmap_height)(void *context, int32_t bitmap);
} mu_pt_host;

/* 1 when CreateParticle, MoveParticles and RenderParticles are reconstructed
 * for the kind (type, subtype):
 *   Fire01 0x7f3c 0..6 and 17, smoke01 0x7f5a 0, 2 and 3, rain02/rain03
 *   0x771c/0x771d 0, Thunder01 0x7f2b 0, Spark02 0x7f25 0, Spark03 0x7f26 0
 *   and 1; NATIVE-JOINT-001: clouds 0x7f89 0x14 and WATERFALL1 0x801a 2 (the
 *   login scene's mist and spray), Shiny01 0x7f66 0 and 1 (Noria);
 *   NATIVE-CHARSEL-002: WATERFALL2 0x801b 2, WATERFALL3 0x801c 0xe, fantaB
 *   0x8017 0 and chasellight 0x8022 5 (the character-select scene);
 *   NATIVE-HELPERS-002: Spark02 0x7f25 1 (the angel's sparkles), smoke02
 *   0x7f5b 0 (the mounts' dust), drop01 0x7fcd 0 (the Dark Horse's dust in
 *   Atlans) and Spark03 0x7f26 0xf (Fenrir's sparks). */
int mu_pt_kind_supported(int32_t type, int32_t subtype);

/* The wrapper 0x0168fafd's drop rule (verified): in world 0x8b only, r =
 * rand() % max(divisor, 1), forced to 0 for the kinds of the filter
 * 0x010954d4; the particle is created when r == 0. Other worlds call no
 * rand() and always create. Returns 1 to create. */
int mu_pt_wrapper_keeps(const mu_pt_host *host, int32_t type, int32_t subtype);

/* CreateParticle's core 0x015ae7b0 on a fresh record (verified for the
 * supported kinds): the common initialisation (live, kinds, position = start,
 * angle = start angle, light, scale, gravity 0, LifeTime 2, frame 0, owner,
 * owner position = the owner's position with z = RequestTerrainHeight, or 0,
 * rotation 0, moving 1, time 0, velocity 0, argument 8), then the kind's case.
 * Returns 1 for a supported kind, 0 otherwise (the record then holds only the
 * common part). */
int mu_pt_create_record(mu_pt_particle *p, const mu_pt_host *host, int32_t type, const float position[3],
                        const float angle[3], const float light[3], int32_t subtype, float scale, int32_t owner,
                        int32_t arg8);

/* One record of MoveParticles 0x01616c80 (verified): returns 0 when the loop
 * head erases it (LifeTime <= 0 or not live); otherwise the motion flag's
 * MovePosition, the owner position refresh, the kind's case, LifeTime - 1 and
 * time += frame time, and returns 1 (2 when the kind is not reconstructed: the
 * common parts ran, the kind's case did not). */
int mu_pt_move_record(mu_pt_particle *p, const mu_pt_host *host);

/* The bitmap record fields RenderParticles and RenderSprites read (+0x204
 * width, +0x208 height, +0x214 component count). */
typedef struct mu_pt_bitmap {
    float width, height;
    int8_t components;
} mu_pt_bitmap;

/* RenderSprite 0x0184c39c(bitmap, position, width, height, light, rotation,
 * u, v, u width, v height, axes). */
typedef struct mu_pt_sprite_call {
    int32_t bitmap;
    float position[3];
    float width, height;
    float light[3];
    float rotation;
    float u, v, uw, vh;
    int32_t axes;
} mu_pt_sprite_call;

/* What RenderParticles does for one live record: up to four GL state wrapper
 * calls (MU_PT_STATE_*, with argument) and at most one RenderSprite. */
typedef struct mu_pt_render_call {
    int32_t state_count;
    int32_t state[4];
    int32_t state_arg[4];
    int32_t sprites;
    mu_pt_sprite_call sprite;
} mu_pt_render_call;

/* RenderParticles' per-record part (verified): mode 1 skips records above
 * z 350, mode 2 records at or below z 300; then the blend chosen by the
 * bitmap's component count, the kind's extra state and its RenderSprite.
 * Returns 1 when the record was drawn, 0 when skipped, 2 for a kind that is
 * not reconstructed (nothing filled). */
int mu_pt_render_record(const mu_pt_particle *p, const mu_pt_bitmap *bitmap, uint8_t mode, mu_pt_render_call *out);

/* ------------------------------------------------------------------------
 * The list (CreateParticle's push_back, MoveParticles, RenderParticles). */

typedef struct mu_pt_system {
    mu_pt_particle *records;  /* list order: creation order, erased records removed */
    int32_t count, capacity;
    float wind[2];            /* list object +0x08: random walk, rand() % 2001 - 1000 times 0.0006, within +-0.6 */
    float wind_sum[2];        /* list object +0x14: += wind, within +-1.7 */
    uint64_t created, dropped, unsupported, overflow;
} mu_pt_system;

/* capacity: records kept at most (the client's list is unbounded; a full
 * system counts overflow and drops the particle, a native choice). */
int mu_pt_system_init(mu_pt_system *s, int32_t capacity);
void mu_pt_system_free(mu_pt_system *s);
void mu_pt_system_clear(mu_pt_system *s);

/* CreateParticle 0x0168fafd: the wrapper's rule, the core, push_back.
 * Unsupported kinds are counted and not kept. Returns 1 when kept. */
int mu_pt_create(mu_pt_system *s, const mu_pt_host *host, int32_t type, const float position[3], const float angle[3],
                 const float light[3], int32_t subtype, float scale, int32_t owner, int32_t arg8);

/* MoveParticles' wind block 0x01616ca7..0x01616ec9 (verified): two rand()
 * calls. */
void mu_pt_wind_step(mu_pt_system *s, const mu_pt_host *host);

/* MoveParticles 0x01616c80: the wind block, then every record in list order
 * (erased at the head as mu_pt_move_record says). */
void mu_pt_move_all(mu_pt_system *s, const mu_pt_host *host);

/* ------------------------------------------------------------------------
 * GL stream of the draw routines (what the client sends to opengl32). */

enum {
    MU_PT_GL_TRIANGLES = 4,
    MU_PT_GL_QUADS = 7
};

typedef struct mu_pt_gl {
    void *context;
    void (*state)(void *context, int32_t wrapper, int32_t argument);  /* a MU_PT_STATE_* wrapper */
    void (*bind)(void *context, int32_t bitmap);                      /* BindTexture 0x0184acf6 */
    void (*begin)(void *context, int32_t mode);
    void (*end)(void *context);
    void (*color3)(void *context, const float rgb[3]);                /* glColor3fv */
    void (*color4)(void *context, float r, float g, float b, float a); /* glColor4f */
    void (*texcoord)(void *context, float u, float v);
    void (*vertex)(void *context, const float v[3]);                   /* glVertex3fv */
    void (*push_matrix)(void *context);
    void (*pop_matrix)(void *context);
} mu_pt_gl;

/* RenderSprite 0x0184c39c (verified): BindTexture; the centre
 * VectorTransform(position, CameraMatrix 0x0bdc5918) (camera: row-major 3x4);
 * half width/height; rotation 0: corners (x-w, y-h), (x+w, y-h), (x+w, y+h),
 * (x-w, y+h) at the eye z; otherwise (-w,-h,0), (w,-h,0), (w,h,0), (-w,h,0)
 * turned by AngleMatrix of the rotation on the axes of `axes` (bit 0 x,
 * bit 1 y, bit 2 z) plus the centre; glBegin(GL_QUADS), the colour
 * (glColor3fv(light) for 3-component bitmaps, glColor4f(l, 1) for 0x7f49 and
 * 0x7df3, else glColor4f(l, l0)), texcoords (u, v+vh), (u+uw, v+vh), (u+uw, v),
 * (u, v), glEnd. components is the bitmap record's +0x214. */
void mu_pt_render_sprite(const float camera[12], const mu_pt_sprite_call *sprite, int32_t components,
                         const mu_pt_gl *gl);
/* The four view-space corners and texcoords RenderSprite emits. */
void mu_pt_sprite_corners(const float camera[12], const mu_pt_sprite_call *sprite, float corners[4][3],
                          float uv[4][2]);

/* RenderParticles 0x0159123f(mode): every live record in list order; the
 * bitmap callback gives the bitmap record (NULL: the client would read
 * through a NULL record; the record is skipped and counted). Returns the
 * number of sprites drawn. */
typedef int (*mu_pt_bitmap_fn)(void *context, int32_t bitmap, mu_pt_bitmap *out);
int32_t mu_pt_render_all(const mu_pt_system *s, uint8_t mode, const float camera[12], mu_pt_bitmap_fn bitmap,
                         void *bitmap_context, const mu_pt_gl *gl);

/* ------------------------------------------------------------------------
 * Sprites (CreateSprite 0x01692eb7 -> 0x01692508, RenderSprites 0x0169270e). */

#define MU_PT_SPRITES 1000
#define MU_PT_SPRITE_BYTES 0x3d8

/* The OBJECT fields of a sprite record. */
typedef struct mu_pt_sprite {
    uint8_t live;            /* +0x00 (SetLive 0x0129f4a5) */
    uint8_t visible;         /* +0x0b set for every live sprite by 0x01692887 before the sprite pass */
    int32_t type;            /* +0x5c bitmap */
    int32_t blend;           /* +0x60 0 add, 1 subtract, 2 alpha test, 3 inverse add, 4 0x0184a7f3 + alpha test */
    int32_t axes;            /* +0x8c RenderSprite's rotation axes */
    float sheet[2];          /* +0x90/+0x94 cells across/down of an animated sheet (1, 1: none) */
    int32_t sheet_time;      /* +0x98 ms per cell */
    float scale;             /* +0xa0 */
    float alpha;             /* +0xd0 1 at creation, +-0.1 per draw by visibility, within 0.2..1 */
    float light[3];          /* +0xec */
    float start[3];          /* +0x110 */
    float position[3];       /* +0x158 */
    float rotation;          /* +0x16c (angle z of +0x164) */
    int32_t owner;           /* +0x34c OBJECT pointer in the client; an index here */
} mu_pt_sprite;

typedef struct mu_pt_sprites {
    mu_pt_sprite records[MU_PT_SPRITES];
    uint64_t created, full;
} mu_pt_sprites;

/* The sheet argument (CreateSprite's last, a pointer to {int across, int
 * down, float ms}; 0x00a0c1d0 builds the default {1, 1, 1.0}). */
typedef struct mu_pt_sheet {
    int32_t across, down;
    float ms;
} mu_pt_sheet;

/* CreateSprite's core 0x01692508 (verified): the first record that is not
 * live gets SetLive(1) and the fields; returns its index, or 0 when all 1000
 * are live (the client returns 0 then too, indistinguishable from slot 0). The
 * wrapper's two option checks (0x00aae6f9, 0x01692f29) are taken as passing. */
int32_t mu_pt_sprite_create(mu_pt_sprites *s, int32_t bitmap, const float position[3], float scale,
                            const float light[3], int32_t owner, float rotation, int32_t blend, int32_t axes,
                            const mu_pt_sheet *sheet);

/* 0x01692887: visible = 1 for every live sprite. */
void mu_pt_sprites_mark_visible(mu_pt_sprites *s);

/* RenderSprites 0x0169270e(mode) (verified): mode 1 skips sprites above z 350;
 * mode 2 kills those at or below z 300 without drawing; every live sprite
 * gets its blend wrapper and the per-sprite draw 0x01692931 (alpha ramp, size
 * = bitmap size * alpha * scale, RenderSprite with the sheet cell for the
 * world time); modes 0 and 2 then kill it (SetLive(0)). The kill cleanup
 * 0x009b0451 is not modelled (counted through `kill`, may be NULL). Returns
 * the number of RenderSprite calls. */
int32_t mu_pt_sprites_render(mu_pt_sprites *s, uint8_t mode, float world_time, const float camera[12],
                             mu_pt_bitmap_fn bitmap, void *bitmap_context, const mu_pt_gl *gl,
                             void (*kill)(void *context, int32_t index), void *kill_context);
/* The per-sprite part 0x01692931 alone, for one record (the alpha ramp is
 * written back); fills the RenderSprite arguments (bitmap 0x7fea: a fixed 64x64
 * cell of a 3x3 sheet chosen by the blend value). Returns 1. */
int mu_pt_sprite_draw_call(mu_pt_sprite *sprite, const mu_pt_bitmap *bitmap, float world_time,
                           mu_pt_sprite_call *out);

/* ------------------------------------------------------------------------
 * RenderBodyShadow 0x012bc07a (verified). */

/* One mesh of the posed model as the shadow reads it: triangle count (mesh
 * +0xa), texture (mesh +2), triangles of 0x24 bytes (corner count byte at +0,
 * i16 vertex indices at +2), the transformed vertices (VertexTransform
 * 0x078978a0 + mesh * 0x2bf20, 12 bytes each). */
typedef struct mu_pt_shadow_mesh {
    int16_t triangle_count;
    int16_t texture;
    const uint8_t *triangles;
    const float *vertices;
    int32_t vertex_count;     /* bound for the native host; the client reads unchecked */
} mu_pt_shadow_mesh;

/* RenderBodyShadow(hide texture, hide mesh, first mesh, end mesh, z offset)
 * on the model (mesh count = model +0x24, BodyOrigin = model +0x78): returns
 * at once without meshes; otherwise the state wrappers 0x0184a783(0)
 * (depth mask on, alpha test off, texture off) and 0x0184a763 (depth mask
 * off), glPushMatrix,
 * for meshes first (-1: 0) up to end (-1: count), except `hide mesh`, meshes
 * without triangles and meshes whose texture is `hide texture`: glBegin(
 * GL_TRIANGLES), every corner of every triangle (the corner count byte, 3 or
 * 4, as drawn: quads add a fourth vertex inside GL_TRIANGLES), projected away
 * from a light at (-2000, 4000) (-2500 in world 0x1e): v = vertex - origin;
 * x += (x + 2000) * z / (z - 4000); z = 5; v += origin; z = terrain height + 2
 * + offset (world 0x91: z = 10 + origin + offset, no terrain); glEnd per mesh;
 * glPopMatrix, 0x0184a743 (depth mask on). Returns the vertices sent. */
int32_t mu_pt_render_body_shadow(const mu_pt_shadow_mesh *meshes, int32_t mesh_count, const float origin[3],
                                 int32_t hide_texture, int32_t hide_mesh, int32_t first_mesh, int32_t end_mesh,
                                 int32_t z_offset, const mu_pt_host *host, const mu_pt_gl *gl);

/* ------------------------------------------------------------------------
 * Bone helpers. */

/* The bone record name test of 0x0129f18a: bones are 0x8c-byte records whose
 * name string starts the record; the lookup returns the first bone whose name
 * equals `name` (string compare 0x0096c6da), -1 when none. names[i] is bone i's
 * name (NUL-terminated). */
int32_t mu_pt_find_bone(const char *const *names, int32_t bone_count, const char *name);

/* TransformPosition 0x012b6ef1(matrix, in, out, translate) (verified): out =
 * VectorTransform(in, matrix) (3x4 row-major); with translate,
 * out = out * BodyScale (model +0x74) + BodyOrigin (model +0x78). A NULL
 * matrix leaves out unchanged. */
void mu_pt_transform_position(const float matrix[12], const float in[3], float out[3], int translate,
                              float body_scale, const float body_origin[3]);

/* ------------------------------------------------------------------------
 * Object visuals (RenderObjectVisual 0x017f9758, verified for Lorencia and
 * the Tormenta handler slot 0x34). They create particles, sprites, joints and
 * effects; the calls are reported in client order. */

enum {
    MU_PT_CALL_PARTICLE = 0x0168fafd,
    MU_PT_CALL_SPRITE = 0x01692eb7,
    MU_PT_CALL_JOINT = 0x0153b02c,
    MU_PT_CALL_EFFECT = 0x013c0eaa,
    MU_PT_CALL_BONE = 0x012b6ef1
};

typedef struct mu_pt_visual_object {
    int32_t index;           /* the object's identity for the owner arguments */
    int32_t type;            /* +0x5c */
    float position[3];       /* +0x158 */
    float angle[3];          /* +0x164 */
    float light[3];          /* +0xec */
    float scale;             /* +0xa0 */
    float blend_light;       /* +0xa8 BlendMeshLight (written) */
    float blend_v;           /* +0xb0 BlendMeshTexCoordV (written) */
} mu_pt_visual_object;

typedef struct mu_pt_visual_host {
    void *context;
    int32_t (*rand)(void *context);
    int (*has_model)(void *context, const mu_pt_visual_object *o);   /* the model getter (0: the routine returns) */
    /* the bone matrix lookup 0x0129f18a(name, 0) followed by TransformPosition(matrix, in, out, 0): */
    void (*bone_position)(void *context, const mu_pt_visual_object *o, const char *bone, const float in[3],
                          float out[3]);
    void (*particle)(void *context, int32_t type, const float position[3], const float angle[3], const float light[3],
                     int32_t subtype, float scale, int32_t owner);
    void (*sprite)(void *context, int32_t bitmap, const float position[3], float scale, const float light[3],
                   int32_t owner, float rotation, int32_t blend, int32_t axes);
    /* CreateJoint 0x0153b02c(bitmap, position, target position, angle, subtype, owner, scale, ...) as the
     * Tormenta handler calls it (position = target position = the object's, angle = the object's) */
    void (*joint)(void *context, int32_t bitmap, const float position[3], const float angle[3], int32_t subtype,
                  int32_t owner, float scale);
    /* CreateEffect 0x013c0eaa(type, position, angle, light, subtype, owner, ...) */
    void (*effect)(void *context, int32_t type, const float position[3], const float angle[3], const float light[3],
                   int32_t subtype, int32_t owner);
    int32_t world;
    float world_time;        /* [0x06fce370] */
    /* NATIVE-JOINT-001: TransformPosition(BoneTransform 0x06fce398 + 0x30 * bone, in, out, 0) (Dungeon) */
    void (*bone_index_position)(void *context, const mu_pt_visual_object *o, int32_t bone, const float in[3],
                                float out[3]);
} mu_pt_visual_host;

/* RenderObjectVisual 0x017f9758 for worlds 0 (Lorencia) and 0x8d (Tormenta
 * Island, through the world manager to slot 0x34; the event-world hooks in
 * front of it answer no there), and (NATIVE-JOINT-001) 1 (Dungeon), 2
 * (Devias) and 3 (Noria). Returns 1 when the world is one of these, 0
 * otherwise (nothing done). Every sprite of the three: blend 0, axes 4, the
 * object as owner; the bone points transform the zero vector unless said:
 *   - Dungeon 0x3d: lightning2 0x7f37 pairs (rotation r and -r, r =
 *     (int)(WorldTime * 0.1) % 360, light (0.4l, 0.8l, l)) at bones 15
 *     (scale 0.3), 19 (0.3) and 21 (1.5) by index;
 *   - Devias 0x64: a lightning2 pair (scale 2.5, light (l, l, l)) at bone
 *     Cylinder01 + (0, 0, 150);
 *   - Noria flares 0x7ef7 (rotation 0, light (0.4l, 0.7l, l)): type 9 Box01
 *     1.5, 0x23 Box04 1.5, 1 light03/light02/light01 0.5, 0x11
 *     Box03/Box08/Box11/Box14 1; type 0x27 a lightning2 pair at light01
 *     (light (0.4l, 0.8l, l)), white flares at light06, light04, light03,
 *     light05, light02, each with two Shiny01 particles (subtypes 0, 1) on
 *     rand % 32 == 0, and at light07 on rand % 8 == 0 eight spark joints
 *     0x7fd5 with Spark02 particles (angle (rand % 60 + 60, 140, rand % 30)).
 * In Lorencia:
 *   - every object with a model draws one rand(): l = (rand % 30 + 70) * 0.01;
 *   - Waterspout01 (0x69): BlendMeshLight 1, v scroll; on rand % 2 == 0 two
 *     smoke01 particles (subtype 0, the object's light and angle) at bone Box04
 *     + (rand%32-16, -20, rand%32-16) and Box03 + (rand%32-16, -80, rand%32-16);
 *   - MerchantAnimal01 (0x38): two flare01 sprites (scale 5l, light (0.6l,
 *     0.3l, 0.1l), additive, axes 4) at bones Box04 and Box10. The client
 *     transforms an uninitialised local there (a reading of stack residue);
 *     the C passes (0, 0, 0), the bone's origin.
 * Tormenta: types 2..5, 9 and 0xbf..0xc5 create a joint 0x7f7d (or, type 9,
 * the effect 0x40e) on rand % 50 == 0 (the light is set first). */
int mu_pt_object_visual(mu_pt_visual_object *o, const mu_pt_visual_host *host);

/* ------------------------------------------------------------------------
 * Client layouts (validator and tests): the modelled fields at their client
 * offsets; owner pointers are left to the caller. */
void mu_pt_particle_store(const mu_pt_particle *p, uint8_t out[MU_PT_RECORD_BYTES]);
void mu_pt_particle_load(mu_pt_particle *p, const uint8_t in[MU_PT_RECORD_BYTES]);
void mu_pt_particle_mask(uint8_t out[MU_PT_RECORD_BYTES]);
void mu_pt_sprite_store(const mu_pt_sprite *s, uint8_t out[MU_PT_SPRITE_BYTES]);
void mu_pt_sprite_load(mu_pt_sprite *s, const uint8_t in[MU_PT_SPRITE_BYTES]);
void mu_pt_sprite_mask(uint8_t out[MU_PT_SPRITE_BYTES]);

#ifdef __cplusplus
}
#endif

#endif
