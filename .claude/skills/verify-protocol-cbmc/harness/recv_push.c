/* R3: mu_recv_push refuses exactly when the bytes would not fit the
 * 0x2000-byte ring, leaves the receiver unchanged when it refuses, and
 * otherwise appends the bytes after the ones already buffered.
 *
 * Harm if broken: a server burst larger than the ring would overwrite memory
 * after the receive buffer (the client logs "Receive Packet Buffer Overflow"
 * and stops instead).
 *
 * Bound: any buffered length 0..0x2000 with any ring contents, and a push of
 * 0..PUSH_N_MAX bytes, so both sides of the guard are reached. */
#include "common.h"

int main(void)
{
    mu_recv r;                    /* contents and len unconstrained */
    harness_recv = &r;
    __CPROVER_assume(r.len <= MU_RECV_CAP);
    size_t n = nondet_size_t();
    __CPROVER_assume(n <= PUSH_N_MAX);
    uint8_t data[PUSH_N_MAX];     /* unconstrained */

    size_t k = nondet_size_t();
    __CPROVER_assume(k < MU_RECV_CAP);
    uint8_t before_k = r.buf[k];
    size_t before_len = r.len;

    int rc = mu_recv_push(&r, data, n);

    if (before_len + n > MU_RECV_CAP) {
        __CPROVER_assert(rc == -1, "R3: a push that would overflow the ring is refused");
        __CPROVER_assert(r.len == before_len, "R3: a refused push leaves the length unchanged");
        __CPROVER_assert(r.buf[k] == before_k, "R3: a refused push leaves the bytes unchanged");
    } else {
        __CPROVER_assert(rc == 0, "R3: a push that fits is accepted");
        __CPROVER_assert(r.len == before_len + n, "R3: the length grows by the pushed count");
        if (k < before_len)
            __CPROVER_assert(r.buf[k] == before_k, "R3: bytes already buffered are untouched");
        else if (k < before_len + n)
            __CPROVER_assert(r.buf[k] == data[k - before_len], "R3: the pushed bytes follow the buffered ones");
    }
    return 0;
}
