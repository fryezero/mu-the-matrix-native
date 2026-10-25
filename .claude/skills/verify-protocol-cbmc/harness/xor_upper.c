/* S2 (upper footprint): on any range an encoded add can produce, XorData
 * encode touches no byte at or past end+2. The object is allocated with
 * exactly start+len+2 bytes, so CBMC's bounds check is the proof.
 *
 * Harm if broken: an encoded add would write past the appended bytes, and for
 * a body near the cap past the packet object.
 *
 * Bound: any start with start + len <= 0x145a and len <= ADD_MAX, which is
 * every call mu_packet_add can make after its guard. */
#include <stdlib.h>
#include "common.h"

int main(void)
{
    size_t start = nondet_size_t(), len = nondet_size_t();
    __CPROVER_assume(start <= MU_PACKET_CAP && len <= ADD_MAX && start + len <= MU_PACKET_CAP);
    uint8_t *obj = malloc(start + len + 2u);   /* exactly the bytes the range may touch */
    __CPROVER_assume(obj != NULL);
    mu_send_xor_encode(obj, start, start + len);
    return 0;
}
