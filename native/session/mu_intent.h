/* SESSION-CORE-001: typed intents, the only way a view asks for change.
 *
 * An intent names what the player (or a scene) wants in domain terms: no opcodes, no bytes.
 * mu_session_submit turns it into the client's own local checks plus the reconstructed
 * request builder. A kind whose builder is not reconstructed yet returns
 * MU_SUBMIT_UNRECOVERED: the type exists so views can be written against it, but no bytes
 * are invented (evidence rule).
 *
 * The kinds and their payloads are GENERATED (build/gen/session_intents.h, scripts/gen_domains.py)
 * from every native/session/domains/<d>.intents:
 *     MU_INTENT_KIND(ADD_STAT, add_stat, struct { int32_t stat; })
 * plus the MU_SUBMIT row in ops/<d>.ops and the submit function in domains/<d>.c. So parallel
 * domain work never edits this file, and a kind without an MU_SUBMIT route fails the build.
 * The sketch's full hand-written list (account, combat, items, social ... kinds) arrives domain by
 * domain; SESSION-CORE-001 has only the hero domain's kinds.
 */
#ifndef MU_INTENT_H
#define MU_INTENT_H

#include <stdint.h>

#include "session_intents.h"   /* generated: enum mu_intent_kind, MU_INTENT_PAYLOADS, MU_INTENT_KIND_NAMES */

#ifdef __cplusplus
extern "C" {
#endif

/* A credential that can only be consumed by a request encoder. It has no getter: the journal,
 * logs and reports cannot serialize it. mu_secret_set copies and the submit path zeroes the
 * intent's copy after encoding (the account domain, SESSION-ACCOUNT-001, is its first user). */
typedef struct mu_secret {
    uint8_t opaque_[64];
    uint8_t length_;
} mu_secret;
void mu_secret_set(mu_secret *s, const char *utf8);   /* truncates to the field width */
void mu_secret_wipe(mu_secret *s);

typedef enum mu_store {          /* where an item sits */
    MU_STORE_INVENTORY = 0, MU_STORE_EQUIPMENT, MU_STORE_WAREHOUSE, MU_STORE_TRADE, MU_STORE_PERSONAL_SHOP,
    MU_STORE_MIX, MU_STORE_EVENT_INVENTORY, MU_STORE_EXTENSION_BAG
} mu_store;

typedef struct mu_intent {
    mu_intent_kind kind;
    union {
        MU_INTENT_PAYLOADS
    } u;
} mu_intent;

/* "add_stat" for MU_INTENT_ADD_STAT (the generated payload field names), "?" out of range. */
const char *mu_intent_kind_name(mu_intent_kind kind);
/* The kind whose payload field is `name`, or MU_INTENT_NONE. */
mu_intent_kind mu_intent_kind_by_name(const char *name);

#ifdef __cplusplus
}
#endif

#endif /* MU_INTENT_H */
