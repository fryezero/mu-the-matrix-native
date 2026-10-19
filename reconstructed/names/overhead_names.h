#ifndef MU_OVERHEAD_NAMES_H
#define MU_OVERHEAD_NAMES_H

/* Overhead text of characters, monsters and NPCs: the game side of the GFx
 * movie hudPlayerName (NATIVE-NAMES-001, docs/research/client-overhead-text.md).
 *
 * The client does not draw names, HP bars or chat bubbles in its 3D/2D layer:
 * the hudPlayerName movie does (classes PlayerName / PlayerNameMC,
 * MonsterName / MonsterInfoMC, HudChat, PlayerStore, ItemNameMC).  Its game
 * handler (vtable 0x01a86478, constructor 0x00afaff8) builds the data and
 * places the movie clips:
 *
 *   addInfo     0x00c82fd1  on character creation (viewport and join packets)
 *   update      0x00c81d1e  every frame (vtable +0x0c): visibility, HP, guild,
 *                           gens, elemental, server name, position
 *   head height 0x00c8526e  the height above the object origin
 *   removeInfo  0x00c83a04  character deletion, SetPlayerDie, the dead fade
 *   setHp       0x00c83afa  the monster HP packet and SetPlayerDie
 *   setTopMovie 0x00c83c9a  the character under the cursor (0x01cf1154)
 *   monster view 0x00c83c86 the option "monster info" (byte +0x44)
 *   setMessage  0x00c83d2a  chat bubbles, from 0x0169d87f (chat receive)
 *
 * Names are investigator labels.  Functions marked verified equal the
 * client's instructions under Unicorn (scripts/validate_names.py); the others
 * are static readings.  Binary32 SSE arithmetic in source order: build with
 * -ffp-contract=off.
 *
 * CHARACTER fields read (c; object o = c + 0x3254):
 *   +0x012 class byte, +0x019 guild relation, +0x01e gens family, +0x01f PK
 *   level, +0x03c guild index (word, -1 none), +0x03e key (word), +0x044
 *   server name (char array), +0x146 monster class (word, -1 players),
 *   +0x14e level (word), +0x150 max HP, +0x154 HP (unsigned), +0x158 name
 *   height (word), +0x15c mark, +0x21a4 wing (word, -1 none), +0x322e ride
 *   item (word, 0xffff none), +0x3268 = o+0x14 elemental, +0x3274 = o+0x20
 *   four resistance words, +0x328f kind (1 player, 2 monster/NPC), +0x33ac =
 *   o+0x158 position, +0x362c gens rank, +0x363c name kind, +0x3640 duel
 *   partner name (std::string), +0x3658 name (std::string). */

#include <stddef.h>
#include <stdint.h>

#define MU_HN_TEXT 256           /* our bound for names and HTML (std::string in the client) */
#define MU_HN_ENTRIES 400        /* our bound (the client's maps grow; 400 characters exist) */
#define MU_HN_OPS 64             /* our bound of operations per character and frame */

enum { MU_HN_PLAYER = 1, MU_HN_MONSTER = 2 };

typedef struct mu_hn_character {
    int16_t key;                 /* +0x3e */
    int16_t guild;               /* +0x3c */
    uint8_t class_byte;          /* +0x12 */
    uint8_t guild_relation;      /* +0x19 */
    uint8_t gens;                /* +0x1e */
    uint8_t pk;                  /* +0x1f */
    uint8_t kind;                /* +0x328f */
    uint8_t live;                /* o + 0 */
    uint8_t gens_rank;           /* +0x362c */
    int16_t monster_class;       /* +0x146 */
    uint16_t level;              /* +0x14e */
    uint16_t height;             /* +0x158 */
    int16_t wing;                /* +0x21a4 */
    uint16_t ride;               /* +0x322e */
    uint16_t resist[4];          /* +0x3274 */
    uint32_t max_hp, hp;         /* +0x150, +0x154 */
    int32_t mark;                /* +0x15c */
    int32_t elemental;           /* +0x3268 */
    int32_t name_kind;           /* +0x363c: 0 name, 1 name[level], 2 name[level+600] */
    float position[3];           /* o + 0x158 */
    char server[MU_HN_TEXT];     /* +0x44 */
    char duel_name[MU_HN_TEXT];  /* +0x3640 */
    char name[MU_HN_TEXT];       /* +0x3658 */
} mu_hn_character;

/* One record of the info map (handler +0x4c, std::map<int, entry>; the
 * entry constructor 0x00c8734a sets the defaults noted). */
typedef struct mu_hn_entry {
    int32_t key, type;           /* +0x00 (-1), +0x04 (0) */
    char name[MU_HN_TEXT];       /* +0x20 the name HTML */
    float x, y;                  /* +0x38, +0x3c last position (0) */
    int32_t hp;                  /* +0x40 (0) */
    uint8_t show;                /* +0x44 (1) */
    int32_t elemental;           /* +0x48 (0) */
    int32_t att[4];              /* +0x4c */
    uint8_t damage_type[3];      /* +0x5c (0) */
    uint8_t hp_show, name_show, strife;   /* +0x5f, +0x60, +0x61 (0) */
    int32_t gens;                /* +0x64 (0) */
    char guild[MU_HN_TEXT];      /* +0x70 */
    char server[MU_HN_TEXT];     /* +0x88 */
    uint8_t flag_a0;             /* +0xa0 (0; no writer found) */
    uint8_t has_mc;              /* the movie clip map +0x54 holds the key (the movie's addMC event) */
    uint8_t addinfo_show;        /* the isShow addInfo sent (ours) */
    uint8_t mc_visible;          /* the clip's _visible as the movie set it (PlayerName.setData: isShow) */
} mu_hn_entry;

/* The handler object (constructor 0x00afaff8). */
typedef struct mu_hn_window {
    int32_t item_height;         /* +0x1c 35  (item labels, NATIVE-ITEMS-001) */
    int32_t item_offset;         /* +0x20 5 */
    int32_t height_player;       /* +0x24 180 */
    int32_t height_wing;         /* +0x28 205 */
    int32_t height_ride_a;       /* +0x2c 220 */
    int32_t height_ride_b;       /* +0x30 225 */
    int32_t height_ride_c;       /* +0x34 280 */
    int32_t height_ride;         /* +0x38 240 */
    int32_t height_state;        /* +0x3c 300 */
    int32_t height_ride_d;       /* +0x40 320 */
    uint8_t monster_view;        /* +0x44 1 */
    int32_t selected;            /* +0x48 -1 */
    uint8_t item_view;           /* +0x5c 1 */
    int32_t count;
    mu_hn_entry entries[MU_HN_ENTRIES];   /* ascending key, as std::map iterates */
} mu_hn_window;

/* Globals and host answers the routines read. */
typedef struct mu_hn_env {
    void *context;
    const mu_hn_character *hero;          /* [0x0a39d754] */
    int32_t hero_level;                   /* 0x00a00367 on [0x01d1df1c]: level + master level */
    int32_t hero_hp, hero_max_hp;         /* [0x01d1df1c] +0x68, +0x40 */
    int32_t duel_key;                     /* [0x06fca290] */
    int32_t duel_hp;                      /* [0x06fca28c] */
    int32_t world;                        /* [0x01cf15fc] */
    uint8_t name_option;                  /* [[0x01d22c7c]] + 0x23: show player names */
    uint8_t hero_bar_a, hero_bar_b;       /* [0x01d1dcc8] + 0x8c, [0x01d1dbac] + 4: the hero's own HP bar */
    uint8_t server_flag;                  /* 0x0095f75d()->0x0095fb99() == 1 */
    uint8_t gens_option;                  /* 0x0095c652(0x5c, 5)->0x00d7b3ce() */
    uint8_t hero_gm;                      /* 0x016a83da */
    uint8_t gens_world;                   /* 0x016bec9f(world) */
    const char *gt_level_format;          /* GlobalText[4595] (0x011753c3), "%s[%d]" when NULL */
    /* 0x0184a3ce: world position to window pixels (float) */
    void (*project)(void *context, const float position[3], float *x, float *y);
    /* 0x0106b9f7 on the manager 0x01d1dce0 with (c, 2, 1) */
    int (*state2)(void *context, const mu_hn_character *c);
    /* 0x0114282c on 0x06fbb664 (monster class, i < 3): the monster's damage types */
    int (*damage_type)(void *context, int32_t monster_class, int32_t i);
    /* the guild table 0x0b44a6f4 (0x58-byte records): name +9, second name +0 */
    void (*guild)(void *context, int32_t index, const char **name, const char **second);
    /* the party window (0x00c7955f by name): member found -> HP percentage (+0x18) */
    int (*party_hp)(void *context, const char *name, int32_t *hp);
} mu_hn_env;

/* GFx operations the routines perform, in order. */
enum {
    MU_HN_OP_INFO_VISIBLE = 1,   /* mc._info SetDisplayInfo visible (number) */
    MU_HN_OP_MC_VISIBLE,         /* mc SetDisplayInfo visible 1 */
    MU_HN_OP_NAME_SHOW,          /* mc._info.setPlayerNameShow(bool) */
    MU_HN_OP_SET_HP,             /* mc._info.setHp(number) (update) or mc.setHp (setHp 0x00c83afa) */
    MU_HN_OP_HP_SHOW,            /* mc._info.setHpShow(bool) */
    MU_HN_OP_HP_VISIBLE,         /* mc._info._hp SetDisplayInfo visible (number) */
    MU_HN_OP_ELEMENTAL,          /* mc._info.setElemental(number) */
    MU_HN_OP_GENS,               /* mc._info.setGensFrame(number) */
    MU_HN_OP_GUILD,              /* mc._info.setGuildName(text) */
    MU_HN_OP_SERVER,             /* mc._info.setServerName(text) */
    MU_HN_OP_STRIFE,             /* mc._info.setStrifeGens(bool) */
    MU_HN_OP_POSITION,           /* mc SetDisplayInfo x, y (doubles) and visible 1 */
    MU_HN_OP_TOP,                /* mc.setTopMovie() */
    MU_HN_OP_MESSAGE,            /* mc.setMessage({msg, time}) */
    MU_HN_OP_REMOVE,             /* movie.removeInfo({key, type}) */
};

typedef struct mu_hn_op {
    int32_t key, kind;
    double number, y;            /* the value; POSITION: x and y */
    char text[MU_HN_TEXT];
} mu_hn_op;

/* The members of addInfo's argument, in the client's order. */
typedef struct mu_hn_info {
    int32_t key, type;
    char name[MU_HN_TEXT], guild[MU_HN_TEXT], server[MU_HN_TEXT];
    int32_t elemental, mark;
    float x, y;
    int32_t hp;
    uint8_t is_show, hp_show, name_show, strife;
    int32_t gens_frame;
    int32_t att[4];
    uint8_t damage_type[3];
} mu_hn_info;

/* ---- the handler ---- */

/* Constructor 0x00afaff8 (static reading). */
void mu_hn_window_init(mu_hn_window *w);
mu_hn_entry *mu_hn_find(mu_hn_window *w, int32_t key);
/* The movie's addMC / delMC events (handler 0x00c81842): the movie clip of a key exists. */
void mu_hn_set_mc(mu_hn_window *w, int32_t key, int has_mc);

/* ---- helpers (verified) ---- */

int32_t mu_hn_head_height(const mu_hn_window *w, const mu_hn_character *c, const mu_hn_env *env);  /* 0x00c8526e */
/* 0x00c84d8a: the plain name, "%s[%d]" with the level, or with level + 600. */
void mu_hn_name_text(const mu_hn_character *c, const mu_hn_env *env, char *out, size_t cap);
const char *mu_hn_class_color(int32_t index);                                         /* 0x00c84f00 */
const char *mu_hn_pk_color(int32_t pk);                                               /* 0x00c8502c */
const char *mu_hn_guild_color(const mu_hn_character *c, const mu_hn_env *env);        /* 0x00c85093 */
void mu_hn_guild_text(const mu_hn_character *c, const mu_hn_env *env, char *out, size_t cap);  /* 0x00c8510c */
int32_t mu_hn_gens_frame(const mu_hn_character *c, const mu_hn_env *env);             /* 0x00c84d08 */
int mu_hn_strife_gens(const mu_hn_character *c, const mu_hn_env *env);                /* 0x00c851f4 */
/* cvttss2si: truncation, 0x80000000 for NaN and out-of-range values. */
int32_t mu_hn_cvtt(float value);
/* HP percentage of addInfo and setHp: (float)(double)hp / (float)(double)max * 100, truncated. */
int32_t mu_hn_hp_percent(uint32_t hp, uint32_t max);

/* SetMonsterInfo 0x013b8ade (verified for the kind; static for the rest):
 * the object kind of a monster class: 2 monster, 4 NPC, 8 trap, 0x80 other.
 * The routine also copies the Npcname(kor) record (name 0x011427c7, name
 * height +0x1c -> c + 0x158, mark +0x20 -> c + 0x15c, byte +0x24 -> o + 0x10).
 * hudPlayerName takes kinds 1 and 2 only: NPCs get no name plate. */
uint8_t mu_hn_monster_kind(int32_t monster_class);

/* ---- the routines ---- */

/* addInfo 0x00c82fd1 (verified).  Returns 1 and fills info when the movie
 * gets addInfo (the entry is inserted), 0 when skipped (kind not 1/2, a
 * player of class 0x396, the key already present). */
int mu_hn_add_info(mu_hn_window *w, const mu_hn_character *c, const mu_hn_env *env, mu_hn_info *info);
/* Writes addInfo's argument as JSON (the member order of the client). */
size_t mu_hn_info_json(const mu_hn_info *info, char *out, size_t cap);

/* The per-frame update 0x00c81d1e, character part (verified): for every key
 * with a movie clip (ascending) whose entry exists and whose character the
 * lookup returns, the visibility, HP, name option, elemental, gens, guild,
 * server and strife updates, then the position.  `character(context, key)`
 * is the key -> character lookup (0x0137c724, 0x0095f6db, 0x009a13f4).
 * Returns the number of operations written (at most max). */
int32_t mu_hn_update(mu_hn_window *w, const mu_hn_character *(*character)(void *context, int32_t key),
                     const mu_hn_env *env, mu_hn_op *ops, int32_t max);

/* setHp 0x00c83afa (verified): 0 or 1 operation. */
int32_t mu_hn_set_hp(mu_hn_window *w, int32_t key, uint32_t hp, uint32_t max, mu_hn_op *op);
/* removeInfo 0x00c83a04 (verified): erases the entry, 1 operation when it existed. */
int32_t mu_hn_remove(mu_hn_window *w, const mu_hn_character *c, mu_hn_op *op);
/* setTopMovie handler 0x00c83c9a (verified): selected = key; 1 operation when shown. */
int32_t mu_hn_select(mu_hn_window *w, int32_t key, mu_hn_op *op);
/* 0x00c83c86 (static): the monster info option. */
void mu_hn_set_monster_view(mu_hn_window *w, int view);

/* The tick's selection wrapper 0x009a1618 (static): `current` (the wrapper's
 * +0xc) follows the character under the cursor; up to two operations. */
int32_t mu_hn_track_selection(mu_hn_window *w, const mu_hn_character **current, const mu_hn_character *hovered,
                              mu_hn_op *ops);

/* Chat bubble 0x0169d87f + setMessage 0x00c83d2a (verified): the first live
 * character (of n, in order) whose name equals `name` gets "name: text" for
 * 40000 ms when flag == 1, else 10000 ms.  Returns 1 with the operation, 0
 * when no character or movie clip matches. */
int32_t mu_hn_chat_bubble(mu_hn_window *w, const mu_hn_character *const *characters, int32_t n, const char *name,
                          const char *text, int32_t flag, mu_hn_op *op);

/* The chat receive handler 0x00c6066a (static reading): prefix rules.
 * Returns the chat type the chat window gets and sets *bubble_flag to -1 (no
 * bubble), 0 (10 s) or 1 (40 s), *skip to the prefix length removed. */
int32_t mu_hn_chat_route(const char *text, int gm, int32_t *bubble_flag, int32_t *skip);

#endif
