#ifndef MU_SKILL_CANUSE_H
#define MU_SKILL_CANUSE_H

/* The usability check of a skill (NATIVE-SKILL-002, docs/research/client-skills.md section 9).  Pinned inputs as
 * in skill_use.h.
 *
 *   bool __thiscall SkillUse::CanUse(SkillUse *t, int skill)        0x010918c7   (t = 0x0107e918(), +0 hero)
 *
 * in its order: the use-type 2 / siege rule 0x016a500c (0x016a8342), the stat check 0x0109228f, the transformation
 * rule (record +0xb0 against hero +0x322e, 0x01092571), the required weapon kind (+0xb4 1..18 over the equipped
 * items' kind byte +0x251, 0x00987982), the ring rule 0x01092597, the world rules 0x00a9b235, the skill-specific
 * buff / item / world cases, SkillRequire 0x01092213, the party rule (base 0x33b), the class tree (use types 7..9,
 * 0x00c2a37a) and the map rule of skills 0x127 / 0x31a.  Everything the hero and the world answer comes through
 * the env's callbacks and values (the validator gives the client's routines the same answers). */

#include <stddef.h>
#include <stdint.h>

#include "skill_use.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_skill_item_state {
    int32_t code;                     /* +0x10 (group * 512 + index, -1 empty) */
    int32_t level_bits;               /* +0x14 ((x >> 3) & 0xf = the level) */
    uint8_t byte1a;                   /* +0x1a */
} mu_skill_item_state;

typedef struct mu_skill_use_env {
    const mu_skill_env *skills;       /* Skill(Kor), the class index, the base skill (0x00bb1c32 when NULL), the hero's
                                         buffs (list 1 = hero +0x35ac, 0 = the character's +0x358 list), tree_learned */
    void *user;
    /* the equipped item `slot` (0 weapon, 1 left hand) has kind byte `kind` (+0x251; 0x00987982) */
    int (*item_kind)(void *u, int slot, int kind);
    int (*special_item)(void *u, int32_t skill);         /* 0x0109260c [1] */
    int (*arrows)(void *u, int auto_reload);             /* 0x0169da9c [1] */
    int (*party)(void *u);                                /* the party rule of base 0x33b [1] */
    int (*map_open)(void *u);                             /* hudMap +0x4e (skills 0x127, 0x31a) [1] */
    int (*it_relic)(void *u);                             /* Illusion Temple relic carried (0x009fbb31) [0] */
    int (*event_map)(void *u, int32_t world);             /* EventMap(0x5c)->0x00d7b35d(world) == 1 [0] */
    int (*confusion_world)(void *u, int32_t world);       /* ConfusionStoneMonsterSet has the world (0x010e6e74) [0] */
    int (*skill_require)(void *u, int32_t base, int32_t *skill, int32_t *master_skill, int32_t *master_level);
                                                          /* SkillRequire record (0x01094669): 0 none */
    int (*master_level)(void *u, int32_t skill);          /* 0x00bb1d9d [0] */
    int32_t world;                    /* [0x01cf15fc] */
    uint8_t siege;                    /* [0x01ec8ee7] */
    uint8_t confusion_flag;           /* [0x0a39d761] */
    int32_t event_flag;               /* [0x01d1e028 + 4] (0x00a6ce15) */
    uint16_t transform;               /* hero +0x322e (0xffff: none) */
    int32_t part_model[2];            /* hero +0x31f4 + i * 0x1c + 4 */
    mu_skill_item_state items[15];    /* [0x01d1df18] + 0x1b58 + i * 0x12c: 0 weapon, 1 left hand, 10/11 rings */
} mu_skill_use_env;

int mu_skill_can_use(const mu_skill_use_env *env, const mu_skill_hero *hero, int32_t skill);   /* 0x010918c7 */
int mu_skill_world_ok(const mu_skill_use_env *env, int32_t base);                               /* 0x00a9b235 */
int mu_skill_require_ok(const mu_skill_use_env *env, const mu_skill_hero *hero, int32_t skill); /* 0x01092213 */
int mu_skill_hero_knows(const mu_skill_env *skills, const mu_skill_hero *hero, int32_t skill);  /* 0x0139db0c */
int mu_skill_illusion_temple(int32_t world);                                                    /* 0x0095fba9 */
int mu_skill_chaos_castle(int32_t world);                                                       /* 0x009dacb8 */
int mu_skill_blood_castle(int32_t world);                                                       /* 0x009dacec */

#ifdef __cplusplus
}
#endif

#endif
