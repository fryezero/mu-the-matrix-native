#ifndef MU_RECOVERY_DECODER_H
#define MU_RECOVERY_DECODER_H
#include <stddef.h>
#include <stdint.h>

/* Reconstructed bounded form of the routine at VA 0x0e64605d.
 * The API is new; it is not the original program's calling convention.
 * Returns 0 on success, -1 on invalid input or exhausted output capacity.
 * Overlapping source/destination buffers are not supported.
 */
int mu_decode_block(const uint8_t *source, size_t source_size,
                    uint8_t *output, size_t capacity,
                    size_t *consumed, size_t *written);
#endif
