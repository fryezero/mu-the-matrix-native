#ifndef MU_MODEL_CODEC_H
#define MU_MODEL_CODEC_H

#include <stdint.h>

/* Logical API for the observed client routine, not an original symbol.
 * Returns length unchanged. NULL destination is a query and never reads source.
 * Nonpositive lengths also access neither caller span.
 * Otherwise both pointers must cover length accessible bytes in a flat span,
 * without address wrapping or aliasing the executing code/call stack.
 * Unaligned and overlapping spans are allowed. Feedback rereads source[i]
 * after destination[i] is written; this is intentionally not memmove behavior.
 * No allocation, envelope validation or status/exception flag contract.
 */
int32_t mu_bmd12_decode(void *destination, const void *source, int32_t length);

#endif
