/* SESSION-CORE-001: introspection for tools, validators and tests - the routing as data and the
 * domains' raw records. Includable from native/session, native/tools, native/tests and native/fixture
 * only (scripts/audit_includes.py): views read typed getters, never client addresses or raw bytes. */
#ifndef MU_SESSION_TOOLS_H
#define MU_SESSION_TOOLS_H

#include <stddef.h>
#include <stdint.h>

#include "mu_session.h"

/* One dispatcher row: a route of the table and the apply function bound to it. */
typedef struct mu_dispatch_row {
    uint8_t opcode;
    uint16_t sub;                /* 0x100: not sub-dispatched */
    uint32_t client_handler;     /* 0: not recovered */
    const char *apply;           /* NULL: unbound; "(ignored) why" for an ignored route */
} mu_dispatch_row;
size_t mu_session_dispatch_rows(const mu_dispatch_row **rows);

/* The submit function name routed for each intent kind (index = kind; [0] is MU_INTENT_NONE). */
size_t mu_session_intent_routes(const char *const **submit_names);

/* A domain record zone in client layout (the lease audit's and the journal snapshot's unit). */
typedef struct mu_session_zone_view {
    const char *name;            /* "hero.attr" */
    const char *field;           /* what lives there */
    const uint8_t *base;
    uint32_t offset, size;
    int motion;                  /* 1: writable under the lease */
    int view;                    /* 1: derived, excluded from replicated-byte comparisons */
} mu_session_zone_view;
size_t mu_session_zone_views(const mu_session *s, mu_session_zone_view *out, size_t cap);

#endif
