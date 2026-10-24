/* P1: mu_frame_parse never reads past `avail` and classifies every buffer by
 * the documented C1..C4 rule.
 *
 * Harm if broken: the receiver trusts the parser's "complete frame" answer to
 * hand `size` bytes to the dispatcher; a wrong answer hands it bytes that have
 * not arrived (stale buffer contents) or reads beyond the received data.
 *
 * Bound: any buffer of 0..PARSE_MAX bytes with any contents. The buffer is
 * allocated at exactly `avail` bytes so CBMC's bounds check is the proof that
 * nothing past `avail` is read. */
#include <stdlib.h>
#include "common.h"

int main(void)
{
    size_t avail = nondet_size_t();
    __CPROVER_assume(avail <= PARSE_MAX);
    uint8_t *buf = malloc(avail ? avail : 1u);   /* contents unconstrained */
    __CPROVER_assume(buf != NULL);

    mu_frame_info info;
    mu_frame_status st = mu_frame_parse(buf, avail, &info);

    if (avail < 3u) {
        __CPROVER_assert(st == MU_FRAME_NEED_MORE, "P1: fewer than 3 bytes is always need-more");
    } else {
        int hlen = spec_header_len(buf[0]);
        uint32_t size = spec_size(buf);
        if (hlen == 0 || size == 0u) {
            __CPROVER_assert(st == MU_FRAME_BAD, "P1: a non-MU head or zero size is bad");
        } else if (size > avail) {
            __CPROVER_assert(st == MU_FRAME_NEED_MORE, "P1: a declared size beyond avail is need-more");
            __CPROVER_assert(info.size == size, "P1: the declared size is reported even when incomplete");
        } else {
            __CPROVER_assert(st == MU_FRAME_OK, "P1: a complete C1..C4 frame is ok");
            __CPROVER_assert(info.size == size, "P1: ok reports the declared total size");
            __CPROVER_assert(info.head == buf[0], "P1: ok reports the head byte");
            __CPROVER_assert(info.header_len == (uint32_t)hlen && info.payload_off == (uint32_t)hlen,
                             "P1: header length is 2 for C1/C3 and 3 for C2/C4");
            __CPROVER_assert(info.encrypted == (buf[0] == 0xC3 || buf[0] == 0xC4),
                             "P1: only C3/C4 are marked encrypted");
        }
    }
    /* The header-length helper agrees with the rule for every head byte. */
    uint8_t any = nondet_uchar();
    __CPROVER_assert(mu_frame_header_len(any) == (uint32_t)spec_header_len(any),
                     "P1: mu_frame_header_len follows the C1..C4 rule");
    free(buf);
    return 0;
}
