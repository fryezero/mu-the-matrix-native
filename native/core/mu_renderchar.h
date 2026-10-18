#ifndef MU_RENDERCHAR_VIEW_H
#define MU_RENDERCHAR_VIEW_H

#include <stdint.h>

#include "mu_bmd.h"
#include "mu_model.h"
#include "mu_scene.h"
#include "mu_textures.h"
#include "../../reconstructed/renderchar/renderchar.h"

/* World-path item rendering for the native viewer (NATIVE-RENDERCHAR-001).
 *
 * The reconstructed decisions (reconstructed/renderchar) give, for one item,
 * the mesh-draw calls the client's RenderObjDraw 0x0176ce74 makes (body and
 * single-mesh passes with their flags, alpha, blend arguments and the model
 * fields written before each). This module draws those passes through the
 * mesh-draw port (mu_scene) in the client's order.
 *
 * Viewer choices (not client facts):
 *  - the EnchantEffect colour table 0x06fbb754 (a script in the localisation
 *    archive) is not read; its colour is a parameter (glow_color);
 *  - item types with type-specific client branches (mu_rc_item_special) and
 *    record kinds outside the reconstructed domain are drawn with one plain
 *    textured body pass and counted in stats->special;
 *  - bitmap overrides other than the model's textures and the environment
 *    specials resolve to the client's miss record (texture name 0). */

typedef struct mu_renderchar_glow {
    int32_t type;            /* client model index (0xae6 + group*512 + index); -1 unknown */
    int32_t level;           /* 0..15 */
    int32_t option1;         /* excellent flag byte */
    int32_t ext;             /* ancient bits */
    int32_t has_record;
    uint8_t kind_a, kind_b, item_kind;
} mu_renderchar_glow;

typedef struct mu_renderchar_env {
    float time;              /* 0x06fce370 */
    int32_t quality;         /* graphics option (glow level cap 2q+5 for q <= 4) */
    float glow_color[3];     /* EnchantEffect colour (viewer parameter) */
    uint32_t render_type;    /* 2: body parts and RenderLinkItem items */
} mu_renderchar_env;

typedef struct mu_renderchar_stats {
    long passes, special;
} mu_renderchar_stats;

void mu_renderchar_default_env(mu_renderchar_env *env);
/* Draws one transformed item model with its world-render passes. base supplies
 * textures, culling and alpha-test overrides; light is the character light
 * (character +0x1b8), alpha the object alpha. */
int mu_renderchar_draw_item(const mu_model *model, const mu_renderchar_glow *glow, const mu_renderchar_env *env,
                            const float light[3], float alpha, const mu_draw_options *base,
                            const mu_render_backend *backend, mu_draw_stats *draw_stats, mu_renderchar_stats *stats);

/* Back-carry root for a weapon (link mode): the extracted local matrix of
 * (type, kind B, right hand); returns 1 composed under the bone, 2 absolute, 0 none. */
int mu_renderchar_back_local(int32_t type, int32_t kind_b, int32_t right_hand, uint32_t local[12]);
/* Weapon link bones the character create assigns to a monster/NPC model index
 * (extracted table); returns 0 when the model is not listed. */
int mu_renderchar_link_bones(int32_t model_index, int32_t *right, int32_t *left);

/* An item attached to a host model by the hand path (rotation position on the
 * host bone with (0,0,0), keep-root pose, transform), as RenderLinkItem does
 * for monster weapons. Host and item share bone/root storage. */
typedef struct mu_renderchar_attachment {
    int loaded;
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    int32_t bone;
    mu_renderchar_glow glow;
    uint8_t *root;           /* shared root matrix storage (0x078965ac) */
} mu_renderchar_attachment;

typedef struct mu_renderchar_host {
    uint8_t *bones, *root, *quaternions;   /* shared storage */
} mu_renderchar_host;

int mu_renderchar_host_init(mu_renderchar_host *host, mu_model *model);
void mu_renderchar_host_free(mu_renderchar_host *host);
int mu_renderchar_attach_load(mu_renderchar_attachment *a, mu_renderchar_host *host, const char *path, int32_t bone,
                              int no_textures, char *error, size_t error_size);
void mu_renderchar_attach_free(mu_renderchar_attachment *a);
/* After the host is posed and skinned: position = host object position.
 * host_bones NULL: hand path (rotation position on host bone `bone`, origin =
 * position + result). Otherwise link mode (RenderLinkItem link 1): root =
 * concat(host_bones[bone], back-table local of the glow type), origin = position. */
int mu_renderchar_attach_update(mu_renderchar_attachment *a, mu_model *host_model, const float *host_bones,
                                const float position[3], float scale, const float light[3]);

#endif
