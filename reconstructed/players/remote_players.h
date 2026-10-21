#ifndef MU_REMOTE_PLAYERS_H
#define MU_REMOTE_PLAYERS_H

/* Other players in the world: the client side of the player viewport
 * (NATIVE-PLAYERS-001, docs/research/client-remote-players.md).
 *
 * The server tells the client about the characters around the hero; the
 * client creates a CHARACTER for each, decodes its class and equipment into
 * the body-part and weapon slots the render reads, and later replays the
 * moves the server sends through the same path follower the hero uses.  The
 * routines (investigator labels; addresses in the pinned restored text):
 *
 *   player viewport  0x0122d413  opcode 0x12: one record per player
 *   CreateCharacter  0x0137f6c2  key -> slot (reuse by key, else first free)
 *   character create 0x0137d8a1  the record and object defaults
 *   class byte       0x0139ca62  packet class byte -> c + 0x12
 *   ChangeCharacterExt 0x0137b68c  the 18 equipment bytes -> part slots
 *     wing switch    0x0137c7df  wing code -> item type, level
 *     helper state   0x0129dc91  the ride state byte c + 0x322c
 *     item level     0x01395741  the 3-bit level code
 *     class skin     0x0139d6a2  class byte -> default part skin index
 *   move packet      0x0126568e  opcode 0x3d: a remote character's new target
 *   remote move step 0x013b852a  MoveCharacters' per-character path replay
 *   viewport destroy 0x01232986  opcode 0x14 -> DeleteCharacter 0x0137c457
 *   store open/close 0x0122e4da / 0x01233b83 (opcode 0x3f) -> hudPlayerName
 *                    setStore 0x00c84731 / 0x00c848fa
 *
 * verified: equals the client's instructions under Unicorn on every compared
 *   case (scripts/validate_players.py): class byte, item level, class skin,
 *   wing switch, helper state, ChangeCharacterExt, the move packet and the
 *   remote move step;
 * static: the viewport record layout and creation effects, the character
 *   create defaults, the destroy/delete path, the store packets (readings of
 *   the decoded instructions that were not executed).
 *
 * CHARACTER fields (c; the OBJECT o = c + 0x3254):
 *   +0x012 class byte, +0x015/+0x016 bytes of the equipment decoder,
 *   +0x017..+0x01b guild bytes, +0x01f PK level, +0x022 direction (move
 *   packet), +0x023 dead counter, +0x02d/+0x02e target tile, +0x031 flag
 *   (teleport instead of a path), +0x038 movement, +0x03c guild index,
 *   +0x03e key, +0x042 server word, +0x14c move speed, +0x14e level,
 *   +0x150/+0x154 max HP / HP, +0x180/+0x184 tile, +0x190 stunned,
 *   +0x1c4 + k * 0x3fc part slot k (0..5 body, 6..7 weapons, 8 wing, 9 muun,
 *   10 helper): +0 type word, +2 level, +3 option, +4 ext;
 *   +0x3194 path, +0x3230, +0x3234 transformed,
 *   +0x3238 three pet item codes, +0x3244 pet index, +0x322c ride state,
 *   +0x322e helper type, +0x31dc, +0x3268 elemental, +0x327c, +0x3330;
 *   o + 0x2a action, o + 0x2c prior action, o + 0x5c model, o + 0x3b kind,
 *   o + 0x158 position, o + 0x164 angles. */

#include <stddef.h>
#include <stdint.h>

#define MU_RP_EQUIP_BYTES 18
#define MU_RP_NAME 11
#define MU_RP_PLAYER_MODEL 0xa91
#define MU_RP_SLOTS 11
#define MU_RP_PATH_CELLS 15

enum {
    MU_RP_SLOT_HEAD = 0, MU_RP_SLOT_HELM = 1, MU_RP_SLOT_ARMOR = 2, MU_RP_SLOT_PANTS = 3, MU_RP_SLOT_GLOVES = 4,
    MU_RP_SLOT_BOOTS = 5, MU_RP_SLOT_WEAPON0 = 6, MU_RP_SLOT_WEAPON1 = 7, MU_RP_SLOT_WING = 8, MU_RP_SLOT_MUUN = 9,
    MU_RP_SLOT_HELPER = 10
};

/* One part slot (c + 0x1c4 + k * 0x3fc). */
typedef struct mu_rp_slot {
    int16_t type;       /* +0 (-1 empty) */
    uint8_t level;      /* +2 */
    uint8_t option;     /* +3 (excellent byte) */
    uint8_t ext;        /* +4 (ancient byte) */
} mu_rp_slot;

/* The path record c + 0x3194 (PATH_t head: current, sub-step, count, cells). */
typedef struct mu_rp_path {
    uint8_t current, current_float, count;
    uint8_t x[MU_RP_PATH_CELLS], y[MU_RP_PATH_CELLS];
} mu_rp_path;

typedef struct mu_rp_character {
    int16_t key;            /* +0x3e */
    uint8_t class_byte;     /* +0x12 */
    uint8_t byte_13;        /* +0x13 */
    uint8_t byte_15;        /* +0x15 */
    uint8_t byte_16;        /* +0x16 */
    uint8_t guild_bytes[5]; /* +0x17..+0x1b */
    uint8_t pk;             /* +0x1f */
    uint8_t direction;      /* +0x22 */
    uint8_t dead;           /* +0x23 */
    uint8_t target[2];      /* +0x2d, +0x2e */
    uint8_t byte_2c;        /* +0x2c */
    uint8_t byte_31;        /* +0x31 */
    uint8_t movement;       /* +0x38 */
    uint8_t byte_39;        /* +0x39 */
    uint8_t byte_0e;        /* +0x0e */
    int16_t guild;          /* +0x3c */
    uint16_t server;        /* +0x42 */
    int16_t class_word;     /* +0x146 (-1 for players) */
    uint16_t move_speed;    /* +0x14c */
    uint16_t level;         /* +0x14e */
    uint32_t max_hp, hp;    /* +0x150, +0x154 */
    int32_t tile[2];        /* +0x180, +0x184 */
    uint8_t stunned;        /* +0x190 */
    uint8_t ride_state;     /* +0x322c */
    uint16_t helper;        /* +0x322e */
    int32_t field_3230;     /* +0x3230 */
    uint8_t transformed;    /* +0x3234 */
    int32_t pets[3];        /* +0x3238 */
    int32_t pet_index;      /* +0x3244 */
    uint8_t byte_31dc;      /* +0x31dc */
    int32_t elemental;      /* +0x3268 (= o + 0x14) */
    uint8_t byte_327c;      /* +0x327c */
    float field_3330;       /* +0x3330 */
    int32_t skill;          /* +0x26 (word) */
    mu_rp_slot slots[MU_RP_SLOTS];   /* the wing level / option / ext are slot 8's +2..+4 (c + 0x21a6..) */
    mu_rp_path path;        /* +0x3194 */
    char name[MU_RP_NAME];  /* +0x3658 (std::string) */
    /* the object */
    int32_t model;          /* o + 0x5c */
    uint16_t action, prior_action;   /* o + 0x2a, o + 0x2c */
    uint8_t kind;           /* o + 0x3b */
    uint8_t live;           /* o + 0 */
    uint8_t byte_43;        /* o + 0x43 */
    float position[3];      /* o + 0x158 */
    float angle[3];         /* o + 0x164 (= c + 0x33b8) */
} mu_rp_character;

/* ---- engine calls the routines make (recorded for comparison) ---- */
enum {
    MU_RP_CALL_C9EA70 = 1,          /* 0x00c9ea70(o) */
    MU_RP_CALL_HELPER_EFFECT_OFF,   /* 0x00b990b0(c, helper type)->0x00eb1015() */
    MU_RP_CALL_SET_LIVE,            /* 0x0129f4a5(object, 0) */
    MU_RP_CALL_HELPER_MODEL,        /* 0x00b990b0(0x1a00 + w, type, position, c, 0, 0)->0x00eb0e78() */
    MU_RP_CALL_EFFECT_24E6,         /* 0x00c9d8df(0x24e6, position, o, 0, 0) */
    MU_RP_CALL_EFFECT_24E6_A14,     /* 0x00c9d42a(0x24e6, position, o, a14, 0, 0) */
    MU_RP_CALL_MOUNT_RESET,         /* 0x009c104e(c)->0x0106ba49() */
    MU_RP_CALL_MOUNT_SET,           /* 0x009c104e(x)->0x0106b85d(c) with x = -1 / helper */
    MU_RP_CALL_HERO_OPTIONS,        /* the hero-only block 0x0137babe (static) */
    MU_RP_CALL_9EBF04,              /* 0x009ebf04(c) */
    MU_RP_CALL_9DADF1,              /* 0x009dadf1(c) */
    MU_RP_CALL_1394F6F,             /* 0x01394f6f(c) */
    MU_RP_CALL_1394870,             /* 0x01394870(c) */
    MU_RP_CALL_PATH,                /* PathFinding2 0x012b0e85(tile, target, &path, 0, mode) */
    MU_RP_CALL_SET_WALK,            /* SetPlayerWalk 0x0139002a(c) */
    MU_RP_CALL_SET_STOP,            /* SetPlayerStop 0x0138fe69(c) */
    MU_RP_CALL_MOVE_PATH,           /* MovePath 0x012b0846(c, 1) */
    MU_RP_CALL_MOVE_POSITION,       /* MoveCharacterPosition 0x0137b351(c) */
    MU_RP_CALL_SET_ACTION,          /* SetAction 0x012affa4(o, action) */
    MU_RP_CALL_SEND_MOVE,           /* SendMove 0x016b5cd0(c, o) (the hero) */
    MU_RP_CALL_AUTO_NEXT,           /* 0x0129cc44(path) (the hero's auto move) */
    MU_RP_CALL_AUTO_REFRESH,        /* 0x0129c51d(path, tile, target) (the hero) */
    MU_RP_CALL_CREATE_ANGLE,        /* CreateAngle 0x012aed9e (model 0x7d9) */
    MU_RP_CALL_TERRAIN_HEIGHT       /* RequestTerrainHeight 0x016cc9e2 (dead model 0x7a7) */
};

typedef struct mu_rp_call {
    int32_t kind;
    int32_t a, b, c, d;
} mu_rp_call;

#define MU_RP_CALLS 32
typedef struct mu_rp_calls {
    mu_rp_call list[MU_RP_CALLS];
    int32_t count;
} mu_rp_calls;

/* Engine state and services the routines use. */
typedef struct mu_rp_env {
    void *context;
    int32_t world;            /* [0x01cf15fc] */
    int32_t scene_state;      /* 0x009b0bc1 on 0x01d1df70 */
    uint8_t is_hero;          /* c == [0x0a39d754] */
    uint8_t hero_key_match;   /* key == [0x06fca288] (the hero's key) */
    uint8_t hero_moving;      /* 0x0095f659()->+8 */
    uint8_t skill_group_7;    /* 0x00961620(c + 0x26)->+0x90 == 7 */
    /* PathFinding2 0x012b0e85(sx, sy, tx, ty, &path, 0.0, mode): returns 1 when a path was found and
     * fills path (the client's path finder over the world's attributes). */
    int (*path_finding2)(void *context, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_rp_path *path, int32_t mode);
    /* MovePath 0x012b0846(c, 1): returns 1 when the path's last cell is reached (the client's spline follower). */
    int (*move_path)(void *context, mu_rp_character *c);
    void (*move_character_position)(void *context, mu_rp_character *c);   /* 0x0137b351 */
    void (*set_player_walk)(void *context, mu_rp_character *c);           /* 0x0139002a */
    void (*set_player_stop)(void *context, mu_rp_character *c);           /* 0x0138fe69 */
    void (*set_action)(void *context, mu_rp_character *c, int32_t action); /* 0x012affa4 */
} mu_rp_env;

void mu_rp_calls_push(mu_rp_calls *calls, int32_t kind, int32_t a, int32_t b, int32_t c, int32_t d);

/* ---- verified helpers ---- */

/* 0x0139ca62: the packet class byte -> c + 0x12. */
uint8_t mu_rp_class_byte(uint8_t packet_class);
/* 0x01395741: the 3-bit level code -> item level (0, 3, 5, 7, 9, 11, 13, 15; 0 above 7). */
int32_t mu_rp_item_level(uint32_t code);
/* 0x0139cb8a: the class tier index (1 for a base class, else the highest set bit of the high nibble + 2). */
uint8_t mu_rp_class_index(uint8_t class_byte);
/* 0x0139d6a2: the default part skin index (low nibble | (tier - 1) << 4). */
uint8_t mu_rp_class_skin(uint8_t class_byte);
/* 0x0137c7df: the wing code of the equipment bytes -> slot 8 (type; level 0, or e[0x11] & 0xf for the listed codes;
 * option and ext 0 when there is no wing). */
void mu_rp_wing(const uint8_t e[MU_RP_EQUIP_BYTES], mu_rp_character *c);
/* 0x0129dc91: the ride state c + 0x322c from e[0x10] bit 0 (4) or e[0xf] & 3. */
void mu_rp_helper_state(const uint8_t e[MU_RP_EQUIP_BYTES], mu_rp_character *c);
/* ChangeCharacterExt 0x0137b68c(index, e, c, a14) for a Player-model character (does nothing for other
 * models): weapons, the helper (pet) type, the wing, the body parts with their levels, options and ext
 * bytes, the ride state and the engine calls listed above. a14 is the fourth argument (an object or 0). */
void mu_rp_change_equipment(mu_rp_character *c, const uint8_t e[MU_RP_EQUIP_BYTES], int32_t a14,
                            const mu_rp_env *env, mu_rp_calls *calls);

/* ---- the move packet and the remote step (verified) ---- */

/* Opcode 0x3d, 0x0126568e(packet): key at +3/+4 (big endian), target at +5/+6, direction at +7 (high
 * nibble).  Dead or unknown characters are ignored.  The hero's branch (hero_key_match and not
 * hero_moving) only records its calls.  Returns 1 when the character was found. */
int mu_rp_move_packet(const uint8_t *packet, mu_rp_character *c, const mu_rp_env *env, mu_rp_calls *calls);

/* 0x013b852a(c, o), the per-character movement MoveCharacters runs for every character but the hero. */
void mu_rp_move_step(mu_rp_character *c, const mu_rp_env *env, mu_rp_calls *calls);

/* ---- static readings ---- */

/* One record of the player viewport (opcode 0x12), 0x44 + 8 * buff count bytes. */
typedef struct mu_rp_viewport {
    int32_t size;
    uint16_t key;             /* bits 0..14 */
    uint8_t created;          /* bit 15: the character appeared here (no walk-in) */
    uint8_t x, y;             /* +2, +3 */
    uint8_t packet_class;     /* +4 */
    uint8_t equipment[MU_RP_EQUIP_BYTES];   /* +5 */
    char name[MU_RP_NAME];    /* +0x18, 10 characters */
    uint8_t target[2];        /* +0x22, +0x23 */
    uint8_t direction;        /* +0x24 >> 4 */
    uint8_t pk;               /* +0x24 & 0xf */
    uint8_t elemental;        /* +0x25 */
    uint16_t pet_code[3];     /* +0x26 + 3 * i (big endian word) */
    uint8_t pet_level[3];     /* +0x28 + 3 * i */
    uint8_t pet_index;        /* +0x2f */
    uint16_t helper;          /* +0x30 (big endian) */
    uint8_t byte_32;          /* +0x32 */
    uint16_t server;          /* +0x3e (little endian word) */
    uint8_t flags;            /* +0x40: bit 0 stunned, bits 1..6 -> c + 0x3230, bit 7 transformed */
    uint8_t muun, muun_level; /* +0x41, +0x42 */
    uint8_t buff_count;       /* +0x43 */
    uint16_t buff_type[56];   /* +0x44 + 8 * i */
    uint32_t buff_value[56];  /* +0x48 + 8 * i */
    uint8_t pose_state;       /* equipment[0x10] >> 5 & 7 */
} mu_rp_viewport;
int mu_rp_viewport_record(const uint8_t *p, int32_t avail, mu_rp_viewport *v);
/* The character create 0x0137d8a1(c, model, x, y, angle): the defaults of the record and object (static). */
void mu_rp_character_create(mu_rp_character *c, int16_t key, int32_t model, uint8_t x, uint8_t y, float angle);
/* The viewport's SetAction for the pose state 2..4 (0x0122d6a9): class_check = 0x00b99205(class byte),
 * ride_59/5a/72 = 0x0129ddd4(c, 1, 0x59) / (c, 0, 0x5a) / (c, 1, 0x72).  Returns -1 for other states. */
int32_t mu_rp_viewport_pose_action(int32_t state, int class_check, int ride_59, int ride_5a, int ride_72);
/* The angle the viewport stores at c + 0x33b8 + 8: (direction - 1) * 45. */
float mu_rp_viewport_angle(uint8_t direction);
/* The creation part of the player viewport (static): the record's fields into a created character, the
 * created / path / teleport placement through env->path_finding2 (mode 2, or 4 in worlds 0x52..0x5a). */
void mu_rp_viewport_apply(const mu_rp_viewport *v, mu_rp_character *c, const mu_rp_env *env, mu_rp_calls *calls);

/* Opcode 0x14 (0x01232986): count at +3, keys (big endian, bit 15 dropped) from +4.  Returns the number
 * of keys written (at most max). */
int32_t mu_rp_destroy_keys(const uint8_t *packet, int32_t avail, uint16_t *keys, int32_t max);
/* DeleteCharacter 0x0137c457 (static): the live byte and the overhead plate (removeInfo unless the world
 * is one of 0x009dacb8's). Returns 1 when removeInfo runs. */
int mu_rp_delete_character(mu_rp_character *c, int32_t world);
/* 0x009dacb8(world): worlds 0x12..0x17, 0x35, 0x61. */
int mu_rp_world_rule(int32_t world);

/* Opcode 0x3f sub 2 (0x0122e4da): count at +5, records of 0x2f bytes from +6: key (big endian) and a title
 * of up to 0x2d characters.  Returns the number of records written. */
typedef struct mu_rp_store {
    uint16_t key;
    char title[0x2e];
} mu_rp_store;
int32_t mu_rp_store_records(const uint8_t *packet, int32_t avail, mu_rp_store *out, int32_t max);
/* setStore 0x00c84731: the "id" member "<font color='PK colour'>name</font>" (static). */
void mu_rp_store_id_html(const char *pk_color, const char *name, char *out, size_t cap);

#endif
