#ifndef MU_JOINTS_H
#define MU_JOINTS_H

/* The client's joint pool: ribbons, trails and lightning bolts
 * (NATIVE-JOINT-001, docs/research/client-joints.md).
 *
 *   - CreateJoint 0x0153b02c(type, position, target position, angle, subtype,
 *     target, scale, key, skill, byte10, arg11, arg12, word13, arg14) takes
 *     the first free record of 500 (0xa64 bytes each at 0x0a4fa4f0);
 *   - MoveJoints 0x01589b06 runs MoveJoint 0x01556c26 once per logic step for
 *     every live record (after MoveEffects, before MoveParticles);
 *   - RenderJoints 0x01589b56(mode) draws every live record in the render
 *     scene: its blend wrapper, a colour, BindTexture and, per tail segment
 *     and face bit, one GL_QUADS quad between two cross-shaped tails.
 *
 * A record carries up to 50 tails; each tail is four corners around the head
 * position (pos + R(-w/2,0,0), R(w/2,0,0), R(0,0,-w/2), R(0,0,w/2), w the
 * record's width +0x14, R the angle matrix). The tail shift 0x01553ba6 pushes
 * the tails down by one and writes tail 0 at the current head.
 *
 * Authored C ports. Every client operation is binary32 SSE: build with
 * -ffp-contract=off. The kinds listed by mu_jt_kind_supported are compared
 * with the client's instructions in Unicorn (scripts/validate_joints.py and
 * NATIVE-COMBAT-002's scripts/validate_skill_fx.py); the client's per-type
 * switches cover a few hundred more (CreateJoint spans 0x0153b02c..0x01553644).
 *
 * The record keeps its previous contents between uses (the client never
 * clears it): CreateJoint builds the first tail from the previous width and a
 * kind that returns early keeps the previous lifetime and tail count. */

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* LoadBitmap indices (the loader 0x0185baac, block 0x0182239b..). */
enum {
    MU_JT_BITMAP_THUNDER = 0x7f7c,     /* Effect\JointThunder01.jpg (drawn by the 0x7f7d bolts) */
    MU_JT_TYPE_THUNDER_BOLT = 0x7f7d,  /* the lightning kind; draws 0x7f7c */
    MU_JT_BITMAP_SPIRIT = 0x7fd3,      /* Effect\JointSpirit01.jpg (Evil Spirit) */
    MU_JT_BITMAP_SPARK = 0x7fd5,       /* the spark streaks (Twisting Slash, Noria) */
    MU_JT_BITMAP_LASER = 0x7fd6,       /* Effect\JointLaser01.jpg */
    MU_JT_BITMAP_ENERGY = 0x7fd8,      /* Effect\JointEnergy01.jpg (Heal) */
    MU_JT_BITMAP_SHINY2 = 0x7f67,      /* Effect\Shiny02.jpg (the bolts' CreateSprite) */
    MU_JT_BITMAP_FLARE = 0x7f78        /* Effect\Flare.jpg (the Dark Horse's ring, NATIVE-HELPERS-002) */
};

/* Client routines the joint code calls, reported through the environment. */
enum {
    MU_JT_CALL_TERRAIN_LIGHT = 0x016cacfc,  /* AddTerrainLight(x, y, light, range, frame light) */
    MU_JT_CALL_PARTICLE = 0x0168fafd,       /* CreateParticle */
    MU_JT_CALL_JOINT = 0x0153b02c,          /* CreateJoint */
    MU_JT_CALL_EFFECT = 0x013c0eaa,         /* CreateEffect(type, pos, angle, light, sub, owner, ...) */
    MU_JT_CALL_SPRITE = 0x01692eb7,         /* CreateSprite(bitmap, pos, scale, light, owner, rotation, blend, axes) */
    MU_JT_CALL_AREA_ATTACK = 0x013bc25e     /* the hero's area attack request (skill, range, pos, serial, ...) */
};

/* GL state wrappers of RenderJoints' render types. */
enum {
    MU_JT_STATE_ADD = 0x0184aa2b,       /* render type 1: EnableAlphaBlend (ONE, ONE) */
    MU_JT_STATE_ALPHA = 0x0184a990,     /* render type 2: EnableAlphaTest(1) */
    MU_JT_STATE_SUBTRACT = 0x0184aab7,  /* render type 3: EnableAlphaBlendMinus (ZERO, ONE_MINUS_SRC_COLOR) */
    MU_JT_STATE_ADD_INVERSE = 0x0184ab46 /* render type 4: (ONE_MINUS_SRC_COLOR, ONE) */
};

#define MU_JT_JOINTS 500
#define MU_JT_RECORD_BYTES 0xa64
#define MU_JT_TAILS 50
#define MU_JT_NO_TARGET (-1)

/* One record: the fields the ported kinds use, client offsets in the
 * comments. target is an index into the environment's object table (the
 * client stores an OBJECT pointer at +0x54). The layout up to field_a60 is
 * NATIVE-COMBAT-002's mu_sfx_joint (skill_fx.h aliases this type). */
typedef struct mu_jt_joint {
    uint8_t live;              /* +0x000 */
    int32_t type;              /* +0x004 the kind */
    int32_t tex_type;          /* +0x008 the bitmap drawn */
    int32_t subtype;           /* +0x00c */
    uint8_t render_type;       /* +0x010 1 add, 2 alpha test, 3 subtract, 4 inverse add */
    uint8_t faces;             /* +0x011 bit 0: quads through corners 2/3, bit 1: through corners 0/1 */
    float scale;               /* +0x014 width */
    float position[3];         /* +0x018 head */
    float start[3];            /* +0x024 */
    float angle[3];            /* +0x030 degrees */
    float light[3];            /* +0x048 */
    int32_t target;            /* +0x054 OBJECT pointer in the client; an index here, -1 none */
    float target_position[3];  /* +0x058 */
    uint8_t field_64;          /* +0x064 RenderJoints' mode filter (2: not in mode 1, 1: not in mode 2) */
    int32_t num_tails;         /* +0x068 */
    int32_t max_tails;         /* +0x06c */
    float tails[MU_JT_TAILS][4][3]; /* +0x070 */
    int32_t lifetime;          /* +0xa00 */
    uint8_t reached;           /* +0xa04 */
    float velocity;            /* +0xa08 forward speed along -y of the angle matrix */
    float jitter[3];           /* +0xa0c */
    uint16_t key;              /* +0xa18 CreateJoint argument 8 */
    uint16_t skill;            /* +0xa1a argument 9 */
    uint8_t serial;            /* +0xa1c */
    uint8_t field_a24, field_a25; /* +0xa24 / +0xa25 texture-coordinate modes of RenderJoints */
    uint8_t tail_update;       /* +0xa26 MoveJoint's closing tail shift */
    uint8_t field_a3c;         /* +0xa3c argument 10 */
    uint16_t field_a44;        /* +0xa44 argument 13 */
    float time;                /* +0xa48 */
    float brightness;          /* +0xa4c */
    float field_a54;           /* +0xa54 */
    uint8_t moving;            /* +0xa5c MoveJoint builds the angle matrix and moves the head */
    int32_t field_a60;         /* +0xa60 argument 14 */
    /* fields beyond NATIVE-COMBAT-002's record */
    int32_t phase;             /* +0xa20 0x7f7d/0x16, 0x17: (int)WorldTime % (max_tails / 2) at creation */
} mu_jt_joint;

/* What the joint code reads of a target object (the client's OBJECT). */
typedef struct mu_jt_object {
    uint8_t live;              /* +0x00 */
    uint8_t visible;           /* +0x0b */
    int16_t weapon;            /* +0x56 (skill_fx's Twisting Slash) */
    float position[3];         /* +0x158 */
    float light[3];            /* +0xec */
    uint16_t action;           /* +0x2a (NATIVE-HELPERS-002: the 0x7f78 ring reads its target's action) */
    int32_t type;              /* +0x5c (NATIVE-HELPERS-002: Fenrir's lightning 0x4ac looks up its owner's model) */
    float eye_188[3], eye_194[3]; /* +0x188 / +0x194, SetEye (0x0137a948) */
} mu_jt_object;

/* One call into another subsystem, in client order; vectors are the values at
 * the moment of the call. NATIVE-COMBAT-002's mu_sfx_call is this type. */
typedef struct mu_jt_call {
    int32_t routine;           /* MU_JT_CALL_* (skill_fx adds its own) */
    int32_t type;              /* bitmap / model / effect type */
    int32_t subtype;
    int32_t owner;             /* object index, -1 none, -2 the calling effect */
    int32_t range;             /* AddTerrainLight range */
    float scale;
    float position[3];
    float target[3];           /* CreateJoint's second position */
    float angle[3];            /* CreateSprite: angle[0] = rotation */
    float light[3];
} mu_jt_call;

typedef struct mu_jt_env {
    void *context;
    int32_t (*rand)(void *context);                               /* rand() 0x01989721 */
    float (*height)(void *context, float x, float y);            /* RequestTerrainHeight 0x016cc9e2 */
    const mu_jt_object *(*object)(void *context, int32_t index); /* NULL: no object */
    void (*call)(void *context, const mu_jt_call *call);         /* NULL: calls are not reported */
    uint8_t serial;            /* [[0x01d1df18] + 0x2dec], the hero's skill serial (Evil Spirit) */
    float world_time;          /* WorldTime [0x06fce370], ms */
    float creation_light[3];   /* CreateJoint argument 12, the eye trails' supplied colour */
} mu_jt_env;

/* 1 when CreateJoint, MoveJoint and RenderJoints are reconstructed for the
 * kind: 0x7fd8 subtype 1 (Heal), 0x7fd3 subtype 0 (Evil Spirit), 0x7fd5
 * subtype 0 (spark streaks), 0x7f7d subtypes 0x10..0x1a (Tormenta Island's
 * lightning); NATIVE-HELPERS-002: 0x7f78 subtype 0 (the Dark Horse's ring of
 * flares around its target). */
int mu_jt_kind_supported(int32_t type, int32_t subtype);

/* CreateJoint's record part 0x0153b0a6.. on a record that keeps its previous
 * contents: the common initialisation (live, kinds, render type 1, faces 3,
 * key, skill, velocity 0, the bytes and arguments, position = start, angle,
 * brightness 1, moving, light (1, 1, 1), jitter 0, the target position
 * argument when there is no target object, target, no tails), the first tail
 * from the previous width, then the kind's case and the 50-tail clamp.
 * Returns 1 for a supported kind (0 otherwise: the common part ran). */
int mu_jt_create(mu_jt_joint *j, int32_t type, const float position[3], const float target_position[3],
                 const float angle[3], int32_t subtype, int32_t target, float scale, uint16_t key, uint16_t skill,
                 uint8_t byte10, uint16_t word13, int32_t arg14, const mu_jt_env *env);

/* The inputs MoveJoint reads besides the record. */
typedef struct mu_jt_move_inputs {
    float time_step;           /* [0x01cf103c] */
    int wall_scene;            /* [0x01ec8ee7] (Evil Spirit's wall stop) */
    uint16_t wall;             /* terrain attribute at the head (0x016d348d) */
    int is_hero_target;        /* the target is the hero's object */
} mu_jt_move_inputs;

/* MoveJoint 0x01556c26 for one live record of a supported kind: the head
 * (angle matrix, forward motion), the kind's case, the closing tail shift
 * (+0xa26), time += time step, LifeTime - 1 (dead below 0). Returns 1 when the
 * kind is reconstructed (0: nothing done). */
int mu_jt_move(mu_jt_joint *j, const mu_jt_env *env, const mu_jt_move_inputs *in);

/* The tail shift 0x01553ba6(j, matrix, 0). */
void mu_jt_tail_shift(mu_jt_joint *j, const float matrix[12]);

/* GL stream of RenderJoints (what the client sends to opengl32). */
enum { MU_JT_GL_QUADS = 7 };

typedef struct mu_jt_gl {
    void *context;
    void (*state)(void *context, int32_t wrapper, int32_t argument);  /* MU_JT_STATE_* */
    void (*bind)(void *context, int32_t bitmap);                      /* BindTexture 0x0184acf6 */
    void (*color3)(void *context, float r, float g, float b);         /* glColor3f */
    void (*begin)(void *context, int32_t mode);
    void (*texcoord)(void *context, float u, float v);
    void (*vertex)(void *context, const float v[3]);
    void (*end)(void *context);
} mu_jt_gl;

/* RenderJoints' part for one record 0x01589bcd..0x0158ba38: the record is
 * skipped when not live, without tails or faces, or by the mode filter;
 * otherwise the render type's wrapper, the kind's colour (none for 0x7fd5:
 * the GL colour stays), BindTexture(+8), and for every tail segment the
 * kind's texture coordinates and colour and one quad per face bit. Returns
 * the number of quads; 0 when skipped. world_time: WorldTime (ms). Kinds that
 * are not reconstructed draw the general path. */
int mu_jt_render(const mu_jt_joint *j, uint8_t mode, float world_time, const mu_jt_gl *gl);

#ifdef __cplusplus
}
#endif

#endif
