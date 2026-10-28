/* Demo-tool compatibility facade. The client belongs to mu_session; all demo policy lives in fixture. */
#ifndef MU_QUEST_SESSION_H
#define MU_QUEST_SESSION_H
#include <stdio.h>
#include "../session/mu_session.h"
struct mu_fixture;
typedef struct mu_quest_session_stats
{
    uint32_t requests, answers, accepted, completed, given_up, progress, lists, events, invokes;
} mu_quest_session_stats;
typedef struct mu_quest_session
{
    mu_session *session;
    struct mu_fixture *fixture;
    mu_transport *transport;
    const mu_quest_client *client; /* compatibility test accessor; views submit QUEST_WINDOW */
    mu_cue_cursor cursor;
    int ready, step;
    void (*event)(void *, const char *);
    void *user;
    int (*travel)(void *, int32_t, int32_t, int32_t);
    uint32_t travels;
    uint8_t travel_answer;
    mu_quest_session_stats stats;
    char cue_line[16384];
    size_t cue_size;
} mu_quest_session;
/* Loads the tables from `lang_dir` (NULL: $MU_LANG_DIR) and the offers from the demo text (may be NULL).
 * Returns 0, or 1 (no quest tables) with a message. */
int mu_quest_session_open(mu_quest_session *s, const char *lang_dir, const char *demo_text,
                          const mu_quest_host *host, char *error, size_t error_size);
void mu_quest_session_close(mu_quest_session *s);
/* The demo offers of a demo text (quest lines); returns the count. */
int32_t mu_quest_session_offers(mu_quest_session *s, const char *demo_text);
/* Logic step: delivers the due answers. */
void mu_quest_session_step(mu_quest_session *s);
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
void mu_quest_session_set_travel(mu_quest_session *s,
                                 int (*travel)(void *user, int32_t world, int32_t x, int32_t y));
void mu_quest_session_travel_complete(mu_quest_session *s, int success);
/* NATIVE-QUEST-002: Data/Local/quest.bmd from the game root (the class-upgrade quests); returns the record count
 * or -1.  The demo's login packets (F6 50, C1 C0) are queued by mu_quest_session_open from the demo text. */
long mu_quest_session_load_classic(mu_quest_session *s, const char *game_root);
/* The demo lines `guide` / `classic` of a demo text (open reads them). */
void mu_quest_session_demo_state(mu_quest_session *s, const char *demo_text);

int mu_quest_session_window(mu_quest_session *, mu_quest_action, const char *, const char *, double, double);
int mu_quest_session_command(mu_quest_session *, const char *);
#endif
