/* S1 (add): from any size word, mu_packet_add refuses exactly when the body
 * would pass 0x145a, then changes nothing but the overflow flag; otherwise it
 * appends the bytes after the body and advances the size word, never writing
 * outside the 0x145c-byte object.
 *
 * Harm if broken: a long outbound message (chat, trade, mail) would overrun
 * the packet object; this is the guard the client has at 0x00d51cae.
 *
 * Bound: any current size word 0..0xffff and any object contents, one plain
 * add of 0..ADD_MAX bytes. Because the starting size word is unconstrained,
 * this is the inductive step for any number of adds after packet_build.c. */
#include "common.h"

int main(void)
{
    mu_packet Q;                  /* unconstrained, including the size word */
    mu_packet *q = &Q;
    harness_packet = q;
    size_t len = nondet_size_t();
    __CPROVER_assume(len <= ADD_MAX);
    uint8_t data[ADD_MAX];        /* unconstrained */
    size_t k = nondet_size_t();
    __CPROVER_assume(k < sizeof Q.obj);
    uint8_t before_k = Q.obj[k];
    uint32_t cur = mu_packet_len(q);

    int rc = mu_packet_add(q, data, len, 0);

    if ((uint64_t)cur + (uint64_t)len > (uint64_t)MU_PACKET_CAP) {
        __CPROVER_assert(rc == -1, "S1: an add past the cap is refused");
        __CPROVER_assert(Q.overflow == 1u, "S1: a refused add raises the overflow flag");
        __CPROVER_assert(Q.obj[k] == before_k, "S1: a refused add leaves the object unchanged");
    } else {
        __CPROVER_assert(rc == 0, "S1: an add within the cap is accepted");
        __CPROVER_assert(mu_packet_len(q) == cur + (uint32_t)len, "S1: the size word grows by the added length");
        __CPROVER_assert(mu_packet_len(q) <= MU_PACKET_CAP, "S1: the size word never exceeds 0x145a");
        if (k >= 2u && k - 2u >= cur && k - 2u < cur + len)
            __CPROVER_assert(Q.obj[k] == data[k - 2u - cur], "S1: the added bytes follow the body");
        else if (k >= 2u)
            __CPROVER_assert(Q.obj[k] == before_k, "S1: bytes outside the appended range are untouched");
    }
    return 0;
}
