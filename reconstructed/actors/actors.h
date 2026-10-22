#ifndef MU_ACTORS_H
#define MU_ACTORS_H

#include <stdint.h>

#include "../model-codec/pose_builder.h"
#include "../model-codec/skinning.h"

/* Authored reconstructions of the client routines that turn a monster or NPC
 * type into a model and give its actions their playback speeds, and of the
 * per-frame speed choice in front of the animation tick 0x012b4dd3. Names
 * are investigator labels, not recovered original symbols. See
 * docs/research/client-actors.md.
 *
 *   0x0180b0f4  mu_monster_open             OpenMonsterModel(type), cdecl
 *   0x013960d2  mu_character_animation_speed  speed choice + tick, cdecl (c, o)
 *
 * Client layouts used (byte offsets):
 *   model (BMD, 0xd0 bytes): +0x24 int16 mesh count, +0x26 int16 action count,
 *     +0x30 u32 action array, +0x60 int32 head bone, +0xa8 u16 current action;
 *   action record (stride 0x10): +0 u8 loop (the tick's stop flag), +4 binary32
 *     play speed, +8 int16 key count, +0xa u8 lock flag.
 * Model records are found through the model container: 0x00966cc4 returns the
 * container and 0x00eaa8cf(index) the model for an index (0 .. 0x3af6). */

enum {
    MU_ACTOR_OK = 0,
    MU_ACTOR_OUTSIDE_MEMORY = 2,
    /* The client would dereference a null action pointer (GetAction or
     * ActionAt on an action index outside the model's action count). */
    MU_ACTOR_CLIENT_FAULT = 3
};

#define MU_MONSTER_MODEL_BASE 0x7a5u    /* model index = type + 0x7a5 */
#define MU_MONSTER_TYPE_COUNT 0x259u    /* types whose index stays below the first NPC model 0x9fe */
#define MU_MONSTER_WORLD 0x01cf15fcu    /* int32 world number read by the texture choice */

/* Engine services the opener calls. model_at returns the client address of
 * the model for an index (0x00eaa8cf) or 0. access_model loads the file
 * (AccessModel 0x018202b4: "<dir><name><nn>.bmd", "%s0%d.bmd" below 10, else
 * "%s%d.bmd") and must leave the model's counts and action array in client
 * memory. open_texture is OpenTexture 0x0181fbe9. */
typedef struct mu_monster_services {
    void *context;
    uint32_t (*model_at)(void *context, uint32_t index);
    void (*access_model)(void *context, uint32_t index, const char *directory, const char *name, int32_t number);
    void (*open_texture)(void *context, uint32_t index, const char *directory, uint32_t wrap, uint32_t filter);
} mu_monster_services;

/* OpenMonsterModel 0x0180b0f4 without its sound and extra texture loads:
 *   index = type + 0x7a5; model = model_at(index); return when 0 or when the
 *   model already has actions or meshes;
 *   access_model(index, "Data\\Monster\\", "Monster", type + 1);
 *   return when it has no meshes; open_texture(index, dir, 0x2901, 0x2600)
 *   with dir "Npc\\" for types 0x46..0x48 in worlds 0x12..0x17, 0x35, 0x61,
 *   "Object31\\" for type 0x4a in world 30, "Monster\\" otherwise;
 *   default speeds through SetActionSpeed 0x012bd437 (checked against the
 *   action count): 0.25, 0.2, 0.34, 0.33, 0.33, 0.5, 0.55 for actions 0..6,
 *   and SetActionLoop 0x012bd471(6, 1);
 *   for actions 0..5 (unchecked): type 3 x1.2, types 5 and 25 x0.7,
 *   types 37, 42 and 0x1ab x0.4 (binary32 multiply);
 *   then the generated per-type operations (monster_open_table.h), in client
 *   order. Direct stores into the action array are not checked against the
 *   action count, as in the client. */
int mu_monster_open(const mu_client_memory *memory, int32_t type, int32_t world, const mu_monster_services *services);

/* Model file the opener asks for: "Data\\Monster\\Monster<nn>.bmd", nn =
 * type + 1 written with AccessModel's rule. Returns 0 for types outside
 * 0 .. MU_MONSTER_TYPE_COUNT - 1. */
int mu_monster_model_file(int32_t type, char *out, uint32_t size);

/* NATIVE-ITEMS-001: the ten model sound slots (model +0xb6) OpenMonsterModel
 * sets through SetMonsterSound 0x018329fa for the model of monster type
 * `type` (model index 0x7a5 + type; extracted table monster_sound_table.h).
 * Returns 1 and fills out, or 0 (out all -1) when no opener sets them. */
int mu_monster_sound_slots(int32_t type, int16_t out[10]);

/* ------------------------------------------------------------------ */
/* Character animation step 0x013960d2 (cdecl, arguments character, object;
 * returns AL). Callers 0x013a763e and 0x013a6e64 pass a character record and
 * its object (character + 0x3254 in the creation code).
 *
 * Object fields: +0x2a u16 action, +0x2c u16 prior action, +0x5c int32 model
 * index, +0xd0 binary32 frame, +0xd4 binary32 prior frame, +0x158 position,
 * +0x164 angles, +0x358 buff container. Character fields: +0xe u8 flag that
 * speeds up actions 3..4 (x1.5), +0x12 u8 class byte, +0x180/+0x184 int32
 * tile x/y. */
#define MU_TERRAIN_ATTRIBUTES 0x0b795420u   /* u16[256 * 256] terrain attribute map */

typedef struct mu_character_services {
    void *context;
    uint32_t (*model_at)(void *context, uint32_t index);                 /* 0x00eaa8cf */
    uint8_t (*has_buff)(void *context, uint32_t buffs, uint32_t buff);   /* 0x01295ade (thiscall on object+0x358) */
    uint8_t (*weapon_check)(void *context, uint32_t character);          /* 0x0129deaa .. 0x00c7974e chain, AL */
    void (*stop)(void *context, uint32_t character);                     /* 0x0138fe69 */
} mu_character_services;

/* speed = Actions[model+0xa8].speed when the model has actions (else 0),
 * clamped to >= 0 (NaN kept), then the per-action and per-model factors
 * listed in docs/research/client-actors.md. Any of the buffs 0x3d, 0x48,
 * 0xb2, 0x118 returns 0 before the tick. Otherwise the reconstructed tick
 * mu_animation_tick runs with &object+0xd0, +0xd4, +0x2c and the speed; a
 * finished loop of action 0x184, 0xd9 or 0x125 (and action 0x170 on a tile
 * whose attribute has bit 4) calls stop(character). *result receives the
 * returned AL, *speed the speed passed to the tick (0 when it did not run). */
int mu_character_animation_step(const mu_client_memory *memory, uint32_t character, uint32_t object,
                                const mu_character_services *services, const mu_tick_globals *globals,
                                uint8_t *result, float *speed);

/* ------------------------------------------------------------------ */
/* SetAction 0x012affa4 (cdecl, arguments object, action). Does nothing when
 * model_at(object+0x5c) is 0, when action >= (int16)model+0x26 (a signed
 * compare: negative actions pass) or when the action is already current.
 * Otherwise: prior action (+0x2c) = action (+0x2a), prior frame (+0xd4) =
 * frame (+0xd0) copied as a dword, action = new value (u16), frame = 0. */
int mu_set_action(const mu_client_memory *memory, uint32_t object, int32_t action,
                  uint32_t (*model_at)(void *context, uint32_t index), void *context);

/* 0x0139d6da: the stop action of an unarmed player for a class byte (low
 * nibble = base class): 2 -> 2, 7 -> 5, 8 -> 6, 14 -> 6, 11 -> 1;
 * 5 -> 1 in the worlds of 0x009dacb8 (0x12..0x17, 0x35, 0x61) else 3;
 * 9 -> 1 there else 6; 12 -> 1 there else 2; 10 -> 1 there, else 0x1f when
 * rand() % 20 == 0, else 1; 15 -> 8 there, else 9 when rand() % 20 == 0,
 * else 8; any other class 1. rand is called only on those two paths. */
int32_t mu_player_unarmed_stop_action(uint8_t class_byte, int32_t world, int32_t (*rand_function)(void *context),
                                      void *context);

/* ------------------------------------------------------------------ */
/* Player actions.
 *
 * Base play speed and loop flag of a Player action (extracted from the speed
 * section of the player loader 0x01830aa6 under emulation; 0 / not written
 * speeds return 0). The hero attack-speed adjustment 0x0138d9cf is not
 * applied. */
float mu_player_action_speed(int32_t action);
int mu_player_action_loop(int32_t action);
#define MU_PLAYER_ACTION_TOTAL 0x186

/* Pose -> Player action. STATIC READING ONLY (not executed): the branch
 * structure of SetPlayerStop 0x01391e55, the walk chooser 0x0139002a and
 * SetPlayerAttack 0x01392bde, reduced to a weapon kind. In the client the
 * kind comes from the weapon item index (0xae6 + 512*group: swords, axes,
 * maces < 0x10e6, spears < 0x12e6, bows/crossbows < 0x14e6, staffs < 0x16e6)
 * and item-attribute bytes (+0x251 kind, +0x253 two-handed) that are runtime
 * item data, plus mounts, buffs, safe zones and special items that are not
 * modelled here. Unarmed stand is the validated 0x0139d6da with rand() fixed
 * to 1; the attack combo counter (character +0x28) and rand() are taken as 0. */
enum { MU_POSE_STAND = 0, MU_POSE_WALK = 1, MU_POSE_ATTACK = 2 };
enum {
    MU_WEAPON_NONE = 0, MU_WEAPON_ONE_HAND = 1, MU_WEAPON_TWO_HAND = 2, MU_WEAPON_SPEAR = 3,
    MU_WEAPON_STAFF = 4, MU_WEAPON_TWO_HAND_STAFF = 5, MU_WEAPON_BOW = 6, MU_WEAPON_CROSSBOW = 7
};
int32_t mu_player_pose_action(int pose, int weapon, uint8_t class_byte, int32_t world);

/* ------------------------------------------------------------------ */
/* Server monster class -> model (CreateMonster 0x0137fbac) and NPC model
 * files (OpenNpc 0x01808a40). These two tables are extracted by executing
 * the client routines under Unicorn (scripts/validate_actors.py), not
 * reconstructed code; see docs/research/client-actors.md for the assumptions
 * (world 0, rand() = 0, world-specific map processors declining). */
enum {
    MU_CLASS_MONSTER = 1,       /* OpenMonsterModel(type); model = type + 0x7a5 */
    MU_CLASS_NPC = 2,           /* OpenNpc(index); model = index */
    MU_CLASS_PLAYER_MODEL = 3,  /* CreateCharacter with the Player model 0xa91 and part slots */
    MU_CLASS_OTHER = 4,         /* no opener call observed */
    MU_CLASS_DEFAULT = 5        /* switch default: unknown class shown as monster type 0 */
};

typedef struct mu_monster_class {
    uint16_t server_class;
    uint8_t kind;
    uint16_t model;             /* model index passed to CreateCharacter 0x0137f6c2 */
    uint16_t opened;            /* OpenMonsterModel type or OpenNpc index */
    uint32_t scale_bits;        /* object +0xa0; 0 = not written (character create leaves 0.9) */
    struct { uint16_t type; uint8_t level; } slots[9];  /* character +0x1c4 + k*0x3fc; slot 8 = wing */
    uint8_t class_byte;         /* character +0x12, when the class creation writes it */
} mu_monster_class;

typedef struct mu_monster_class_speed {
    uint16_t server_class;
    uint16_t model;
    uint8_t action;
    uint32_t speed_bits;        /* 0x7fc0dead: speed not written (loop only) */
    uint8_t loop;
} mu_monster_class_speed;

typedef struct mu_npc_model {
    uint16_t index;
    const char *directory;
    const char *name;
    int32_t number;             /* -1: "<name>.bmd" */
    uint32_t speed_bits[16];    /* 0 = not written */
} mu_npc_model;

const mu_monster_class *mu_monster_class_find(uint32_t server_class);
const mu_monster_class_speed *mu_monster_class_speeds_for(uint32_t server_class, uint32_t *count);
const mu_npc_model *mu_npc_find(uint32_t index);
/* Object scale for a class row (0.9 when CreateMonster leaves it). */
float mu_monster_class_scale(const mu_monster_class *row);
/* AccessModel 0x018202b4 file name: "<dir><name>.bmd" for number -1,
 * "<dir><name>0<n>.bmd" below 10, "<dir><name><n>.bmd" otherwise. */
int mu_access_model_file(const char *directory, const char *name, int32_t number, char *out, uint32_t size);

/* Generated operation record (see monster_open_table.h). */
enum {
    MU_MONSTER_OP_SPEED = 1,        /* SetActionSpeed(action, value) on the model, checked */
    MU_MONSTER_OP_LOOP = 2,         /* SetActionLoop(action, value) on the model, checked */
    MU_MONSTER_OP_ACTION_SPEED = 3, /* GetAction/ActionAt(action)->speed = value; null when out of range */
    MU_MONSTER_OP_RAW32 = 4,        /* Actions[action] + offset = value (u32), unchecked */
    MU_MONSTER_OP_RAW8 = 5,         /* Actions[action] + offset = value (u8), unchecked */
    MU_MONSTER_OP_FIELD32 = 6,      /* model + offset = value (u32) */
    MU_MONSTER_OP_FIELD8 = 7        /* model + offset = value (u8) */
};

typedef struct mu_monster_op {
    uint8_t kind;
    int16_t model;      /* index relative to the opened model */
    uint8_t action;
    uint8_t offset;
    uint32_t value;
} mu_monster_op;

/* Number of generated operations for a type and a pointer to them (NULL when
 * the type is outside the table). */
const mu_monster_op *mu_monster_type_ops(int32_t type, uint32_t *count);

#endif
