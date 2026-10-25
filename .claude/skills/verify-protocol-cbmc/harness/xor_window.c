/* S2 (window): XorData encode changes only obj[start+2 .. end+2) and follows
 * the chain rule there,
 *     obj[i+2] ^= obj[i+1] ^ key[i & 31]      for i in [start, end), ascending,
 * chaining on the byte it just wrote (or the size word's high byte at i == 0).
 *
 * Harm if broken: an encoded add would scramble bytes before the appended
 * range, or produce a frame the server cannot decode.
 *
 * Bound: a size word plus WINDOW body bytes, any contents, any start with
 * start + len <= WINDOW and len <= ADD_MAX. xor_upper.c extends the upper
 * side of the footprint to the full packet range; the lower side and the rule
 * do not depend on where the range sits beyond this window (unverified past
 * it). */
#include "common.h"

#ifndef WINDOW
#define WINDOW 64u
#endif

int main(void)
{
    uint8_t obj[2u + WINDOW];   /* unconstrained */
    size_t start = nondet_size_t(), len = nondet_size_t();
    __CPROVER_assume(start <= WINDOW && len <= ADD_MAX && start + len <= WINDOW);
    size_t k = nondet_size_t();
    __CPROVER_assume(k < sizeof obj);
    uint8_t before_k = obj[k];
    size_t j = nondet_size_t();
    __CPROVER_assume(len == 0u || (start <= j && j < start + len));
    uint8_t old_j2 = len ? obj[j + 2u] : 0u;

    mu_send_xor_encode(obj, start, start + len);

    if (k < start + 2u || k >= start + len + 2u)
        __CPROVER_assert(obj[k] == before_k, "S2: encode touches only obj[start+2 .. end+2)");
    if (len)
        __CPROVER_assert(obj[j + 2u] == (uint8_t)(old_j2 ^ obj[j + 1u] ^ MU_SEND_XOR_KEY[j & 31u]),
                         "S2: encode follows the chain rule at every index of the range");
    return 0;
}
