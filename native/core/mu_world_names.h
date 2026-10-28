#ifndef MU_WORLD_NAMES_H
#define MU_WORLD_NAMES_H

/* hudPlayerName's game side in the walk-around world (NATIVE-NAMES-001).
 *
 * Joins core/mu_names to the session: the hero (kind 1) and the demo-placed
 * monsters and NPCs (kind from SetMonsterInfo 0x013b8ade: NPCs get no
 * plate), their positions, session viewport HP, deaths and respawns, the
 * character under the cursor and chat lines.
 *
 * Server data, DEMO here: character keys (hero 0x1234 as mu_combat, actors
 * 0x100 + index), the hero's name and level, monster levels (0: names are
 * never coloured), the chat echo of the hero's own lines. Remote HP comes only from the
 * session viewport; absent HP stays zero and no damage-based pool is invented.  Names and name heights come from the Npcname(kor)
 * table (core/mu_lang, NATIVE-LANG-001: MU_LANG_DIR) when present;
 * otherwise the placement label and height 200 are placeholders.  Picking
 * the character under the cursor uses the demo cylinder test of mu_combat,
 * not the client's OBB selection. */

#include <stdint.h>

#include "mu_combat.h"
#include "mu_names.h"
#include "mu_walk.h"
#include "mu_world_actors.h"

struct mu_lang;

typedef struct mu_world_names {
    mu_names names;
    mu_label_fonts fonts;
    int has_fonts;
    mu_walk *walk;
    mu_world_actors *actors;
    mu_combat *combat;
    int32_t hero_key, actor_key0;
    uint32_t hp_seen[MU_WORLD_ACTORS_MAX];
    uint8_t dead_seen[MU_WORLD_ACTORS_MAX], shown[MU_WORLD_ACTORS_MAX];
    const struct mu_lang *lang;       /* NATIVE-LANG-001 tables (Npcname), NULL without them */
    struct mu_lang *own_lang;
    int32_t npc_count;                /* actors named from the table */
    int hover_enabled, created;
    int hero_wing;                    /* the hero wears a wing (c + 0x21a4 != -1): the caller sets it */
    int32_t hovered;
} mu_world_names;

typedef struct mu_world_names_config {
    const char *hero_name;            /* DEMO */
    int32_t hero_level;               /* DEMO */
    const char *lang_dir;             /* NATIVE-LANG-001 tables; NULL: owned load from $MU_LANG_DIR */
    const char *font_face;            /* stand-in font (NULL "Arial") */
    int monster_view;                 /* the option byte +0x44 (client default 1) */
} mu_world_names_config;

int mu_world_names_init(mu_world_names *wn, const mu_world_names_config *config, mu_walk *walk,
                        mu_world_actors *actors, mu_combat *combat);
void mu_world_names_free(mu_world_names *wn);
/* After every logic step (after the combat step): HP packets, deaths, respawns. */
void mu_world_names_step(mu_world_names *wn);
/* Every rendered frame, after the camera of the frame: the selection
 * wrapper 0x009a1618 and the handler's update 0x00c81d1e. */
void mu_world_names_frame(mu_world_names *wn, uint32_t now_ms);
/* A received chat line (the demo echoes the hero's own lines). */
void mu_world_names_chat(mu_world_names *wn, const char *name, const char *text);
/* Stand-in drawing into an RGBA frame (top row first). */
void mu_world_names_draw(mu_world_names *wn, uint8_t *frame, int32_t width, int32_t height);

#endif
