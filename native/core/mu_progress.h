/* Character progression in the native client (NATIVE-PROGRESS-001, docs/research/client-progression.md).
 *
 * The session side of reconstructed/progress: the hero's attribute record (level, experience, master
 * level, the five stats, the class formula's derived values), the experience bar of the HUD, the
 * character window's "+" buttons, and an OFFLINE DEMO server that answers them with the packets the
 * client parses (this build's numbering):
 *
 *   opcode 0x16           the experience of a kill (and the key of the dead monster)
 *   opcode 0xA0 sub 0x06  level up (level, free points, HP/MP/SD/AG maxima, the four added words)
 *   opcode 0xA0 sub 0x11  the answer to a stat point request
 *   opcode 0x55 sub 0x57  the character window's stat values
 *   opcode 0xA0 sub 0x22  master level up, 0xA0 sub 0x60 master experience
 *
 * What the client does with them is reconstructed (verified in Unicorn, scripts/validate_progress.py);
 * the demo server's rules are the demo's choices, labelled DEMO:
 *
 *   - a kill gives (L + 25) * L / 3 experience times the rate, L = 1 + server class % 40 (the classic
 *     server formula with a demo monster level);
 *   - the experience counts within the level as the client keeps it (0x00a00f4a resets it to 0 and
 *     sets next = table(level + 1) - table(level)); at next the server sends level up and drops the
 *     rest; five free points per level (seven for class indices 3, 4, 6), level at most 400;
 *   - HP/MP/SD/AG maxima from per-class base values and per-level / per-stat steps (demo values in the
 *     style of the classic server tables);
 *   - a third-class hero (class byte bit 5) at level 400 gains master experience and master levels the
 *     same way (next = the table's difference at level + master level);
 *   - a stat point request is accepted while points remain: +1 to the stat, the answer and the stat
 *     values follow;
 *   - the attack and magic speeds (opcode 0x55 sub 0x94) from agility over per-class divisors in the style
 *     of the classic server (at join and after every agility change).
 *
 * The host receives every line of the reconstructed handlers (progress.h's list) through `line` and
 * plays the effects, sounds and chat lines; the experience bar's setExpData JSON is kept in
 * exp_json. */
#ifndef MU_PROGRESS_CORE_H
#define MU_PROGRESS_CORE_H

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/progress/progress.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_progress_config {
    uint8_t class_byte;          /* low nibble class index, high nibble evolution bits (bit 5 third class) */
    int32_t level, master_level;
    int32_t stats[5];            /* strength, agility, vitality, energy, command; 0 = the class's start value */
    int32_t points;
    int64_t exp;                 /* experience within the level */
    int32_t exp_rate;            /* DEMO: kill experience multiplier (1) */
    int32_t latency_steps;       /* DEMO: logic steps before an answer arrives (2) */
} mu_progress_config;

void mu_progress_default_config(mu_progress_config *config);

#define MU_PROGRESS_PENDING 32

typedef struct mu_progress_packet {
    int32_t due;                 /* logic step */
    int32_t kind;                /* MU_PRGK_* */
    uint8_t data[64];
    int32_t size;
} mu_progress_packet;

enum { MU_PRGK_KILL = 1, MU_PRGK_LEVELUP, MU_PRGK_POINT, MU_PRGK_STATS, MU_PRGK_MASTER_UP, MU_PRGK_MASTER_EXP,
       MU_PRGK_SPEED };

typedef struct mu_progress {
    mu_progress_config config;
    uint8_t attr[MU_PRG_ATTR_SIZE];       /* CharacterAttribute */
    uint8_t machine[MU_PRG_MACHINE_SIZE]; /* the stat machine's totals */
    uint8_t hero[0x400];                  /* the hero CHARACTER (class byte at +0x12) */
    uint8_t monster[0x400];               /* the killed monster's record (+0x23, +0x38) */
    mu_prg_bar_cache bar;                 /* window +0x88 (the client never writes it) */
    mu_prg_stat_window stat_window;
    uint16_t speed_row[2];                /* the speed row's last values (window +0xbc, +0xbe) */
    char speed_text[32];                  /* its text (GlobalText 0x10be) */
    uint32_t last_request;                /* 0x01d22d4c */
    uint32_t now_ms;
    int32_t step;
    char exp_json[256];
    int exp_dirty;                        /* setExpData was invoked since the host last took it */
    int hero_dirty;                       /* level/stats/points changed (the character window refreshes) */
    /* demo server state (what the server would keep) */
    int32_t server_stats[5];
    mu_progress_packet pending[MU_PROGRESS_PENDING];
    int32_t npending;
    /* statistics */
    int32_t kills, level_ups, master_level_ups, requests, accepted, respawns;
    mu_prg_respawn respawn;               /* the last respawn answer's position, map, angle, money */
    char last[256];                       /* last event, for logs and tests */
    /* host hooks */
    void (*line)(void *context, const char *line);
    void *context;
    const char *(*global_text)(void *context, int32_t index);
} mu_progress;

/* The DEMO join: the attribute record from the configuration (start stats per class when 0), the
 * maxima, the level's experience (0x00a00f4a), the class formula, the bar. */
void mu_progress_init(mu_progress *p, const mu_progress_config *config);

/* The class formula of the stat machine (slot 0 + totals, verified) over the current record. */
void mu_progress_recalc(mu_progress *p);

/* A monster of this server class died by the hero's hand (the DEMO server's kill experience). */
void mu_progress_kill(mu_progress *p, int32_t server_class, int32_t monster_key);

/* The character window's onClickButton(row) (CharacterInfoSetup row id): the client's rule and
 * request; the DEMO server answers.  Returns the stat (0..4) requested or -1. */
int32_t mu_progress_button(mu_progress *p, double row);

/* One 40 ms logic step: due DEMO answers go through the reconstructed handlers. */
void mu_progress_step(mu_progress *p);

/* The DEMO server's respawn answer (opcode 0xA0 sub 0x30) after the hero's death, through the client's
 * handler (mu_prg_recv_respawn): HP/MP/SD/AG at their maxima, the total experience unchanged (DEMO: no
 * death penalty; the live server takes a share), the money, the town tile the host chose (mu_map_respawn). */
void mu_progress_respawn(mu_progress *p, int32_t map, int32_t tile_x, int32_t tile_y, int32_t dir, uint32_t money);

/* Values for the HUD and the character window */
typedef struct mu_progress_view {
    int32_t class_index, stage;
    int32_t level, master_level, points, master_points;
    int64_t exp, next_exp, master_exp, master_next;
    int32_t stats[5], added[5];
    int32_t life, life_max, mana, mana_max, shield_max, ag_max;
    int32_t dmg_min, dmg_max, dmg_min_left, dmg_max_left;
    int32_t atk_rate, pvp_rate, defense, def_rate, pvp_defrate;
    int32_t magic_min, magic_max, curse_min, curse_max;
    int32_t atk_speed, magic_speed;
    char speed_text[32];
} mu_progress_view;
void mu_progress_get_view(const mu_progress *p, mu_progress_view *view);

/* The demo server's maxima for a class index, level and stats (DEMO) */
void mu_progress_demo_maxima(int32_t class_index, int32_t level, const int32_t stats[5], int32_t out[4]);
/* The DEMO kill experience of a server class */
int64_t mu_progress_demo_kill_exp(int32_t server_class, int32_t rate);

/* "F:kill:CLASS F:add:STAT F:button:ROW F:level:N" (frame numbers), for headless runs */
#define MU_PROGRESS_SCRIPT_MAX 128
typedef struct mu_progress_script_item {
    int32_t frame;
    char verb[16];
    int32_t a;
} mu_progress_script_item;
typedef struct mu_progress_script {
    mu_progress_script_item items[MU_PROGRESS_SCRIPT_MAX];
    int count;
} mu_progress_script;
int mu_progress_script_parse(mu_progress_script *script, const char *text);

#ifdef __cplusplus
}
#endif

#endif
