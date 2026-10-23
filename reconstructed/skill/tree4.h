#ifndef MU_TREE4_H
#define MU_TREE4_H

/* The fourth skill tree (NATIVE-SKILL-003, docs/research/client-skills.md section 12).  Pinned inputs as in
 * skill_use.h.  Static readings of the instructions; the behaviour is compared with the client's routines by
 * scripts/validate_skill_later.py.
 *
 * Data: Lang.mpr's 4ThTreeData, object 0x06fbb8ec (vtable 0x01aba1d4, minimum columns +0x38, map +0x3c).  The
 * loader 0x010b499f reads rows; a one-column row other than "end" opens a class (map +0x3c gets an empty class
 * object), and every other row goes to the row parser 0x010b4506 (vtable slot 8).  The parser rejects rows with
 * fewer than [+0x38] columns and rows of an unknown class, reads 27 integer columns (boost::lexical_cast<int>) and
 * hands the 0x6c-byte record to the class object (0x01098d4a): the group map (+8, keyed by column 1) gets an empty
 * group {+0 key, +4 rows = 0, +8 map} when it is new, and the group keeps the first record of an index (column 0);
 * rows = max(index / 10 + 1).  Getter 0x010b4406(class, group, index) -> record or the default 0x06fba950.
 *
 * Record (int32 columns, in file order except the five link pairs, which alternate in the file):
 *   f[0] index (slot), f[1] group, f[2] type (0 normal, 1, 2, 3 branch), f[3] sibling set (nodes with the same
 *   value exclude each other), f[4] skill, f[5], f[6], f[7] tooltip, f[8..12] child indices (-1 none, file columns
 *   8, 10, .., 16), f[13..17] the link's visibility (1 shown, file columns 9, 11, .., 17), f[18] cost (points per
 *   level), f[19] maximum level, f[20] level that opens the children, f[21] required skill and f[22] its level
 *   (master level for use types 3/4), f[23] / f[25] prerequisite skills in the same group and f[24] / f[26] their
 *   levels.  +0x6c is a byte the parser sets to 0 (a set byte hides the record).
 *
 * The window is the SkillTree4th handler (0xfc bytes, ctor 0x00c22e0b, GfxMgr +0x1f8, getter 0x0095fb49):
 *   +0x78 class index, +0x7c points, +0x80 / +0x84 pending (group, index) between the click and the confirm box,
 *   +0x88 current tab, +0x8c current group state, +0x90 map<group id, group state>, +0xa0 map<skill, node> of the
 *   use-type-8 skills, +0xa8 map<tab key, tab>, +0xec the branch popup flag, +0xf0 vector<int> the branch choices.
 * A group state (0x1c bytes, ctor 0x0109ed0a, init 0x0109ee60): +0 id, +4 rows, +8 kind (2 when a record has type
 * 2, else 0; it is also the group's tab key), +0xc map<index, node>, +0x14 map<index, node> of the roots (index
 * % 10 == 0 and type != 3).  A node (0x48 bytes, ctor 0x0109dee1): +0 index, +4 leaf flag, +8 state {skill, level,
 * value, next, +0x10 available, +0x11 open}, +0x34 record, +0x38 std::list parents, +0x40 std::list children. */

#include <stddef.h>
#include <stdint.h>

#include "skill_tooltip.h"

#ifdef __cplusplus
extern "C" {
#endif

#define MU_T4_FIELDS 27
#define MU_T4_LINKS 32
#define MU_T4_TEXT 4096

enum {
    MU_T4_INDEX = 0, MU_T4_GROUP = 1, MU_T4_TYPE = 2, MU_T4_SIBLING = 3, MU_T4_SKILL = 4, MU_T4_TIP = 7,
    MU_T4_CHILD = 8, MU_T4_SHOW = 13, MU_T4_COST = 18, MU_T4_MAX = 19, MU_T4_OPEN = 20, MU_T4_REQ_SKILL = 21,
    MU_T4_REQ_LEVEL = 22, MU_T4_PRE1 = 23, MU_T4_PRE1_LEVEL = 24, MU_T4_PRE2 = 25, MU_T4_PRE2_LEVEL = 26
};

typedef struct mu_t4_record {
    int32_t f[MU_T4_FIELDS];
    uint8_t hidden;                      /* +0x6c */
} mu_t4_record;

typedef struct mu_t4_tgroup {            /* a class object's group (0x0109a802) */
    int32_t key, rows;
    mu_t4_record *rec;                    /* sorted by index */
    int nrec, cap;
} mu_t4_tgroup;

typedef struct mu_t4_tclass {
    int32_t cls;
    mu_t4_tgroup *groups;                 /* sorted by key */
    int ngroups, cap;
} mu_t4_tclass;

typedef struct mu_t4_table {
    int32_t min_columns;                  /* +0x38 */
    mu_t4_tclass *classes;                /* sorted by class */
    int nclasses, cap;
} mu_t4_table;

void mu_t4_table_init(mu_t4_table *t, int32_t min_columns);
void mu_t4_table_free(mu_t4_table *t);
/* The loader's class row: an empty class object when the class is new. */
void mu_t4_table_class(mu_t4_table *t, int32_t cls);
/* 0x010b4506 over an already-cast row of `columns` values (the caller does the casts: mu_skill_lexcast_int; a
 * failed cast drops the row in the client's catch path).  Returns 1 when the row was accepted (the class exists and
 * the row has at least min_columns and 27 columns); a repeated index in a group keeps the first record. */
int mu_t4_table_row(mu_t4_table *t, int32_t cls, const int32_t *values, int columns);
/* 0x010b4406 / 0x010b4465: NULL for the client's default record / default class object. */
const mu_t4_record *mu_t4_table_get(const mu_t4_table *t, int32_t cls, int32_t group, int32_t index);
const mu_t4_tclass *mu_t4_table_class_of(const mu_t4_table *t, int32_t cls);

/* ---- the runtime tree ----------------------------------------------------------------------------------- */

typedef struct mu_t4_node {
    int32_t index;                        /* +0 */
    uint8_t leaf;                         /* +4: 1 until a child is linked */
    int32_t skill, level;                 /* +8, +0xc */
    float value, next;                    /* +0x10, +0x14 */
    uint8_t avail;                        /* +0x18 */
    uint8_t open;                         /* +0x19 */
    int32_t rect[4];                      /* +0x1c: the movie's slot rectangle x, y, x + w, y + h (0x00c2b3ec) */
    const mu_t4_record *rec;              /* +0x34 */
    int16_t parents[MU_T4_LINKS];         /* +0x38: positions in the group's node array, list order */
    int nparents;
    int16_t children[MU_T4_LINKS];        /* +0x40 */
    int nchildren;
    /* +0x2c map<skill, int>: on a use-type-8 skill's node, the learned use-type-7 enhancements below it and their
     * truncated values (0x00c2a28b) */
    int32_t enh_skill[MU_T4_LINKS], enh_value[MU_T4_LINKS];
    int nenh;
} mu_t4_node;

typedef struct mu_t4_group {
    int32_t id, rows, kind;
    mu_t4_node *nodes;                    /* +0xc, sorted by index */
    int nnodes;
    int16_t *roots;                       /* +0x14, node positions sorted by index */
    int nroots;
} mu_t4_group;

typedef struct mu_t4_tab {               /* 0x14 bytes, ctor 0x010a22f0 */
    int32_t key;                          /* +0 */
    int32_t page;                         /* +4 */
    int32_t count;                        /* +8 */
    int32_t *groups;                      /* +0xc map<position, group id> */
} mu_t4_tab;

typedef struct mu_t4_skill_node { int32_t skill; int group, node; } mu_t4_skill_node;

/* Boundary calls (the validator records the client's). */
typedef struct mu_t4_env {
    void *user;
    /* Skill(Kor) 0x00961620: the record's first byte and use type (+0x58); 0 when the record is missing. */
    int (*skill_info)(void *u, int32_t skill, int *byte0, int *use_type);
    int (*hero_has)(void *u, int32_t skill);                       /* 0x00a00287 on [0x01d1df1c] */
    int (*master_level)(void *u, int32_t skill);                   /* Master tree 0x00bb1d9d */
    const char *(*text)(void *u, int32_t index);                   /* GlobalText 0x0095f027 */
    void (*invoke)(void *u, const char *name, const char *json);   /* GFx invokes: JSON value or a printf string */
    void (*msgbox)(void *u, const char *text);                     /* 0x00b3967c */
    void (*confirm)(void *u, int id, const char *text);            /* 0x00b39648 */
    void (*event)(void *u, const char *what, int32_t a);
    /* 4thTreeSideOption 0x010b6f79(index, group): the side-option key holding the slot, -1 none. */
    int (*side_category)(void *u, int32_t index, int32_t group);
    /* the info popup (GfxMgr window 0x009e819e) is open and belongs to this tree (0x00aae6f9, 0x00bfe788) */
    int (*popup_shows_tree)(void *u);
    /* Skill(Kor)'s name of a skill (record +8; the side texts) */
    const char *(*skill_name)(void *u, int32_t skill);
} mu_t4_env;

/* 4thTreeSideOption (object 0x06fbbaec): +0x3c map<class, vector<record of 22 int32>> (f[0] class, f[1] category,
 * f[2] slot, f[3] skill, f[4]/f[7]/f[10] the category's points that open stages 1..3, f[5]/f[8]/f[11] their
 * costs, f[6]/f[9]/f[12] their levels, ...), +0x44 map<category, vector<(index, group)>>: the slots that count
 * for a category (0x00c2a4bc) and draw SlotBG 2 (0x010b6f79). */
typedef struct mu_t4_side_record { int32_t f[22]; } mu_t4_side_record;
typedef struct mu_t4_side_pair { int32_t category, index, group; } mu_t4_side_pair;
typedef struct mu_t4_side_table {
    mu_t4_side_record *records;           /* file order */
    int nrecords;
    mu_t4_side_pair *pairs;
    int npairs;
} mu_t4_side_table;

#define MU_T4_SIDE 8
typedef struct mu_t4_side_entry {        /* 0x18 bytes, ctor 0x00c2fd4c */
    uint8_t category, slot, level;        /* +0, +1, +2 */
    float value, next;                    /* +4, +8 */
    uint8_t locked;                       /* +0xc */
    int32_t state, stage;                 /* +0x10, +0x14 (1 by the ctor) */
} mu_t4_side_entry;

typedef struct mu_t4_window {
    const mu_t4_table *table;
    int32_t cls;                          /* +0x78 */
    int32_t points;                       /* +0x7c */
    int32_t pend_group, pend_index;       /* +0x80, +0x84 */
    int32_t cur_tab;                      /* +0x88 */
    int cur_group;                        /* +0x8c: position in groups, -1 none */
    mu_t4_group *groups;                  /* +0x90, sorted by id */
    int ngroups;
    mu_t4_skill_node *skill8;             /* +0xa0, sorted by skill */
    int nskill8;
    mu_t4_tab *tabs;                      /* +0xa8, sorted by key */
    int ntabs;
    uint8_t branch_visible;               /* +0xec */
    int32_t branch[MU_T4_LINKS];          /* +0xf0 */
    int nbranch;
    /* the side options (+0xb0: entries +4, points per category +0x10) */
    const mu_t4_side_table *side;
    uint8_t side_ready;
    mu_t4_side_entry side_entry[MU_T4_SIDE];
    int32_t side_points[64][2];
    int nside_points;
    int32_t side_pending[3];              /* +0xe0/+0xe4/+0xe8: the clicked entry's category, slot and level */
    float side_pos[MU_T4_SIDE][2];        /* +0xb4 map<index, {x, y}> (RequestSideOptionUIPos) */
    float side_size[2];                   /* +0xbc / +0xc0 (RequestSideOptionUISize) */
    float branch_pos[MU_T4_LINKS][2];     /* +0xc4 map<index, {x, y}> (RequestSelectBranchUIPos) */
    uint8_t hidden;                       /* +0xcc: the window draws nothing */
} mu_t4_window;

void mu_t4_window_init(mu_t4_window *w, const mu_t4_table *table);
void mu_t4_window_set_side(mu_t4_window *w, const struct mu_t4_side_table *side);
void mu_t4_window_free(mu_t4_window *w);

/* Group state (0x0109ee60 init with 0x0109fc40 links; the checks 0x0109f27c, 0x0109f339, 0x0109f400,
 * 0x0109f5d5, 0x0109f570; the level setter 0x0109f0a2 with 0x0109fd1a, 0x0109fddc, 0x0109ffac; the branch
 * cleanup 0x0109f6e1). */
int mu_t4_group_init(mu_t4_group *g, const mu_t4_tgroup *tg, const mu_t4_env *env);
void mu_t4_group_free(mu_t4_group *g);
int mu_t4_group_find(const mu_t4_group *g, int32_t index);           /* 0x0109f070 -> position or -1 */
int mu_t4_group_find_skill(const mu_t4_group *g, int32_t skill);     /* 0x0109f668 -> index or -1 */
int mu_t4_req_ok(const mu_t4_group *g, const mu_t4_env *env, int32_t index);       /* 0x0109f27c */
int mu_t4_prereq_ok(const mu_t4_group *g, int32_t index);                           /* 0x0109f339 */
int mu_t4_sibling_free(const mu_t4_group *g, int32_t index);                        /* 0x0109f400 */
int mu_t4_branch_parent(const mu_t4_group *g, int32_t index);                       /* 0x0109f5d5 */
int mu_t4_can_learn(const mu_t4_group *g, const mu_t4_env *env, int32_t index);    /* 0x0109f570 */
int mu_t4_has_sibling(const mu_t4_group *g, int32_t index);                         /* 0x0109f4bf */
void mu_t4_set_level(mu_t4_group *g, const mu_t4_env *env, int32_t index, int32_t level, float value,
                     float next);                                                   /* 0x0109f0a2 */
void mu_t4_branch_cleanup(mu_t4_group *g);                                          /* 0x0109f6e1 */

/* The window. */
void mu_t4_set_class(mu_t4_window *w, int32_t cls);                  /* +0x78 (0x00c23b6f's first step) */
void mu_t4_set_points(mu_t4_window *w, const mu_t4_env *env, int32_t points);      /* 0x00c23a96 SetRemainPoint */
void mu_t4_build(mu_t4_window *w, const mu_t4_env *env);             /* 0x00c24024 (reset 0x00c23e5f) */
void mu_t4_set_tab_info(const mu_t4_window *w, const mu_t4_env *env);/* 0x00c246b2 */
void mu_t4_show_page(mu_t4_window *w, const mu_t4_env *env, int32_t page);          /* 0x00c23dc2 */
void mu_t4_slots(const mu_t4_window *w, const mu_t4_env *env, int32_t group);       /* 0x00c24922 */
void mu_t4_refresh_all(mu_t4_window *w, const mu_t4_env *env);       /* 0x00c26e11 */
void mu_t4_refresh_group(const mu_t4_window *w, const mu_t4_env *env, int32_t group);  /* 0x00c25173 */
void mu_t4_entry(mu_t4_window *w, const mu_t4_env *env, int32_t index, int32_t group, int32_t level, float value,
                 float next);                                         /* 0x00c26224 */
void mu_t4_entry_links(const mu_t4_window *w, const mu_t4_env *env, int32_t index, int32_t group);   /* 0x00c2632a */
int mu_t4_branch_learned(const mu_t4_window *w, int32_t group, int32_t index);     /* 0x00c26c5c */
void mu_t4_skill8_refresh(mu_t4_window *w, const mu_t4_env *env);                  /* 0x00c2a1b7 */
/* 0x00c2a37a-style query: the enhancement value of `enh` under the use-type-8 skill `skill`; 0 when absent. */
int mu_t4_enhancement(const mu_t4_window *w, int32_t skill, int32_t enh, int32_t *value);
void mu_t4_change_tab(mu_t4_window *w, const mu_t4_env *env, int32_t tab);          /* 0x00c25b6c */
/* onClickprevBtn / onClicknextBtn (0x00c2c77e): the current tab's page (0x00c25baa) -1 / +1 through 0x00c23dc2. */
void mu_t4_step_page(mu_t4_window *w, const mu_t4_env *env, int step);
/* RequestSlotUIInfo(index, x, y, w, h) 0x00c2b3ec: every group's node of that index keeps the truncated rectangle. */
void mu_t4_slot_rect(mu_t4_window *w, int32_t index, float x, float y, float width, float height);
/* 0x00c25bda OnMouseClickSlot(index): 1 when the confirm box (id 0x73) opened. */
int mu_t4_click(mu_t4_window *w, const mu_t4_env *env, int32_t index);
void mu_t4_message(const mu_t4_env *env, int kind);                  /* 0x00c2a0f1 */
/* The confirm box's answer (0x00b3771c, id 0x73, result 0): the request fields when the pending record exists and
 * is not hidden; the pending pair is cleared (0x00c2b8c6).  Returns 1 with the fields. */
int mu_t4_confirm(mu_t4_window *w, int result, uint8_t *group, uint16_t *skill, uint16_t *index);
/* The request (0x00b3b703): C1 08 7E 01 <u8 group> <u16 skill> <u16 index> before the send XOR. */
size_t mu_t4_request(uint8_t *out, size_t cap, uint8_t group, uint16_t skill, uint16_t index);

/* The server's answers, opcode 0x7E (dispatcher 0x01287ead, sub = packet[3] of a C1 head / [4] of C2).
 * 0x02 0x0127f539: points (u16 +5), build, then entries of 12 bytes from +0xb (count u32 +7): u8 group, u16 index,
 * u8 level, f32 value, f32 next -> 0x00c26224 and 0x00c2632a each; then 0x00c23dc2(page) of the current tab ...
 * 0x01 0x0125051f: result +4: 1 learned (points u16 +5, group u8 +7, level u8 +8, index u16 +9, f32 +0xb, +0xf),
 * 4 and 7 messages. */
int mu_t4_receive(mu_t4_window *w, const mu_t4_env *env, const uint8_t *packet, size_t size);

/* ---- tooltip and icons (tree4_ui.c) ---------------------------------------------------------------------------
 * 4ThTreeSkillTooltip (object 0x06fbb930, map +0x3c keyed by skill, default record +0x44): {+0 skill, +4 text,
 * +0x1c the next level's text, +0x34 value kind (-1 the text alone, 0 an int, 1 a double), +0x38 show the next
 * level, +0x39 no value}. */
typedef struct mu_t4_tip {
    int32_t id;
    char desc[256], next[256];
    int32_t kind;
    uint8_t show_next, fixed;
} mu_t4_tip;
const mu_t4_tip *mu_t4_tip_of(const mu_t4_tip *tips, int ntips, int32_t skill);   /* 0x010ba100 (sorted) */
int mu_t4_parent_open(const mu_t4_group *g, int32_t index);                        /* 0x0109f1b9 */
/* 0x00c29007(index) (0x00c2986a for a branch): the classic text list as the master tooltip fills it (TextList
 * 0x10c76988, colours, bold, the header flags 0x0b477ef4) and the popup's anchor (the slot rectangle's x, y; size
 * 0x1a x 0x25); returns the line count the InfoPopup gets (0x00b8d94b), 0 without a node.  tenv: Skill(Kor), the
 * wrap and FormulaData (0x0117b5eb(mgr 3, f[7], f[18]) for level 0). */
int mu_t4_tooltip(const mu_t4_window *w, const mu_skill_tip_env *tenv, const mu_t4_env *env, const mu_t4_tip *tips,
                  int ntips, int32_t index, mu_skill_tip *out, uint8_t header[MU_SKILL_TIP_LINES], int32_t pos[2]);
/* 0x00c2bb34 (the window's per-frame icons; nothing with +0xcc set or without a current group): with the branch
 * popup (+0xec) its choices at +0xc4; else the current group's open nodes at (x0 + rect.x * scale) * ratio, size
 * rect * scale * ratio, white when available, else 0xff3c3c3c (skill -1: icon 0x1c1), then the side options at
 * +0xb4 with the side size.  Bitmap 0x7e1c (4th_Skill_Icon), cell icon % 25 / 25 of 0.0390625 x 0.0546875. */
typedef void (*mu_t4_draw_fn)(void *user, int32_t bitmap, float x, float y, float w, float h, float u, float v,
                              float uw, float vh, uint32_t color);
void mu_t4_icons(const mu_t4_window *w, const mu_skill_env *skills, float x0, float y0, float scale, float ratio_x,
                 float ratio_y, mu_t4_draw_fn draw, void *user);
/* SelectBranchSkill 0x00c2b5f4 and RequestSelectBranchUIPos 0x00c2b79d (the branch popup). */
int mu_t4_select_branch(mu_t4_window *w, const mu_t4_env *env, int32_t group, int32_t index);
void mu_t4_branch_rect(mu_t4_window *w, int32_t index, float x, float y);

/* 0x00c23175 SetText: one object of GlobalText strings (tabs, side and stat labels, buttons), PointResult
 * sprintf(GT 0x19f0, 0) and ExplainSelectDebuff through the HTML line builder 0x00ab4dc0(text 0x149f, 1, 0). */
void mu_t4_set_text(const mu_t4_env *env);
/* 0x00c239c2 SetLevel: sprintf(GT 0x144c, level + master level) (0x00a00367). */
void mu_t4_show_level(const mu_t4_env *env, int32_t level_sum);

/* Side options (tree4_side.c). */
void mu_t4_side_table_init(mu_t4_side_table *t);
void mu_t4_side_table_free(mu_t4_side_table *t);
void mu_t4_side_table_record(mu_t4_side_table *t, const int32_t f[22]);
void mu_t4_side_table_pair(mu_t4_side_table *t, int32_t category, int32_t index, int32_t group);
int mu_t4_side_category(const mu_t4_side_table *t, int32_t index, int32_t group);   /* 0x010b6f79, -1 none */
void mu_t4_side_index(const mu_t4_window *w, const mu_t4_env *env);                 /* 0x00c2436e */
void mu_t4_side_create(mu_t4_window *w, const mu_t4_env *env);                      /* 0x00c242b6 */
void mu_t4_side_set(mu_t4_window *w, int category, int slot, int level, float value, float next); /* 0x00c2a9cd */
void mu_t4_side_refresh(mu_t4_window *w, const mu_t4_env *env);                     /* 0x00c2aa33 */
/* OnBtnOverSideOption 0x00c29a29(index): SelectSideOptionCategory, then the side skill's tooltip as the slot's. */
int mu_t4_side_tooltip(mu_t4_window *w, const mu_skill_tip_env *tenv, const mu_t4_env *env, const mu_t4_tip *tips,
                       int ntips, int32_t index, mu_skill_tip *out, uint8_t header[MU_SKILL_TIP_LINES],
                       int32_t pos[2]);
void mu_t4_side_rect(mu_t4_window *w, int32_t index, float x, float y);            /* 0x00c2b4b3 */
void mu_t4_side_size(mu_t4_window *w, float width, float height);                  /* 0x00c2b580 */
/* OnBtnClickSideOption 0x00c2a5ad(index): messages 2 (locked), 1 (closed), 3 (points < the stage's cost); the
 * stat skills 0x472/0x477/0x4d9/0x4da open the stat panel (0x00c26ed3, not reconstructed: an event); else the
 * pending entry and the confirm box 0x79 (GT 0x6eb, "
", GT 0x143f with the stage's cost). 1: the box opened. */
int mu_t4_side_click(mu_t4_window *w, const mu_t4_env *env, int32_t index);
/* The box's answer (0x00b3771c case 0x79, result 0): category, slot, level + 1 for 0x00b3baf7; cleared (0x00c2b5b6). */
int mu_t4_side_confirm(mu_t4_window *w, int result, uint8_t *category, uint8_t *slot, uint8_t *level);
/* C1 07 7E 05 <u8 category> <u8 slot> <u8 level> (0x00b3baf7) before the send XOR. */
size_t mu_t4_side_request(uint8_t *out, size_t cap, uint8_t category, uint8_t slot, uint8_t level);

/* The runtime state as JSON (the validator's comparison and debugging); returns the full length. */
size_t mu_t4_dump(const mu_t4_window *w, char *out, size_t cap);

#ifdef __cplusplus
}
#endif

#endif
