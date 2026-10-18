#ifndef MU_COMBAT_H
#define MU_COMBAT_H

/* Client-side combat visuals and timing (NATIVE-COMBAT-001,
 * docs/research/client-combat.md).
 *
 * Authored C ports of client routines; names are investigator labels and
 * addresses are the routines in the pinned restored text (capture09). Every
 * client operation is binary32 SSE unless noted: build with
 * -ffp-contract=off. Functions marked "verified" equal the client's
 * instructions under Unicorn (scripts/validate_combat.py); the others are
 * static readings, labelled as such.
 *
 * Character (CHARACTER c) and object (OBJECT o = c + 0x3254) fields used here:
 *   c + 0x004 safe-zone byte, c + 0x012 class byte, c + 0x021 AttackTime,
 *   c + 0x023 Dead counter, c + 0x026 skill (word), c + 0x028 attack counter,
 *   c + 0x038 movement, c + 0x040 target index (word), c + 0x146 monster class,
 *   c + 0x19ac / + 0x3fc weapon item index (word, -1 none), c + 0x1a8 fade timer,
 *   c + 0x21a4 wing type (word), c + 0x3324 float;
 *   o + 0x008 live byte, o + 0x02a action, o + 0x05c type (0xa91 = Player),
 *   o + 0x0d0 frame, o + 0x0dc alpha, o + 0x158 position, o + 0x164 angles. */

#include <stddef.h>
#include <stdint.h>

/* ------------------------------------------------------------------------
 * Floating damage text: the points pool 0x0a3ae150 (1000 records of 0xb4
 * bytes), CreatePoint 0x016912ae, MovePoints 0x016914a0, RenderPoints
 * 0x0169159e and RenderNumber 0x0184cd2f. */

#define MU_POINTS 1000          /* 0x3e8 */
#define MU_POINT_BYTES 0xb4

/* Special values of a point (RenderNumber draws a bitmap instead of digits). */
enum {
    MU_POINT_MISS = -1,    /* Interface\font_miss.tga   0x7df4 */
    MU_POINT_HIT = -2,     /* Interface\Hit.tga         0x7df3 */
    MU_POINT_RESIST = -3,  /* Interface\resist.tga      0x7df5 */
    MU_POINT_BLOCK = -4,   /* Interface\block.tga       0x7df6 */
    MU_POINT_PARRY = -5,   /* Interface\parry.tga       0x7df7 */
    MU_POINT_ABSORB = -6,  /* Interface\absorb.tga      0x7df8 */
    MU_POINT_BLEED = -7,   /* Interface\font_bleed.tga  0x7dfd */
    MU_POINT_BIND = -8,    /* Interface\font_bind.tga   0x7dfc */
    MU_POINT_SLOW = -9,    /* Interface\font_slow.tga   0x7dfb */
    MU_POINT_TOXIC = -10,  /* Interface\font_toxic.tga  0x7dfa */
    MU_POINT_STUN = -11    /* Interface\font_stun.tga   0x7df9 */
};

/* Bitmap of the digit font (Interface\font_damage.tga). */
#define MU_BITMAP_FONT_DAMAGE 0x7534

/* One record of the pool; client offsets in the comments. Bytes the client
 * never writes are not represented. */
typedef struct mu_point {
    uint8_t live;           /* +0x08 */
    int32_t value;          /* +0x0c damage or MU_POINT_* */
    int32_t extra;          /* +0x14 CreatePoint argument 8 (not read by the routines here) */
    float scale;            /* +0x18 */
    float position[3];      /* +0x20 */
    float color[3];         /* +0x2c */
    int32_t delay;          /* +0x48 steps before the point moves (CreatePoint stores 0) */
    float render_arg;       /* +0x60 CreatePoint argument 7, RenderNumber argument 6 */
    uint8_t move;           /* +0x68 rises while set */
    float gravity;          /* +0x6c rise per step; alpha = gravity * 0.4 */
    uint8_t floor_test;     /* +0xa4 */
    float floor;            /* +0xa8 terrain height + 140 */
} mu_point;

typedef float (*mu_height_fn)(void *context, float x, float y);

/* CreatePoint 0x016912ae (thiscall on the pool, 8 arguments), verified:
 * takes the first record whose live byte is clear: live = 1, value, extra,
 * position = pos with z + 140, color, floor_test, floor =
 * RequestTerrainHeight(x, y) + 140 (height callback), render_arg, gravity
 * 10, scale, delay 0, move. Returns the record index, or -1 when the pool is
 * full (the client then does nothing). */
int32_t mu_point_create(mu_point *points, const float position[3], int32_t value, const float color[3], float scale,
                        uint8_t move, uint8_t floor_test, float render_arg, int32_t extra, mu_height_fn height,
                        void *context);

/* MovePoints 0x016914a0, one logic step, verified: for every live point,
 * --delay; once delay < 0: z += gravity when move; gravity -= 0.3; the point
 * dies when gravity <= 0 (0 >= gravity, so NaN keeps it); unless value == -2
 * (HIT), scale -= 5 and a scale below 15 becomes 15. */
void mu_points_move(mu_point *points);

/* Arguments of one RenderNumber call made by RenderPoints. */
typedef struct mu_number_call {
    int32_t index;          /* record */
    float position[3];
    int32_t value;
    float color[3];
    float alpha;            /* gravity * 0.4 */
    float scale;
    float render_arg;
} mu_number_call;

/* RenderPoints 0x0169159e(mode) (thiscall, after blend mode 0x0184a990(1)
 * and depth test off), verified: for every live point, in pool order, skip it
 * when mode 1 and z > 350, when mode 2 and 300 >= z, or (other modes) when
 * floor_test and floor >= z; otherwise RenderNumber(position, value, color,
 * gravity * 0.4, scale, render_arg). Writes up to max calls; returns the
 * number of calls the client makes. */
int32_t mu_points_render(const mu_point *points, uint8_t mode, mu_number_call *calls, int32_t max);

/* Arguments of RenderSpriteUV 0x0184ca6b(bitmap, position, width, height,
 * uv[4][2], light[4][3], alpha, skew). */
typedef struct mu_sprite_call {
    int32_t bitmap;
    float position[3];
    float width, height;
    float uv[4][2];
    float light[4][3];
    float alpha;
    float skew;
} mu_sprite_call;

/* The thousands formatter 0x016b8b26 (static reading): "%d" of the leading
 * group, then ",%03d" per further group of three digits, for the value
 * converted to an unsigned integer (negative values are not passed by
 * RenderNumber). Returns the length. */
int32_t mu_format_thousands(int32_t value, char *out, size_t size);

/* RenderNumber 0x0184cd2f(position, value, color, alpha, scale, arg6),
 * verified with the formatter and RenderSpriteUV recorded: values -11..-1
 * draw one bitmap (width scale * 3.2 / 6.4 / 5.4 / 3.4, height scale * 1.6 /
 * 1.7 by bitmap); other values are formatted with mu_format_thousands, the
 * start is moved left by length * 5 and by length * scale * 0.125 (x and y),
 * and each character is a scale x scale sprite of font_damage (digit d at
 * u = d / 11 .. (d + 1) / 11 of the upper half, the comma as the eleventh
 * cell, drawn smaller), the position advancing by scale * 0.5 (x and y)
 * per character. Writes up to max sprites; returns the number of sprites. */
int32_t mu_render_number(const float position[3], int32_t value, const float color[3], float alpha, float scale,
                         float arg6, mu_sprite_call *sprites, int32_t max);

/* RenderSpriteUV's corners (verified as part of RenderNumber's caller chain,
 * static for the vertex part): the position is transformed by the camera
 * matrix 0x0bdc5918 (VectorTransform 0x00d002b2: eye = M[3x4] * p) and the
 * quad is (x - w/2 - skew, y - h/2), (x + w/2 - skew, y - h/2),
 * (x + w/2 + skew, y + h/2), (x - w/2 + skew, y + h/2) at eye z, drawn as
 * GL_QUADS with glColor4f(light[i], alpha) and glTexCoord2f(uv[i]). camera
 * is row-major 3x4. */
void mu_sprite_corners(const float camera[12], const float position[3], float width, float height, float skew,
                       float corners[4][3]);

/* Damage information built by the damage packet handler 0x01224455
 * (constructor 0x00a02e4c) and read by ShowDamage. */
typedef struct mu_damage_info {
    int32_t damage;         /* +0x00 */
    int32_t type;           /* +0x04 packet[0x0d] & 15 */
    uint8_t flag8;          /* +0x08 packet[0x0d] bit 7: three stacked points */
    uint8_t flag9;          /* +0x09 packet[0x0d] bit 6: two stacked points */
    uint8_t flag_a;         /* +0x0a packet[0x0c] bit 0: three stacked points, brighter */
    uint8_t flag_b;         /* +0x0b packet[0x10] == 1: scale x 1.5 and offsets */
    uint8_t flag_c;         /* +0x0c packet[0x0c] bit 1: offset (-35, -35, +25) */
    uint8_t flag_d;         /* +0x0d packet[0x0c] bit 2 (not read by ShowDamage) */
} mu_damage_info;

/* Damage colour 0x01691738(type, key, color, flag_a, flag_b), verified:
 * flag_a (packet[0x10] == 1): flag_b ? (0.99, 0.89, 0.98) : (1, 1, 0);
 * else flag_b (packet[0x0c] bit 1): type 2 (0.97, 0.58, 0.93), type 3 (1, 0.96,
 * 0.59), other (0.99, 0.89, 0.98); else by type: 0 red (1, 0, 0) on the hero
 * (key == hero key 0x06fca288) and orange (1, 0.6, 0) on others, 1 (0, 1, 1),
 * 2 (0, 1, 0.6), 3 (0, 0.6, 1), 4 (1, 0, 1), 5 (0, 1, 0), 6 (0.7, 0.4, 1),
 * 11 (0.5, 0.5, 0.75), any other white. */
void mu_damage_color(int32_t type, int32_t key, int32_t hero_key, uint8_t flag_a, uint8_t flag_b, float color[3]);

/* Damage text scale 0x01691bbe(type), verified: 50 for types 1..3, 80 for
 * 11, 15 otherwise. The handler uses 50 instead when packet[0x0d] bit 7 is
 * set (static). */
float mu_damage_scale(int32_t type);

/* ShowDamage 0x00a01a25(key, position, color, scale, info) (thiscall on
 * 0x01d1df18), verified with CreatePoint run as client code: damage 0 shows
 * one bitmap point (type 7 RESIST, 8 BLOCK, 9 PARRY, 10 ABSORB, 12 none,
 * else MISS) in white for the hero key, grey (0.5) otherwise, scale 1,
 * move and floor test on; damage > 0 shows one to three stacked digit points
 * (flag8: three, darker by 0.4 / 0.2, scales +0 / +15 / +25, z + 7 each;
 * flag_a: three, brighter; flag9: two; else one) after the flag_b / flag_c /
 * type 5 offsets. color is read, never written (the zero branch writes the
 * caller's colour array). Returns the number of points created. */
int32_t mu_show_damage(mu_point *points, int32_t key, int32_t hero_key, const float position[3], float color[3],
                       float scale, const mu_damage_info *info, mu_height_fn height, void *context);

/* ------------------------------------------------------------------------
 * Attack speed and attack actions. */

#define MU_PLAYER_ACTIONS 0x186

/* SetAttackSpeed 0x0138dc60(attack_speed, magic_speed), verified: the
 * PlaySpeed of 175 Player actions (179 stores) as binary32 expressions of the
 * two speeds, e.g. the fist attacks 0x6f/0x70 = 0.6 + (attack_speed >= 288 ?
 * 1.148 : attack_speed * 0.004). Writes only the stored actions of speeds
 * (MU_PLAYER_ACTIONS entries). The caller 0x0138d9cf passes the character
 * attribute words +0x1b6 / +0x1c2 plus equipment bonuses (static). */
void mu_set_attack_speed(float attack_speed, float magic_speed, float *speeds);
/* 1 when SetAttackSpeed stores action's speed. */
int mu_attack_speed_writes(int32_t action);

/* Inputs of SetPlayerAttack 0x01392bde(c): the character fields it reads and
 * the answers of the engine services it calls. */
typedef struct mu_attack_input {
    int32_t object_type;    /* o + 0x5c */
    uint8_t class_byte;     /* c + 0x12 (class = low nibble, 0x0095f5cc) */
    uint8_t safe_zone;      /* c + 0x04 (0x0095fb27) */
    uint8_t counter;        /* c + 0x28 */
    int16_t weapon[2];      /* c + 0x19ac, c + 0x19ac + 0x3fc */
    int16_t wing;           /* c + 0x21a4 */
    uint8_t attr_present[2];/* item attribute record of weapon[k] - 0xae6 (0x00cd4ea8 / 0x00cd5d29) non-null */
    uint8_t two_handed;     /* attribute +0x253 of weapon 0 */
    int32_t bow_kind;       /* 0x0139d8f8(c): 1 bow, 2 crossbow, else 0 */
    uint8_t dual;           /* 0x0139d9ed(c, 0) */
    uint8_t state_72;       /* 0x0129ddd4(c, 0x72, 1) */
    const int32_t *rand_values;   /* rand() results in call order */
    int32_t rand_count;
} mu_attack_input;

typedef struct mu_attack_result {
    int32_t action;         /* SetAction argument, -1 when not called */
    int32_t speed_update;   /* 1 when the hero speed adjustment 0x0138d9cf ran */
    int32_t attack_start;   /* 1 when 0x01392afd(c, 0, 1) ran */
    int32_t rand_used;      /* rand() calls consumed */
    int32_t fault;          /* 1 when more rand values were needed than given */
} mu_attack_result;

/* SetPlayerAttack's action choice for the Player model (o + 0x5c == 0xa91),
 * verified: fists 0x6f (classes 7, 8, 9, 12, 14: 0x70); one-handed sword /
 * axe / mace 0x71..0x74 by counter % 4 with a second one-handed weapon, else
 * 0x71 + counter % 2 (class 9: 0x82); two-handed 0x75 + counter % 3 (four
 * items 0x78); a one-handed weapon in the left hand only 0x73 + rand() % 2;
 * staffs 0x70 / 0x88 / 0x71 + rand() % 2, two-handed staffs 0xa3 + rand() % 2;
 * spears 0x7b + counter % 3 (class 7: 0x7a, items 0x10e7/0x10e8: 0x79); bow
 * 0x7e and crossbow 0x7f (with wings 0x80 / 0x81); dual wield 0x83..0x86;
 * else 0x6f (0x87 in state 0x72). The monster default is mu_monster_attack_action. */
void mu_player_attack_action(const mu_attack_input *input, mu_attack_result *result);

/* SetPlayerAttack's default monster branch (no special model), verified:
 * action 3 when counter % 3 == 0, else 4; the counter is incremented by the
 * branch and again by the common tail (static: both increments are in the
 * routine). special_blocks: any of the 16 world/event predicates said no
 * (then no action). Returns the action or -1. */
int32_t mu_monster_attack_action(uint8_t counter, int special_blocks);

/* SetPlayerMagic 0x013944d9(c, skill) for the Player model, static: the
 * hero speed adjustment, then SkillAction 0x012b001a with action 0xa5 (class
 * 14: 0x10e) when 0x00b99205(class) is non-zero, else 0xa1 + rand() % 2;
 * monsters 3 / 4 by counter % 3 like the attack. */
int32_t mu_player_magic_action(uint8_t class_byte, int class_check, int32_t rand_value);

/* ------------------------------------------------------------------------
 * Hero attack (MoveHero's attack case 3 in 0x01697c17), hit reaction and death. */

/* The in-range test 0x016a52a6(c, x, y, range), verified: c non-null and
 * sqrt(dx * dx + dy * dy) <= range, dx/dy = character tile - (x, y) as
 * binary32 (cvtsi2ss of the integer differences), the square root through
 * the CRT's double sqrt rounded to binary32. */
int mu_in_range(int32_t tile_x, int32_t tile_y, int32_t x, int32_t y, float range);

/* Attack range of the hero in tiles (static reading of 0x01697cab..0x01697d51):
 * 1; 2 for weapon items 0x600..0x7ff of the hero's right-hand inventory slot;
 * 6 when the bow check 0x0139d994 is non-zero; 8 for an item with property
 * 0x54; 7 for character class word 9. Later rules win. */
float mu_hero_attack_range(int32_t weapon_item, int bow, int item_flag_54, int16_t class_word);

/* Direction byte of the attack packet (static, 0x01698025): ((angle_z + 22.5)
 * / 360 * 8 + 1) truncated, low byte, modulo 8. */
uint8_t mu_attack_direction(float angle_z);

/* The monster hit-reaction predicate 0x0139f3a0(class, action), verified:
 * class 0x2fb never reacts in actions >= 8 or 4; other classes do not react
 * while in action 3 or 4 (their attacks). SetPlayerShock 0x0138f92f then
 * sets action 5 (static). */
int mu_monster_shock_allowed(int32_t monster_class, int32_t action);

/* SetPlayerShock 0x0138f92f's gate and monster action (static reading,
 * the predicate is verified): nothing when the character is dead (c + 0x23),
 * in one of the Player actions 0x8f, 0x9c, 0x9f, 0xe2, 0xe3, 0xdc, 0xe0,
 * 0xe1, 0x11d, 0x126, 0x127, or when damage <= 0 for types other than 12
 * and 15; a monster then takes action 5 when mu_monster_shock_allowed.
 * Returns the action set or -1. */
int32_t mu_shock_action(uint8_t dead, int32_t object_type, int32_t action, int32_t monster_class, int32_t damage,
                        int32_t type);

/* The dead counter in MoveCharacter 0x013a85a9 (static reading,
 * 0x013a87c4..0x013a8819): after the animation step, when c + 0x23 > 0 the
 * byte is incremented (wrapping at 256); from 15 on SetPlayerDie 0x01393a61
 * runs every step (a monster gets SetAction(6) once; SetAction ignores the
 * repeats). Returns the new counter; *die is set when SetPlayerDie runs. */
uint8_t mu_dead_step(uint8_t dead, int *die);

/* The fade of a dead character (0x013a5ea1, run before the animation step),
 * verified on its default path: while c + 0x23 > 0 the timer c + 0x1a8 grows
 * by 0.02 per step (0.05 for model 0x7c5 in world 7; models 0x7e5 / 0x940:
 * 0.01 once o + 0x6c >= 100, else 0.02); from 1 on the alpha is 1 - (t - 1)
 * (model 0x819 keeps its alpha); while alpha >= 0.01 the object sinks 0.4
 * per step, then a character other than the hero is removed (live byte 0,
 * c + 0x2a = 0, o + 0x44 = 0, list removal). */
typedef struct mu_fade_state {
    float timer;            /* c + 0x1a8 */
    float alpha;            /* o + 0xdc */
    float z;                /* o + 0x158 + 8 */
    int32_t model;          /* o + 0x5c */
    int32_t world;          /* 0x01cf15fc */
    int32_t o6c;            /* o + 0x6c */
    uint8_t is_hero;
    uint8_t removed;        /* set when the client removes the character */
} mu_fade_state;
void mu_dead_fade(uint8_t dead, mu_fade_state *state);

/* ------------------------------------------------------------------------
 * The hero's own hit, death and attack sounds (NATIVE-COMBAT-002). */

/* Inputs of the Player-model branches of SetPlayerShock 0x0138f92f and
 * SetPlayerDie 0x01393a61 and of SetPlayerAttack's sound tail: the
 * character fields and the answers of the engine services they call. */
typedef struct mu_player_state {
    uint8_t class_byte;       /* c + 0x12 (class = low nibble 0x0095f5cc) */
    uint8_t state_59;         /* 0x0129ddd4(c, 1, 0x59) */
    uint8_t state_5a;         /* 0x0129ddd4(c, 0, 0x5a) */
    uint8_t state_72;         /* 0x0129ddd4(c, 1, 0x72) */
    uint8_t predicate;        /* 0x0139f3db(o) */
    uint8_t class_check;      /* 0x00b99205(class): the second voice set */
    uint16_t transform;       /* 0x0129dcda(c): 0x1a25 silences the voice */
    float field_3324;         /* c + 0x3324: the sound block runs only when it is 0 */
    uint8_t world_voice;      /* 0x009dacb8([0x01cf15fc]) == 1 (SetPlayerDie) */
} mu_player_state;

/* SetPlayerShock 0x0138f92f for the Player model, not riding (0x0106bdb7
 * false), after the gates of mu_shock_action (verified): SetAction 0x136
 * (state 0x59), 0x138 (state 0x5a), 0x13a (state 0x72) or 0x134; then, when
 * c + 0x3324 == 0: 0x7b (mBone1) when the predicate (the skeleton form) is
 * true, else the voice: class nibble 4 with
 * rand() % 5 != 0: 0x1c6 (pDarkPain) unless transformed; class nibble 4 with
 * rand() % 5 == 0 or another class without the class check: 0x69 + rand() %
 * 3 unless transformed; with the class check: 0x6d + rand() % 2 unless
 * transformed. *sound = -1 when nothing plays. rand values in call order;
 * returns the number used. */
int32_t mu_player_shock(const mu_player_state *state, const int32_t *rands, int32_t rand_count, int32_t *action,
                        int32_t *sound);

/* SetPlayerDie 0x01393a61 for the Player model when the predicate is false
 * (verified; the skeleton form's death with its 0x435 / 0x436 effects is not
 * reconstructed): SetAction 0x144 (state 0x59), 0x145 (state 0x5a), 0x147
 * (state 0x72), 0x146 (class nibble 13) or 0x142; then, when c + 0x3324 ==
 * 0: 0x5e + rand() % 2 in the worlds of 0x009dacb8, else the voice 0x1c7
 * (class nibble 4, pDarkDeath), 0x6c (pMaleDie) or 0x6e with the class check
 * (pFemaleScream2), and 0x2b9 as well when transformed; the block then
 * stores c + 0x3324 = 0.001, so the voice plays once. sounds: up to 2. */
int32_t mu_player_die(const mu_player_state *state, const int32_t *rands, int32_t rand_count, int32_t *action,
                      int32_t sounds[2]);

/* SetPlayerAttack's sound for the Player model (verified; 0x01393924): when
 * c + 0x3324 == 0 and the predicate is false (the skeleton form plays the
 * model's sound table instead, not reconstructed): bow 0x55 (eBow), crossbow 0x56
 * (eCrossbow), right-hand items 0x12f3..0x12f4 0x76, items 0xaf0 / 0x10e6
 * 0x3e (eSwingLightSword), any other weapon in either hand 0x3c + rand() % 2
 * (eSwingWeapon1/2), no weapon: nothing. world 0x49 skips it. */
int32_t mu_player_attack_sound(const mu_player_state *state, int32_t bow_kind, int16_t weapon0, int16_t weapon1,
                               int32_t world, const int32_t *rands, int32_t rand_count, int32_t *sound);

/* 0x00b99205(class), static reading: 1 for class nibbles 2, 5, 7, 8, 9, 12
 * and 14 (the second voice set, and SetPlayerMagic's action 0xa5). */
int mu_class_check(uint8_t class_byte);

/* SetPlayerShock's gates before either branch (static, as mu_shock_action):
 * 1 when the reaction runs. */
int mu_shock_gate(uint8_t dead, int32_t action, int32_t damage, int32_t type);

/* ------------------------------------------------------------------------
 * The attack timeline (static readings of MoveCharacter 0x013a85a9 and the
 * per-step attack routine 0x013966ea). An attack starts with AttackTime
 * (c + 0x21) = 1, set with the action by the action packet 0x78/0x79, the
 * magic packets or the hero's own attack (0x01697ec9). Every logic step while
 * AttackTime > 0: 0x013966ea (skill effects of the step; stores the limit
 * [0x01cf1050] = 15, some skills change it), then ++AttackTime; when it
 * reaches the limit the target index is cleared, AttackTime = 0 and the
 * end-of-attack switch on the skill creates the projectiles and impact
 * effects (arrows for bow actions 0x7e..0x81, MODEL_FIRE for Fire Ball, ...). */
#define MU_ATTACK_TIME_LIMIT 15

/* One step of the attack timer: returns 1 on the step whose end-of-attack
 * effects run (AttackTime reached the limit and was reset). */
int mu_attack_time_step(uint8_t *attack_time, int32_t limit);

/* ------------------------------------------------------------------------
 * Skill to visual mapping (static readings of the magic receive handler
 * 0x01253a92, the position-skill handler 0x0125c7b0 and the end-of-attack
 * switch 0x013af035). Skill numbers are the base skill of 0x00bb1c32. */
enum { MU_SKILL_RECEIVE_MAGIC = 1, MU_SKILL_RECEIVE_AREA = 2, MU_SKILL_RECEIVE_ATTACK = 3 };

typedef struct mu_skill_visual {
    int32_t skill;
    const char *name;        /* usual name of the base skill (inference) */
    int32_t receive;         /* MU_SKILL_RECEIVE_* */
    int32_t action;          /* Player action (-1: SetPlayerMagic 0xa1/0xa2 or 0xa5) */
    int32_t effect;          /* end-of-attack CreateEffect type (-1 none), static */
    int32_t effect_subtype;
    int32_t effect_count;
    int32_t arrows;          /* CreateArrows 0x0158d5bd calls at the end of the attack */
    int32_t sound;           /* sound id played by the receive handler (-1 none) */
    int32_t end_sound;       /* sound id of the end-of-attack block (-1 none) */
} mu_skill_visual;

/* The table of the representative subset; returns NULL for other skills. */
const mu_skill_visual *mu_skill_visual_find(int32_t skill);
const mu_skill_visual *mu_skill_visual_at(int32_t index);
int32_t mu_skill_visual_count(void);

#endif
