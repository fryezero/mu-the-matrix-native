/* S1 (begin/finish): from any object contents, mu_packet_begin clears the
 * overflow flag and lays down exactly the head byte, the size placeholder
 * (one byte for C1/C3, two for C2/C4, none for any other head) and the opcode;
 * the rest of the body area is zero; mu_packet_finish then returns that body
 * length and writes it into the size field in the head's format.
 *
 * Harm if broken: every frame the native client sends would start with a wrong
 * header, or carry a stale overflow flag from a previous packet.
 *
 * Bound: any head byte, any opcode, any prior object contents. */
#include "common.h"

int main(void)
{
    mu_packet P;                  /* unconstrained before begin */
    mu_packet *p = &P;
    harness_packet = p;
    uint8_t head = nondet_uchar(), opcode = nondet_uchar();

    mu_packet_begin(p, head, opcode);
    __CPROVER_assert(P.overflow == 0u, "S1: begin clears the overflow flag");
    uint32_t body = mu_packet_len(p);

    uint32_t total = mu_packet_finish(p);
    __CPROVER_assert(total == body, "S1: finish returns the body length");
    if (head == MU_HEAD_C1 || head == MU_HEAD_C3)
        __CPROVER_assert(body == 3u && P.obj[2] == head && P.obj[3] == 3u && P.obj[4] == opcode,
                         "S1: C1/C3 body is head, one-byte size field holding 3, opcode");
    else if (head == MU_HEAD_C2 || head == MU_HEAD_C4)
        __CPROVER_assert(body == 4u && P.obj[2] == head && P.obj[3] == 0u && P.obj[4] == 4u && P.obj[5] == opcode,
                         "S1: C2/C4 body is head, big-endian size field holding 4, opcode");
    else
        __CPROVER_assert(body == 2u && P.obj[2] == head && P.obj[3] == opcode,
                         "S1: a non-MU head reserves no size field");

    size_t k = nondet_size_t();
    __CPROVER_assume(k >= 2u + body && k < sizeof P.obj);
    __CPROVER_assert(P.obj[k] == 0u, "S1: begin clears the body area past the header");
    return 0;
}
