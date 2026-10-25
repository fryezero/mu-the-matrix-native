/* domains/hero.h (PUBLIC): the hero as views see it. */
#ifndef MU_DOM_HERO_H
#define MU_DOM_HERO_H
#include <stdint.h>

typedef struct mu_session mu_session;

/* Derived from the client records on every call (cheap; views call it when MU_DOMAIN_HERO's
 * revision changed). Replaces mu_gfx_hero's demo values once the GFx windows read the session. */
typedef struct mu_hero_stats {
    char name[11];
    uint8_t class_byte;          /* CharacterAttribute +0x187 */
    int32_t class_index, stage;
    int32_t level, master_level, points, master_points;
    int32_t hp, max_hp, mp, max_mp, sd, max_sd, ag, max_ag;
    int64_t exp, next_exp, master_exp, master_next_exp;
    int32_t stats[5], added[5];  /* strength, agility, vitality, energy, command */
    int32_t attack_speed, magic_speed;
    /* the class formula's rows (mu_prg_calc_class), once the stat machine recalculated */
    int has_derived;
    int32_t dmg_min, dmg_max, atk_rate, pvp_rate, defense, def_rate, pvp_defrate;
    int32_t magic_min, magic_max, curse_min, curse_max;
} mu_hero_stats;

void mu_session_hero(const mu_session *s, mu_hero_stats *out);
int64_t mu_session_money(const mu_session *s);
/* The experience bar's last setExpData object (JSON), "" before the first one. */
const char *mu_session_hero_exp_bar(const mu_session *s);
/* The character window's speed row text (GlobalText 0x10be), "" before the first 0x55 0x94. */
const char *mu_session_hero_speed_text(const mu_session *s);

#endif
