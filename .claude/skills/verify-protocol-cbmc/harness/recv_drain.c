/* R1 and R2: one mu_recv_drain over any buffered bytes.
 *
 * R1 (CBMC's built-in checks): mu_recv_drain and mu_frame_parse never touch
 *     memory outside the receiver's 0x2000-byte ring, and no loop runs past
 *     the bound.
 * R2 (the assertions below): the frames the callback receives are consecutive
 *     slices of the buffered bytes starting at the ring's front, in order,
 *     byte-identical, each shaped by the C1..C4 rule and cut only with 3 or
 *     more bytes still buffered; afterwards the leftover is exactly the
 *     unconsumed tail moved to the front with no complete frame left in it,
 *     or the ring is empty because a non-MU head or a zero size was met.
 *
 * With R3 (a push appends after the buffered bytes and never reorders them)
 * this covers any server stream in any chunking: each drain consumes a prefix
 * of what is buffered and keeps the rest at the front, so the next push
 * appends to exactly the unconsumed stream. (A harness stating the property
 * directly over several pushes was tried and does not finish on either CBMC
 * backend, even at 6 bytes in 2 pushes.)
 *
 * Harm if broken: the dispatcher behind the callback would see stale, torn or
 * repeated frames, or the receiver would read or write past its ring.
 *
 * Bound: any buffered length 0..STREAM_MAX with any ring contents.
 *
 * Layout: the receiver lives in a plain byte array viewed through a mu_recv
 * pointer, with plain byte-loop copies (common.h), so every access the drain
 * makes through a pointer at a symbolic offset is an array index for the
 * solver. -DHARNESS_STRUCT uses a struct object and the redirect model
 * instead (about twice as slow at this bound). */
#ifndef HARNESS_STRUCT
#define HARNESS_PLAIN_COPY 1
#endif
#include "common.h"

static mu_recv *r;              /* the receiver under test (a local of main: unconstrained) */
static uint8_t snap[STREAM_MAX]; /* the buffered bytes before the drain */
static size_t initial_len;
static size_t consumed;         /* ring offset of the next frame still to deliver */

static void cb(const uint8_t *frame, size_t size, void *ud)
{
    (void)ud;
    size_t off = (size_t)(frame - r->buf);
    __CPROVER_assert(off == consumed, "R2: frames are consecutive from the ring front");
    __CPROVER_assert(size >= 1u && size <= initial_len - consumed, "R2: frame lies inside the buffered bytes");
    if (size >= 1u && size <= initial_len - consumed) {
        size_t k = nondet_size_t();
        __CPROVER_assume(k < size);
        __CPROVER_assert(frame[k] == snap[consumed + k], "R2: frame bytes are the buffered bytes");
        __CPROVER_assert(initial_len - consumed >= 3u, "R2: a frame is cut only with 3 or more bytes buffered");
        if (initial_len - consumed >= 3u) {
            __CPROVER_assert(spec_header_len(snap[consumed]) != 0, "R2: a delivered frame has a C1..C4 head");
            __CPROVER_assert(spec_size(snap + consumed) == size, "R2: the frame length is its declared size");
        }
    }
    consumed += size;
}

int main(void)
{
#ifdef HARNESS_STRUCT
    mu_recv receiver;               /* contents and len unconstrained */
    r = &receiver;
#else
    uint8_t storage[sizeof(mu_recv)];   /* contents and len unconstrained */
    r = (mu_recv *)storage;
#endif
    harness_recv = r;
    __CPROVER_assume(r->len <= STREAM_MAX);
    initial_len = r->len;
    for (size_t i = 0; i < STREAM_MAX; ++i)
        snap[i] = r->buf[i];
    consumed = 0;

    size_t delivered = mu_recv_drain(r, cb, NULL);

    __CPROVER_assert(r->len <= initial_len, "R2: a drain never grows the buffer");
    if (r->len == 0u && consumed != initial_len) {
        /* the only way to drop bytes: a bad head reset at the next frame start */
        __CPROVER_assert(initial_len - consumed >= 3u, "R2: the ring is cleared only with 3 or more bytes buffered");
        if (initial_len - consumed >= 3u)
            __CPROVER_assert(spec_header_len(snap[consumed]) == 0 || spec_size(snap + consumed) == 0u,
                             "R2: the ring is cleared only on a non-MU head or a zero size");
    } else {
        __CPROVER_assert(consumed + r->len == initial_len, "R2: the leftover is exactly the unconsumed tail");
        if (r->len && consumed + r->len == initial_len) {
            size_t k = nondet_size_t();
            __CPROVER_assume(k < r->len);
            __CPROVER_assert(r->buf[k] == snap[consumed + k], "R2: the tail is moved to the front unchanged");
        }
        mu_frame_info info;
        __CPROVER_assert(mu_frame_parse(r->buf, r->len, &info) != MU_FRAME_OK,
                         "R2: no complete frame is left undelivered");
    }
    (void)delivered;
    return 0;
}
