/* S1 (build): a packet built by mu_packet_begin, one plain mu_packet_add and
 * mu_packet_finish stays inside its 0x145c-byte object, its size word equals
 * the body length, and the size field written by finish is that length in the
 * head's format.
 *
 * Harm if broken: every outbound message would carry a wrong length or overrun
 * the packet object on the native client's own stack or heap.
 *
 * Bound: any head byte and opcode, one add of 0..ADD_MAX plain bytes. Further
 * adds are covered by packet_add.c, which starts from any size word. An
 * encoded add differs from a plain one only by mu_send_xor_encode(obj, cur,
 * cur+len), whose footprint xor_upper.c and xor_window.c bound. */
#include "common.h"

int main(void)
{
    mu_packet P;                  /* unconstrained before begin */
    mu_packet *p = &P;
    harness_packet = p;
    uint8_t head = nondet_uchar(), opcode = nondet_uchar();

    mu_packet_begin(p, head, opcode);
    __CPROVER_assert(P.overflow == 0u, "S1: begin clears the overflow flag");
    __CPROVER_assert(P.obj[2] == head, "S1: the head byte is the first body byte");

    size_t len = nondet_size_t();
    __CPROVER_assume(len <= ADD_MAX);
    uint8_t data[ADD_MAX];        /* unconstrained */
    uint32_t cur = mu_packet_len(p);
    int rc = mu_packet_add(p, data, len, 0);
    __CPROVER_assert(rc == 0, "S1: an add within the cap is accepted");
    __CPROVER_assert(mu_packet_len(p) == cur + (uint32_t)len, "S1: the size word grows by the added length");
    if (len) {
        size_t k = nondet_size_t();
        __CPROVER_assume(k < len);
        __CPROVER_assert(P.obj[2u + cur + k] == data[k], "S1: the add copies the bytes after the body");
    }

    uint32_t total = mu_packet_finish(p);
    __CPROVER_assert(total == mu_packet_len(p), "S1: finish returns the body length");
    __CPROVER_assert(total <= MU_PACKET_CAP, "S1: the wire frame fits the object");
    if (head == MU_HEAD_C1 || head == MU_HEAD_C3)
        __CPROVER_assert(P.obj[3] == (uint8_t)(total & 0xffu) && P.obj[4] == opcode,
                         "S1: C1/C3 size field is the low byte of the total, then the opcode");
    else if (head == MU_HEAD_C2 || head == MU_HEAD_C4)
        __CPROVER_assert(((uint32_t)P.obj[3] << 8 | P.obj[4]) == total && P.obj[5] == opcode,
                         "S1: C2/C4 size field is the big-endian total, then the opcode");
    else
        __CPROVER_assert(P.obj[3] == opcode, "S1: a non-MU head reserves no size field");
    return 0;
}
