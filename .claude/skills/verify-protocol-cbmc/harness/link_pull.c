/* L1 and L2: one read step of a connection, the link-to-dechunker path (NET-LINK-001,
 * native/net/conn.c mu_conn_pull, which feeds mu_recv_push).
 *
 * L1: with 0x2000 bytes already buffered, or once the connection stopped, the step reads nothing
 *     from the link, leaves the ring as it was and reports MU_DECODE_OVERFLOW, and the connection
 *     stays stopped. This is the client's receive guard: 0x01290792 compares the buffered length
 *     with 0x2000 (0x0129079e) and logs "Receive Packet Buffer Overflow" instead of calling recv.
 * L2: otherwise the link is asked for exactly the ring's room (0x2000 - buffered, as the client's
 *     recv(sock, buf + len, 0x2000 - len) at 0x012907c3..0x012907ee), every byte the link returns
 *     is pushed after the buffered ones (none lost, none reordered, the old ones untouched), and the
 *     ring never holds more than 0x2000 bytes.
 *
 * With R1-R3 (one drain cuts exact frames and keeps the tail; a push appends or refuses) this covers
 * the link -> dechunker path for any link that honours its read contract (at most `cap` bytes).
 *
 * Harm if broken: a burst from the server overruns the receive ring, bytes are dropped silently (a
 * push refused because the conn asked for more than fits), or the guard never triggers and a frame
 * that cannot fit is waited for forever while the ring is full.
 *
 * Bound: any buffered length 0..0x2000 with any ring contents and any stopped flag; a link read of
 * 0..LINK_N_MAX bytes of any value.
 *
 * Layout: the connection is a struct object with the redirecting copy model (common.h), like
 * recv_push.c: the push writes at a symbolic offset of the ring, which is mu_conn's first member
 * (asserted below), so the redirect indexes the ring from the object's start. The transport's link
 * calls are stubbed here. */
#include "common.h"

#ifndef MU_CONN_SOURCE
#define MU_CONN_SOURCE "../../../../native/net/conn.c"
#endif
#include MU_CONN_SOURCE

#define LINK_N_MAX 0x40u

static int link_reads;
static size_t asked, gave;
static uint8_t given[LINK_N_MAX];

/* the link: returns 0..min(cap, LINK_N_MAX) bytes of anything */
size_t mu_link_read(mu_transport *t, mu_link_id id, uint8_t *out, size_t cap)
{
    (void)t;
    (void)id;
    link_reads++;
    asked = cap;
    size_t n = nondet_size_t();
    __CPROVER_assume(n <= cap && n <= LINK_N_MAX);
    for (size_t i = 0; i < n; ++i) {
        given[i] = nondet_uchar();
        out[i] = given[i];
    }
    gave = n;
    return n;
}

/* the rest of the link interface conn.c references (not reached by mu_conn_pull) */
mu_link_id mu_link_open(mu_transport *t, const mu_endpoint *e) { (void)t; (void)e; return -1; }
int mu_link_allow(mu_transport *t, const mu_endpoint *e) { (void)t; (void)e; return 0; }
mu_link_state mu_link_state_of(mu_transport *t, mu_link_id id, int *error_code)
{
    (void)t;
    (void)id;
    if (error_code)
        *error_code = 0;
    return MU_LINK_CLOSED;
}
int mu_link_write(mu_transport *t, mu_link_id id, const uint8_t *p, size_t n) { (void)t; (void)id; (void)p; (void)n; return -1; }
void mu_link_close(mu_transport *t, mu_link_id id) { (void)t; (void)id; }

_Static_assert(offsetof(mu_conn, rx) == 0, "mu_conn.rx must be the first member");

int main(void)
{
    mu_conn conn;                       /* contents unconstrained: any ring, any length, any stopped flag */
    mu_conn *c = &conn;
    harness_recv = &c->rx;
    __CPROVER_assume(c->rx.len <= MU_RECV_CAP);
    size_t before_len = c->rx.len;
    int before_stopped = c->stopped;
    size_t k = nondet_size_t();
    __CPROVER_assume(k < MU_RECV_CAP);
    uint8_t before_k = c->rx.buf[k];

    size_t got = 12345;
    mu_decode_status st = mu_conn_pull(c, NULL, &got);

    if (before_stopped || before_len >= MU_RECV_CAP) {
        __CPROVER_assert(st == MU_DECODE_OVERFLOW, "L1: a full ring (or a stopped connection) reports the overflow");
        __CPROVER_assert(c->stopped != 0, "L1: the connection stays stopped");
        __CPROVER_assert(link_reads == 0, "L1: nothing is read from the link");
        __CPROVER_assert(got == 0, "L1: no bytes are reported read");
        __CPROVER_assert(c->rx.len == before_len, "L1: the buffered length is unchanged");
        __CPROVER_assert(c->rx.buf[k] == before_k, "L1: the buffered bytes are unchanged");
    } else {
        __CPROVER_assert(st == MU_DECODE_OK, "L2: a step with room is not an overflow");
        __CPROVER_assert(link_reads == 1, "L2: the link is read once");
        __CPROVER_assert(asked == MU_RECV_CAP - before_len, "L2: the link is asked for exactly the ring's room");
        __CPROVER_assert(got == gave, "L2: every byte the link returned is pushed");
        __CPROVER_assert(c->rx.len == before_len + gave, "L2: the length grows by the bytes read");
        __CPROVER_assert(c->rx.len <= MU_RECV_CAP, "L2: the ring never holds more than 0x2000 bytes");
        if (k < before_len)
            __CPROVER_assert(c->rx.buf[k] == before_k, "L2: bytes already buffered are untouched");
        else if (k < before_len + gave)
            __CPROVER_assert(c->rx.buf[k] == given[k - before_len], "L2: the link's bytes follow the buffered ones");
    }
    return 0;
}
