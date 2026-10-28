#ifndef MU_WORLD_GFX_TREE_H
#define MU_WORLD_GFX_TREE_H

/* MasterSkillTree's native host. Logic and tables live in core/mu_skill and reconstructed/skill/master_tree.
 * 4th/5th movies register their callbacks, but stay empty until their live Lang tables are decoded. */
#include <stdint.h>
struct wg_skill;
struct mu_gfx_layer;
struct mu_lang;
typedef struct wg_tree wg_tree;
wg_tree *wg_tree_open(struct wg_skill *skill, struct mu_gfx_layer *layer, const struct mu_lang *lang);
void wg_tree_tick(wg_tree *tree);
void wg_tree_close(wg_tree *tree);
void wg_tree_call(wg_tree *tree, int movie, const char *name, const char *args);
void wg_tree_draw(wg_tree *tree, int movie, int32_t stage_w, int32_t stage_h);
/* Script equivalents of the movie callbacks. tree / tree4 / tree5 toggle, treeover / treeclick take a slot. */
int wg_tree_action(wg_tree *tree, const char *verb, int slot);
#endif
