#ifndef MU_CLIENT_LEA_H
#define MU_CLIENT_LEA_H

#include <stdint.h>

/* Byte-defined context: up to 192 little-endian round-key words, then a
 * little-endian round count at offset 768. This is an authored logical API,
 * not an original symbol. No original C struct type is assumed.
 */
#define MU_CLIENT_LEA_CONTEXT_BYTES 772

/* NULL context/key or a key size other than 16/24/32 is a no-op.
 * Otherwise context must cover 772 writable bytes and key must cover key_bytes
 * readable bytes. Unaligned pointers are allowed. The spans must be disjoint,
 * accessible and not wrap or alias executing code/call stack.
 * Writes 144/168/192 round-key words and round count 24/28/32. Unused context
 * words remain untouched. Key/context overlap and fault/status flags are not
 * part of this contract. The original helper has no specified return value.
 */
void mu_client_lea_setup(void *context, const void *key, int32_t key_bytes);

/* ECB decoder for a context produced by setup with a supported key size.
 * NULL context, zero length, a nonmultiple of 16, or NULL input/output is a
 * no-op. Otherwise context must cover its 772 readable bytes, disjoint from
 * both caller spans. Input/output must cover length accessible bytes with no
 * wrapping or code/stack aliasing. Unaligned and overlapping data is allowed.
 * Reads a complete group of eight blocks, then four, then individual blocks
 * before writing each group. Later groups can read earlier output on overlap.
 * Contexts modified externally, flags/exceptions and arbitrary round counts
 * are outside this logical API. No capacity/envelope validation is performed.
 */
void mu_client_lea_decode(void *destination, const void *source, uint32_t length,
                          const void *context);

#endif
