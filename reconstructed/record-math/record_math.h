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

/* Rotation conversion observed at 0x00d00724. Angles cover 12 readable bytes
 * (three little-endian binary32 values a0,a1,a2); quaternion covers 16 writable
 * bytes receiving x,y,z,w. Each angle is halved in binary64 and rounded to
 * binary32, then sine/cosine results are rounded to binary32 before RNE binary32
 * products in the original left-to-right order. Angles are read a2,a1,a0 and all
 * reads precede the four ordered stores, so in-place spans are permitted.
 * The trig callbacks receive the binary64 widening of each halved angle in
 * original call order sin(h2),cos(h2),sin(h1),cos(h1),sin(h0),cos(h0).
 * mu_rotation_quaternion uses the host libm sin/cos; that is a substitute for
 * the original client trig helpers and is equal only where their binary32-rounded
 * results agree (see docs/research/client-rotation.md). No null gate.
 */
typedef double (*mu_rotation_trig)(double);
void mu_rotation_quaternion_using(const void *angles, void *quaternion,
                                  mu_rotation_trig sine, mu_rotation_trig cosine);
void mu_rotation_quaternion(const void *angles, void *quaternion);

#endif
