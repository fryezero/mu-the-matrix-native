/* Talking to NPCs in the walk-around world (NATIVE-NPC-001,
 * docs/research/client-npc-interaction.md).
 *
 * Client behaviour (reconstructed/npc, the walk session's path finder):
 *   - picking: every logic step with a fresh left click, the client's
 *     character pick 0x016b47bf with the NPC mask 4 over each actor's
 *     oriented box (the character create's box for its model, placed at its
 *     position as the model transform does), before any other click use;
 *   - the click branch of MoveHero (0x016aae09, static): nothing while
 *     NpcShop or StorageInven is open; movement type c+0x39 = 2,
 *     TargetNpc = SelectedNpc, PathFinding2 toward the NPC's tile with
 *     distance 0 and level 2 (mu_walk_path_to); no path (already next to it)
 *     talks at once; model 0xa3e talks within 550 units;
 *   - MoveCharacters' character bit (0x0137a7ce, static): every step bit 2
 *     of TerrainWall is cleared and set again on the tile of every live
 *     character (hero, monsters, NPCs), so the path ends beside the NPC;
 *   - at the end of the walk MoveHero calls Action, whose talk case
 *     (0x0169901c, static) stops the hero (no turn toward the NPC, no talk
 *     animation), applies the local refusals, sets NpcShop's repair flag by
 *     class and sends the talk request;
 *   - the answer goes through ReceiveTalk 0x01280659 (mu_npc_talk_result,
 *     verified): the window per result code, SND_Play 25 and 28.
 *
 * DEMO (labelled; there is no server): the answer is produced locally after
 * `latency` steps from a demo table (talk result byte per server class,
 * dialog text, shop and storage contents), file format:
 *
 *     talk <server-class> <result-byte> [dialog <index> ...] [options <index> ...]
 *     shop <server-class> <item-code>[+level] ...
 *     storage <item-code>[+level] ...
 *     actor ...   (a placement line, appended to the session's --placement)
 *
 * Item codes are the client's (group * 512 + index). */
#ifndef MU_NPC_H
#define MU_NPC_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "../../reconstructed/npc/npc_pick.h"
#include "../../reconstructed/npc/npc_talk.h"
#include "mu_walk.h"
#include "mu_world_actors.h"

#define MU_NPC_DEMO_ROWS 32
#define MU_NPC_ITEMS 120
#define MU_NPC_DIALOG 8

typedef struct mu_npc_item {
    int32_t code, level;
} mu_npc_item;

typedef struct mu_npc_demo_row {
    int32_t server_class;
    int32_t result;                       /* talk result byte */
    int32_t dialog[MU_NPC_DIALOG], dialog_count;     /* Dialog(kor) indices: the pages */
    int32_t options[MU_NPC_DIALOG], option_count;    /* Dialog(kor) indices: the select buttons */
    mu_npc_item shop[MU_NPC_ITEMS];
    int32_t shop_count;
} mu_npc_demo_row;

typedef struct mu_npc_demo {
    mu_npc_demo_row rows[MU_NPC_DEMO_ROWS];
    int32_t count;
    mu_npc_item storage[MU_NPC_ITEMS];
    int32_t storage_count;
    char placement[4096];       /* "actor ..." lines for the placement */
    size_t placement_length;
} mu_npc_demo;

/* Parses the demo table; returns 0, or 1 with a message. */
int mu_npc_demo_parse(mu_npc_demo *demo, const char *text, char *error, size_t error_size);
int mu_npc_demo_load(mu_npc_demo *demo, const char *path, char *error, size_t error_size);
const mu_npc_demo_row *mu_npc_demo_find(const mu_npc_demo *demo, int32_t server_class);

/* What the host should show after an answer. */
typedef enum mu_npc_window_kind {
    MU_NPC_WINDOW_NONE = 0,
    MU_NPC_WINDOW_DIALOG,       /* npcdialogue */
    MU_NPC_WINDOW_SHOP,         /* NpcShop (+ the inventory, as the shop's Open 0x00bf0354 opens it) */
    MU_NPC_WINDOW_STORAGE,      /* StorageInven */
    MU_NPC_WINDOW_OTHER         /* a window the native client does not play (named by `movie`) */
} mu_npc_window_kind;

typedef struct mu_npc_open {
    mu_npc_window_kind kind;
    int32_t actor, server_class, npc_index, model;
    uint8_t result;
    mu_talk_window window;      /* the dispatch's view of the result */
    int repair;                 /* NpcShop repair flag the talk case set (0x00bf172e) */
    int32_t shop_tabs;          /* packet[0xb] (0x00bf17c2) */
    const mu_npc_demo_row *demo;
    int close_all;              /* the handler closed every window first */
} mu_npc_open;

typedef struct mu_npc_stats {
    uint32_t picks, pick_hits, clicks_ignored, walks, immediate_talks, talks, refusals, answers, windows,
        not_played, sounds;
} mu_npc_stats;

typedef struct mu_npc {
    mu_walk *walk;
    mu_world_actors *actors;
    const mu_npc_demo *demo;
    int32_t latency;            /* demo server answer delay (logic steps) */
    int32_t hero_level;         /* demo character level (the talk case's refusals) */
    int32_t selected;           /* SelectedNpc 0x01cf1150 at the last click */
    int32_t target;             /* TargetNpc 0x01cf1168 */
    uint8_t movement_type;      /* hero c + 0x39 (2: walking to talk) */
    uint32_t arrivals_seen;     /* walk->arrivals at the last step */
    int32_t pending_actor, pending_step;
    int32_t step;
    int window_open;            /* a shop or storage window is up (gates the click, 0x016aae23) */
    int character_bit;          /* apply MoveCharacters' TerrainWall bit 2 (default 1) */
    mu_pick_character pick[MU_PICK_CHARACTERS];
    int32_t last_pick;          /* index the last pick returned (-1) */
    /* host callbacks */
    void (*open)(void *context, const mu_npc_open *open);
    void (*close_all)(void *context);
    void (*sound)(void *context, int32_t id);
    void *context;
    mu_npc_stats stats;
    char log[32][112];
    int32_t log_count;
} mu_npc;

void mu_npc_init(mu_npc *npc, mu_walk *walk, mu_world_actors *actors, const mu_npc_demo *demo);

/* After the key scan, before MoveHero's click code (mu_walk pre-step hook):
 * picks NPCs on a fresh left click and starts the walk or the talk; a click
 * on an NPC is consumed (no terrain move). */
void mu_npc_pre_step(mu_npc *npc);
/* End of the logic step: MoveCharacters' wall bits, the talk at the end of
 * the walk, and the demo server's answer when due. */
void mu_npc_step(mu_npc *npc);
/* Talks to an actor directly (scripts): the click branch without picking. */
int mu_npc_click(mu_npc *npc, int32_t actor);
/* The host closed the NPC window. */
void mu_npc_window_closed(mu_npc *npc);
/* Actor by label or index (-1). */
int32_t mu_npc_find_actor(const mu_npc *npc, const char *name);
/* Builds the pick inputs from the actors (o + 0x3b kind: 4 NPC, 2 monster). */
void mu_npc_pick_inputs(mu_npc *npc);

void mu_npc_report_frame(const mu_npc *npc, FILE *out, int32_t frame);
void mu_npc_report_summary(const mu_npc *npc, FILE *out, int quiet);

/* Scripted interaction (headless runs, tests), items separated by ';', ','
 * or whitespace before the next "FRAME:":
 *   F:click:ACTOR  mouse click on the actor's screen position (through the pick)
 *   F:talk:ACTOR   the click branch without picking
 *   F:buy:SLOT  F:sell:CELL  F:take:SLOT  F:put:CELL  F:option:N  F:next  F:close
 * (the window verbs act on the GFx layer when it is loaded). */
#define MU_NPC_SCRIPT 32
typedef struct mu_npc_script_item {
    int32_t frame;
    char verb[8];
    char arg[48];
} mu_npc_script_item;
typedef struct mu_npc_script {
    mu_npc_script_item items[MU_NPC_SCRIPT];
    int32_t count;
} mu_npc_script;
int mu_npc_script_parse(mu_npc_script *script, const char *text);

#endif
