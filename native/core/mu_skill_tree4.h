#ifndef MU_SKILL_TREE4_H
#define MU_SKILL_TREE4_H

/* The fourth skill tree in the native client (NATIVE-SKILL-003, docs/research/client-skills.md section 12).
 *
 * The client's SkillTree4th window over reconstructed/skill/tree4.c:
 *   - 4ThTreeData from the Lang tables read out of a running client (MU_LANG_DIR/tree4.tsv, written by
 *     scripts/live_lang_to_plain.py from a langread snapshot taken with graph:0x06fbb8ec); without the file the
 *     window stays empty;
 *   - the hero's answers the checks ask for: Skill(Kor) records (the skill book), the hero's learned skills and the
 *     Master tree's levels;
 *   - the server's 7E 02 list, 7E 01 answer and 7E 03 points through the client's handlers.
 * OFFLINE DEMO (the server in the real game): at login a 7E 02 list with every node at level 0 and demo points;
 * a C1 09 7E 01 request answers 7E 01 result 1 with the level + 1 and the points - cost.  The answer's two floats
 * (the node's value and next value) are demo stand-ins (level and level + 1): the server's formula is unknown. */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/skill/tree4.h"

#ifdef __cplusplus
extern "C" {
#endif

struct mu_skill_book;
typedef struct mu_skill_tree4 mu_skill_tree4;

/* lang_dir: MU_LANG_DIR (tree4.tsv); book: the hero's skills (Skill(Kor), the learned list, the Master tree). */
mu_skill_tree4 *mu_skill_tree4_open(const char *lang_dir, struct mu_skill_book *book);
void mu_skill_tree4_close(mu_skill_tree4 *t);
size_t mu_skill_tree4_records(const mu_skill_tree4 *t);          /* 4ThTreeData rows loaded */
mu_t4_window *mu_skill_tree4_window(mu_skill_tree4 *t);
/* The environment the window routines call (the module answers Skill(Kor), the hero and the Master tree; the
 * host's callbacks below get the host's user pointer). */
mu_t4_env *mu_skill_tree4_env(mu_skill_tree4 *t);
typedef struct mu_skill_tree4_host {
    void *user;
    const char *(*text)(void *u, int32_t index);
    void (*invoke)(void *u, const char *name, const char *json);
    void (*msgbox)(void *u, const char *text);
    void (*confirm)(void *u, int id, const char *text);
} mu_skill_tree4_host;
void mu_skill_tree4_set_host(mu_skill_tree4 *t, const mu_skill_tree4_host *host);
/* The hero enters the world (class index 0..15 = 0x0095f5cc(class byte)). */
void mu_skill_tree4_enter(mu_skill_tree4 *t, int32_t class_index);
/* A server packet with opcode 0x7E; 1 when handled. */
int mu_skill_tree4_receive(mu_skill_tree4 *t, const uint8_t *packet, size_t size);
/* OFFLINE DEMO: the login list (7E 02, every node of the class at level 0) with `points`; a decoded request. */
int mu_skill_tree4_demo_login(mu_skill_tree4 *t, int32_t points);
int mu_skill_tree4_demo_request(mu_skill_tree4 *t, const uint8_t *packet, size_t size);

#ifdef __cplusplus
}
#endif

#endif
