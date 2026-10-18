#ifndef MU_OBJECT_RENDER_H
#define MU_OBJECT_RENDER_H

#include <stddef.h>
#include <stdint.h>

#include "objects.h"

/* World-object lifecycle of the client: creation, the per-step move pass and
 * the per-frame render pass (NATIVE-OBJECTS-002, docs/research/client-objects-render.md).
 * Names are ours; every function names the client routine it follows.
 *
 * Objects are raw little-endian images of the client's 0x3d8-byte OBJECT, so
 * that the reconstruction reads and writes exactly the fields the client does
 * (MU_OBJ_* offsets below). Calls into other subsystems (particles, sounds,
 * the animation tick, the mesh draw, model transforms) are not executed here:
 * each one is appended to an event log (mu_obj_log) with its arguments, and
 * the values such calls return are explicit inputs (callbacks or fields).
 * scripts/validate_object_render.py compares the logs and the object bytes
 * with the client's instructions run in Unicorn.
 *
 * Coverage: the generic paths of every routine, world 0 (Lorencia), world
 * 0x8d (Tormenta Island, handler class with vtable 0x01aabd10) and world 0x5e
 * (the login scene, CGMLogInScene_Ex: login_world.h, NATIVE-LOGIN-001). Branches for
 * other worlds or special object types return MU_OBJ_UNSUPPORTED (nothing is
 * guessed); the caller decides what to do. */

#define MU_OBJ_SIZE 0x3d8
#define MU_OBJ_SECTORS 256

/* OBJECT offsets (client layout). */
enum {
    MU_OBJF_LIVE = 0x00,             /* u8, set by 0x0129f4a5 */
    MU_OBJF_SHADOW = 0x03,           /* u8, RenderObject draws the body shadow when set */
    MU_OBJF_LIGHT_ENABLE = 0x05,     /* u8, record +0x2c -> model +0x50 */
    MU_OBJF_LIGHT_FULL = 0x06,       /* u8, record +0x2d: terrain light not scaled by 0.1 */
    MU_OBJF_LIGHT_DYNAMIC = 0x07,    /* u8, record +0x2e: frame light (with AddTerrainLight) instead of the primary */
    MU_OBJF_AFTER_CHARACTER = 0x0a,  /* u8, drawn by the second pass 0x016d6949 in some worlds */
    MU_OBJF_VISIBLE = 0x0b,          /* u8, TestFrustrum2D result of the render pass */
    MU_OBJF_ALPHA_LINEAR = 0x0c,     /* u8, 0x012af883 steps alpha linearly */
    MU_OBJF_BONE_BUFFER = 0x0d,      /* u8, own bone buffer (0x0129f11a) instead of 0x06fce398 */
    MU_OBJF_FLAG_E = 0x0e,           /* u8 -> model +0x51 */
    MU_OBJF_ACTION = 0x2a,           /* u16 -> model +0xa8 */
    MU_OBJF_PRIOR_ACTION = 0x2c,     /* u16 */
    MU_OBJF_SECTOR = 0x46,           /* u8 */
    MU_OBJF_TYPE = 0x5c,             /* i32 */
    MU_OBJF_HIDDEN_MESH = 0x68,      /* i32: -1 none, -2 the whole object is not drawn, k skips mesh k */
    MU_OBJF_BLEND_MESH = 0x74,       /* i32: mesh drawn with the blend pass (-1 none) */
    MU_OBJF_RENDER_MODE = 0x80,      /* i32: 0x80 draws with flags 0x82 */
    MU_OBJF_SCALE = 0xa0,            /* f32 */
    MU_OBJF_BLEND_LIGHT = 0xa8,      /* f32 */
    MU_OBJF_BLEND_U = 0xac, MU_OBJF_BLEND_V = 0xb0, /* f32 texture offsets of the blend mesh */
    MU_OBJF_TIMER = 0xb4,
    MU_OBJF_BONE_SCALE = 0xb8,       /* f32, select 1 only */
    MU_OBJF_VELOCITY = 0xbc,         /* f32, animation speed of the move pass */
    MU_OBJF_RANGE = 0xc0,            /* f32, TestFrustrum2D range of the render pass */
    MU_OBJF_C4 = 0xc4,
    MU_OBJF_FRAME = 0xd0, MU_OBJF_PRIOR_FRAME = 0xd4,
    MU_OBJF_ALPHA_TARGET = 0xd8, MU_OBJF_ALPHA = 0xdc, MU_OBJF_ALPHA_RATE = 0xe0,
    MU_OBJF_VALUE_E4 = 0xe4, MU_OBJF_VALUE_E8 = 0xe8, /* record +0x30/+0x34, Transform arguments */
    MU_OBJF_LIGHT = 0xec,            /* f32[3], record +0x1c, added to the terrain light */
    MU_OBJF_DIRECTION = 0xf8,
    MU_OBJF_START = 0x110,           /* f32[3] */
    MU_OBJF_BOX_MIN = 0x128, MU_OBJF_BOX_MAX = 0x134,
    MU_OBJF_POSITION = 0x158, MU_OBJF_ANGLE = 0x164, MU_OBJF_HEAD_ANGLE = 0x170,
    MU_OBJF_LIGHT_COPY = 0x1e8,      /* f32[3], body light copy */
    MU_OBJF_OBB = 0x31c,
    MU_OBJF_OWNER = 0x34c,
    MU_OBJF_PREV = 0x350, MU_OBJF_NEXT = 0x354, /* sector list links */
    MU_OBJF_BUFFS = 0x358,
    MU_OBJF_EFFECTS = 0x3d0          /* attached effect container (0x00d99e3f tests it) */
};

/* Model (BMD object) fields the routines write. */
enum {
    MU_MDL_LIGHTING = 0x50, MU_MDL_FLAG_51 = 0x51, MU_MDL_COLOR = 0x54, MU_MDL_SCALE = 0x74,
    MU_MDL_ORIGIN = 0x78, MU_MDL_HEIGHT = 0x90, MU_MDL_ACTION = 0xa8, MU_MDL_SECONDARY = 0xcb
};
#define MU_MDL_SIZE 0xd0

enum { MU_OBJ_OK = 0, MU_OBJ_SKIPPED = 1, MU_OBJ_UNSUPPORTED = 2, MU_OBJ_BAD_ARGUMENT = 3 };

/* ---- event log ---- */

#define MU_OBJ_EVENT_ARGS 16
typedef struct mu_obj_event {
    uint32_t call;                      /* client address of the callee */
    int32_t object;                     /* index of the object it concerns (-1 none) */
    int32_t count;
    uint32_t args[MU_OBJ_EVENT_ARGS];   /* words; floats as bits; vectors expanded */
} mu_obj_event;

typedef struct mu_obj_log {
    int32_t count, capacity, overflow;
    mu_obj_event *events;               /* caller storage */
} mu_obj_log;

/* Callees that appear in logs. */
#define MU_OBJ_CALL_RENDER_OBJECT 0x016d4fe4u   /* (object, 0, 0, 0, -1, -1) */
#define MU_OBJ_CALL_VISUAL 0x017f9758u          /* RenderObjectVisual (per-world effects while drawing) */
#define MU_OBJ_CALL_EFFECTS 0x0129f671u         /* attached effects update (frame time 0x01cf103c) */
#define MU_OBJ_CALL_MOVE_PRE 0x01802168u
#define MU_OBJ_CALL_MOVE_OBJECT 0x017ff238u
#define MU_OBJ_CALL_MOVE_WORLD10 0x0180249eu
#define MU_OBJ_CALL_MOVE_EVENT 0x017ec026u
#define MU_OBJ_CALL_TICK 0x012b4dd3u            /* animation tick (frame, prior frame, prior action, speed) */
#define MU_OBJ_CALL_ADD_LIGHT 0x016cacfcu       /* AddTerrainLight (x, y, rgb, range, frame light) */
#define MU_OBJ_CALL_PARTICLE 0x0168fafdu        /* CreateParticle (bitmap, position, angle, light, sub, scale, 0, 0) */
#define MU_OBJ_CALL_SOUND 0x00a6ac96u           /* PlayBuffer (id, 0, 0) */
#define MU_OBJ_CALL_REGISTER 0x016d9f51u        /* operable-object table (object, 1) */
#define MU_OBJ_CALL_ANIMATION 0x012b5064u       /* BMD::Animation (bones, frame, prior frame, prior action, angle, head angle, 0, !translate) */
#define MU_OBJ_CALL_TRANSFORM 0x00966ea5u       /* BMD::Transform (bones, box min, box max, OBB, translate, 0, 0.4, e4, e8) */
#define MU_OBJ_CALL_TINT 0x017f9375u            /* buff tint of the model (buff list +0x358) */
#define MU_OBJ_CALL_SHADOW 0x012bc07au          /* RenderBodyShadow */
#define MU_OBJ_CALL_CUSTOM 0x017f76ecu          /* per-world custom render, returns handled */
#define MU_OBJ_CALL_BODY 0x00966defu            /* RenderBody (flags, alpha, blend mesh, blend light, u, v, hidden, -1) */
#define MU_OBJ_CALL_AFTER 0x017f919eu           /* after-render visuals */

/* Particle bitmaps of CreateFire 0x01616930. */
#define MU_OBJ_BITMAP_FIRE 0x7f3c
#define MU_OBJ_BITMAP_SMOKE 0x7f5a

/* ---- 1. terrain light at a point ---- */

/* RequestTerrainLight: 0x016cb2f7 reads the primary light 0x0bab5430, 0x016cb08d the
 * frame light 0x0b9f5430 (the primary light copied over the visible box plus the
 * AddTerrainLight sources of this step). grid: 256 x 256 x 3 floats.
 *   scene_state ([0x01d1df70]) 1, 2 or 4, or terrain_ready ([0x0b5e3ea4]) 0: (0, 0, 0)
 *   x /= 100, y /= 100 (divss), xi = (int)x, yi = (int)y (cvttss2si)
 *   outside 0..254 in either axis: (0, 0, 0)
 *   per channel: a = (L[yi+1][xi] - L[yi][xi]) * fy + L[yi][xi]
 *                b = (L[yi+1][xi+1] - L[yi][xi+1]) * fy + L[yi][xi+1]
 *                out = (b - a) * fx + a,   fx = x - (float)xi, fy = y - (float)yi */
void mu_obj_terrain_light(const float *grid, int32_t scene_state, uint8_t terrain_ready, float x, float y,
                          float out[3]);

/* ---- 2. body light ---- */

typedef float (*mu_obj_sin_fn)(void *context, float x);

typedef struct mu_obj_light_inputs {
    const float *primary;       /* 0x0bab5430 */
    const float *frame;         /* 0x0b9f5430 */
    int32_t scene_state;        /* 0x01d1df70 */
    uint8_t terrain_ready;      /* 0x0b5e3ea4 */
    float time;                 /* 0x06fce370 (type 0x444 only) */
    mu_obj_sin_fn sine;         /* 0x009681bd (type 0x444 only; NULL: host sinf) */
    void *context;
} mu_obj_light_inputs;

/* 0x017ec3d8(object, model): the model's body light.
 *   type 0x7dc: colour (0.6, 0.6, 0.6); type 0x444: colour v = sin(time * 0.003) * 0.5 + 0.5
 *   otherwise model +0x50 = object +5 and
 *     light = object +7 ? frame light : primary light, at the object position
 *     light *= 0.1 unless object +6 is set
 *     colour = light + object light (+0xec)
 *     when +5 or +6 is set the colour is also copied to object +0x1e8. */
void mu_obj_body_light(uint8_t *object, uint8_t *model, const mu_obj_light_inputs *inputs);

/* ---- 3. creation ---- */

/* MSVC rand() 0x01989721 as a callback (the caller keeps the seed). */
typedef int32_t (*mu_obj_rand_fn)(void *context);

/* CreateObject 0x016d8538 for a loader record: sector (int)(x/1600)*16 + (int)(y/1600)
 * (returns MU_OBJ_SKIPPED outside 0..15), the generic fields, then the world's
 * type defaults: world 0 (Lorencia) in CreateObject itself and world 0x8d
 * through the Tormenta handler's slot 0x2c (0x00e4c6ba). Other worlds:
 * MU_OBJ_UNSUPPORTED after the generic fields. object must hold MU_OBJ_SIZE
 * bytes; fields CreateObject does not write are left as they are (the client's
 * constructor 0x0129e792 sets them). *sector receives the sector index. The
 * operable-object registration 0x016d9f51 is logged, the sector list is not
 * built here (MU_OBJF_PREV/NEXT untouched). */
int mu_obj_create(const mu_object_record *record, int32_t world, uint8_t *object, int32_t *sector, int32_t index,
                  mu_obj_log *log);

/* ---- 4. the move pass ---- */

typedef struct mu_obj_world {
    uint8_t **objects;                  /* object images by index */
    int32_t count;
    int32_t head[MU_OBJ_SECTORS];       /* first object index of each sector list, -1 empty */
    int32_t *next;                      /* next index in the list, -1 last (CreateObject appends) */
    uint8_t block_visible[MU_OBJ_SECTORS]; /* sector +0xc */
} mu_obj_world;

/* MoveObjects 0x016d82c7 (one logic step). world: [0x01cf1600], which the pass uses as
 * [0x01cf15fc] while it runs. For each sector i (x) and j (y), list order:
 *   sector visible (+0xc): live and visible objects get MoveObject, 0x0180249e, 0x017ec026
 *   otherwise: MoveObject when the world handler asks (handler slot 0x1c, `handler_moves`),
 *              0x017ec026 for live objects, then visible = 0.
 * Every call is logged (the C does not run MoveObject itself; mu_obj_move does). */
typedef uint8_t (*mu_obj_answer_fn)(void *context, int32_t index);
void mu_obj_move_pass(mu_obj_world *w, int32_t world, mu_obj_answer_fn handler_moves, void *context,
                      mu_obj_log *log);

/* The world handler's slot 0x1c, which MoveObjects asks for objects of invisible sectors:
 * the base class 0x00d5cbbc answers 0; Tormenta (0x00e4bfff) answers TestFrustrum2D(x*0.01,
 * y*0.01, range) for types 0x1f and 0x20. */
uint8_t mu_obj_handler_moves(const uint8_t *object, int32_t world, const float *x2d, const float *y2d,
                             int32_t scene_state);

/* ---- 5. MoveObject ---- */

typedef float (*mu_obj_speed_fn)(void *context, int32_t type, int32_t action);

typedef struct mu_obj_move_inputs {
    int32_t world;              /* 0x01cf15fc */
    int32_t scene_state;        /* 0x01d1df70 */
    int32_t hero_tile;          /* HeroTile 0x0b437c10 */
    float time;                 /* 0x06fce370 */
    float hero[3];              /* hero position (Tormenta sounds) */
    uint8_t has_model;          /* model of the type loaded (else MoveObject returns after the alpha step) */
    uint8_t model_has_actions;  /* model +0x30 != 0 (worlds 0x87/0x88) */
    mu_obj_speed_fn speed;      /* PlaySpeed of (type, action) from the model's action table */
    mu_obj_rand_fn rand_fn;
    void *context;
    uint32_t now_ms;            /* timeGetTime (world 0x5e's pulse, NATIVE-LOGIN-001) */
} mu_obj_move_inputs;

/* MoveObject 0x017ff238: roof fade (world 0 types 0x7d/0x7e by HeroTile 4, world 2),
 * alpha step 0x012af883, the animation speed, the tick (logged; the caller runs it),
 * then the world's object cases: world 0 (lights, CreateFire 0x01616930, blend-mesh
 * flicker and scroll, hidden light markers) and world 0x8d (handler slot 0x30
 * 0x00e4c95e: ambient sounds near three types). Returns MU_OBJ_SKIPPED when the
 * object is transparent or has no model, MU_OBJ_UNSUPPORTED for a world whose case
 * is not reconstructed (the tick is logged before that). */
int mu_obj_move(uint8_t *object, int32_t index, const mu_obj_move_inputs *inputs, mu_obj_log *log);
/* The part of 0x017ff238 before the per-world switch at 0x017ff8ad (MU_OBJ_OK when the world
 * case would follow). */
int mu_obj_move_generic(uint8_t *object, int32_t index, const mu_obj_move_inputs *inputs, mu_obj_log *log);

/* CreateFire 0x01616930(type, object, x, y, z): rotated offset plus random jitter;
 * type 0 fire particle and AddTerrainLight (range 4), 1 and 2 smoke particles. */
void mu_obj_create_fire(int32_t type, const uint8_t *object, int32_t index, float x, float y, float z,
                        mu_obj_rand_fn rand_fn, void *context, mu_obj_log *log);

/* 0x012af883: alpha towards the target (linear 0.05 steps when +0xc, else
 * alpha += (target - alpha) * rate), then blend light = min(blend light, alpha). */
void mu_obj_alpha_step(uint8_t *object);

/* RenderObjectVisual 0x017f9758, the part before its first effect call for Lorencia's
 * Waterspout01 (world 0, type 0x69): blend light 1 and the blend mesh's texture scroll
 * v = (float)(-(int)time % 1000) * 0.001. The smoke particles and flare sprites it then creates
 * at named bones are not reconstructed. Other worlds/types: MU_OBJ_UNSUPPORTED, object untouched. */
int mu_obj_visual(uint8_t *object, int32_t world, float time);

/* ---- 6. the render pass ---- */

typedef struct mu_obj_render_inputs {
    int32_t world;              /* [0x01cf1600], used as [0x01cf15fc] during the pass */
    int32_t scene_state;
    uint8_t top_view;           /* 0x0bdc58b7 */
    const float *x2d, *y2d;     /* CreateFrustrum2D polygon (0x0b6b5400 / 0x0b6b5410) */
    mu_obj_answer_fn render_first;  /* 0x017fcd18: draw before the frustum test */
    mu_obj_answer_fn has_effects;   /* 0x00d99e3f: attached effects present */
    void *context;
    float frame_time;           /* 0x01cf103c (effects update argument) */
} mu_obj_render_inputs;

/* RenderObjects 0x016d5020. counter: 0x06fc9c90 (reset above 40, then +1).
 * Sector (i, j) visible = TestFrustrum2D(i*16+8, j*16+8, r), r = -180, -300 in worlds
 * 0x86..0x88, 0x8a, 0x8c, 0x8d and -200 in 0x89. Per object: render_first objects are
 * drawn, then (sector visible or top view, and live) visible = TestFrustrum2D(x*0.01,
 * y*0.01, range + (world 10 ? -10 : 0)); others get the test first and are drawn only
 * when visible. A draw logs RenderObject, RenderObjectVisual and, with effects, their
 * update. */
void mu_obj_render_pass(mu_obj_world *w, const mu_obj_render_inputs *inputs, int32_t *counter, mu_obj_log *log);

/* ---- 7. RenderObject ---- */

typedef struct mu_obj_draw_inputs {
    int32_t world;
    int32_t scene_state;
    uint8_t has_model;
    uint8_t chaos_hero_flag;    /* hero CHARACTER +0x325c (Chaos Castle worlds only) */
    uint8_t option_flag;        /* 0x009a645f on 0x009a6ef3()+0x78 (shadow gate) */
    int32_t bounds_mode;        /* 0x0b437bfc */
    mu_obj_light_inputs light;
    mu_obj_answer_fn custom_render; /* 0x017f76ec: returns handled */
    mu_obj_answer_fn registry;      /* render registry 0x01d1e010 lookup (found and handled) */
    void *context;
} mu_obj_draw_inputs;

/* RenderObject 0x016d4fe4(object, translate, select, extra, a, b) for the static-object
 * call (select 0, extra 0): the setup 0x017ec896 (alpha gate, model fields, body light,
 * Animation and Transform, logged) and the draw 0x017edf43 (HiddenMesh -2 skip, flags
 * 0x82 for +0x80 == 0x80, shadow, custom render, RenderBody(2, alpha, blend mesh, blend
 * light, u, v, hidden mesh, -1)). model: MU_MDL_SIZE bytes. Types 0x7e1, 0x7e2, world
 * 0x6e/0x6f type 0, world 0x84 type 0x1e and select/extra other than 0 give
 * MU_OBJ_UNSUPPORTED. Returns MU_OBJ_SKIPPED when the setup refuses (alpha < 0.01 or no
 * model) or the object is hidden. */
int mu_obj_render(uint8_t *object, int32_t index, uint8_t *model, uint8_t translate, const mu_obj_draw_inputs *inputs,
                  mu_obj_log *log);

/* ---- helpers ---- */

static inline float mu_obj_f32(const uint8_t *object, uint32_t offset)
{
    float v;
    __builtin_memcpy(&v, object + offset, 4);
    return v;
}
static inline void mu_obj_set_f32(uint8_t *object, uint32_t offset, float v) { __builtin_memcpy(object + offset, &v, 4); }
static inline int32_t mu_obj_i32(const uint8_t *object, uint32_t offset)
{
    int32_t v;
    __builtin_memcpy(&v, object + offset, 4);
    return v;
}
static inline void mu_obj_set_i32(uint8_t *object, uint32_t offset, int32_t v) { __builtin_memcpy(object + offset, &v, 4); }
static inline uint16_t mu_obj_u16(const uint8_t *object, uint32_t offset)
{
    uint16_t v;
    __builtin_memcpy(&v, object + offset, 2);
    return v;
}
static inline void mu_obj_set_u16(uint8_t *object, uint32_t offset, uint16_t v) { __builtin_memcpy(object + offset, &v, 2); }

/* MSVC rand recurrence (seed = seed * 214013 + 2531011, (seed >> 16) & 0x7fff). */
int32_t mu_obj_msvc_rand(uint32_t *seed);

#endif
