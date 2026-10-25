/* SESSION-CORE-001 / NET-DISPATCH-001 (sketch): THE receive dispatcher.
 *
 * Stands for the client's 0x01287ead(opcode, packet, length, encrypted). Two inputs, one owner
 * each:
 *   native/net/dispatch.def      the client's routing (families + routes), generated from the
 *                                binary by scripts/gen_dispatch.py and verified under Unicorn
 *   build/gen/ops_all.def        every native/session/ops/<domain>.ops, concatenated: which
 *                                apply function binds which route, which submit fn owns an intent
 * gen_domains.py joins them into build/gen/bound_routes.def (MU_BOUND / MU_UNBOUND / MU_IGNORED
 * rows) and fails the build when an MU_OP names no route, two MU_OP rows bind one route, or an
 * MU_OP and an MU_IGNORE share one. So routing is one list from evidence, binding is one row per
 * domain file, and duplicates are duplicate case labels that do not compile.
 */
#include "session_internal.h"

/* Prototypes of every apply/submit function named in the rows (an apply function may serve
 * several rows, e.g. quests_receive; repeated prototypes are legal C). */
#define MU_OP(op, sub, fn) mu_apply fn(mu_session *s, const mu_frame *f);
#define MU_SUBMIT(kind, fn) mu_submit fn(mu_session *s, const mu_intent *in);
#include "ops_all.def"
#undef MU_OP
#undef MU_SUBMIT

static mu_apply unbound(mu_session *s, const mu_frame *f, uint32_t sub, uint32_t client_handler)
{
    /* The original reaches client_handler here and the native client has no apply yet (or the
     * opcode has no route at all: client_handler == 0, the client's default case). Counted per
     * client address in the journal and in the --coverage report; fatal under --strict. Never
     * silent, never a guess at the body. */
    (void)s; (void)f; (void)sub; (void)client_handler;
    MU_NOT_IMPLEMENTED();
}

mu_apply mu_session_dispatch(mu_session *s, const mu_frame *f)
{
    uint32_t sub = MU_SUB_NONE;
    switch (f->opcode) {       /* the sub byte, at the offset the original reads for this head */
#define MU_FAMILY(op, c1, c2, addr)                                                   \
    case (op): {                                                                     \
        uint32_t at = (f->head == MU_HEAD_C1 || f->head == MU_HEAD_C3) ? (c1) : (c2); \
        sub = at == MU_AT_UNKNOWN ? MU_SUB_HEAD : f->length > at ? f->bytes[at] : MU_SUB_SHORT; \
        break;                                                                       \
    }
#define MU_ROUTE(op, sb, addr, ev)
#include "dispatch.def"
#undef MU_FAMILY
#undef MU_ROUTE
    default: break;
    }
    switch (MU_OP_KEY(f->opcode, sub)) {
#define MU_BOUND(op, sb, addr, fn) case MU_OP_KEY((op), (sb)): return fn(s, f);
#define MU_UNBOUND(op, sb, addr) case MU_OP_KEY((op), (sb)): return unbound(s, f, sub, (addr));
#define MU_IGNORED(op, sb, addr, why) case MU_OP_KEY((op), (sb)): return MU_APPLY_IGNORED;
#include "bound_routes.def"
#undef MU_BOUND
#undef MU_UNBOUND
#undef MU_IGNORED
    default: return unbound(s, f, sub, 0);
    }
}

/* The submit routing, also from the rows. -Werror=initializer-overrides makes two owners of
 * one kind a build failure; test_session_routes.py checks that no kind is left NULL. Window
 * events are intents too: their kinds are generated from native/gfx/windows/<movie>.c meta
 * lines (one kind per window that owns session-side handler state), so there is no second
 * routing table by window id inside the session. */
const mu_submit_fn mu_session_submit_routes[MU_INTENT_KINDS] = {
#define MU_OP(op, sb, fn)
#define MU_SUBMIT(kind, fn) [kind] = fn,
#include "ops_all.def"
#undef MU_OP
#undef MU_SUBMIT
};

/* For `mu-session routes`, validate_dispatch.py and the coverage report. */
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
