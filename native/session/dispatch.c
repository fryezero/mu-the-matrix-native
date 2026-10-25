/* SESSION-CORE-001: THE receive dispatcher.
 *
 * Stands for the client's 0x01287ead(opcode, packet, length, encrypted). Two inputs, one owner each:
 *   build/gen/routes.def       the client's routing (families + routes) from native/net/dispatch.def
 *                              (generated from the binary by the wire-research lane), or from
 *                              native/net/dispatch.seed.def until that file exists
 *   build/gen/ops_all.def      every native/session/ops/<domain>.ops: which apply function binds
 *                              which route, which submit fn owns an intent kind
 * scripts/gen_domains.py joins them into build/gen/bound_routes.def (MU_BOUND / MU_UNBOUND /
 * MU_IGNORED rows) and fails the build when an MU_OP names no route, two MU_OP rows bind one route,
 * or an MU_OP and an MU_IGNORE share one. Past the generator, two bindings of one route are
 * duplicate case labels below and two owners of one intent kind are an initializer override
 * (-Werror=initializer-overrides): neither compiles.
 */
#include "session_internal.h"

#include <stdio.h>
#include <string.h>

/* Prototypes of every apply/submit function named in the rows (an apply function may serve several
 * rows; repeated prototypes are legal C). */
#define MU_OP(op, sub, fn) mu_apply fn(mu_session *s, const mu_frame *f);
#define MU_SUBMIT(kind, fn) mu_submit fn(mu_session *s, const mu_intent *in);
#include "ops_all.def"
#undef MU_OP
#undef MU_SUBMIT

static mu_apply unbound(mu_session *s, const mu_frame *f, uint32_t sub, uint32_t client_handler)
{
    /* The original reaches client_handler here and the native client has no apply yet (or the opcode
     * has no route at all: client_handler == 0, the client's default case). Counted and journaled per
     * client address; never silent, never a guess at the body. */
    s->unhandled++;
    s->route.client_handler = client_handler;
    s->route.apply = NULL;
    mu_cue c;
    memset(&c, 0, sizeof c);
    c.kind = MU_CUE_UNHANDLED;
    c.handler = client_handler;
    c.u.unhandled.head = f->head;
    c.u.unhandled.opcode = f->opcode;
    c.u.unhandled.sub = (uint16_t)sub;
    c.u.unhandled.length = f->length;
    c.u.unhandled.client_handler = client_handler;
    mu_session_cue(s, &c);
    return MU_APPLY_IGNORED;
}

mu_apply mu_session_dispatch(mu_session *s, const mu_frame *f)
{
    uint32_t sub = MU_SUB_NONE;
    switch (f->opcode) {       /* the sub byte, at the offset the original reads for this head */
#define MU_FAMILY(op, c1, c2, addr)                                                         \
    case (op): {                                                                           \
        uint32_t at = (f->head == MU_HEAD_C1 || f->head == MU_HEAD_C3) ? (uint32_t)(c1) : (uint32_t)(c2); \
        sub = at == MU_AT_UNKNOWN ? MU_SUB_HEAD : f->length > at ? f->bytes[at] : MU_SUB_SHORT;   \
        break;                                                                             \
    }
#define MU_ROUTE(op, sb, addr, ev)
#include "routes.def"
#undef MU_FAMILY
#undef MU_ROUTE
    default:
        break;
    }
    s->route.head = f->head;
    s->route.opcode = f->opcode;
    s->route.sub = (uint16_t)sub;
    switch (MU_OP_KEY(f->opcode, sub)) {
#define MU_BOUND(op, sb, addr, fn)                                                          \
    case MU_OP_KEY((op), (sb)):                                                            \
        s->route.client_handler = (addr);                                                  \
        s->route.apply = #fn;                                                              \
        return fn(s, f);
#define MU_UNBOUND(op, sb, addr) \
    case MU_OP_KEY((op), (sb)):  \
        return unbound(s, f, sub, (addr));
#define MU_IGNORED(op, sb, addr, why) \
    case MU_OP_KEY((op), (sb)):       \
        s->route.client_handler = (addr); \
        s->route.apply = "(ignored)";     \
        return MU_APPLY_IGNORED;
#include "bound_routes.def"
#undef MU_BOUND
#undef MU_UNBOUND
#undef MU_IGNORED
    default:
        return unbound(s, f, sub, 0);
    }
}

/* The submit routing, also from the rows. Window events are intents too (later: one generated kind
 * per window that owns session-side handler state), so there is no second routing table by window id. */
#if defined(__clang__)
#pragma clang diagnostic error "-Winitializer-overrides"
#elif defined(__GNUC__)
#pragma GCC diagnostic error "-Woverride-init"
#endif
const mu_submit_fn mu_session_submit_routes[MU_INTENT_KINDS] = {
#define MU_OP(op, sb, fn)
#define MU_SUBMIT(kind, fn) [kind] = fn,
#include "ops_all.def"
#undef MU_OP
#undef MU_SUBMIT
};
const char *const mu_session_submit_names[MU_INTENT_KINDS] = {
#define MU_OP(op, sb, fn)
#define MU_SUBMIT(kind, fn) [kind] = #fn,
#include "ops_all.def"
#undef MU_OP
#undef MU_SUBMIT
};

static const mu_dispatch_row ROWS[] = {
#define MU_BOUND(op, sb, addr, fn) {(op), (sb), (addr), #fn},
#define MU_UNBOUND(op, sb, addr) {(op), (sb), (addr), NULL},
#define MU_IGNORED(op, sb, addr, why) {(op), (sb), (addr), "(ignored) " why},
#include "bound_routes.def"
#undef MU_BOUND
#undef MU_UNBOUND
#undef MU_IGNORED
};

size_t mu_session_dispatch_rows(const mu_dispatch_row **rows)
{
    *rows = ROWS;
    return sizeof ROWS / sizeof ROWS[0];
}

size_t mu_session_intent_routes(const char *const **submit_names)
{
    *submit_names = mu_session_submit_names;
    return MU_INTENT_KINDS;
}
