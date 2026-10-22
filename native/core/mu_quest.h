/* Quests in the native client (NATIVE-QUEST-001, docs/research/client-quests.md).
 *
 * The client side is reconstructed/quest (libquest: the quest system, the F6
 * quest packets and the windows' game side, verified in Unicorn).  This module
 * runs it in a session: the quest tables come from the plaintext of a live
 * read (MU_LANG_DIR: quests.tsv, queststrings.tsv, itemleveltip.tsv), every
 * effect the client code produces (GFx invokes, show/hide, packets, notices)
 * reaches the host through `event` as libquest logs it, and the packets the
 * client sends go to a LOCAL DEMO server (there is no server in the native
 * session):
 *
 *   C1 F6 71 npc            the NPC's quest list: the demo answers F6 71 with
 *                           the quests the demo file offers for that dialogue NPC
 *                           and their states;
 *   C1 F6 72 group quest    accept: F6 72 result 0 (the quest goes to state 1);
 *   C1 F6 74 npc group quest  complete: F6 74 result 0 when the quest is in
 *                           state 2 (the demo adds the reward's zen and exp to its
 *                           counters), result 4 (quest item missing) otherwise;
 *   C1 F6 73 group quest    give up: F6 73 result 0;
 *   C1 F6 77, C1 54         no answer.
 * Progress (F6 75) is the demo's: a monster kill of the goal's class (goal
 * type 2) or in the goal's world (type 8) counts one; the talk goals (types
 * 4, 5, 6) complete when accepted; mu_quest_session_progress sets a count
 * (scripts).  Answers arrive `latency` steps after the request.
 *
 * Demo file lines (the NPC demo file of core/mu_npc, which keeps them):
 *     quest <dialogue-npc> <quest>[:<state>] ...   quests the NPC lists (start state, default 0)
 *
 * NATIVE-QUEST-002 adds the guide quest, the quest summary HUD, "Go Now" and the class-upgrade quests; the demo
 * server also answers:
 *   C1 F6 51 step          the guide step's reward: F6 51 result 1 (QuestProgressInfo), then F6 50 state 3
 *                          (the client steps to the next one);
 *   C1 F6 52 step / 53     give up the step / abort the chapter: F6 50 of the next step;
 *   C1 F6 55 step          arrived at a "Move to" step's target: F6 50 state 2;
 *   C1 F6 54 step, F6 7A group quest   the server moves the hero to another map: the TRAVEL hook (`travel`,
 *                          NATIVE-MAP-001 owns the warp); without a host the request is noted;
 *   C1 F6 76 group quest   arrived at a talk goal: F6 75 state 2;
 *   C1 B3 quest 1          a class-upgrade quest taken (state 3 -> 1) or completed (1 -> 2): C1 A1;
 *   C1 F6 1C               the current class-upgrade quest's kills: F6 1C.
 * Guide progress: a kill of a hunt step's monster (goal type 2, +0x90) counts one (F6 50, state 2 at the count);
 * class-upgrade kills count for the current quest's monster conditions.
 *     guide <step>[:<count>[:<state>]]              the hero's guide step at login (F6 50)
 *     classic <quest>:<state> ...                   class-upgrade quest states at login (C1 C0)
 */
#ifndef MU_QUEST_SESSION_H
#define MU_QUEST_SESSION_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "../../reconstructed/quest/quest.h"

#define MU_QUEST_OFFERS 64
#define MU_QUEST_QUEUE 32

typedef struct mu_quest_offer {
    int32_t npc, quest, state;
} mu_quest_offer;

typedef struct mu_quest_packet {
    int32_t due;
    size_t size;
    uint8_t bytes[256];
} mu_quest_packet;

typedef struct mu_quest_session_stats {
    uint32_t requests, answers, accepted, completed, given_up, progress, lists, events, invokes;
} mu_quest_session_stats;

typedef struct mu_quest_session {
    mu_quest_data data;
    mu_quest_client client;
    int ready;
    mu_quest_offer offers[MU_QUEST_OFFERS];
    int32_t noffers;
    mu_quest_packet queue[MU_QUEST_QUEUE];
    int32_t nqueue;
    int32_t step, latency;
    int32_t world;
    int64_t zen, exp;                     /* demo rewards received */
    /* the host's executor for every non-packet effect line (invoke/value/show/hide/notice/msgbox/summary...) */
    void (*event)(void *user, const char *line);
    void *user;
    mu_quest_session_stats stats;
    char last[160];
    char log[48][160];
    int32_t log_count;
    /* NATIVE-QUEST-002 */
    int32_t guide_step, guide_count, guide_state;   /* the demo's guide state (-1: no guide line) */
    uint8_t classic_states[50];                     /* the demo's class-upgrade states (2 bits each) */
    int32_t classic_count;                          /* quests the C0 packet carries (0: no classic line) */
    int32_t classic_kills[5][2];                    /* monster, kills of the current quest */
    /* the cross-map hook: the server would move the hero to (world, x, y); returns 1 when the host travelled */
    int (*travel)(void *user, int32_t world, int32_t x, int32_t y);
    uint32_t travels;
} mu_quest_session;

/* Loads the tables from `lang_dir` (NULL: $MU_LANG_DIR) and the offers from the demo text (may be NULL).
 * Returns 0, or 1 (no quest tables) with a message. */
int mu_quest_session_open(mu_quest_session *s, const char *lang_dir, const char *demo_text, const mu_quest_host *host,
                          char *error, size_t error_size);
void mu_quest_session_close(mu_quest_session *s);
/* The demo offers of a demo text (quest lines); returns the count. */
int32_t mu_quest_session_offers(mu_quest_session *s, const char *demo_text);
/* Logic step: delivers the due answers. */
void mu_quest_session_step(mu_quest_session *s);
/* A packet the client sent (C1 ...): the demo server's part. */
void mu_quest_session_request(mu_quest_session *s, const uint8_t *packet, size_t size);
/* The dialogue's server request 901 (0x00be906d case 0: C1 F6 71 with the dialogue NPC). */
void mu_quest_session_npc_list(mu_quest_session *s, int32_t npc);
/* The demo NPC talk answer C1 A1 with the current class-upgrade quest and its packed state byte. */
void mu_quest_session_classic_talk(mu_quest_session *s);
/* Demo progress. */
void mu_quest_session_kill(mu_quest_session *s, int32_t monster_class, int32_t world);
void mu_quest_session_progress(mu_quest_session *s, int32_t quest, int32_t count);
/* The quest window (T): open or close MyQuestInfo as its vtable +0x40 / +0x44 do. */
void mu_quest_session_toggle_info(mu_quest_session *s);
void mu_quest_session_report(const mu_quest_session *s, FILE *out);
/* Tests (ctypes): the session's size, its client, and the host's event callback. */
size_t mu_quest_session_size(void);
mu_quest_client *mu_quest_session_client(mu_quest_session *s);
void mu_quest_session_set_event(mu_quest_session *s, void (*event)(void *user, const char *line), void *user);
void mu_quest_session_set_travel(mu_quest_session *s, int (*travel)(void *user, int32_t world, int32_t x, int32_t y));
/* NATIVE-QUEST-002: Data/Local/quest.bmd from the game root (the class-upgrade quests); returns the record count or
 * -1.  The demo's login packets (F6 50, C1 C0) are queued by mu_quest_session_open from the demo text. */
long mu_quest_session_load_classic(mu_quest_session *s, const char *game_root);
/* The demo lines `guide` / `classic` of a demo text (open reads them). */
void mu_quest_session_demo_state(mu_quest_session *s, const char *demo_text);

#endif
