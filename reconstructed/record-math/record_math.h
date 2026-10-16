#ifndef MU_RECORD_MATH_H
#define MU_RECORD_MATH_H

/* Authored names for observed operations, not recovered original symbols.
 * Cofactor/inverse records contain sixteen little-endian IEEE binary32 values, row-major.
 * Supported comparisons use RNE binary64 intermediates and binary32 stores,
 * finite moderate inputs/intermediates, masked exceptions and no concurrency.
 * NaN payloads, exception flags/traps and other FP modes are unverified. */
/* Basic storage/rounding check; does not verify trap masks or flush-to-zero. */
int mu_record_math_environment_supported(void);

/* Source contains 64 readable bytes; removed row and column are each 0..3. */
float mu_record_cofactor(const void *source, unsigned row, unsigned column);

/* Source/destination contain 64 readable/writable bytes. Unaligned and
 * overlapping buffers are allowed. The zero-scalar fallback writes its public
 * identity template before reading translation fields, preserving alias effects.
 * No original return-value contract is inferred for this logical void API. */
void mu_record_inverse(void *destination, const void *source);

/* Pose composition: parent/local/destination each cover 48 bytes containing
 * twelve little-endian binary32 values, row-major 3x4. Accessible nonwrapping
 * spans may be unaligned and overlap, but cannot alias code/call stack.
 * Uses RNE binary32 products and left-to-right sums, row-major sequential
 * stores. Inputs/intermediates must be finite normal values or zero, with
 * no underflow/overflow; masked exceptions, no concurrency. Other FP modes,
 * flags/traps and original live caller state remain unverified. No null gate.
 */
void mu_pose_concat(const void *parent, const void *local, void *destination);

#endif
