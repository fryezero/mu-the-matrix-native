#ifndef MU_SKILL_USE_H
#define MU_SKILL_USE_H

/* The hero's skills on the game side of the interface (NATIVE-SKILL-001,
 * docs/research/client-skills.md).  Pinned inputs: restored text capture 09
 * (2bd5f2e9...3724), second image section run 10.
 *
 * Client state these routines read (static, the names are readings):
 *   hero        [0x0a39d754]: +0x12 class byte (-> class index 0x0095f5cc), +0x32 CurrentSkill (index into
 *               the learned list), +0x38/+0x39 the mounted state (onSelectSkill), +0x3268 the elemental
 *               attribute (the bar's "Elemental");
 *   attributes  [0x01d1df1c]: +0x18a strength, +0x18c agility, +0x18e vitality, +0x190 energy, +0x192
 *               command (u16; the tooltip builder); +0x1e4 learned count (u8), +0x1e6 learned skill ids
 *               (u16), +0xccc the per-index delay timers (i32, ms);
 *               [0x01d1df18] = the same block seen 8 bytes lower (+0x192..+0x19a in the stat check);
 *   hotkeys     0x01d1df5c: +0 the selected skill, +0xc std::map<slot, skill> of the bar's 10 slots.
 *
 * Routines:
 *   0x0109228f  stat requirements of a skill (verified)
 *   0x01091692  mana / AG check before a cast; drinks a mana potion when mana is short (verified)
 *   0x01696aca  StartSkillDelay (+ 0x01696ca6 the shared delay of skills 0xdd/0xde) (verified)
 *   0x016969e9  IsSkillReady (verified)
 *   0x01696e06  the per-frame delay tick (verified)
 *   0x01096e55  the class special cases of the bar's isUse (verified)
 *   0x00c58797  the bar feed: SetSkillSlot on the main movie when a slot or the selection changed (verified)
 *   0x00a0811a  the hotkey manager's selected slot (verified through the feed)
 *   0x00c70f4b  main onSelectSkill (static) with 0x01096951 (slot -> learned index) and 0x00a079d2
 *   0x01097130  the skill icon draw of the stamp window and the bar's legacy path: RenderBitmap's bitmap
 *               and cell (verified) */

#include <stddef.h>
#include <stdint.h>

#include "skill_table.h"

#ifdef __cplusplus
extern "C" {
#endif

#define MU_SKILL_LEARNED 255          /* attributes +0x1e4 is a byte */
#define MU_SKILL_LIST 0x3a1           /* the id and timer arrays (the full list clears 0x742 bytes) */
#define MU_SKILL_TICK_MAX 0x3a1       /* the tick walks at most 929 entries */
#define MU_SKILL_SLOTS 10

/* Outside lookups the routines make, all optional (NULL = the "none" answer given in brackets). */
typedef struct mu_skill_env {
    void *user;
    const mu_skill_table *table;      /* Skill(Kor); absent keys read as the zero record (default record) */
    int32_t class_index;              /* 0x0095f5cc(hero class byte) */
    /* master-skill manager (GfxMgr -> 0x0095f998) */
    int32_t (*base_skill)(void *u, int32_t skill);              /* 0x00bb1c32 [skill] */
    int (*master_has_delay)(void *u, int32_t skill);            /* 0x00bb1ea1 [0] */
    float (*master_value)(void *u, int32_t skill, int32_t which); /* 0x00bb1ed0 [0] */
    /* class skill tree (GfxMgr -> 0x0095fb5b / 0x0095fb49) */
    int32_t (*tree_map)(void *u, int32_t class_index, int32_t skill); /* 0x00c354b7 [-1] */
    int (*tree_node)(void *u, int32_t skill);                   /* 0x00c2a236 != 0 [0] */
    int32_t (*tree_value)(void *u, int32_t skill, int32_t id);  /* 0x00b48a9e on that node [0] */
    int (*tree_learned)(void *u, int32_t skill);                /* 0x00c2a37a (4th/5th tree skills) [1] */
    /* buffs [0]: list 0 = the character's (c + 0x358, 0x01295ade), 1 = the hero's (hero + 0x35ac,
     * 0x01295ade), 2 = 0x0139f66e(hero, buff) */
    int (*buff)(void *u, int list, int32_t buff);
} mu_skill_env;

typedef struct mu_skill_hero {
    int32_t class_index;
    uint16_t strength, agility, vitality, energy, command;  /* attributes +0x18a..+0x192 */
    int32_t mana, ag;                 /* 0x0096169b / 0x009616ba on the attributes */
    uint8_t mana_bonus;               /* [0x01d1df18] + 0x2ded (Triple Shot's extra mana with buffs 6/0x8f) */
    int32_t elemental;                /* hero + 0x3268 */
    uint8_t current;                  /* hero + 0x32 CurrentSkill */
    uint8_t mounted, mount_kind;      /* hero + 0x38, + 0x39 */
    int count;                        /* attributes + 0x1e4 */
    uint16_t skills[MU_SKILL_LIST];   /* attributes + 0x1e6 */
    int32_t timers[MU_SKILL_LIST];    /* attributes + 0xccc */
} mu_skill_hero;

/* The record of a skill: the table's, or the zero record for absent keys (the default record at
 * this+0x38 is zero apart from the strings; static). */
const mu_skill_record *mu_skill_record_of(const mu_skill_env *env, int32_t skill);

/* 0x0109228f: 1 when the hero's stats meet the skill's requirements; 0 for an absent skill (index 0).
 * Class index 1 needs strength OR energy when the skill asks for both. */
int mu_skill_stats_ok(const mu_skill_env *env, const mu_skill_hero *hero, int32_t skill);

/* 0x01091692 for the cast of `skill` (use-controller +8) whose base skill is `base` (+0xc).  mana/ag:
 * GetSkillInformation's values (skills 0x3a and 0x28 take 0x28's, 0x18b and 0x188 take 0x188's; the AG
 * of 0x28 and 0x188 is zeroed), computed by the caller (core/mu_lang's mu_lang_skill_info).  Returns 1
 * when the cast may go on; *potion = 1 when mana was short (the client then uses the first mana potion
 * the inventory finder 0x00b920bc returns, through 0x00960420). */
int32_t mu_skill_info_skill(int32_t skill);   /* the skill whose GetSkillInformation the check asks */
int mu_skill_mana_ok(const mu_skill_env *env, const mu_skill_hero *hero, int32_t skill, int32_t base, int32_t mana,
                     int32_t ag, int *potion);

/* The delay a skill starts (StartSkillDelay's computation before the timers; may be <= 0: none). */
int32_t mu_skill_delay_of(const mu_skill_env *env, int32_t skill);
/* 0x01696aca: start the delay of every learned entry of `skill` whose timer is 0, then the shared one of
 * 0xdd/0xde (0x01696ca6).  out_events receives (skill, delay) pairs the client sends to the bar as
 * onUseSkillDelay (at most 2); returns their count. */
int mu_skill_delay_start(const mu_skill_env *env, mu_skill_hero *hero, int32_t skill, int32_t out_events[2][2]);
/* 0x016969e9: 1 when learned entry `index` may be used (no delay or its timer is 0). */
int mu_skill_ready(const mu_skill_env *env, const mu_skill_hero *hero, int index);
/* 0x01696e06: every running timer loses dt ms and stops at 0. */
void mu_skill_delay_tick(mu_skill_hero *hero, int32_t dt);

/* 0x01096e55: 0 for the class special cases whose buff is missing (class index 5: base skills 0xdf,
 * 0xe0, 0xe1, 0x120, 0x80b, 0x80c need buff 0x12d; class index 1: base skill 0x5df needs 0x145; list 2),
 * else 1. */
int mu_skill_special_ok(const mu_skill_env *env, int32_t skill);

/* The bar's hotkeys (0x01d1df5c) and the bar feed's state (the main handler's +0x1c..+0x30). */
typedef struct mu_skill_hotkeys {
    int32_t selected;                 /* +0 */
    int32_t slots[MU_SKILL_SLOTS];    /* the map's values (0 = empty) */
} mu_skill_hotkeys;
/* 0x00a0811a: the slot that holds the selected skill, else the first non-empty slot, else 0. */
int32_t mu_skill_selected_slot(const mu_skill_hotkeys *hotkeys);

typedef struct mu_skill_bar_slot {
    int32_t skill;
    uint8_t use;
    int32_t damage_type;
} mu_skill_bar_slot;
typedef struct mu_skill_bar {
    uint8_t dirty;                    /* +0x1c */
    int32_t select_skill;             /* +0x20 */
    uint8_t select_use;               /* +0x24 */
    int32_t select_slot;              /* +0x28 */
    int32_t elemental;                /* +0x2c */
    mu_skill_bar_slot slots[MU_SKILL_SLOTS];  /* +0x30 vector of 12-byte entries */
} mu_skill_bar;
/* The bar's usability predicate of a skill: 0x010918c7 && 0x01096e55 (the first is the caller's). */
typedef int (*mu_skill_usable_fn)(void *user, int32_t skill);
/* 0x00c58797: refresh `bar` from the hero and the hotkeys.  Returns 1 and writes the SetSkillSlot
 * argument (JSON, the members in the client's order) when something changed, else 0. */
int mu_skill_bar_feed(const mu_skill_env *env, mu_skill_bar *bar, const mu_skill_hero *hero,
                      const mu_skill_hotkeys *hotkeys, mu_skill_usable_fn usable, void *usable_user, char *json,
                      size_t cap);

/* main onSelectSkill (0x00c70f4b) for bar slot `slot` holding `slot_skill`: the learned index of that
 * skill (0x01096951), -1 when none; when it differs from CurrentSkill and the mounted rule allows it
 * (hero +0x38 set and +0x39 == 7: only skills of type 7), CurrentSkill takes it and the hotkeys select
 * the skill (0x00a079d2).  Returns 1 when the selection changed. */
int mu_skill_learned_index(const mu_skill_hero *hero, int32_t skill);
int mu_skill_select(const mu_skill_env *env, mu_skill_hero *hero, mu_skill_hotkeys *hotkeys, int32_t slot_skill);

/* 0x01097130: the bitmap and texture cell RenderBitmap draws for a skill icon.  The stamp manager's
 * entry is {+0 base skill, +4 learned skill (0: not learned)}; the icon is the learned skill's, else the
 * base skill's, and it is the normal one only when the skill is learned and usable (0x010918c7 &&
 * 0x01096e55; the 4th/5th tree kinds also need 0x00c2a37a).  cell_w/cell_h: the texel size of a cell
 * (RenderBitmap's u = cell_w/512 * column).  Returns 0 when nothing is drawn.
 * Bitmaps: 0x7c40 newui_skill00 / 0x7c43 newui_non_skill00 (SkillUseType 0, 1), 0x7e18 (+1 per 450
 * icons) new_Master_Icon / 0x7e1a new_Master_Non_Icon (3, 4), 0x7e1c 4th_Skill_Icon / 0x7e1d (7..9),
 * 0x7e22 / 0x7e23 (14). */
typedef struct mu_skill_icon {
    int32_t bitmap;
    float u, v, uw, vh;               /* RenderBitmap's texture rectangle: cell (column, row) of a 25-wide grid */
} mu_skill_icon;
int mu_skill_icon_of(const mu_skill_env *env, int32_t base, int32_t learned, int usable, float cell_w, float cell_h,
                     mu_skill_icon *out);

#ifdef __cplusplus
}
#endif

#endif
