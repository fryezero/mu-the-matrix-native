/* S2: XorData decode is the exact inverse of encode on every range, and
 * encode follows the documented chain rule
 *     obj[i+2] ^= obj[i+1] ^ key[i & 31]      for i in [start, end), ascending.
 *
 * Harm if broken: an outbound packet the server cannot decode, or a decoder
 * (mu-proto, tests) that misreads captured frames.
 *
 * Bound: a size word plus 0..XOR_MAX body bytes, any contents, any
 * 0 <= start <= end <= XOR_MAX. */
#include <string.h>
#include "common.h"

int main(void)
{
    uint8_t obj[2u + XOR_MAX];    /* unconstrained */
    uint8_t copy[2u + XOR_MAX];
    memcpy(copy, obj, sizeof obj);
    size_t start = nondet_size_t(), end = nondet_size_t();
    __CPROVER_assume(start <= end && end <= XOR_MAX);

    mu_send_xor_encode(obj, start, end);
    if (end > start) {
        size_t j = nondet_size_t();
        __CPROVER_assume(start <= j && j < end);
        /* obj[j+1] is the previous body byte as it stands after encoding (or
         * the size word's high byte when j == 0), which is what the rule chains on */
        __CPROVER_assert(obj[j + 2u] == (uint8_t)(copy[j + 2u] ^ obj[j + 1u] ^ MU_SEND_XOR_KEY[j & 31u]),
                         "S2: encode follows the chain rule at every index");
        size_t outside = nondet_size_t();
        __CPROVER_assume(outside < sizeof obj && (outside < start + 2u || outside >= end + 2u));
        __CPROVER_assert(obj[outside] == copy[outside], "S2: encode touches only the range");
    }

    mu_send_xor_decode(obj, start, end);
    size_t k = nondet_size_t();
    __CPROVER_assume(k < sizeof obj);
    __CPROVER_assert(obj[k] == copy[k], "S2: decode restores every byte");
    return 0;
}
