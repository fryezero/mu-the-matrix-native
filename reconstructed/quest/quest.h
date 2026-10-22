#ifndef MU_QUEST_H
#define MU_QUEST_H

/* The client's quest system (NATIVE-QUEST-001, docs/research/client-quests.md).
 *
 * Restated in C from the pinned restored text (capture09 2bd5f2e9...3724) and
 * second section (run10 c985e2e6...a0672f); scripts/validate_quest.py runs the
 * client's routines in Unicorn and compares them with this library.
 *
 * Data (Lang.mpr tables, read from a running client: scripts/live_lang_to_plain.py):
 *   MUQuest        0x06fbbddc, map +0x38, 0x104-byte records (record builder 0x0113eb75):
 *                  +0 index, +4 name (std::string), +0x1c, +0x20, +0x24 the accept block (30 ints,
 *                  first 0), +0x9c the goal block (26 ints, first 1);
 *   MUQuestString  0x06fbbd9c, map +0x38: +0 index, +4 text, +0x1c type (1 title, 2 page,
 *                  3 progress text, 4 complete text, 5 summary), +0x20 quest index.
 * The quest system (singleton [0x01ec2e60], 0x2c bytes, constructor 0x00fe249e) is built while
 * MUQuest loads: the record builder calls 0x00fe138b (quest object) and 0x00fe15e9 (dialogue
 * object) for every record.  Maps: +4 index -> quest (0x38 bytes, 0x00fdfc65), +0xc category
 * id (2, 3, 4) -> category (0xc bytes: id, map index -> quest of the active quests), +0x14
 * index -> dialogue (0x6c bytes, 0x00fe74cb), +0x1c item code -> value (item goals of active
 * quests), +0x24 index -> value (packets F6 0x82 / 0x83).
 *
 * Packets (receive dispatcher 0x01287ead, opcode 0xF6, sub-code packet[3]) are handled by
 * mu_quest_receive; the windows they drive (NpcQuestProgress, MyQuestInfo, npcdialogue's quest
 * list) are reconstructed in quest_ui.c and report what the client does as an event log (GFx
 * invokes with their arguments, show/hide, packets sent, message boxes).  The packet layer's
 * encryption (C3/C4) and the XOR obfuscation of sub-codes 0x70 / 0x71 are out of scope: those
 * handlers take the decoded payload. */

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Planted mistakes for scripts/validate_quest.py --mutations (0 = the reconstruction). */
#ifndef MU_QUEST_MUTATION
#define MU_QUEST_MUTATION 0
#endif

#define MU_QUEST_ACCEPT_INTS 30
#define MU_QUEST_GOAL_INTS 26
#define MU_QUEST_CATEGORY_FIRST 2
#define MU_QUEST_CATEGORY_LAST 4

/* ---- data ---------------------------------------------------------------------------------- */

typedef struct mu_quest_record {          /* MUQuest record (0x104 bytes) */
    int32_t index;                        /* +0 */
    char *name;                           /* +4 std::string */
    int32_t f1c, f20;                     /* +0x1c, +0x20 (0 in this build) */
    int32_t accept[MU_QUEST_ACCEPT_INTS]; /* +0x24: [0] 0, [1] the group the requests carry, [5] the NPC class,
                                             [14..29] class flags (static reading of the data) */
    int32_t goal[MU_QUEST_GOAL_INTS];     /* +0x9c: [0] 1, [1] goal type, [2]/[3] item group/index or monster
                                             class, [4] count, [8] world, [11] exp, [12] zen, [13] the fourth
                                             reward line, [14..22] three reward items (group, index, level),
                                             [7..10] the move target (world, ?, x, y) */
} mu_quest_record;

typedef struct mu_quest_string {          /* MUQuestString record */
    int32_t index, type, quest;
    char *text;
} mu_quest_string;

typedef struct mu_quest_level_tip {       /* ItemLevelTooltip (0x06fbb9b0, map +0x38) record */
    int32_t key;
    int32_t group, index, level;          /* +0x18, +0x1a, +0x1c (u16) */
    char *name;                           /* +0 std::string */
} mu_quest_level_tip;

typedef struct mu_quest_data {
    mu_quest_record *records;             /* sorted by index (the map's order) */
    size_t nrecords;
    mu_quest_string *strings;             /* sorted by index */
    size_t nstrings;
    mu_quest_level_tip *level_tips;       /* sorted by key */
    size_t nlevel_tips;
} mu_quest_data;

/* Plaintext of scripts/live_lang_to_plain.py (MU_LANG_DIR):
 *   quests.tsv        index TAB name TAB f1c TAB f20 TAB 30 ints (space separated) TAB 26 ints
 *   queststrings.tsv  index TAB type TAB quest TAB text
 *   itemleveltip.tsv  key TAB group TAB index TAB level TAB name
 * Text fields use the converter's escapes (\t \n \r \\ \xHH).  Each parse replaces that table
 * (a repeated key keeps the first record, as std::map insert does); returns the count or -1. */
long mu_quest_parse_records(mu_quest_data *d, const char *text);
long mu_quest_parse_strings(mu_quest_data *d, const char *text);
long mu_quest_parse_level_tips(mu_quest_data *d, const char *text);
/* Loads the three files from a directory (missing files leave their table empty); returns the
 * MUQuest record count (0 when quests.tsv is absent). */
long mu_quest_load_dir(mu_quest_data *d, const char *dir);
void mu_quest_data_free(mu_quest_data *d);
const mu_quest_record *mu_quest_record_get(const mu_quest_data *d, int32_t index);   /* 0x0113e6de */

/* ---- the quest system ------------------------------------------------------------------------ */

typedef struct mu_quest {                 /* quest object (0x38 bytes, constructor 0x00fdfc65) */
    const mu_quest_record *record;        /* +0 */
    int32_t index;                        /* +4 */
    int32_t f20, f24;                     /* +0x20 record +0x1c, +0x24 record +0x20 */
    int32_t category;                     /* +0x28 0x00fe1a06(index) */
    int32_t state;                        /* +0x2c: 0 not taken, 1 in progress, 2 complete (reward), 3, 4 */
    int32_t count;                        /* +0x30 goal progress */
    uint8_t seen;                         /* +0x34 the list shows it as not new */
} mu_quest;

typedef struct mu_quest_dialogue {        /* dialogue object (0x6c bytes, 0x00fe74cb / 0x00fe764a) */
    int32_t index;                        /* +0 */
    const char *title;                    /* +4  MUQuestString type 1 (last one wins) */
    const char *progress;                 /* +0x1c type 3 */
    const char *complete;                 /* +0x34 type 4 */
    const char *summary;                  /* +0x4c type 5 */
    const char **pages;                   /* +0x64 map<string index, text> of type 2, in index order */
    int32_t npages;
} mu_quest_dialogue;

typedef struct mu_quest_pair {
    int32_t key, value;
} mu_quest_pair;

typedef struct mu_quest_system {
    const mu_quest_data *data;
    mu_quest *quests;                     /* +4, sorted by index */
    size_t nquests;
    mu_quest_dialogue *dialogues;         /* +0x14, sorted by index */
    size_t ndialogues;
    int32_t *active[3];                   /* +0xc: categories 2, 3, 4: their active quest indices, sorted */
    size_t nactive[3], cap_active[3];
    mu_quest_pair *items;                 /* +0x1c item code -> value, sorted */
    size_t nitems, cap_items;
    mu_quest_pair *values;                /* +0x24 index -> value, sorted */
    size_t nvalues, cap_values;
} mu_quest_system;

int32_t mu_quest_category(int32_t index);                                        /* 0x00fe1a06 */
/* Builds the system as the record builder does: 0x00fe249e, then for every MUQuest record
 * 0x00fe138b(index) and 0x00fe15e9(index) (the dialogue from MUQuestString, 0x00fe764a).
 * Returns 0, -1 on allocation failure. */
int mu_quest_system_build(mu_quest_system *qs, const mu_quest_data *data);
void mu_quest_system_free(mu_quest_system *qs);
mu_quest *mu_quest_get(const mu_quest_system *qs, int32_t index);                  /* 0x00fe14d4 */
const mu_quest_dialogue *mu_quest_dialogue_get(const mu_quest_system *qs, int32_t index);   /* 0x00fe1695 */
int mu_quest_has_category(const mu_quest_system *qs, int32_t category);            /* 0x00fe1506 != 0 */
int32_t mu_quest_item_value(const mu_quest_system *qs, int32_t code);              /* 0x00fe1555 (-1) */
int mu_quest_value_get(const mu_quest_system *qs, int32_t index, int32_t *value);  /* map +0x24 */
/* The active quests of a category in index order (0x00fdfede); returns the count. */
size_t mu_quest_active(const mu_quest_system *qs, int32_t category, const int32_t **indices);
int mu_quest_is_active(const mu_quest_system *qs, int32_t category, int32_t index);  /* 0x00fdfe8f != 0 */

/* ---- the event log ------------------------------------------------------------------------- */

/* One line per client effect, the form scripts/validate_quest.py records:
 *   invoke WINDOW METHOD ARGS     a GFx invoke 0x00aae7e0 (ARGS: a JSON array by the format)
 *   value WINDOW METHOD ARGS      an invoke with a GFx value 0x00aaf3ef (ARGS: a JSON array)
 *   show WINDOW / hide WINDOW     the window's show 0x00aae420 / hide 0x00aae470
 *   send HEX                      a packet the client sends (bytes after the builder)
 *   msgbox ...                    a message box (0x00b3967c / 0x00b39648)
 *   notice TEXT                   a system message (0x0095f4ec)
 *   summary add|remove|clear|update N   the quest summary HUD (QuestSummary, 0x00c89ff9 ...)
 * WINDOW is NpcQuestProgress, MyQuestInfo or npcdialogue. */
typedef struct mu_quest_log {
    char *text;
    size_t len, cap;
    int32_t lines;
} mu_quest_log;
void mu_quest_log_clear(mu_quest_log *log);
void mu_quest_log_free(mu_quest_log *log);

/* Host lookups (text in the client's code page; NULL when unknown). */
typedef struct mu_quest_host {
    void *user;
    const mu_quest_data *data;                                  /* ItemLevelTooltip for the reward items */
    const char *(*text)(void *user, int32_t index);            /* GlobalText 0x0095f027 */
    const char *(*npc_name)(void *user, int32_t npc);           /* Npcname 0x011427c7 */
    const char *(*map_name)(void *user, int32_t world);         /* 0x016baaa6 */
    const char *(*item_name)(void *user, int32_t code);         /* 0x00cd61a8 (empty when unknown) */
    int (*item_kind)(void *user, int32_t code, int32_t kind);   /* 0x00cd5fac(code, kind) */
    int (*item_byte)(void *user, int32_t code, int32_t value);  /* 0x00cd6017(code, value) */
    /* ANSI -> UTF-8 0x00a99d93 where the client converts; NULL: unchanged.  Returns dst. */
    const char *(*to_utf8)(void *user, const char *src, char *dst, size_t cap);
} mu_quest_host;

/* ---- texts ----------------------------------------------------------------------------------- */

typedef struct mu_quest_line {            /* the condition / reward object (0x20 bytes) */
    uint32_t font;                        /* +0 (0, or [0x06fc9ca8] for the reward) */
    uint32_t color;                       /* +4 ABGR */
    char text[1024];                      /* +8 */
} mu_quest_line;

/* 0x00fe1a52: the goal line; the object starts as 0x00fe4817 makes it ({[0x06fc9ca4] = font_default,
 * 0xff67bfdf, GlobalText 0x551}), which is also the result without a quest (returns 0 then). */
int mu_quest_condition(const mu_quest_host *h, const mu_quest *q, uint32_t font_default, mu_quest_line *out);
/* 0x00fe1e92: the reward lines joined, font [0x06fc9ca8] = font_reward (returns 0 likewise). */
int mu_quest_reward(const mu_quest_host *h, const mu_quest *q, uint32_t font_default, uint32_t font_reward,
                    mu_quest_line *out);
/* 0x0096fe90(text, colour, bold, line_break): the HTML line ("" for an empty text or "\n"). */
void mu_quest_html_line(const char *text, uint32_t color, int bold, int line_break, char *out, size_t cap);

/* ---- the client ------------------------------------------------------------------------------- */

typedef struct mu_quest_progress_window { /* NpcQuestProgress handler (0x168 bytes, ctor 0x00bedc4c) */
    int visible;
    int32_t quest;                        /* +0x78 */
    int32_t quest_ptr;                    /* +0x7c: the quest index the pointer refers to, or -1 (NULL) */
    char **pages;                         /* +0x80 deque<string> of the dialogue pages left */
    int32_t npages, page_first;
    char wrapped[4096];                   /* +0x94 (the movie's QuestDialogTextWidth) */
    char select[2048];                    /* +0xb0 stringstream: "1. ...;2. ...;" */
    int32_t mode;                         /* +0x160: -1, 1 pages, 2 conditions */
} mu_quest_progress_window;

typedef struct mu_quest_tab {             /* MyQuestInfo quest tab (0xc4 bytes, ctor 0x00d4f16e) */
    int32_t category;                     /* +0xbc */
    int32_t selected;                     /* +0x84 */
    char title[256];                      /* +0xa4 GlobalText 0x1522 / 0x1523 / 0x1524 */
    char base_text[256];                  /* +4 0x00fdc814: GlobalText 0xb09 */
} mu_quest_tab;

typedef struct mu_quest_info_window {     /* MyQuestInfo handler (0x88 bytes, ctor 0x00be3710) */
    int visible;
    int32_t tab;                          /* +0x78 */
    uint8_t first_open;                   /* +0x7c (1 after the constructor) */
    mu_quest_tab tabs[3];                 /* +0x80 map: tabs 2, 3, 4 (0 guide and 1 job change are not played) */
} mu_quest_info_window;

typedef struct mu_quest_dialog_list {     /* npcdialogue's quest-list mode (0x00be9c75) */
    int visible;
    uint8_t list_mode;                    /* +0x1d04 */
    int32_t options;                      /* +0x1c80 entries + 1 (the leave option) */
    int32_t quests[20];                   /* +0x1d0c: quest index per entry (the choice reads +0x1d08 + choice*4) */
    int32_t choice;                       /* +0x1cd8 */
    int32_t page_count, page;             /* +0x1ce0, +0x1cdc */
    int32_t line_count[21];               /* +0x1c84 */
    int32_t page_lines[4], page_entries[4];   /* +0x1ce4, +0x1cf4 */
    char lines[21][0x80];                 /* +0x1200 */
    int32_t text_state;                   /* +0x1d08 (0x00be86de) */
    char wrapped[4096];                   /* +0x1d68 the movie's NPCDialogTextWidth text (host-set) */
    int32_t ment_page;                    /* +0x11f8 the text page (host-set) */
} mu_quest_dialog_list;

typedef struct mu_quest_client {
    mu_quest_system qs;
    mu_quest_host host;
    mu_quest_progress_window progress;
    mu_quest_info_window info;
    mu_quest_dialog_list dialog;
    uint32_t font;                        /* [0x06fc9ca8] (the reward line's) */
    uint32_t font_default;                /* [0x06fc9ca4] (0x00fe4817) */
    int32_t world;                        /* [0x01cf15fc] */
    int32_t hero_x, hero_y;               /* hero +0x180 / +0x184 */
    char hero_name[32];                   /* the character name SetUIOpenText shows */
    int summary;                          /* the quest summary HUD exists (0x01d22c60 holds it) */
    const char *(*dialogue_word)(void *user, int32_t id);   /* QuestWords 0x00fdc9c1 (0x5dd, 0x5de, 0x3ef) */
    mu_quest_log log;
} mu_quest_client;

int mu_quest_client_init(mu_quest_client *c, const mu_quest_data *data, const mu_quest_host *host);
void mu_quest_client_free(mu_quest_client *c);

/* A quest packet (the payload after the C1 header: packet[0..3] included; sub-codes 0x70 and 0x71
 * already de-obfuscated).  Returns 1 when the sub-code is one of the handled ones. */
int mu_quest_receive(mu_quest_client *c, const uint8_t *packet, size_t size);

/* NpcQuestProgress (handler routines, quest_ui.c). */
int mu_quest_progress_set(mu_quest_client *c, int32_t quest);       /* 0x00bee2b3 */
int mu_quest_progress_show_page(mu_quest_client *c);                /* 0x00bee333 */
void mu_quest_progress_refresh(mu_quest_client *c);                 /* 0x00bee997 */
void mu_quest_progress_open(mu_quest_client *c);                    /* vtable +0x4c 0x00bedfb4 */
void mu_quest_progress_close(mu_quest_client *c);                   /* vtable +0x50 0x00bee1fa */
void mu_quest_progress_onload(mu_quest_client *c);                  /* vtable +8 0x00bedd69 */
int mu_quest_progress_select(mu_quest_client *c, int32_t index);    /* 0x00beebc2 */
void mu_quest_progress_confirm(mu_quest_client *c);                 /* 0x00beec0b */
void mu_quest_progress_wrapped(mu_quest_client *c, const char *text);   /* QuestDialogTextWidth 0x00beeb75 */
void mu_quest_progress_button(mu_quest_client *c, int complete);    /* 0x00beea7a */
/* The movie's callbacks (0x00beec8c): onClickSelectBtn(index), onClickbtnConfirm, LeaveComplete,
 * QuestDialogTextWidth(lines, text).  Returns 1 when handled. */
int mu_quest_progress_callback(mu_quest_client *c, const char *name, double number, const char *text);

/* npcdialogue's quest list (0x00be9c75) and its choice (0x00be906d, list mode). */
void mu_quest_dialog_quests(mu_quest_client *c, const int32_t *quests, int32_t n);
/* Returns 1 when the list mode took the choice; *leave 1 when it left the list (the host shows
 * dialogue state 0 again, 0x00be86de(0)). */
int mu_quest_dialog_choice(mu_quest_client *c, int32_t choice, int *leave);

/* MyQuestInfo. */
void mu_quest_info_open(mu_quest_client *c);                        /* vtable +0x40 0x00be420e */
void mu_quest_info_close(mu_quest_client *c);                       /* vtable +0x44 0x00be42dc */
void mu_quest_info_onload(mu_quest_client *c);                      /* vtable +8 0x00be3ab5 */
void mu_quest_info_tab_buttons(mu_quest_client *c);                 /* 0x00be4922 */
void mu_quest_info_checked(mu_quest_client *c);                     /* 0x00be4732 */
void mu_quest_info_select_tab(mu_quest_client *c, int32_t tab);     /* OnSelectTab */
void mu_quest_tab_init(mu_quest_client *c, mu_quest_tab *t);        /* tab vtable +4 0x00d4f285 */
void mu_quest_tab_select(mu_quest_client *c, mu_quest_tab *t, int32_t quest);   /* +0x2c 0x00d4f3ac */
void mu_quest_tab_show(mu_quest_client *c, mu_quest_tab *t, int32_t quest);     /* +0x10 0x00d4f2e0 */
void mu_quest_tab_list(mu_quest_client *c, mu_quest_tab *t);        /* 0x00d4f485 */
void mu_quest_tab_action(mu_quest_client *c, mu_quest_tab *t, int32_t quest);   /* 0x00d50067 */
mu_quest_tab *mu_quest_info_tab(mu_quest_client *c, int32_t tab);   /* 0x00be46dd (NULL outside 2..4) */
void mu_quest_info_giveup_ok(mu_quest_client *c);                   /* 0x00be436d(0x2d, 0) */
/* The movie's callbacks (0x00be4b89).  Returns 1 when handled. */
int mu_quest_info_callback(mu_quest_client *c, const char *name, const double *numbers, int n);

/* ---- hosts and tests ----------------------------------------------------------------------------- */

size_t mu_quest_client_size(void);
const char *mu_quest_log_text(const mu_quest_client *c);
void mu_quest_client_log_clear(mu_quest_client *c);
/* Named fields for hosts and the validator (ctypes): "progress.visible", "progress.quest", "progress.quest_ptr",
 * "progress.mode", "progress.pages", "info.visible", "info.tab", "info.first_open", "info.selected2" (3, 4),
 * "dialog.visible", "dialog.list_mode", "dialog.options", "dialog.choice", "summary", "font", "font_default", "world".
 * set != 0 writes value; returns the (new) value, or INT32_MIN for an unknown name. */
int32_t mu_quest_client_field(mu_quest_client *c, const char *name, int set, int32_t value);
/* A quest object's fields: state, count, seen, category (0 when the index has no quest object). */
int mu_quest_fields(const mu_quest_client *c, int32_t index, int32_t out[4]);
/* Sets a quest's state, count and seen directly (tests; the server does it through the packets). */
int mu_quest_set_fields(mu_quest_client *c, int32_t index, int32_t state, int32_t count, int32_t seen);
/* The item map (+0x1c) and the value map (+0x24) as "key=value,..." (sorted). */
const char *mu_quest_maps_text(const mu_quest_client *c);
void mu_quest_set_hero(mu_quest_client *c, const char *name);
void mu_quest_set_dialogue_words(mu_quest_client *c, const char *(*word)(void *user, int32_t id));
void mu_quest_dialog_set_text(mu_quest_client *c, const char *wrapped, int32_t page);

#ifdef __cplusplus
}
#endif

#endif
