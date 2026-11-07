#ifndef MU_MUUN_EFFECTS_NATIVE_H
#define MU_MUUN_EFFECTS_NATIVE_H

#include <stdint.h>

#include "../../reconstructed/objects/muun_effects.h"

struct mu_effect_scene;

/* RENDER-EFFECTS-018: the Muun effect table MuunEffectInfo (0x06fbb46c + 0x38) and its consumers in the native
 * port (docs/research/client-render-effects-018.md).
 *
 * The table is the client's decoded game data: RENDER-EFFECTS-008's scripts/live_effect_table_to_plain.py writes it
 * as muuneffects.tsv into the local lang directory (MU_LANG_DIR); it is never committed. Without it nothing is
 * attached.
 *
 * A Muun OBJECT exists only after the server's Muun packets (0x01219294, out of scope), so no native world creates
 * one yet; an owner here is the OBJECT's effect list +0x3d0 driven by its caller (a host, a fixture or a later
 * Muun port): the slot refresh attaches the effects of the Muun's render-info id through an EffectManager scene,
 * and the per-frame update places them with the OBJECT's posed bones. */

typedef struct mu_muun_effects {
    mu_muun_effect_table table;
    mu_muun_effect_entry *entries;
    char *paths;
    int32_t count;
} mu_muun_effects;

/* <dir>/muuneffects.tsv (code, path, x, y, z, rx, ry, rz, scale, bone, follow). NULL when the directory is NULL or
 * holds no readable table. Rows keep the multimap's order: ascending codes, equal codes in file order. */
mu_muun_effects *mu_muun_effects_load(const char *dir);
/* The directory named by MU_LANG_DIR. */
mu_muun_effects *mu_muun_effects_load_default(void);
void mu_muun_effects_free(mu_muun_effects *table);

enum { MU_MUUN_RECORDS = 32 };

typedef struct mu_muun_owner {
    struct mu_effect_scene *scene;    /* creates the effects; NULL: the requests are counted, nothing is created */
    mu_object_effect_record records[MU_MUUN_RECORDS];   /* the OBJECT's list +0x3d0 */
    int32_t count;
    int32_t next_handle;              /* requests without a scene */
    long requested, invalid, attached, cleared, scaled, updates, expired, overflow;
} mu_muun_owner;

/* The manager's refresh of one slot (0x009ba7f5..0x009ba829): 0x009af6f6 clears the OBJECT's list, then
 * 0x009af699 attaches the table's entries for the slot's render-info id (each through the scene's factory). The
 * slot's object index is not used here: the owner is that OBJECT's list. Returns 1 when it attached. */
int mu_muun_owner_refresh(mu_muun_owner *owner, const mu_muun_effects *table, const mu_muun_slot *slot);

/* 0x0129f671(dt) for the OBJECT: expired timed records leave the list, each effect takes template scale x OBJECT
 * scale and the external matrix of its bone and follow flag, then its node update (scene instances only). */
void mu_muun_owner_update(mu_muun_owner *owner, const mu_effect_object *object, float dt);

#endif
