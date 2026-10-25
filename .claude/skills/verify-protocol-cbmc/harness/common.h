/* Shared declarations for the CBMC harnesses of native/core/mu_protocol.c.
 *
 * Each harness compiles the product source unchanged by including it. run.sh
 * overrides MU_PROTOCOL_SOURCE to point at a mutated copy for the planted-
 * mistake check; the default is the real file, four directories up.
 *
 * Library model. The product reaches memcpy and memmove only through pointers
 * at a symbolic offset into its two fixed objects, the 0x2000-byte receive ring
 * (mu_recv.buf) and the 0x145c-byte packet object (mu_packet.obj). CBMC's own
 * library versions turn such a copy into a byte-update of the whole struct,
 * which either does not finish or, with --arrays-uf-always, aborts CBMC. The
 * models below have the C-standard semantics and only change how the
 * destination is named: when the pointer lies in the registered receiver or
 * packet, the bytes are written by indexing that member directly, which the
 * array decision procedure handles in seconds. memmove copies ascending when
 * the destination is below the source and descending otherwise. Each harness
 * registers the object under test in harness_recv / harness_packet before
 * calling the product. memset is left to CBMC's library: the product's only
 * call clears the packet body at a constant offset and size. (An earlier
 * model used __CPROVER_array_set on the member, which CBMC applied to the
 * whole struct and so also cleared the overflow flag: a planted mistake that
 * removed the flag's clear went unnoticed. Keep models narrower than the
 * code they stand in for.) */
#ifndef VERIFY_PROTOCOL_COMMON_H
#define VERIFY_PROTOCOL_COMMON_H

/* The redirect is the default; -DHARNESS_PLAIN_COPY keeps plain byte loops. */
#ifndef HARNESS_PLAIN_COPY
#define HARNESS_REDIRECT 1
#endif

#include <stddef.h>
#include <stdint.h>
#include <string.h>

static void *harness_memcpy(void *dest, const void *src, size_t n);
static void *harness_memmove(void *dest, const void *src, size_t n);
#define memcpy harness_memcpy
#define memmove harness_memmove

#ifndef MU_PROTOCOL_SOURCE
#define MU_PROTOCOL_SOURCE "../../../../native/core/mu_protocol.c"
#endif
#include MU_PROTOCOL_SOURCE

#undef memcpy
#undef memmove

static mu_recv *harness_recv;       /* the receiver under test, or NULL */
static mu_packet *harness_packet;   /* the packet under test, or NULL */

/* The redirect indexes the member from the object's byte offset, which is
 * exact only because both arrays start their struct. */
_Static_assert(offsetof(mu_recv, buf) == 0, "mu_recv.buf must be the first member");
_Static_assert(offsetof(mu_packet, obj) == 0, "mu_packet.obj must be the first member");

static void *harness_memcpy(void *dest, const void *src, size_t n)
{
    const unsigned char *s = src;
#ifdef HARNESS_REDIRECT
    if (harness_recv && __CPROVER_same_object(dest, harness_recv->buf)) {
        size_t d = (size_t)__CPROVER_POINTER_OFFSET(dest);
        for (size_t i = 0; i < n; ++i)
            harness_recv->buf[d + i] = s[i];
    } else if (harness_packet && __CPROVER_same_object(dest, harness_packet->obj)) {
        size_t d = (size_t)__CPROVER_POINTER_OFFSET(dest);
        for (size_t i = 0; i < n; ++i)
            harness_packet->obj[d + i] = s[i];
    } else
#endif
    {
        unsigned char *d = dest;
        for (size_t i = 0; i < n; ++i)
            d[i] = s[i];
    }
    return dest;
}

static void *harness_memmove(void *dest, const void *src, size_t n)
{
#ifdef HARNESS_REDIRECT
    if (harness_recv && __CPROVER_same_object(dest, harness_recv->buf) &&
        __CPROVER_same_object(src, harness_recv->buf)) {
        size_t d = (size_t)__CPROVER_POINTER_OFFSET(dest), s = (size_t)__CPROVER_POINTER_OFFSET(src);
        if (d <= s) {
            for (size_t i = 0; i < n; ++i)
                harness_recv->buf[d + i] = harness_recv->buf[s + i];
        } else {
            for (size_t i = n; i > 0; --i)
                harness_recv->buf[d + i - 1] = harness_recv->buf[s + i - 1];
        }
        return dest;
    }
#endif
    unsigned char *d = dest;
    const unsigned char *s = src;
    if (d <= s) {
        for (size_t i = 0; i < n; ++i)
            d[i] = s[i];
    } else {
        for (size_t i = n; i > 0; --i)
            d[i - 1] = s[i - 1];
    }
    return dest;
}

/* CBMC treats a bodyless function whose name starts with nondet_ as a fresh
 * unconstrained value of its return type at every call. */
size_t nondet_size_t(void);
unsigned char nondet_uchar(void);
int nondet_int(void);

/* The bounds every harness states in SKILL.md. Loops unroll to these, so the
 * --unwind run.sh passes for a harness must stay above its largest loop. */
#ifndef PARSE_MAX
#define PARSE_MAX  24u   /* bytes offered to mu_frame_parse */
#endif
#ifndef STREAM_MAX
#define STREAM_MAX 12u   /* buffered bytes drained in one mu_recv_drain */
#endif
#ifndef ADD_MAX
#define ADD_MAX    20u   /* body bytes per mu_packet_add */
#endif
#ifndef XOR_MAX
#define XOR_MAX    22u   /* body bytes under the XorData round trip */
#endif
#ifndef PUSH_N_MAX
#define PUSH_N_MAX 0x40u /* bytes per push in the push-guard harness */
#endif

/* Independent statement of the C1..C4 head and size-field rule from
 * docs/research/client-net-protocol.md (not a call into the product). */
static int spec_header_len(uint8_t head)
{
    if (head == 0xC1 || head == 0xC3) return 2;
    if (head == 0xC2 || head == 0xC4) return 3;
    return 0;
}

static uint32_t spec_size(const uint8_t *s)
{
    int hlen = spec_header_len(s[0]);
    if (hlen == 2) return s[1];
    if (hlen == 3) return ((uint32_t)s[1] << 8) + s[2];
    return 0;
}

#endif
