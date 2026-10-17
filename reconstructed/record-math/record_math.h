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

/* Pose-builder helpers (CLIENT-POSE-BUILD-001, docs/research/client-pose-builder.md).
 * Records hold little-endian binary32 values; matrices are row-major 3x4
 * (twelve values, 48 bytes) and quaternions are x,y,z,w (16 bytes). */

/* Quaternion comparison at 0x00cfec33. For i = 0..3 the binary32 difference
 * a[i]-b[i] is passed through the client fabs chain and compared as binary64
 * against 0.001. Returns 0 at the first component whose magnitude exceeds
 * 0.001, otherwise 1. An unordered (NaN) difference does not exceed and counts
 * as equal, as in the original COMISD/JBE. */
int mu_quaternion_compare(const void *a, const void *b);

/* Quaternion interpolation at 0x00d00ca4, argument order (p, q, t, out).
 * Accumulates a = sum (p-q)^2 and b = sum (p+q)^2 in binary32; if a > b the
 * four components of q are negated IN PLACE (sign-bit flips). cosom is the
 * binary32 dot product. If 1+cosom > 1e-8 and 1-cosom > 1e-8 (binary64
 * tests), omega = acos(cosom), sinom = sin(omega), and the scales are
 * sin((1-t)*omega)/sinom and sin(t*omega)/sinom; when only the first test
 * holds the scales are 1-t and t (linear). out[i] = sp*p[i] + sq*q[i].
 * Otherwise (q nearly opposite p) out becomes (-p1, p0, -p3, p2) and its first
 * three components are blended with sin((1-t)*pi/2) and sin(t*pi/2), where pi
 * is binary32 pi widened. Every trig result is rounded to binary32. Reads and
 * writes follow the original order, so aliasing spans are sequential. The
 * result is not renormalized. The _using variant takes acos/sin callbacks
 * called in the original order; mu_quaternion_slerp uses host libm (a
 * substitute for the client SSE2 helpers). */
void mu_quaternion_slerp_using(const void *p, void *q, float t, void *out,
                               mu_rotation_trig arccosine, mu_rotation_trig sine);
void mu_quaternion_slerp(const void *p, void *q, float t, void *out);

/* Quaternion to rotation matrix at 0x00d008bf. Writes the nine rotation
 * fields column by column, [r][c] order 00,10,20,01,11,21,02,12,22. Each is a
 * binary64 expression of widened components rounded once to binary32, e.g.
 * m00 = (1 - (2y)y) - (2z)z. Column 3 (translation) is not written. The
 * quaternion is reread for every field; it is not normalized first. */
void mu_quaternion_matrix(const void *quaternion, void *matrix);

/* Euler angles in degrees to a 3x4 matrix at 0x00cff32a. Each angle is
 * multiplied by binary32 0.017453292 (MULSS), then sin/cos are taken in the
 * order a2, a1, a0 and rounded to binary32. The matrix is Rz(a2)Ry(a1)Rx(a0)
 * with binary32 products; translation fields are set to +0. All angle reads
 * precede the stores, so in-place spans are allowed. The _using variant takes
 * sin/cos callbacks; mu_angle_matrix uses host libm. */
void mu_angle_matrix_using(const void *angles, void *matrix,
                           mu_rotation_trig sine, mu_rotation_trig cosine);
void mu_angle_matrix(const void *angles, void *matrix);

/* Vector helpers used by the model transform (CLIENT-SKIN-001,
 * docs/research/client-skinning.md). in/out cover three binary32 values,
 * matrix is a row-major 3x4 record. Each output component is a binary32
 * left-to-right sum of RNE binary32 products; inputs are reread for every
 * component and out[r] is stored before out[r+1] is computed, so aliasing
 * spans behave sequentially as in the original.
 * mu_vector_rotate (0x00d000ad):    out[r] = (in0*m[r][0] + in1*m[r][1]) + in2*m[r][2]
 * mu_vector_transform (0x00d002b2): out[r] = rotate term + m[r][3]
 * mu_vector_irotate (0x00cfff3c):   out[c] = (in0*m[0][c] + in1*m[1][c]) + in2*m[2][c] */
void mu_vector_rotate(const void *in, const void *matrix, void *out);
void mu_vector_transform(const void *in, const void *matrix, void *out);
void mu_vector_irotate(const void *in, const void *matrix, void *out);

#endif
