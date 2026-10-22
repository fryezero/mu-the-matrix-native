/* Character progression and the in-game options of the client (NATIVE-PROGRESS-001,
 * docs/research/client-progression.md).
 *
 * Pinned inputs: restored text capture09 (2bd5f2e9...3724) at 0x00401000 and the second image
 * section run10 (c985e2e6...a0672f) at 0x01a7c000.
 *
 * Client pieces restated in C (each says whether scripts/validate_progress.py ran it against the
 * client's instructions in Unicorn, "verified", or whether it is a reading of them, "static"):
 *
 *   - the hero's attribute record (CharacterAttribute, the global 0x01d1df1c, = CharacterMachine
 *     [0x01d1df18] + 8): level, experience, master level, the five stats, the derived values;
 *   - the class formula of the stat machine (CharacterMachine +0x2d98, one class per class index,
 *     created by 0x00a0088d; vtable slot 0 of the 16 classes) and the stat totals 0x0098d2c4;
 *   - the experience bar of the main HUD movie (setExpData, 0x00c5125b);
 *   - the server's answers: level up (opcode 0xA0 sub 0x06, 0x01250b05), the stat point answer
 *     (0xA0 sub 0x11, 0x01223f04), the experience of a kill (opcode 0x16, 0x01234c08), the master
 *     level (0xA0 sub 0x22, 0x01285b68) and master level up (0xA0 sub 0x60, 0x01285efa);
 *   - the character window's "+" buttons (onClickButton, 0x00b469c4) and the stat request
 *     (0x00b48aca);
 *   - the options window winOption (the game side 0x00c75bb2 .. 0x00c76b02) and ./option.ini.
 *
 * This build numbers its packets itself (docs/research/client-skills.md section 8): the server's
 * F3 family is opcode 0xA0 here, with its own sub numbers.  The network side (sending, the C3/C4
 * cipher) stays outside: requests are returned as the bytes the client's packet builder is given.
 *
 * Every call into another subsystem (GFx invokes, effects, sounds, the chat, windows) is reported
 * as one text line through env->emit, in client order:
 *
 *   invoke METHOD JSON          a GFx invoke on the window's movie
 *   call ADDRESS ARGS           a client routine (hex address, then its arguments in hex)
 *
 * The validator stubs the same routines and records the same lines. */
#ifndef MU_PROGRESS_H
#define MU_PROGRESS_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- the attribute record (CharacterAttribute) --------------------------------------------------- */

#define MU_PRG_ATTR_SIZE 0x200
/* field offsets (static readings of the getters 0x00a00066..0x00a00278 and their users) */
#define MU_PRG_A_LEVEL        0x000   /* int, SetLevel 0x00a00031 clamps to 400 */
#define MU_PRG_A_EXP          0x008   /* u64 */
#define MU_PRG_A_NEXT_EXP     0x010   /* u64 */
#define MU_PRG_A_MLEVEL       0x018   /* int, read only for a third-class hero (0x00a000e9) */
#define MU_PRG_A_MEXP         0x020   /* u64 */
#define MU_PRG_A_MNEXT_EXP    0x028   /* u64 */
#define MU_PRG_A_MPOINTS      0x030   /* int (0xA0 0x22 packet +6) */
#define MU_PRG_A_M34          0x034   /* int (0xA0 0x22 +8, 0x60 +0x16, 0x14) */
#define MU_PRG_A_M3C          0x03c   /* int (0xA0 0x22 +0xa) */
#define MU_PRG_A_LIFE         0x068   /* int */
#define MU_PRG_A_MANA         0x06c   /* int */
#define MU_PRG_A_LIFE_MAX     0x070   /* int */
#define MU_PRG_A_MANA_MAX     0x074   /* int */
#define MU_PRG_A_SHIELD_MAX   0x07c   /* int */
#define MU_PRG_A_AG_MAX       0x084   /* int (SkillManaMax) */
#define MU_PRG_A_CLASS        0x187   /* u8, class byte (low nibble class index, bit 5 third class) */
#define MU_PRG_A_STRENGTH     0x18a   /* u16 */
#define MU_PRG_A_DEXTERITY    0x18c   /* u16 */
#define MU_PRG_A_VITALITY     0x18e   /* u16 */
#define MU_PRG_A_ENERGY       0x190   /* u16 */
#define MU_PRG_A_COMMAND      0x192   /* u16 */
#define MU_PRG_A_PVP_RATE     0x194   /* u16, PvP attack rate */
#define MU_PRG_A_PVP_DEFRATE  0x196   /* u16, PvP defense rate */
#define MU_PRG_A_ADD_STR      0x198   /* u16, added strength (items, buffs) */
#define MU_PRG_A_ADD_DEX      0x19a
#define MU_PRG_A_ADD_VIT      0x19c
#define MU_PRG_A_ADD_ENE      0x19e
#define MU_PRG_A_ADD_CMD      0x1a4
#define MU_PRG_A_ADD_POINT    0x1ae   /* u16 x 4 (+0x1ae..+0x1b4): level-up packet +0x10..+0x16 */
#define MU_PRG_A_ATK_RATE     0x1b8   /* u16, attack rate */
#define MU_PRG_A_DMG_MIN_L    0x1ba   /* u16 x 4: attack damage min/max, left then right */
#define MU_PRG_A_DMG_MAX_L    0x1bc
#define MU_PRG_A_DMG_MIN_R    0x1be
#define MU_PRG_A_DMG_MAX_R    0x1c0
#define MU_PRG_A_MAGIC_MIN    0x1c4   /* u16 */
#define MU_PRG_A_MAGIC_MAX    0x1c6
#define MU_PRG_A_CURSE_MIN    0x1c8   /* u16 (Summoner) */
#define MU_PRG_A_CURSE_MAX    0x1ca
#define MU_PRG_A_DEF_RATE     0x1da   /* u16, defense rate (successful blocking) */
#define MU_PRG_A_DEFENSE      0x1dc   /* u16 */
#define MU_PRG_A_POINTS       0x1e2   /* u16, LevelUpPoint */

/* The stat machine object (one per class, 0x1e4 bytes) */
#define MU_PRG_MACHINE_SIZE 0x1e4
#define MU_PRG_M_TOTAL        0x1bc   /* int x 5: str, dex, vit, ene, cmd totals (0x0098d2c4) */

static inline uint16_t mu_prg_u16(const uint8_t *p, size_t off) { return (uint16_t)(p[off] | p[off + 1] << 8); }
static inline void mu_prg_set16(uint8_t *p, size_t off, uint32_t v)
{
    p[off] = (uint8_t)v;
    p[off + 1] = (uint8_t)(v >> 8);
}
static inline int32_t mu_prg_i32(const uint8_t *p, size_t off)
{
    return (int32_t)((uint32_t)p[off] | (uint32_t)p[off + 1] << 8 | (uint32_t)p[off + 2] << 16 |
                     (uint32_t)p[off + 3] << 24);
}
static inline void mu_prg_set32(uint8_t *p, size_t off, uint32_t v)
{
    for (int i = 0; i < 4; i++)
        p[off + (size_t)i] = (uint8_t)(v >> (8 * i));
}
static inline uint64_t mu_prg_u64(const uint8_t *p, size_t off)
{
    return (uint64_t)(uint32_t)mu_prg_i32(p, off) | (uint64_t)(uint32_t)mu_prg_i32(p, off + 4) << 32;
}
static inline void mu_prg_set64(uint8_t *p, size_t off, uint64_t v)
{
    mu_prg_set32(p, off, (uint32_t)v);
    mu_prg_set32(p, off + 4, (uint32_t)(v >> 32));
}

/* ---- the environment ----------------------------------------------------------------------------- */

typedef struct mu_prg_env {
    void *user;
    uint8_t *attr;                    /* CharacterAttribute (MU_PRG_ATTR_SIZE bytes) */
    uint8_t hero_class;               /* the hero CHARACTER's class byte (Hero +0x12) */
    /* one line per call into another subsystem (see above) */
    void (*emit)(void *user, const char *line);
    /* GlobalText (0x0095f027 / 0x011753c3); NULL or a missing entry gives "" */
    const char *(*global_text)(void *user, int32_t index);
    /* the hero's buff test 0x0139f66e(Hero, buff) (boundary) */
    int (*has_buff)(void *user, int32_t buff);
    /* equipment queries on the hero's item slot s (CharacterMachine +0x1b58 + s * 0x12c), boundaries:
     * 0x00993731 the item counts (equipped and usable), 0x0139d95f the weapon kind, item +0x38 (byte),
     * 0x00987982 the item is of kind k */
    int (*item_valid)(void *user, int32_t slot);
    int32_t (*item_weapon_kind)(void *user, int32_t slot);
    uint8_t (*item_byte38)(void *user, int32_t slot);
    int (*item_is)(void *user, int32_t slot, int32_t kind);
    /* the GFx window manager's typed getters (0x00c60c60 list, e.g. 0x0095c50b the main frame,
     * 0x0095c5da, 0x009a19ae): 1 when the window exists (boundary) */
    int (*window)(void *user, uint32_t getter);
    /* the hero CHARACTER record (Hero 0x0a39d754; at least 0x400 bytes) */
    uint8_t *hero;
    /* a character by its server key: 0x0137c724 (key -> index) and 0x0095f6db / 0x009a13f4 (index ->
     * CHARACTER); returns the record (at least 0x400 bytes) or NULL, *index the index (boundary) */
    uint8_t *(*character)(void *user, int32_t key, int32_t *index);
    /* 0x009dacb8(world 0x01cf15fc): the world hides damage numbers (boundary) */
    int (*world_hides_damage)(void *user);
    /* the attack speed row's master-tree bonus (boundaries): GFx manager +0x1f8 exists; 0x00c354b7(class,
     * value) on 0x06fbc8bc (-1: none); 0x00c2a236(id) the node (0: none) and its value 0x00b48a9e(0x3f0) */
    int (*tree)(void *user);
    int32_t (*tree_map)(void *user, int32_t class_index, int32_t value);
    int (*tree_node)(void *user, int32_t id, int32_t key, int32_t *value);
    /* the hero's effect test 0x01295ade(Hero +0x35ac, effect) (boundary) */
    int (*has_effect)(void *user, int32_t effect);
} mu_prg_env;

/* The level used by the formulas, 0x00a00367: level + master level, where the master level counts
 * only when the attribute's class byte has bit 5 (0x0139d8ea -> 0x0139cb15). Verified. */
int32_t mu_prg_effective_level(const uint8_t *attr);
/* 0x00a000e9 (verified) */
int32_t mu_prg_master_level(const uint8_t *attr);

/* ---- the class formulas (verified) ------------------------------------------------------------------ */

/* The stat machine's slot 0 for class index cls (0..15): attack damage, magic/curse damage, attack
 * rate, PvP attack and defense rates, defense, defense rate, from the stats plus the five extra
 * points (the arguments of CalculateAll 0x00993a45).  Writes into the attribute record. */
void mu_prg_calc_class(const mu_prg_env *env, int cls, const int32_t extra[5]);
/* The stat totals 0x0098d2c4: machine +0x1bc..+0x1cc = stat + added stat + extra. */
void mu_prg_calc_totals(const uint8_t *attr, uint8_t *machine, const int32_t extra[5]);
/* the client's vtable slot 0 address of class cls (for reports) */
uint32_t mu_prg_class_routine(int cls);

/* ---- experience and the server's answers (verified) --------------------------------------------------- */

/* The experience table 0x00a00e79 (int64 level): n = level - 1; 0 for n <= 0; else
 * (n + 9) * n * n * 10, plus (m + 9) * m * m * 1000 for n > 255 with m = n - 255 (the second product
 * in 32 bits, sign-extended); negative results become 0.  Cumulative experience of a level. */
int64_t mu_prg_exp_table(int64_t level);
/* 0x00a00f4a (on CharacterMachine): experience 0, next = table(level + 1) - table(level). */
void mu_prg_level_exp(uint8_t *attr);

/* Level up, opcode 0xA0 sub 0x06 (0x01250b05).  packet: +4 level, +6 free points, +8 HP max,
 * +0xa MP max, +0xc SD max, +0xe AG max, +0x10..+0x16 the four added-point words (u16 LE).  The
 * level (SetLevel 0x00a00031: at most 400, then 0x00a00386), points, maxima (at least 1; HP and MP
 * filled), the window calls, the chat line GlobalText 0x1e6 with next - exp, 0x00a00f4a,
 * 0x00a00fb7, the effects (joints 0x7f78: subtype 0x2d once and 0x2e x 19 for a third-class hero,
 * else subtype 0 x 15 and the effect 0x7f84) and the sound 0x98. */
void mu_prg_recv_levelup(const mu_prg_env *env, const uint8_t *packet);
/* The stat point answer, 0xA0 sub 0x11 (0x01223f04): packet +4 = result (high nibble: accepted,
 * low nibble: the stat 0..4), +6 HP or MP max (vitality / energy), +8 SD max, +0xa AG max. */
void mu_prg_recv_point(const mu_prg_env *env, const uint8_t *packet);
/* The experience of a kill, opcode 0x16 (0x01234c08): +3..+4 key (big endian, bit 15: the monster
 * died), +5..+6 experience, +7..+8 damage.  encrypted == 0 is refused with the client's report packet
 * (C1 4D 02 00 16, returned in report[5]); returns the handler's result. */
int mu_prg_recv_kill_exp(const mu_prg_env *env, const uint8_t *packet, int encrypted, uint8_t report[5]);
/* Master level up, 0xA0 sub 0x22 (0x01285b68): +4 master level, +6, +8, +0xa (i16) into +0x30, +0x34,
 * +0x3c; the chat line 0x6d6 with mnext - mexp, the window calls and the third-class effects.  The
 * restored text has 76 NOP bytes at 0x01285bda (static: their original content is unknown). */
void mu_prg_recv_master_levelup(const mu_prg_env *env, const uint8_t *packet);
/* Master experience, 0xA0 sub 0x60 (0x01285efa): +4 master level (when it changed: the window
 * calls), +6..+0xd master exp and +0xe..+0x15 next (big endian), +0x16 into +0x34, the windows and
 * the experience bar.  76 NOP bytes at 0x01286256 (static). */
void mu_prg_recv_master_exp(const mu_prg_env *env, const uint8_t *packet);

/* The character window's stat values, opcode 0x55 sub 0x57 (0x0122a5f6 -> 0x00b3ee5e): packet +4
 * strength, +6 added strength, +8/+0xa agility, +0xc/+0xe vitality, +0x10/+0x12 energy, +0x14/+0x16
 * command, +0x18 a float (row 0x39).  The window keeps its own copy (+0x119.., the totals +0xa8..)
 * and the float (+0x13d); changed stats are written into the attribute record. */
typedef struct mu_prg_stat_window {
    uint16_t shown[10];          /* +0x119..+0x12b: base and added per stat, as last shown */
    uint16_t total[5];           /* +0xa8..+0xb0 */
    float rate;                  /* +0x13d */
    uint8_t dirty;               /* +0x10c */
} mu_prg_stat_window;
int mu_prg_recv_stats(const mu_prg_env *env, mu_prg_stat_window *window, const uint8_t *packet);

/* ---- the character window's "+" buttons (verified) ------------------------------------------------- */

/* onClickButton(row) of CharacterInfoFrame, the branch of 0x00b469c4 (after the name test; the
 * points are read through a displaced "mov eax, [0x01d1df1c]" at 0x00b46a27, an IGC.dll jump):
 * nothing without free points; the CharacterInfoSetup row ids 8, 13, 24, 29, 42 (the buttons of
 * strength, agility, vitality, energy, command; GFx numbers compared as doubles) send the request
 * for stat 0..4.  Returns the stat or -1. */
int32_t mu_prg_stat_button(const uint8_t *attr, double row);

/* The stat request 0x00b48aca: at most one per 100 ms of GetTickCount (*last = 0x01d22d4c, unsigned
 * difference), then C1 [size] 01 | 00 STAT (the bytes the packet builder is given; the builder
 * obfuscates the last two) and the click sound 0x19.  Returns the packet length (5) or 0. */
int mu_prg_stat_request(const mu_prg_env *env, uint32_t *last, uint32_t now, int32_t stat, uint8_t packet[5]);

/* The attack and magic speed, opcode 0x55 sub 0x94 (0x0122a13d): packet +4 attack speed (+0x1b6), +8
 * magic speed (+0x1c2), then the window's speed row (call 00b40380). */
#define MU_PRG_A_ATK_SPEED   0x1b6
#define MU_PRG_A_MAGIC_SPEED 0x1c2
#define MU_PRG_A_FLAGS_1A6   0x1a6
void mu_prg_recv_speed(const mu_prg_env *env, const uint8_t *packet);

/* The character window's speed row ("* ATK Speed", row 0x15), 0x00b40380 (window visible): the magic
 * speed for the class indices 0, 5 and 8, else the attack speed; the master-tree bonus; +20 when the
 * attribute byte +0x1a6 has bit 0 or bit 3; halved under effect 0xb0; at most the class's maximum
 * (0x009942bf); unchanged (window +0xbc/+0xbe) does nothing, else GlobalText 0x10be ("%d / %d") with
 * the speed and the maximum (call 00b3e33f 15 "TEXT", call 00b3e2a4 15) and
 * UpdateScorllList(2).  cls = the stat machine's class (machine +0x1d4).  Returns 1 when it updated. */
int mu_prg_speed_row(const mu_prg_env *env, int32_t cls, uint16_t cache[2], int visible);
/* 0x009942bf: the class's maximum speed */
int32_t mu_prg_speed_max(int32_t cls);

/* ---- the experience bar (verified) ------------------------------------------------------------------- */

/* The bar's last values, window +0x88 (compared by 0x00c54a49; the routine never writes them back) */
typedef struct mu_prg_bar_cache {
    int32_t stage;              /* +0 class stage (0x0139cb8a) */
    int32_t unused;             /* +4 */
    uint64_t exp;               /* +8 */
    uint64_t next;              /* +0x10 */
} mu_prg_bar_cache;

/* The class stage of a class byte, 0x0139cb8a: 1 without evolution bits (bits 4..7), else 2 + the
 * index of the highest of them (verified). */
int32_t mu_prg_class_stage(uint8_t class_byte);

/* The main HUD's experience bar, 0x00c5125b (its first instruction, at 0x00c51256, jumps into
 * IGC.dll; the routine is entered after it): for a stage of 3 or more the master experience and
 * "full" when the master level reaches master_cap (0x016963bf: 400, 500 or 1350 by server type),
 * else the normal experience; unchanged values against the cache do nothing; else
 * invoke setExpData {"ClassLevel", "curExp", "maxExp", "page", "rate"}: page = exp / (next / 10),
 * rate = the remainder in percent of a tenth (doubles, truncated), the numbers as "%I64d".
 * Returns 1 when it invoked. */
int mu_prg_exp_bar(const mu_prg_env *env, const mu_prg_bar_cache *cache, int32_t master_cap);

#ifdef __cplusplus
}
#endif

#endif
