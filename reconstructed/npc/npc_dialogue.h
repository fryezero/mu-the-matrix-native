#ifndef MU_NPC_DIALOGUE_H
#define MU_NPC_DIALOGUE_H

/* The NPC dialogue manager (singleton 0x01ec9858) and the npcdialogue window's
 * choice logic (NATIVE-LANG-002, docs/research/client-npc-interaction.md).
 *
 * The manager is fed by three local files, not by Lang.mpr (static reading of
 * its loaders, verified in Unicorn by scripts/validate_npc_dialogue.py):
 *   - Data\Local\NPCDialogue.bmd, loader 0x00fdcbb4: 88-byte records read
 *     until a short read, each decoded by 0x00976855; the first u32 is the
 *     key (NPC class << 16) + state, the other 84 bytes the value: the text id
 *     and ten (option text id, next) pairs; std::map insert at +4 (a repeated
 *     key keeps the first record);
 *   - Data\Local\QuestProgress.bmd, loader 0x00fdccc1: 41-byte records into
 *     the map at +0xc (not used by the dialogue window);
 *   - Data\Local\QuestWords.bmd, loader 0x00fdcdc8: repeated 6-byte headers
 *     (u32 id, s16 length) and texts, each unit decoded by 0x00976855; the
 *     text becomes a std::string from its first NUL (constructor 0x0094afda);
 *     std::map insert at +0x14 (first wins).
 * The routines here take the decoded bytes (reconstructed/data decodes the
 * files with the same unit schedule).
 *
 * Lookups (thiscall on the manager; +0x1c is the dialogue NPC 0x00fdc96c
 * stores):
 *   0x00fdc9c1 text(id)              the QuestWords string or NULL;
 *   0x00fdca1b state_text(state)     NULL when the NPC is 0 or the record is
 *                                    absent, else text(record text id);
 *   0x00fdca92 option_text(state, i) NULL for NPC 0, an absent record or an
 *                                    option text id 0, else text(id);
 *   0x00fdcb1f option_next(state, i) 0 for NPC 0, -1 for an absent record or an
 *                                    option text id 0, else the option's next.
 * The window (handler 0x00be906d, the quest-list mode +0x1d04 == 0): the
 * chosen option's next (0x00fdcb1f(state, choice)) shows that state when it is
 * <= 900 and not -1 (0x00be86de); 901..920 are server requests (packets C1 F6 /
 * C1 F8 with sub-codes, some close the window, static); anything else shows
 * state 999.  The option list (0x00be8a9b) stops at the first absent option
 * text (i < 10). */

#include <stddef.h>
#include <stdint.h>

#define MU_DLG_RECORD_SIZE 88
#define MU_DLG_OPTIONS 10
#define MU_DLG_SHOW_LIMIT 900         /* 0x00be9199: cmp next, 0x384; jg */
#define MU_DLG_ACTION_FIRST 901       /* 0x00be91bf: next - 0x385, jump table of 20 */
#define MU_DLG_ACTION_LAST 920
#define MU_DLG_FALLBACK_STATE 999     /* 0x00be98f9: push 0x3e7 */

typedef struct mu_dlg_record {
    int32_t key;                      /* (npc << 16) + state */
    int32_t text;                     /* value +0 */
    int32_t option_text[MU_DLG_OPTIONS], option_next[MU_DLG_OPTIONS];   /* value +4 + 8i, +8 + 8i */
} mu_dlg_record;

typedef struct mu_dlg_word {
    int32_t id;
    char *text;
} mu_dlg_word;

typedef struct mu_dlg_tables {
    mu_dlg_record *records;           /* sorted by key, first record of a key kept */
    size_t nrecords;
    mu_dlg_word *words;               /* sorted by id, first text of an id kept */
    size_t nwords;
    int32_t npc;                      /* manager +0x1c (0x00fdc96c) */
} mu_dlg_tables;

/* Parse the decoded NPCDialogue.bmd bytes (whole 88-byte records; a short tail is ignored as the loader's short
 * read is).  Returns the number of records kept, -1 on allocation failure. */
long mu_dlg_parse_records(mu_dlg_tables *t, const uint8_t *decoded, size_t size);
/* Parse the decoded QuestWords.bmd bytes.  A header whose length is negative or runs past the end stops the
 * parse (the client's fread would fail or overrun).  Returns the number of texts kept, -1 on failure. */
long mu_dlg_parse_words(mu_dlg_tables *t, const uint8_t *decoded, size_t size);
void mu_dlg_free(mu_dlg_tables *t);

void mu_dlg_set_npc(mu_dlg_tables *t, int32_t npc);                       /* 0x00fdc96c (the name copy aside) */
const mu_dlg_record *mu_dlg_find(const mu_dlg_tables *t, int32_t npc, int32_t state);
const char *mu_dlg_text(const mu_dlg_tables *t, int32_t id);                         /* 0x00fdc9c1 */
const char *mu_dlg_state_text(const mu_dlg_tables *t, int32_t state);                /* 0x00fdca1b */
const char *mu_dlg_option_text(const mu_dlg_tables *t, int32_t state, int32_t i);    /* 0x00fdca92 */
int32_t mu_dlg_option_next(const mu_dlg_tables *t, int32_t state, int32_t i);        /* 0x00fdcb1f */

typedef enum mu_dlg_choice_kind {
    MU_DLG_SHOW = 0,                  /* show `value` (0x00be86de(value)) */
    MU_DLG_ACTION                     /* server request `value` (901..920) */
} mu_dlg_choice_kind;

typedef struct mu_dlg_choice {
    mu_dlg_choice_kind kind;
    int32_t value;
} mu_dlg_choice;

/* 0x00be906d (quest-list mode off): the effect of choosing option `choice` (0-based) in `state`. */
mu_dlg_choice mu_dlg_select(const mu_dlg_tables *t, int32_t state, int32_t choice);
/* The options the window lists for a state (0x00be8a9b without its line-count stop): the count of leading
 * options whose text is present (at most 10). */
int mu_dlg_option_count(const mu_dlg_tables *t, int32_t state);
/* Static reading of the 20 server requests: 1 when the case also closes the window (0x00be8565). */
int mu_dlg_action_closes(int32_t action);

#endif
