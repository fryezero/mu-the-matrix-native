#ifndef MU_SKILL_LIST_H
#define MU_SKILL_LIST_H

/* The server's skill packets and the managers they update (NATIVE-SKILL-002, docs/research/client-skills.md
 * section 8).  Pinned inputs as in skill_use.h (restored text capture 09, second image section run 10).
 *
 * This build numbers its packets itself: the receive dispatcher 0x01287ead sends opcode 0xA0 to the
 * sub-dispatch at 0x0128805c (sub = packet[3] for C1, packet[4] for C2).  Its sub 0x20 is the skill list
 * (handler 0x0126176e) and sub 0x03 the saved hotkeys (0x0126f225).  Only the game logic is here: the
 * C3/C4 decryption and the login packets stay outside.
 *
 * Client objects (static readings, the behaviour verified by scripts/validate_skill.py):
 *   attributes  [0x01d1df1c] +0x1e4 the learned count (u8), +0x1e6 u16 skill ids (0x3a1 entries: the full
 *               list's memset is 0x742 bytes), +0x187 the class byte;
 *   hero        [0x0a39d754] +0x32 CurrentSkill (u8 index into the learned list), +0x3268 the elemental;
 *   stamp       the Skill Imprint (stamp) manager, the static at [0x01d1dbcc] (getter 0x0095f861):
 *               +4 class byte, +8 elemental, +0xc std::vector<entry*> basic tab, +0x18 the special tab,
 *               +0x24 entry*[10] the window's slots, +0x4c entry*[10] the bar's slots, +0x80 int[10] the saved
 *               skill ids, +0xa8 the slot of skill 0x12a (-1); entry = {+0 base skill, +4 learned skill
 *               (0 = not learned), +8 u8 imprint};
 *   keys        the hotkey manager 0x01d1df5c: +0 the selected skill, +4 std::map<int, std::string> of the
 *               learned skills (record index -> name), +0xc std::map<int, int> bar slot -> skill. */

#include <stddef.h>
#include <stdint.h>

#include "skill_use.h"

#ifdef __cplusplus
extern "C" {
#endif

#define MU_SKILL_KEYS_MAX 1024       /* the learned map of the hotkey manager (one key per record index) */
#define MU_SKILL_STAMP_MAX 1024      /* entries per tab */

/* 0x00bb1c10: the record's brand (+0x5c) — the skill this one improves on. */
int32_t mu_skill_brand_of(const mu_skill_env *env, int32_t skill);
/* 0x00bb1c32: the first skill of a brand chain (the master manager's base skill): the skill itself when the
 * record is absent, else the last index reached by following the brands until 0 or 0x4b. */
int32_t mu_skill_master_base(const mu_skill_env *env, int32_t skill);

typedef struct mu_skill_stamp_entry {
    int32_t base;                    /* +0 */
    int32_t learned;                 /* +4 */
    uint8_t imprint;                 /* +8 */
} mu_skill_stamp_entry;

typedef struct mu_skill_stamp_tab {
    mu_skill_stamp_entry *items[MU_SKILL_STAMP_MAX];
    int count;
    mu_skill_stamp_entry pool[MU_SKILL_STAMP_MAX];   /* the entries' storage (the client's operator new) */
} mu_skill_stamp_tab;

typedef struct mu_skill_stamp_mgr {
    int32_t class_byte;              /* +4 (the attributes' +0x187 it was built for; -1: never) */
    int32_t elemental;               /* +8 */
    mu_skill_stamp_tab basic;        /* +0xc */
    mu_skill_stamp_tab special;      /* +0x18 */
    mu_skill_stamp_entry *edit[MU_SKILL_SLOTS];   /* +0x24 */
    mu_skill_stamp_entry *slots[MU_SKILL_SLOTS];  /* +0x4c */
    int32_t saved[MU_SKILL_SLOTS];   /* +0x80 */
    int32_t special_slot;            /* +0xa8 */
} mu_skill_stamp_mgr;

void mu_skill_stamp_init(mu_skill_stamp_mgr *s);
/* An entry appended to a tab (the populate routines' push_back); NULL when full. */
mu_skill_stamp_entry *mu_skill_stamp_push(mu_skill_stamp_mgr *s, int special, int32_t base, int32_t learned);
/* 0x01095c77 (the window's open 0x00c2008b): clear both slot arrays, 0x01095f20 (a new class byte: drop the
 * basic tab and fill it (0x01095d30, 0x0109630b for class indices 10..15); the same class: forget the learned
 * skills (0x0109664d) and the imprint flags (0x0109658a)), then rebuild the special tab (0x01096710). */
void mu_skill_stamp_reset(const mu_skill_env *env, mu_skill_stamp_mgr *s, int32_t class_byte);
/* 0x01095f5c: a learned skill joins its base skill's entry (the basic tab's first entry of that base; the
 * entry keeps a later skill of the chain), else the special tab's first entry of that base. */
void mu_skill_stamp_add(const mu_skill_env *env, mu_skill_stamp_mgr *s, int32_t skill);
/* 0x010960a8: the first entry of the skill's base holding exactly that skill forgets it. */
void mu_skill_stamp_remove(const mu_skill_env *env, mu_skill_stamp_mgr *s, int32_t skill);
/* 0x010961b0: elemental = hero +0x3268; imprint = the learned skill's element (+0x50) is the hero's
 * (non-zero) element, or 6 (all elements). */
void mu_skill_stamp_refresh(const mu_skill_env *env, mu_skill_stamp_mgr *s, int32_t elemental);
/* 0x01096aa7: the entry whose base or learned skill is `skill` (basic tab first). */
mu_skill_stamp_entry *mu_skill_stamp_find(const mu_skill_stamp_mgr *s, int32_t skill);
/* 0x01096cba: the window slot of a server key (key 0 is slot 9, key k slot k - 1); 0 when no entry. */
int mu_skill_stamp_set_key(mu_skill_stamp_mgr *s, int key, int32_t skill);
/* 0x01096d2a Save: the bar takes the window's slots, saved[i] = their learned skills. */
void mu_skill_stamp_save(mu_skill_stamp_mgr *s);
/* 0x01096dd0 Cancel: the window takes the bar's slots back. */
void mu_skill_stamp_cancel(mu_skill_stamp_mgr *s);
/* 0x01096a19 / 0x01096a60: the skill a bar / window slot shows (learned, else base; -1 none). */
int32_t mu_skill_stamp_slot_skill(const mu_skill_stamp_mgr *s, int window, int slot);
/* 0x01096951: the learned-list index of an entry's learned skill (-1 none). */
int mu_skill_stamp_learned_index(const mu_skill_hero *hero, const mu_skill_stamp_entry *e);

/* The hotkey manager 0x01d1df5c. */
typedef struct mu_skill_keys {
    int32_t selected;                       /* +0 */
    int32_t learned[MU_SKILL_KEYS_MAX];     /* +4: the map's keys, sorted */
    int nlearned;
    uint8_t has_slot[MU_SKILL_SLOTS];       /* +0xc: the map's keys 0..9 */
    int32_t slot[MU_SKILL_SLOTS];
} mu_skill_keys;

/* Boundary calls the routines make, in call order (the validator records the client's). */
enum {
    MU_SKILL_EV_TREE_ADD = 1,        /* GfxMgr +0x1f8 -> 0x00c26ad8(skill) (a skill added) */
    MU_SKILL_EV_KEYS_ALL,            /* listener [0x01d22c60] -> 0x00c5e991(the packet's skill vector) */
    MU_SKILL_EV_KEYS_ADD,            /* listener -> 0x00c5ea96(record index) */
    MU_SKILL_EV_MASTER_ADD,          /* GfxMgr -> 0x0095f986 -> 0x00ba7366(skill) */
    MU_SKILL_EV_SELECT,              /* GfxMgr -> 0x00995257 -> 0x00b40380() (the selection changed) */
    MU_SKILL_EV_USABLE               /* 0x010918c7 && 0x01096e55 asked for a skill (post-save) */
};
#define MU_SKILL_EVENTS 64
typedef struct mu_skill_events {
    int count;
    int32_t kind[MU_SKILL_EVENTS], arg[MU_SKILL_EVENTS];
} mu_skill_events;

/* 0x00a08058: the skill is in the learned map. */
int mu_skill_keys_has(const mu_skill_keys *k, int32_t skill);
/* 0x00a081eb: select a skill (nothing for 0 or the selected one; 0 when not learned or of use type 3). */
void mu_skill_keys_select(const mu_skill_env *env, mu_skill_keys *k, int32_t skill, mu_skill_events *ev);
/* 0x00a079d2: select the hero's CurrentSkill. */
void mu_skill_keys_follow(const mu_skill_env *env, mu_skill_keys *k, const mu_skill_hero *hero, mu_skill_events *ev);
/* 0x00a08330: the bar slots from the stamp manager's bar slots (slot i -> its entry's learned skill). */
void mu_skill_keys_rebuild(mu_skill_keys *k, const mu_skill_stamp_mgr *s);
/* 0x00a07a11 / 0x00a07c8a / 0x00a07ebb: the learned map set from a list, one skill added, one removed. */
void mu_skill_keys_set(const mu_skill_env *env, mu_skill_keys *k, const mu_skill_stamp_mgr *s, const int32_t *skills,
                       int n, mu_skill_events *ev);
void mu_skill_keys_add(const mu_skill_env *env, mu_skill_keys *k, const mu_skill_stamp_mgr *s, int32_t skill,
                       mu_skill_events *ev);
void mu_skill_keys_remove(const mu_skill_env *env, mu_skill_keys *k, const mu_skill_stamp_mgr *s, int32_t skill,
                          mu_skill_events *ev);
/* The bar's ten hotkeys the feed reads (absent slots are 0). */
void mu_skill_keys_hotkeys(const mu_skill_keys *k, mu_skill_hotkeys *out);

/* Opcode 0xA0 sub 0x20, 0x0126176e.  packet[5]: 0xFF one skill removed, 0xFE one added, else the count of a
 * full list; 4-byte entries from offset 7, the skill u16 at entry +1.  A full list keeps the skills whose use
 * type (+0x58) is not 3 (master tree skills stay out of the learned list but reach the stamp manager and the
 * hotkeys); CurrentSkill is then moved off empty entries and the skills 0x43..0x48.  `usable` answers
 * 0x010918c7 && 0x01096e55 (not asked here: NULL is fine).  Returns 0 for a packet shorter than its entries. */
typedef struct mu_skill_world {
    const mu_skill_env *env;
    mu_skill_hero *hero;             /* the learned list, CurrentSkill, the elemental */
    mu_skill_stamp_mgr *stamp;
    mu_skill_keys *keys;
    mu_skill_usable_fn usable;
    void *usable_user;
} mu_skill_world;
int mu_skill_list_receive(mu_skill_world *w, const uint8_t *packet, size_t size, mu_skill_events *ev);

/* Opcode 0xA0 sub 0x03, 0x0126f225 (the part about skills): ten big-endian u16 skills from offset 4 (0xffff
 * none; 0x12a records its key in stamp +0xa8) become the window slots (0x01096cba), Save (0x01096d2a), then
 * the CurrentSkill rule 0x01096f37 (it stays when a bar slot shows it; else the learned index of the first
 * window slot, unless the skill is usable; else the first special entry of brand 0x4b), and at the end of the
 * handler the bar is rebuilt (0x00a08330).  The packet's other fields (item hotkeys, options) are not read. */
int mu_skill_keys_receive(mu_skill_world *w, const uint8_t *packet, size_t size, mu_skill_events *ev);
/* 0x01096f37 alone. */
void mu_skill_stamp_after_save(mu_skill_world *w, mu_skill_events *ev);

/* 0x0109750c (the Skill Imprint window and MacroMain): the imprint marker over an icon — only for an entry with its
 * imprint flag and a learned skill: bitmap 0x7e26 (Interface/SkillStamp.tga, 128 x 32), u = cw / 128 * (element - 1),
 * v 0, uw = cw / 128, vh = ch / 32 at (x, y) size (w, h).  0x01097601: the damage-type icon (record +0xcc > 0 and a
 * learned skill): bitmap 0x8313 (Interface/DamageTypeIcon.tga, 64 x 32), u = cw / 64 * (type - 1), uw = cw / 64,
 * vh = ch / 32.  Return 0 when nothing is drawn. */
typedef struct mu_skill_quad {
    int32_t bitmap;
    float x, y, w, h, u, v, uw, vh;
} mu_skill_quad;
int mu_skill_stamp_marker(int32_t elemental, const mu_skill_stamp_entry *e, float x, float y, float cw, float ch,
                          float w, float h, mu_skill_quad *out);
int mu_skill_damage_type_icon(int32_t type, int32_t learned, float x, float y, float cw, float ch, float w, float h,
                              mu_skill_quad *out);

/* Requests a demo server answers with (the packets above), built the way a server sends them (C1 head). */
size_t mu_skill_list_packet(uint8_t *out, size_t cap, int kind, const int32_t *skills, int n);   /* kind: 0 list, 0xFE, 0xFF */
size_t mu_skill_keys_packet(uint8_t *out, size_t cap, const int32_t keys[MU_SKILL_SLOTS]);       /* -1: none */

#ifdef __cplusplus
}
#endif

#endif
