#ifndef MU_NAMES_H
#define MU_NAMES_H

/* Overhead names, monster HP bars and chat bubbles in the native world
 * (NATIVE-NAMES-001, docs/research/client-overhead-text.md).
 *
 * The client does all of this through the GFx movie hudPlayerName; its
 * game handler is reconstructed in reconstructed/names (verified against
 * the client in Unicorn).  This module runs that handler for the native
 * session's characters (the hero, the demo monsters) and
 *
 *   - forwards every operation to a sink: with --gfx, world_gfx sends them
 *     to the real movie through mugfx (addInfo/removeInfo invokes, the clip
 *     invokes and display-info changes the client makes);
 *   - keeps a model of what the movie shows (the AS2 code's effect of each
 *     call: PlayerName/PlayerNameMC, MonsterName/MonsterInfoMC, HudChat with
 *     its setInterval expiry), which mu_names_draw composites as a stand-in
 *     (core/mu_label) when the movie is not running.
 *
 * Client order per frame: the tick's selection wrapper 0x009a1618 (the
 * character under the cursor), then the movie handler's update 0x00c81d1e.
 * addInfo runs when a character is created (viewport/join packets),
 * removeInfo on deletion, at SetPlayerDie (non-Player models) and after the
 * dead fade; setHp on the monster HP packet and at SetPlayerDie.
 *
 * Demo/viewer choices are labelled where the data comes from the server
 * (keys, monster levels and HP) or where the stand-in replaces the movie's
 * drawing (fonts, bar colours). */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/names/overhead_names.h"
#include "mu_label.h"

#define MU_NAMES_MAX 64

/* What the movie shows for one key (the AS2 state the calls produce). */
typedef struct mu_names_plate {
    int32_t key, type;
    float x, y;                   /* the clip position (window pixels) */
    uint8_t mc_visible;           /* PlayerName._visible (isShow), set to 1 by the update */
    uint8_t info_visible;         /* MonsterInfoMC._visible (isShow / monster view / selection) */
    uint8_t hp_show, name_show, strife;
    int32_t hp, elemental, gens, mark;
    char name[MU_HN_TEXT], guild[MU_HN_TEXT], server[MU_HN_TEXT];
    char message[MU_HN_TEXT];     /* HudChat text */
    uint32_t message_until;       /* setInterval(validateNow, time) */
    uint32_t order;               /* setTopMovie / attach order (depth) */
} mu_names_plate;

/* Receiver of the movie calls (world_gfx forwards them to mugfx). */
typedef struct mu_names_sink {
    void *user;
    void (*add_info)(void *user, const mu_hn_info *info);
    void (*remove_info)(void *user, int32_t key, int32_t type);
    void (*op)(void *user, int32_t type, const mu_hn_op *op);
} mu_names_sink;

typedef struct mu_names_stats {
    uint32_t added, removed, skipped, frames, ops, positions, messages, hp_updates, selections;
} mu_names_stats;

typedef struct mu_names {
    mu_hn_window window;
    mu_hn_env env;
    mu_hn_character chars[MU_NAMES_MAX];
    uint8_t used[MU_NAMES_MAX];
    int32_t hero_slot;
    const mu_hn_character *hovered_current;   /* the wrapper's +0xc */
    mu_names_plate plates[MU_NAMES_MAX];
    int32_t plate_count;
    uint32_t order, now;
    mu_names_sink sink;
    void (*project)(void *context, const float position[3], float *x, float *y);
    void *project_context;
    mu_names_stats stats;
    char log[16][96];
    int32_t log_count;
} mu_names;

void mu_names_init(mu_names *n);
void mu_names_set_sink(mu_names *n, const mu_names_sink *sink);

/* The character record of a key, created with the CHARACTER defaults (guild
 * -1, wing -1, ride 0xffff, monster class -1, live) on first use. */
mu_hn_character *mu_names_character(mu_names *n, int32_t key);
mu_hn_character *mu_names_find(mu_names *n, int32_t key);
/* Marks a key as the hero ([0x0a39d754]). */
void mu_names_set_hero(mu_names *n, int32_t key);

/* addInfo (and the movie's addMC event).  Returns 1 when the movie got a plate. */
int mu_names_add(mu_names *n, int32_t key);
/* removeInfo; the character record stays unless forget. */
void mu_names_remove(mu_names *n, int32_t key, int forget);
/* setHp(key, hp, max) as the monster HP packet / SetPlayerDie. */
void mu_names_set_hp(mu_names *n, int32_t key, uint32_t hp, uint32_t max);
/* The character under the cursor (0x01cf1154), -1 none: 0x009a1618. */
void mu_names_hover(mu_names *n, int32_t key);
/* The monster info option (0x00c83c86). */
void mu_names_set_monster_view(mu_names *n, int view);
/* A received chat line (name, text): the prefix rules of 0x00c6066a and the
 * bubble 0x0169d87f.  gm: the sender is a GM (0x00c61a71).  Returns the
 * chat type the chat window gets. */
int32_t mu_names_chat(mu_names *n, const char *name, const char *text, int gm);
/* The handler's update (once per rendered frame), now = milliseconds. */
void mu_names_update(mu_names *n, void (*project)(void *context, const float position[3], float *x, float *y),
                     void *context, uint32_t now);

/* Stand-in drawing of the plates into an RGBA frame (top row first), in
 * depth order, as the movie would lay them out (positions from the
 * movie's sprites, see the research note). */
void mu_names_draw(const mu_names *n, mu_label_fonts *fonts, uint8_t *frame, int32_t width, int32_t height);

/* Run summary (JSON object body). */
void mu_names_report(const mu_names *n, char *out, size_t cap);

#endif
