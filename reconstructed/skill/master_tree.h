#ifndef MU_MASTER_TREE_H
#define MU_MASTER_TREE_H

/* The master skill tree (NATIVE-SKILL-002, docs/research/client-skills.md section 10).  Pinned inputs as in
 * skill_use.h.
 *
 * The client's "master skill manager" is the MasterSkillTree window's handler (0xd8 bytes, ctor 0x00baf1ef,
 * GfxMgr +0x1f4, getter 0x0095f998).  Its state (static readings; the behaviour verified by
 * scripts/validate_skill_tree.py):
 *   +0x78 u16[3]      points spent per tree (group 0..2), the SetText attribute lines;
 *   +0x7e u8[3][10]   the highest level seen per (tree, rank) — the rank rule's memory;
 *   +0x9c / +0xa0     the pending learn (cost, skill) between the click and the confirm box;
 *   +0xa4 / +0xa8 / +0xac   the class mask bit, the GlobalText of the three tree names, of the class title;
 *   +0xb8 map<skill, Entry>   the learned master skills {u8 level, f32 value, f32 next value, u8 flag};
 *   +0xc0 map<slot, Node>     the class's MasterSkillTreeData records (24 bytes, keyed by the movie slot 1..108);
 *   +0xc8 map<skill, Tip>     the class's MasterSkillTooltip records (808 bytes);
 *   +0xd0 map<slot, {x, y}>   the slot positions the movie reports (RequestPositionInfo).
 * The server's answers (opcode 0xA0: sub 0x10 the list, 0x14 a learn result) fill +0xb8; a click on a slot runs the
 * client's checks and, after the confirm box (id 0x47), sends C1 08 01 16 <u32 skill>. */

#include <stddef.h>
#include <stdint.h>

#include "skill_list.h"
#include "skill_tooltip.h"
#include "skill_use.h"

#ifdef __cplusplus
extern "C" {
#endif

#define MU_MASTER_NODES 256
#define MU_MASTER_LEARNED 1024
#define MU_MASTER_TIPS 1024

typedef struct mu_master_entry {        /* +0xb8 value (setter 0x00bb5ab7) */
    uint8_t level;                       /* +0 (0x00bb5a5b) */
    float value;                         /* +4 (0x00bb5a6a) */
    float next;                          /* +8 (0x00bb5a4c) */
    uint8_t flag;                        /* +0xc (0x00bb5a79) */
} mu_master_entry;

typedef struct mu_master_node {         /* MasterSkillTreeData, 24 bytes (copied to 0x01d22d70) */
    uint8_t slot;                        /* +0 the movie slot 1..108 (map key) */
    uint8_t x1;                          /* +1 */
    uint16_t mask;                       /* +2 class mask */
    uint8_t group;                       /* +4 tree 0..2 */
    uint8_t cost;                        /* +5 points per level */
    uint8_t max_level;                   /* +6 */
    uint8_t arrow;                       /* +7 SetArrowDirection */
    int32_t prereq1, prereq2;            /* +8, +0xc: learned with level >= 10 */
    int32_t skill;                       /* +0x10 */
    int32_t formula;                     /* +0x14 FormulaData id (group 3) of the level-0 value */
} mu_master_node;

typedef struct mu_master_tip {          /* MasterSkillTooltip, 808 bytes (copied to 0x01d2ed70) */
    int32_t skill;                       /* +0 (map key) */
    int16_t mask;                        /* +4 class mask (-1 all) */
    char rank_line[64];                  /* +0x006 "Rank %d, Skill Level: %d/%d" */
    char desc[256];                      /* +0x046 '#' line breaks, %d or a float format */
    char cost_line[32];                  /* +0x146 "Required Points: %d" */
    char brand_line[64];                 /* +0x166 */
    char rank_req[128];                  /* +0x1a6 */
    char pre1[128];                      /* +0x226 */
    char pre2[128];                      /* +0x2a6 */
} mu_master_tip;
void mu_master_node_decode(const uint8_t rec[24], mu_master_node *out);
void mu_master_tip_decode(const uint8_t rec[808], mu_master_tip *out);

typedef struct mu_master_learned { int32_t skill; mu_master_entry e; } mu_master_learned;
typedef struct mu_master_pos { uint8_t has; float x, y; } mu_master_pos;

typedef struct mu_master_tree {
    uint8_t state[0x24];                 /* +0x78..+0x9b: u16 spent[3], then u8 ranks[3][10] (byte addressed) */
    uint8_t pending_cost;                /* +0x9c */
    uint8_t pad9d[3];                    /* +0x9d (the rank rule's index can reach these bytes: tree 3) */
    int32_t pending_skill;               /* +0xa0 */
    int32_t mask, gt_names, gt_title;    /* +0xa4, +0xa8, +0xac */
    float icon_w, icon_h;                /* +0xb0, +0xb4 */
    mu_master_learned learned[MU_MASTER_LEARNED];   /* +0xb8, sorted by skill */
    int nlearned;
    mu_master_node nodes[MU_MASTER_NODES];          /* +0xc0, sorted by slot */
    int nnodes;
    const mu_master_tip *tips[MU_MASTER_TIPS];      /* +0xc8, sorted by skill (the caller keeps the records) */
    int ntips;
    mu_master_pos pos[256];                          /* +0xd0 */
} mu_master_tree;

void mu_master_init(mu_master_tree *t);
uint16_t mu_master_spent(const mu_master_tree *t, int group);
uint8_t mu_master_rank_seen(const mu_master_tree *t, int group, int rank);

/* Boundary calls the routines make (the validator records the client's). */
typedef struct mu_master_env {
    void *user;
    const mu_skill_env *skills;                                   /* Skill(Kor) */
    const char *(*text)(void *u, int32_t index);                  /* GlobalText 0x0095f027 */
    void (*invoke)(void *u, const char *name, const char *args);  /* movie invokes (Invoke 0x00aae7e0) */
    void (*msgbox)(void *u, int owner, const char *text);         /* 0x00b3967c (owner 0 / the tree) */
    void (*confirm)(void *u, int id, const char *text);           /* 0x00b39648 (owner the tree) */
    int (*special_item)(void *u, int32_t skill);                  /* 0x0109260c [1] */
    void (*event)(void *u, const char *what, int32_t a);          /* other notifications (sound, stat recalc...) */
    /* the hero (attributes [0x01d1df1c]) */
    int32_t points;                      /* +0x34 (0x00a001a6) master points */
    int32_t level_sum;                   /* 0x00a00367: level + master level */
    uint64_t exp, next_exp;              /* 0x00a00131 / 0x00a0015d */
} mu_master_env;

/* 0x00baf92c: the class code ((stage - 1) << 4 | class index; 0x20..0x4f) -> mask / GlobalText ids; 0 when the code
 * is outside the switch (the fields stay). */
int mu_master_class(mu_master_tree *t, int code);
/* 0x00baf8f3 after the class switch: 0x00bb0250 (nodes with the mask bit, up to the first zero slot or the first
 * repeated slot), 0x00bb02fe (tooltips, up to skill 0 or the first repeated skill), 0x00bb04ac (SetArrowDirection per
 * node, SetSkillSlot "s1,s2,...,"); SetText(0x7f) is the caller's (mu_master_set_text). */
void mu_master_build(mu_master_tree *t, const mu_master_env *env, const mu_master_node *nodes, int nnodes,
                     const mu_master_tip *tips, int ntips);

/* Accessors over +0xb8 (0x00bb1d9d level, 0x00bb1ca1 value, 0x00bb5a4c next, 0x00bb1df9 flag, 0x00bb1e55 has). */
const mu_master_entry *mu_master_find(const mu_master_tree *t, int32_t skill);
uint8_t mu_master_level(const mu_master_tree *t, int32_t skill);
float mu_master_value(const mu_master_tree *t, int32_t skill);
uint8_t mu_master_flag(const mu_master_tree *t, int32_t skill);
int mu_master_is_master(int32_t skill);                                   /* 0x00bb1ea1: 300..929 */
float mu_master_chain(const mu_master_tree *t, const mu_skill_env *env, int32_t skill, int32_t flag);   /* 0x00bb1ed0 */
float mu_master_kind_sum(const mu_master_tree *t, const mu_skill_env *env, int32_t skill, int kind);    /* 0x00bb1cfd */
const mu_master_node *mu_master_node_at(const mu_master_tree *t, int slot);
const mu_master_tip *mu_master_tip_of(const mu_master_tree *t, int32_t skill);

/* The checks of a click (static readings verified as a whole by the click family). */
int mu_master_points_ok(const mu_master_env *env, int16_t points, const mu_master_node *n, int16_t level); /* 0x00bb194c */
int mu_master_prereq_ok(const mu_master_tree *t, int32_t p1, int32_t p2);                                 /* 0x00bb1a19 */
int mu_master_rank_ok(mu_master_tree *t, uint8_t group, uint8_t rank, uint8_t level);                     /* 0x00bb1b06 */
int mu_master_brand_ok(const mu_skill_env *env, const mu_skill_hero *hero, int32_t skill, uint8_t level); /* 0x00bb1b76 */
/* 0x00bb22e1: OnClickBtnSkillSlot(slot).  Returns 1 when the confirm box (id 0x47) opened, 0 otherwise. */
int mu_master_click(mu_master_tree *t, const mu_master_env *env, const mu_skill_hero *hero, int slot);
/* 0x00baf47b: the box's answer; id 0x47 with result 0 (OK) gives the request's two body fields (the u8 0x16 and the
 * u32 skill, opcode 0x01 of a C1 packet); returns 1 then. */
int mu_master_confirm(const mu_master_tree *t, int id, int result, int32_t *skill);
/* The request as sent (C1 08 01 16 <u32 skill>) before the send XOR (mu_protocol encodes the body bytes). */
size_t mu_master_request(uint8_t *out, size_t cap, int32_t skill);

/* 0x00bb0803 SetText(mask): one "SetText %d %s" per bit (1 class title, 2 level, 4 points, 8 exp %, 0x10/0x20/0x40
 * the trees' spent points). */
void mu_master_set_text(const mu_master_tree *t, const mu_master_env *env, int mask);
/* 0x00bb03bc RequestPositionInfo(slot, x, y): the icon size from the window scale and the GfxMgr ratios, the
 * slot's position (kept when already known). */
void mu_master_position(mu_master_tree *t, int slot, float x, float y, float scale, float ratio_x, float ratio_y);

/* The server's answers.  0x012863c5 (A0 10): clear +0xb8 and +0x78..+0x9b, then 0x00bb0644 per 16-byte entry from
 * +0xc (count u32 at +8): the node's skill gets the entry, the tree's spent points grow by the *level*, SetRank, and
 * SetText(0x70) per entry.  0x01285995 (A0 14): the hero's points (+6); result 1: 0x00bb25f3 (the hero's list: the
 * brand becomes the skill), the stamp manager's and the hotkeys' add, 0x00bb26a8 (the entry replaced, spent points
 * grow by the node's *cost*, SetText(0x74), SetRank, the tooltip again when the popup is visible); 6 / 7: message
 * boxes GlobalText 0xd09 / 0xd1a. */
int mu_master_receive_list(mu_master_tree *t, const mu_master_env *env, const uint8_t *packet, size_t size);
int mu_master_receive_learn(mu_master_tree *t, const mu_master_env *env, mu_skill_world *w, const uint8_t *packet,
                            size_t size, int popup_visible, int32_t *points);
void mu_master_list_entry(mu_master_tree *t, const mu_master_env *env, int slot, int level, float value, float next,
                          int flag);                                                          /* 0x00bb0644 */
void mu_master_hero_upgrade(const mu_skill_env *env, mu_skill_hero *hero, int32_t skill);      /* 0x00bb25f3 */

/* 0x00a01692: the skill damage the tooltip shows (the brand chain from the skill to its base: the base's record
 * damage, or for a master base (use type 4) the formula of group 3 (level 0, brand 0) or its master value; each
 * upgrade of flag 1 adds its truncated master value).  formula: 0x0117b5eb(mgr, 3, damage, master factor). */
typedef double (*mu_master_formula_fn)(void *user, int32_t group, int32_t a, int32_t b);
int32_t mu_master_skill_damage(const mu_master_tree *t, const mu_skill_env *env, int32_t skill,
                               mu_master_formula_fn formula, void *user);

/* 0x00bb1183(slot): the slot's tooltip into the classic text list (TextList 0x10c76988, colours 0x10c7b938, bold
 * 0x10c7ba78, the header flags 0x0b477ef4): the skill's name (colour 3, bold), the rank line, the description with
 * the level-0 formula value (0x0117b5eb(mgr, 3, id, cost) through tenv->formula) or the learned value, the next
 * level's value (GlobalText 0xd00 header), the cost (0xd01 header; red when above the points), the brand line (red
 * when 0x00bb1b76 fails), and below the max level and rank 1 the rank and prerequisite lines (red when unmet; the
 * rank rule's side effect runs).  Returns the line count GfxMgr's InfoPopup gets (0x00b8d94b), 0 when the slot, the
 * skill or the tooltip record is missing. */
int mu_master_tooltip(mu_master_tree *t, const mu_skill_tip_env *tenv, const mu_master_env *env,
                      const mu_skill_hero *hero, int slot, mu_skill_tip *out, uint8_t header[MU_SKILL_TIP_LINES]);

/* 0x00bb0e2d (the window's per-frame overlay): every node's icon at its reported position, (X0 + scale * x) *
 * ratio_x, (Y0 + scale * y) * ratio_y, size icon_w x icon_h, bitmap 0x7e18 + Magic_Icon / 450, cell (icon % 450) % 25
 * x 0.0390625, (icon % 450) / 25 x 0.0546875; white (0xffffffff) when 0x00bb1a19, 0x00bb1b06 (whose side effect
 * runs), 0x00bb1b76 and the special-item answer pass, else grey (0xff787878).  Nodes without a position are
 * skipped. */
typedef void (*mu_master_draw_fn)(void *user, int32_t bitmap, float x, float y, float w, float h, float u, float v,
                                  float uw, float vh, uint32_t color);
void mu_master_icons(mu_master_tree *t, const mu_master_env *env, const mu_skill_hero *hero, float x0, float y0,
                     float scale, float ratio_x, float ratio_y, mu_master_draw_fn draw, void *user);

#ifdef __cplusplus
}
#endif

#endif
