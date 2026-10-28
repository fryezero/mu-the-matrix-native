/* The client's ambient world life and weather (NATIVE-ENV-001).
 *
 * Client routines (restored text, main.exe SHA-256 3cf91f3c...b5527a); names
 * are investigator choices, see docs/research/client-environment.md:
 *
 *   MoveBoids        0x00c9eb04  40 ambient flyers at 0x0bdb71f0 (0x3d8-byte objects):
 *                                birds (Lorencia), bats (Dungeon, Lost Tower), butterflies
 *                                (Noria), crows (Blood Castle), fish shoals (Atlans)
 *   MoveBird         0x00ca2dcb  landing/take-off state machine (birds, crows)
 *   MoveButterfly    0x00ca2ba7  random vertical wander between ground+50 and ground+300
 *   MoveBat          0x00ca2acd  height = ground + 350 - 150|sin(phase)|
 *   MoveBoidFlight   0x00ca3e2f  forward step, despawn at 1500 units and 1/512 per step
 *   MoveBoidFlock    0x012af9a9  steering toward neighbours within 400 units
 *   CreateAngle      0x012aeced  integer heading (x1, y1) -> (x2, y2)
 *   TurnAngle        0x012aef0c  integer turn toward a heading by a step
 *   AtlansShoal      0x00ca27b1  Atlans/abyss shoal creation (Fish02/Fish03)
 *   MoveFishs        0x00ca05b3  10 swimmers at 0x0bdc0bb0: fish (Lorencia water tiles),
 *                                rats (Dungeon, Lost Tower), Atlans fish
 *   FadeAlpha        0x012af883  alpha toward its target
 *   ObjectInit       0x0129eb81  object reset (only the fields modelled here)
 *   RenderBoids      0x00c9fd8d  per pass (o+0xa == pass): frustum test, body, glow
 *                                sprite, blob shadow
 *   RenderFishs      0x00ca1cf7
 *   MoveLeaves       0x01537a43  200 weather particles (0xb4 bytes) at 0x0a3a0e28,
 *                                count per world, rain level, wind
 *   CreateLeaf...    0x0153959d (Lorencia), 0x0153939c (Devias snow), 0x01539ace (Noria,
 *                                Atlans), 0x015398de (Icarus rain), Tormenta rain 0x00e5377c
 *                                (world class vtable 0x01aabd10 slot 0x64) -> 0x00e53c14
 *   MoveLeaf...      0x0153a634 (Lorencia, Icarus), 0x0153ac06 (default), Tormenta
 *                                0x00e538ec (slot 0x68)
 *   RenderLeaves     0x01538145  plane quads 0x0184c121 or billboards 0x0184c39c
 *
 * Every entry point takes the client state it reads as plain inputs (the
 * hero, the camera, the terrain attribute and layer-1 grids, the world time)
 * and calls the host for the engine services the client calls: rand()
 * (MSVC LCG, kept here), RequestTerrainHeight, SND_Play, SetAction, the
 * model's animation tick, CreateParticle, and the render primitives. Float
 * arithmetic follows the client's binary32 order; sin/cos/atan/sqrt are host
 * libm in binary64 rounded once (the client's CRT entries agree in binary32,
 * see client-rotation.md).
 */
#ifndef MU_ENV_H
#define MU_ENV_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    MU_ENV_BOIDS = 40,          /* 0x0bdb71f0 */
    MU_ENV_FISHS = 10,          /* 0x0bdc0bb0 */
    MU_ENV_LEAVES = 200,        /* 0x0a3a0e28 */
    MU_ENV_OBJECT_BYTES = 0x3d8,
    MU_ENV_LEAF_BYTES = 0xb4
};

/* Model indices (object +0x5c), loaded by the object model pass 0x018392db. */
enum {
    MU_ENV_MODEL_BIRD = 0x192,       /* Data/Object1/Bird01.bmd (world 0) */
    MU_ENV_MODEL_BUTTERFLY = 0x193,  /* Data/Object1/Butterfly01.bmd (world 3) */
    MU_ENV_MODEL_BAT = 0x194,        /* Data/Object2/Bat01.bmd (worlds 1, 4) */
    MU_ENV_MODEL_RAT = 0x196,        /* Data/Object2/Rat01.bmd (worlds 1, 4) */
    MU_ENV_MODEL_BUG = 0x197,        /* Data/Object7/Bug01.bmd (world 6) */
    MU_ENV_MODEL_FISH = 0x198,       /* Data/Object1/Fish01.bmd (world 0) */
    MU_ENV_MODEL_ATLANS_FISH = 0x199,/* 0x199..0x1a0: Data/Object8/Fish02..09.bmd (world 7) */
    MU_ENV_MODEL_CROW = 0x1a2,       /* Data/Object12/Crow01.bmd (Blood Castle) */
    MU_ENV_MODEL_ELBELAND = 0x1a4
};

/* Bitmap indices of the weather textures (0x01829e21 loads them per world
 * from Data/World<n+1>/). */
enum {
    MU_ENV_BITMAP_LEAF1 = 0x771f,    /* leaf01 (Lorencia leaf, Devias snow, Noria leaf, Atlans bubble) */
    MU_ENV_BITMAP_LEAF2 = 0x7720,    /* leaf02 */
    MU_ENV_BITMAP_RAIN = 0x7721,     /* rain01 (World1/rain011 in world 0x22) */
    MU_ENV_BITMAP_RAIN_SPLASH = 0x771c, /* rain02 */
    MU_ENV_BITMAP_RAIN_RING = 0x771d    /* rain03 */
};

/* The fields of the client's 0x3d8-byte OBJECT that these routines read or
 * write, named by offset. */
typedef struct mu_env_object {
    uint8_t live;            /* +0x00 (getter 0x0095f977, setter 0x0129f4a5) */
    uint8_t flag_01;         /* +0x01 */
    uint8_t flag_05;         /* +0x05 */
    uint8_t pass;            /* +0x0a RenderBoids pass (0 before, 1 after the characters) */
    uint8_t visible;         /* +0x0b */
    uint8_t alpha_enable;    /* +0x0c FadeAlpha mode */
    uint8_t ai;              /* +0x29 bird state */
    uint16_t action;         /* +0x2a */
    uint16_t prior_action;   /* +0x2c */
    int32_t type;            /* +0x5c */
    int32_t subtype;         /* +0x60 */
    int32_t field_68;        /* +0x68 */
    int32_t timer;           /* +0x6c */
    int32_t field_74;        /* +0x74 */
    float velocity;          /* +0xa0 */
    float field_a8;          /* +0xa8 */
    float phase;             /* +0xb4 */
    float scale;             /* +0xbc */
    float field_c4;          /* +0xc4 */
    float gravity;           /* +0xc8 turn step of the flock */
    float frame;             /* +0xd0 */
    float prior_frame;       /* +0xd4 */
    float alpha_target;      /* +0xd8 */
    float alpha;             /* +0xdc */
    float alpha_speed;       /* +0xe0 */
    float light[3];          /* +0xec */
    float direction[3];      /* +0xf8 */
    float position[3];       /* +0x158 */
    float angle[3];          /* +0x164 */
    float field_170[3];      /* +0x170 */
    float start[3];          /* +0x188 */
    float matrix[3][4];      /* +0x2e8 */
} mu_env_object;

/* The fields of the client's 0xb4-byte weather particle. */
typedef struct mu_env_leaf {
    uint8_t live;            /* +0x08 */
    int32_t texture;         /* +0x0c */
    float scale;             /* +0x18 */
    float position[3];       /* +0x20 */
    float angle[3];          /* +0x2c */
    float light[3];          /* +0x38 */
    float alpha;             /* +0x44 */
    float rotation;          /* +0x60 */
    float velocity[3];       /* +0x70 */
    float turn[3];           /* +0x7c */
    float start[3];          /* +0x88 */
} mu_env_leaf;

typedef struct mu_env_host {
    void *context;
    /* RequestTerrainHeight 0x016cc9e2 */
    float (*terrain_height)(void *context, float x, float y);
    /* SND_Play 0x00a6ac96(id, object, loop); object NULL for 0 */
    void (*play_sound)(void *context, int32_t id, const mu_env_object *object, int32_t loop);
    /* SetAction 0x012affa4(object, action) */
    void (*set_action)(void *context, mu_env_object *object, int32_t action);
    /* the model's current action = object action, then the tick 0x012b4dd3
     * (frame, prior frame, prior action, speed, position, angle) */
    void (*animate)(void *context, mu_env_object *object, float speed);
    /* CreateParticle 0x0168fafd(bitmap, position, angle, light, subtype, scale, owner 0, 0) */
    void (*create_particle)(void *context, int32_t bitmap, const float position[3], const float angle[3],
                            const float light[3], int32_t subtype, float scale);
    /* the cleanup of SetLive(object, 0): 0x009b0451 (optional) */
    void (*kill)(void *context, mu_env_object *object);
    /* ObjectInit 0x0129eb81 was called (optional) */
    void (*init)(void *context, mu_env_object *object);
    /* the model getter 0x00966cc4 -> 0x00eaa8cf returns a model for the
     * index (NULL ends MoveBoids/MoveFishs); NULL callback = always present */
    int (*has_model)(void *context, int32_t model);
    /* the effect factory 0x0153b02c(bitmap, position, position, angle, ..., owner, scale, ...)
     * of the fish creators in worlds 8, 0x21, 0x22, 0x86 and Kalima (optional) */
    void (*create_effect)(void *context, int32_t bitmap, const mu_env_object *owner, float scale, int32_t argument);
    void (*open_monster)(void *context, int32_t model); /* 0x0180b0f4, asset request */
} mu_env_host;

/* Client state the routines read. */
typedef struct mu_env_inputs {
    int32_t world;                 /* 0x01cf15fc */
    float hero_position[3];        /* hero +0x33ac */
    int32_t hero_tile[2];          /* hero +0x180 / +0x184 */
    uint16_t hero_action;          /* hero object (+0x3254) +0x2a, i.e. hero +0x327e */
    uint8_t hero_safe_zone;        /* hero +4 (0x0095fb27) */
    float camera_position[3];      /* CameraPosition 0x0bdc5ab4 */
    float world_time;              /* 0x06fce370 */
    float frame_time;              /* [0x01cf103c] (0.1) */
    int32_t event_state;           /* 0x06fc9eb4 (world 0x22) */
    int32_t login_scene;           /* 0x01ec3254; only 0 (in-world) is ported */
    const uint16_t *attributes;    /* TerrainWall 0x0b795420, 256x256 */
    const uint8_t *layer1;         /* TerrainMappingLayer1 0x0b735420, 256x256 */
    int32_t ambient_clock; /* 0x0bdc5eb0, millisecond clock */
} mu_env_inputs;

/* World object of Tormenta Island (class vtable 0x01aabd10, constructor
 * 0x00e4be37): +6 weather on (1), +0x14 rain maximum (10), +0x18 rain level. */
typedef struct mu_env_world_object {
    uint8_t weather;               /* +0x06 */
    float rain_max;                /* +0x14 */
    float rain;                    /* +0x18 */
} mu_env_world_object;

typedef struct mu_env {
    uint32_t rand_state;           /* the CRT rand() state, shared with the rest of the client */
    uint64_t rand_calls;
    mu_env_object boids[MU_ENV_BOIDS];
    mu_env_object fishs[MU_ENV_FISHS];
    mu_env_leaf leaves[MU_ENV_LEAVES];
    int32_t rain_target;           /* leaves +0x8ca0 */
    int32_t rain_level;            /* leaves +0x8ca4 (0x0a3a9acc, read by the audio block) */
    int32_t wind_8ca8;             /* leaves +0x8ca8 */
    int32_t wind_8cac;             /* leaves +0x8cac */
    int32_t wind_8cb0;             /* leaves +0x8cb0 */
    mu_env_world_object tormenta;  /* the world manager's object for world 0x8d */
    mu_env_host host;
} mu_env;

/* Clears every particle and object (dead) and sets the Tormenta world object
 * to its constructor values. */
void mu_env_init(mu_env *env, uint32_t rand_seed, const mu_env_host *host);

/* rand() 0x01989721: MSVC LCG state * 214013 + 2531011, (state >> 16) & 0x7fff. */
int32_t mu_env_rand(mu_env *env);

/* ObjectInit 0x0129eb81 on the modelled fields. */
void mu_env_object_init(mu_env *env, mu_env_object *o);

/* ---- the body light of RenderObject (NATIVE-FIDELITY-001) ----
 * RenderBoids/RenderFishs draw each body with RenderObject 0x016d4fe4(o, a1, 0, 0, -1, -1); its setup 0x017ec896
 * calls the body light 0x017ec3d8 (NATIVE-OBJECTS-002, verified): model +0x50 = object +5, colour = (object +7 ?
 * frame light : primary light) at the position, times 0.1 unless object +6, plus the object light +0xec.
 * ObjectInit 0x0129eb81 sets +6 = +7 = 1 and +0xe4/+0xe8 = 0.8/0.2; no routine of this module writes +6/+7
 * (the movers write +5 only). So an environment body has lighting flag = flag_05 (birds, bats, crows and the
 * MoveFishs creatures 1; butterflies and the Atlans shoal 0) and colour = frame light + object light (0.5,
 * butterflies and the shoal 1), with the transform light terms 0.4 / 0.8 / 0.2.
 * frame_light: RequestTerrainLight 0x016cb08d at the object position. */
#define MU_ENV_LIGHT_AMBIENT 0.4f      /* Transform's constant term (0x017edc95) */
#define MU_ENV_LIGHT_SCALE 0.8f        /* object +0xe4 (ObjectInit) */
#define MU_ENV_LIGHT_MINIMUM 0.2f      /* object +0xe8 (ObjectInit) */
void mu_env_body_light(const mu_env_object *o, const float frame_light[3], float color[3], uint8_t *lighting);

/* ---- tick (one 40 ms logic step, in the order of the in-world tick 0x0185613e) ---- */

/* MoveLeaves 0x01537a43. Returns 1 (its AL). */
int mu_env_move_leaves(mu_env *env, const mu_env_inputs *in);
/* MoveBoids 0x00c9eb04 (in-world branch). */
void mu_env_move_boids(mu_env *env, const mu_env_inputs *in);
/* MoveFishs 0x00ca05b3. */
void mu_env_move_fishs(mu_env *env, const mu_env_inputs *in);

/* Guard of the MoveLeaves call in the tick (0x01856a5c..0x01856ceb): Lorencia
 * except on layer-1 tile 4 (the pub), Devias on tiles other than 3 and below
 * 10, the leaf worlds 3 and 7, and the event worlds of the guard list; the
 * world manager's flag (+6 of the world object) for the others. hero_tile is
 * HeroTile 0x0b437c10. world_object_weather is +6 of the current world object
 * (1 for Tormenta Island, 0 when the world has none). */
int mu_env_leaves_active(int32_t world, int32_t hero_tile, int world_object_weather);

/* ---- render ---- */

typedef struct mu_env_render_host {
    void *context;
    /* TestFrustrum2D 0x016ccce7(x * 0.01, y * 0.01, -20) */
    int (*frustum)(void *context, float x, float y, float range);
    /* RenderObject 0x016d4fe4(object, a1, 0, 0, -1, -1) with the object's
     * angle already turned by +90 (the client adds 90 to angle.z around it) */
    void (*draw_object)(void *context, const mu_env_object *object, int32_t a1);
    /* glow sprite 0x01692eb7(bitmap, position, scale, light, owner, 0) */
    void (*sprite)(void *context, int32_t bitmap, const float position[3], float scale, const float light[3],
                   const mu_env_object *owner);
    /* TransformPosition 0x012b6ef1 with the bone matrix BoneTransform[bone] (0x06fce398) */
    void (*bone_position)(void *context, const mu_env_object *object, int32_t bone, const float vector[3],
                          float out[3]);
    /* the model getter of the render routines (NULL ends them); NULL = always present */
    int (*has_model)(void *context, int32_t model);
    /* EnableAlphaTest 0x0184a990(arg) / EnableAlphaBlend 0x0184aa2b */
    void (*alpha_test)(void *context, int32_t depth_mask);
    void (*alpha_blend)(void *context);
    void (*color4)(void *context, float r, float g, float b, float a);   /* glColor4f */
    void (*color3)(void *context, float r, float g, float b);            /* glColor3f */
    /* RenderBodyShadow 0x012bc07a with BodyOrigin (model +0x78) = origin */
    void (*shadow)(void *context, const mu_env_object *object, const float origin[3]);
    /* BindTexture 0x0184acf6 */
    void (*bind)(void *context, int32_t bitmap);
    /* glPushMatrix; glTranslatef(position); RenderPlane3D 0x0184c121(width,
     * height, AngleMatrix(angle)) as one GL_QUADS; glPopMatrix. corners are
     * the four transformed corners in the order drawn with texcoords (0,1),
     * (1,1), (1,0), (0,0), relative to position; count 0 (and corners
     * NULL) when the client pushes, translates and pops without a quad. */
    void (*plane)(void *context, const float position[3], const float corners[4][3], int32_t count);
    /* FindTexture 0x00c97ce3 on the bitmap table: 0 skips the particle; NULL = present */
    int (*has_bitmap)(void *context, int32_t bitmap);
    /* RenderSprite 0x0184c39c(bitmap, position, width, height, light, 0, 0, 0, 1, 1, 4):
     * a camera-facing quad; color is the glColor4f/3fv the client sends. */
    void (*billboard)(void *context, int32_t bitmap, const float position[3], float width, float height,
                      const float light[3]);
} mu_env_render_host;

/* RenderBoids 0x00c9fd8d(pass). terrain height through env->host. */
void mu_env_render_boids(mu_env *env, const mu_env_inputs *in, uint8_t pass, const mu_env_render_host *r);
/* RenderFishs 0x00ca1cf7. */
void mu_env_render_fishs(mu_env *env, const mu_env_inputs *in, const mu_env_render_host *r);
/* RenderLeaves 0x01538145 (world modelview pass). */
void mu_env_render_leaves(mu_env *env, const mu_env_inputs *in, const mu_env_render_host *r);

/* RenderSprite 0x0184c39c with rotation 0: the view-space centre
 * VectorTransform(position, CameraMatrix 0x0bdc5918) +/- (width/2, height/2),
 * drawn as one GL_QUADS under the identity modelview of BeginSprite
 * 0x0184a699, vertices in the order drawn with texcoords (u, v+vh),
 * (u+uw, v+vh), (u+uw, v), (u, v). */
void mu_env_billboard_quad(const float camera[3][4], const float position[3], float width, float height,
                           float out[4][3]);
/* Its colour after glBegin: glColor3fv(light) for 3-component bitmaps (+0x214
 * of the bitmap record), glColor4f(l0, l1, l2, 1) for bitmaps 0x7f49/0x7df3,
 * else glColor4f(l0, l1, l2, l0). Returns 3 or 4 (the call used). */
int mu_env_billboard_color(int32_t bitmap, int32_t components, const float light[3], float rgba[4]);

/* ---- per-world table (static readings, docs/research/client-environment.md) ---- */

typedef struct mu_env_world_info {
    int32_t world;
    float clear[3];                /* glClearColor of the render scene 0x0185916b (alpha 1) */
    int32_t fog;                   /* 0: the scene clears FogEnable 0x0bdc597c; 1: world 0x1e box fog */
    int32_t boid_model;            /* model MoveBoids spawns, -1 none */
    int32_t boid_limit;            /* objects MoveBoids walks before it stops */
    int32_t fish_model;            /* model MoveFishs spawns, -1 none, -2 several */
    int32_t fish_limit;            /* 10, or 3 outside the water worlds */
    int32_t leaf_count;            /* MoveLeaves particle count */
    int32_t leaf_bitmap;           /* bitmap of the particles it creates, -1 none */
    int32_t leaf_blend;            /* 0 alpha test, 1 additive blend, -1 not drawn */
    int32_t leaf_billboard;        /* 1: RenderSprite billboards (snow) */
} mu_env_world_info;

void mu_env_world_info_get(int32_t world, mu_env_world_info *info);
/* Model file the world's model pass 0x018392db loads at a model index
 * (Data/Object<f>/<name><nn>.bmd), 0 when none is known. */
int mu_env_model_file(int32_t world, int32_t model, char *out, size_t out_size);
/* Weather texture of a bitmap index for a world (Data/World<n+1>/...). */
int mu_env_bitmap_file(int32_t world, int32_t bitmap, char *out, size_t out_size);

/* ---- client layout (validator and tests) ---- */

/* Writes/reads the modelled fields at their client offsets. */
void mu_env_object_store(const mu_env_object *o, uint8_t out[MU_ENV_OBJECT_BYTES]);
void mu_env_object_load(mu_env_object *o, const uint8_t in[MU_ENV_OBJECT_BYTES]);
void mu_env_leaf_store(const mu_env_leaf *l, uint8_t out[MU_ENV_LEAF_BYTES]);
void mu_env_leaf_load(mu_env_leaf *l, const uint8_t in[MU_ENV_LEAF_BYTES]);
/* Byte mask (1 = modelled) of the object and leaf layouts. */
void mu_env_object_mask(uint8_t out[MU_ENV_OBJECT_BYTES]);
void mu_env_leaf_mask(uint8_t out[MU_ENV_LEAF_BYTES]);

/* cvttss2si: INT32_MIN for NaN and out-of-range values. */
int32_t mu_env_cvttss2si(float value);

#ifdef __cplusplus
}
#endif

#endif
