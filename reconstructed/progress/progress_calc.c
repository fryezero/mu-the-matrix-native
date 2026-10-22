/* The class formulas of the stat machine (vtable slot 0 of the 16 CharacterMachine classes) and the
 * stat totals 0x0098d2c4 (NATIVE-PROGRESS-001).  See progress.h.
 *
 * All values are the client's: the stat sums are kept in 16-bit locals (word stores), divisions are
 * signed integer divisions of non-negative values, the "rate" formulas use single-precision floats
 * (cvtsi2ss, mulss/divss, addss, cvttss2si) and every result is stored as a 16-bit word. */
#include "progress.h"

#ifndef MU_PROGRESS_MUTATION
#define MU_PROGRESS_MUTATION 0
#endif

int32_t mu_prg_master_level(const uint8_t *a)
{
    /* 0x00a000e9: 0x0139d8ea(class) -> 0x0139cb15: (class >> 5) & 1 */
    return (a[MU_PRG_A_CLASS] >> 5 & 1) == 1 ? mu_prg_i32(a, MU_PRG_A_MLEVEL) : 0;
}

int32_t mu_prg_effective_level(const uint8_t *a)
{
    return (int32_t)((uint32_t)mu_prg_i32(a, MU_PRG_A_LEVEL) + (uint32_t)mu_prg_master_level(a));
}

static const uint32_t ROUTINES[16] = {0x0099a917, 0x009991f8, 0x0099d6f4, 0x009a789c, 0x00999e9a, 0x009f5fc4,
                                      0x009d842f, 0x0099e486, 0x009da301, 0x009ea4ea, 0x0099edde, 0x009ff69c,
                                      0x009a6f75, 0x009a5b41, 0x0098702b, 0x00998a96};

uint32_t mu_prg_class_routine(int cls)
{
    return cls >= 0 && cls < 16 ? ROUTINES[cls] : 0;
}

/* the stat + added stat + extra, kept as a 16-bit local */
static uint16_t stat(const uint8_t *a, size_t base, size_t add, int32_t extra)
{
    return (uint16_t)((uint32_t)mu_prg_u16(a, base) + (uint32_t)extra + (uint32_t)mu_prg_u16(a, add));
}

/* cvttss2si of a single-precision sum (the inputs are small: no overflow) */
static int32_t ftrunc(float v)
{
    return (int32_t)v;
}

static int has_buff(const mu_prg_env *e, int32_t buff)
{
    return e->has_buff ? e->has_buff(e->user, buff) : 0;
}

static void damage(uint8_t *a, int32_t min, int32_t max)
{
    mu_prg_set16(a, MU_PRG_A_DMG_MIN_L, (uint32_t)min);
    mu_prg_set16(a, MU_PRG_A_DMG_MAX_L, (uint32_t)max);
    mu_prg_set16(a, MU_PRG_A_DMG_MIN_R, (uint32_t)min);
    mu_prg_set16(a, MU_PRG_A_DMG_MAX_R, (uint32_t)max);
}

/* attack rate: level * 5 + dex * 3 / 2 + str / 4 (the common form; the 0xffff clamp on a 16-bit
 * local is a no-op) */
static void attack_rate(uint8_t *a, int32_t level, uint16_t str, uint16_t dex)
{
    int32_t v = level * 5 + (int32_t)dex * 3 / 2 + (int32_t)str / 4;
    mu_prg_set16(a, MU_PRG_A_ATK_RATE, (uint16_t)v);
}

static void pvp(uint8_t *a, int32_t level, uint16_t dex, float atk_level, float atk_dex, float def_level,
                float def_dex)
{
    mu_prg_set16(a, MU_PRG_A_PVP_RATE, (uint32_t)ftrunc((float)level * atk_level + (float)dex * atk_dex));
    (void)def_level;
    (void)def_dex;
}

static void pvp_def(uint8_t *a, int32_t level, uint16_t dex, float def_level, float def_dex)
{
    mu_prg_set16(a, MU_PRG_A_PVP_DEFRATE, (uint32_t)ftrunc((float)level * def_level + (float)dex * def_dex));
}

static void pvp_def_div(uint8_t *a, int32_t level, uint16_t dex, float div)
{
    mu_prg_set16(a, MU_PRG_A_PVP_DEFRATE, (uint32_t)ftrunc((float)level * 2.0f + (float)dex / div));
}

/* ---- the 16 classes --------------------------------------------------------------------------------- */

/* class 0, 0x0099a917 */
static void class0(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    damage(a, str / 8, str / 4);
    mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 9));
    mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 4));
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, MU_PROGRESS_MUTATION == 1 ? 4.5f : 4.0f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 4));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.25f);
}

/* class 1, 0x009991f8; buff 0x145 changes the damage and the defense */
static void class1(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    int32_t min = str / 6, max = str / 4;
    if (has_buff(e, 0x145)) {
        min = str / 9;
        max = str / 6;
    }
    damage(a, min, max);
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 4.5f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 3));
    if (has_buff(e, 0x145))
        mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 2));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.5f);
}

static int item_valid(const mu_prg_env *e, int32_t slot)
{
    return e->item_valid ? e->item_valid(e->user, slot) : 0;
}

static int32_t weapon_kind(const mu_prg_env *e, int32_t slot)
{
    return e->item_weapon_kind ? e->item_weapon_kind(e->user, slot) : 0;
}

static uint8_t byte38(const mu_prg_env *e, int32_t slot)
{
    return e->item_byte38 ? e->item_byte38(e->user, slot) : 0;
}

static int item_is(const mu_prg_env *e, int32_t slot, int32_t kind)
{
    return e->item_is ? e->item_is(e->user, slot, kind) : 0;
}

/* class 2, 0x0099d6f4: the bow/crossbow in slot 0 (weapon kind 2 or 1) uses its own formula, both
 * zero when the item's byte +0x38 is 0; the right hand is 0 when slot 1 holds kind 0x4b */
static void class2(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    int32_t min = 0, max = 0;
    if (item_valid(e, 0) && weapon_kind(e, 0) == 2) {
        if (byte38(e, 0)) {
            min = dex / 7 + str / 14;
            max = dex / 4 + str / 8;
        }
    } else if (item_valid(e, 0) && weapon_kind(e, 0) == 1) {
        if (byte38(e, 0)) {
            min = dex / 7 + str / 14;
            max = dex / 4 + str / 8;
        }
    } else {
        min = (str + dex) / 7;
        max = (str + dex) / 4;
    }
    mu_prg_set16(a, MU_PRG_A_DMG_MIN_L, (uint32_t)min);
    mu_prg_set16(a, MU_PRG_A_DMG_MAX_L, (uint32_t)max);
    int bow = (item_valid(e, 0) && weapon_kind(e, 0) == 2) || (item_valid(e, 0) && weapon_kind(e, 0) == 1);
    if (bow && item_is(e, 1, 0x4b)) {
        mu_prg_set16(a, MU_PRG_A_DMG_MIN_R, 0);
        mu_prg_set16(a, MU_PRG_A_DMG_MAX_R, 0);
    } else {
        mu_prg_set16(a, MU_PRG_A_DMG_MIN_R, (uint32_t)min);
        mu_prg_set16(a, MU_PRG_A_DMG_MAX_R, (uint32_t)max);
    }
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 0.6f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 10));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 4));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.1f);
}

/* class 3, 0x009a789c */
static void class3(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    damage(a, str / 6 + ene / 12, str / 4 + ene / 8);
    mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 9));
    mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 4));
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 3.5f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 4));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.25f);
}

/* class 4, 0x00999e9a (command counts) */
static void class4(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    uint16_t cmd = stat(a, MU_PRG_A_COMMAND, MU_PRG_A_ADD_CMD, x[4]);
    damage(a, str / 6 + ene / 14 + cmd / 7, str / 4 + ene / 10 + cmd / 5);
    int32_t level = mu_prg_effective_level(a);
    mu_prg_set16(a, MU_PRG_A_ATK_RATE, (uint16_t)(level * 5 + (int32_t)dex * 2 / 3 + str / 4 + cmd / 15));
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 4.0f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 7));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 7));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.5f);
}

/* class 5, 0x009f5fc4: buff 0x12d swaps the magic and curse formulas */
static void class5(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    damage(a, (str + dex) / 7, (str + dex) / 4);
    if (has_buff(e, 0x12d)) {
        mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 18));
        mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 10));
        mu_prg_set16(a, MU_PRG_A_CURSE_MIN, (uint32_t)(ene / 9));
        mu_prg_set16(a, MU_PRG_A_CURSE_MAX, (uint32_t)(ene / 4));
    } else {
        mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 9));
        mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 4));
        mu_prg_set16(a, MU_PRG_A_CURSE_MIN, (uint32_t)(ene / 18));
        mu_prg_set16(a, MU_PRG_A_CURSE_MAX, (uint32_t)(ene / 10));
    }
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 3.5f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 3));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 4));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.5f);
}

/* class 6, 0x009d842f (vitality counts) */
static void class6(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t vit = stat(a, MU_PRG_A_VITALITY, MU_PRG_A_ADD_VIT, x[2]);
    damage(a, str / 7 + vit / 15, str / 5 + vit / 12);
    int32_t level = mu_prg_effective_level(a);
    mu_prg_set16(a, MU_PRG_A_ATK_RATE, (uint16_t)(level * 3 + (int32_t)dex * 5 / 4 + str / 6));
    pvp(a, mu_prg_effective_level(a), dex, 2.6f, 3.6f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 8));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 10));
    pvp_def(a, mu_prg_effective_level(a), dex, 1.5f, 0.2f);
}

/* class 7, 0x0099e486 */
static void class7(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    damage(a, str / 8 + dex / 10, str / 4 + dex / 6);
    int32_t level = mu_prg_effective_level(a);
    mu_prg_set16(a, MU_PRG_A_ATK_RATE, (uint16_t)(level * 5 + (int32_t)dex * 5 / 4 + str / 4));
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 2.5f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 7));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 4));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.2f);
}

/* class 8, 0x009da301 */
static void class8(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    damage(a, str / 8, str / 4);
    mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 9));
    mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 4));
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 4.0f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 5));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    pvp_def_div(a, mu_prg_effective_level(a), dex, 3.0f);
}

/* class 9, 0x009ea4ea */
static void class9(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    damage(a, str / 9 + dex / 20, str / 5 + dex / 14);
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 2.5f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 10));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    pvp_def_div(a, mu_prg_effective_level(a), dex, 3.0f);
}

/* class 10, 0x0099edde: buff 0x17c raises the magic damage and lowers the defense */
static void class10(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    damage(a, str / 8, str / 5);
    if (has_buff(e, 0x17c)) {
        mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 6));
        mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 3));
    } else {
        mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 8));
        mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 4));
    }
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 3.0f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(has_buff(e, 0x17c) ? dex / 8 : dex / 4));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 4));
    pvp_def_div(a, mu_prg_effective_level(a), dex, 3.0f);
}

/* class 11, 0x009ff69c */
static void class11(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    damage(a, str / 8, str / 4);
    mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 5));
    mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 3));
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 4.0f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 3));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.25f);
}

/* class 12, 0x009a6f75 (attack rate: str / 2) */
static void class12(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    damage(a, str / 8, str / 4);
    mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 5));
    mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 3));
    int32_t level = mu_prg_effective_level(a);
    mu_prg_set16(a, MU_PRG_A_ATK_RATE, (uint16_t)(level * 5 + (int32_t)dex * 3 / 2 + str / 2));
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 4.0f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 4));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    pvp_def(a, mu_prg_effective_level(a), dex, 2.0f, 0.25f);
}

/* class 13, 0x009a5b41 (strength counts in the defense) */
static void class13(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    damage(a, str / 11 + dex / 9, str / 9 + dex / 6);
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    pvp(a, mu_prg_effective_level(a), dex, 3.0f, 2.5f, 0, 0);
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(str / 5 + dex / 10));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    pvp_def_div(a, mu_prg_effective_level(a), dex, 4.0f);
}

/* class 14, 0x0098702b (integer PvP rates) */
static void class14(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    uint16_t ene = stat(a, MU_PRG_A_ENERGY, MU_PRG_A_ADD_ENE, x[3]);
    damage(a, str / 8, str / 4);
    mu_prg_set16(a, MU_PRG_A_MAGIC_MIN, (uint32_t)(ene / 4));
    mu_prg_set16(a, MU_PRG_A_MAGIC_MAX, (uint32_t)(ene / 3));
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    int32_t level = mu_prg_effective_level(a);
    mu_prg_set16(a, MU_PRG_A_PVP_RATE, (uint32_t)(level * 3 + (int32_t)dex * 4));
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 2));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    level = mu_prg_effective_level(a);
    mu_prg_set16(a, MU_PRG_A_PVP_DEFRATE, (uint32_t)(dex / 3 + level * 2));
}

/* class 15, 0x00998a96 (integer PvP rates) */
static void class15(const mu_prg_env *e, const int32_t x[5])
{
    uint8_t *a = e->attr;
    uint16_t str = stat(a, MU_PRG_A_STRENGTH, MU_PRG_A_ADD_STR, x[0]);
    uint16_t dex = stat(a, MU_PRG_A_DEXTERITY, MU_PRG_A_ADD_DEX, x[1]);
    damage(a, str / 6, str / 4);
    attack_rate(a, mu_prg_effective_level(a), str, dex);
    int32_t level = mu_prg_effective_level(a);
    mu_prg_set16(a, MU_PRG_A_PVP_RATE, (uint32_t)(level * 3 + (int32_t)dex * 4));
    mu_prg_set16(a, MU_PRG_A_DEFENSE, (uint32_t)(dex / 2));
    mu_prg_set16(a, MU_PRG_A_DEF_RATE, (uint32_t)(dex / 3));
    level = mu_prg_effective_level(a);
    mu_prg_set16(a, MU_PRG_A_PVP_DEFRATE, (uint32_t)(dex / 3 + level * 2));
}

void mu_prg_calc_class(const mu_prg_env *env, int cls, const int32_t extra[5])
{
    static void (*const FN[16])(const mu_prg_env *, const int32_t *) = {
        class0, class1, class2, class3, class4, class5, class6, class7,
        class8, class9, class10, class11, class12, class13, class14, class15};
    if (env && env->attr && cls >= 0 && cls < 16)
        FN[cls](env, extra);
}

void mu_prg_calc_totals(const uint8_t *a, uint8_t *m, const int32_t x[5])
{
    static const size_t BASE[5] = {MU_PRG_A_STRENGTH, MU_PRG_A_DEXTERITY, MU_PRG_A_VITALITY, MU_PRG_A_ENERGY,
                                   MU_PRG_A_COMMAND};
    static const size_t ADD[5] = {MU_PRG_A_ADD_STR, MU_PRG_A_ADD_DEX, MU_PRG_A_ADD_VIT, MU_PRG_A_ADD_ENE,
                                  MU_PRG_A_ADD_CMD};
    for (int i = 0; i < 5; i++)
        mu_prg_set32(m, MU_PRG_M_TOTAL + 4 * (size_t)i,
                     (uint32_t)mu_prg_u16(a, BASE[i]) + (uint32_t)x[i] + (uint32_t)mu_prg_u16(a, ADD[i]));
}
