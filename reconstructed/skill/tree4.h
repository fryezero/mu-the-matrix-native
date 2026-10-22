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
} mu_t4_env;

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
} mu_t4_window;

void mu_t4_window_init(mu_t4_window *w, const mu_t4_table *table);
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

/* The runtime state as JSON (the validator's comparison and debugging); returns the full length. */
size_t mu_t4_dump(const mu_t4_window *w, char *out, size_t cap);

#ifdef __cplusplus
}
#endif

#endif
