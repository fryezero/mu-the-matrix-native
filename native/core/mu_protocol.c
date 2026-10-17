/* NATIVE-NET-001: reconstruction of the client's framing + send obfuscation.
 * See mu_protocol.h and docs/research/client-net-protocol.md. */
#include "mu_protocol.h"

#include <string.h>

const uint8_t MU_SEND_XOR_KEY[32] = {
    0xab, 0x11, 0xcd, 0xfe, 0x18, 0x23, 0xc5, 0xa3,
    0xca, 0x33, 0xc1, 0xcc, 0x66, 0x67, 0x21, 0xf3,
    0x32, 0x12, 0x15, 0x35, 0x29, 0xff, 0xfe, 0x1d,
    0x44, 0xef, 0xcd, 0x41, 0x26, 0x3c, 0x4e, 0x4d
};

uint32_t mu_frame_header_len(uint8_t head)
{
    switch (head) {
    case MU_HEAD_C1:
    case MU_HEAD_C3:
        return 2u;
    case MU_HEAD_C2:
    case MU_HEAD_C4:
        return 3u;
    default:
        return 0u;
    }
}

mu_frame_status mu_frame_parse(const uint8_t *buf, size_t avail, mu_frame_info *out)
{
    uint8_t head;
    uint32_t hlen;
    uint32_t size;

    /* The client's loop only begins once at least 3 bytes are buffered
     * (0x01290840), so a 1- or 2-byte prefix is always "need more". */
    if (avail < 3u)
        return MU_FRAME_NEED_MORE;

    head = buf[0];
    hlen = mu_frame_header_len(head);
    if (hlen == 0u)
        return MU_FRAME_BAD;

    if (hlen == 2u)
        size = buf[1];
    else
        size = (uint32_t)((uint32_t)buf[1] << 8) + buf[2];

    /* Signed <= 0 is rejected by the client (0x01290937). */
    if (size == 0u || size > 0x7fffffffu)
        return MU_FRAME_BAD;

    if (out) {
        out->head = head;
        out->size = size;
        out->header_len = hlen;
        out->payload_off = hlen;
        out->encrypted = (head == MU_HEAD_C3 || head == MU_HEAD_C4) ? 1 : 0;
    }

    if (size > avail)
        return MU_FRAME_NEED_MORE;
    return MU_FRAME_OK;
}

/* XorData, 0x00d52055. obj[0..1] is the little-endian size word; body is obj+2.
 * body[i] ^= body[i-1] ^ key[i & 31], seeded from obj[1] (size high byte). */
void mu_send_xor_encode(uint8_t *obj, size_t start, size_t end)
{
    size_t i;
    for (i = start; i < end; ++i)
        obj[i + 2u] = (uint8_t)(obj[i + 2u] ^ obj[i + 1u] ^ MU_SEND_XOR_KEY[i & 31u]);
}

void mu_send_xor_decode(uint8_t *obj, size_t start, size_t end)
{
    size_t i;
    /* Inverse of the ascending chain: walk high -> low so obj[i+1] still holds
     * the encoded previous byte when we decode obj[i+2]. */
    if (end <= start)
        return;
    for (i = end; i-- > start;)
        obj[i + 2u] = (uint8_t)(obj[i + 2u] ^ obj[i + 1u] ^ MU_SEND_XOR_KEY[i & 31u]);
}

static void packet_set_size(mu_packet *p, uint32_t size)
{
    p->obj[0] = (uint8_t)(size & 0xffu);
    p->obj[1] = (uint8_t)((size >> 8) & 0xffu);
}

uint32_t mu_packet_len(const mu_packet *p)
{
    return (uint32_t)p->obj[0] | ((uint32_t)p->obj[1] << 8);
}

int mu_packet_add(mu_packet *p, const uint8_t *data, size_t len, int encode)
{
    uint32_t cur = mu_packet_len(p);

    /* Guard at 0x00d51cae: current + len must stay <= 0x145a. */
    if ((uint64_t)cur + (uint64_t)len > (uint64_t)MU_PACKET_CAP) {
        p->overflow = 1u;
        return -1;
    }
    if (len)
        memcpy(&p->obj[2u + cur], data, len);
    if (encode)
        mu_send_xor_encode(p->obj, cur, cur + len);
    packet_set_size(p, cur + (uint32_t)len);
    return 0;
}

void mu_packet_begin(mu_packet *p, uint8_t head, uint8_t opcode)
{
    uint8_t placeholder[2];

    memset(p->obj, 0, sizeof p->obj);
    p->overflow = 0u;
    packet_set_size(p, 0u);

    /* Begin (0x00d51baf): head byte, then reserve the size field by appending
     * one byte for C1/C3 and two for C2/C4, then the opcode byte. */
    mu_packet_add(p, &head, 1u, 0);

    placeholder[0] = 0u;
    placeholder[1] = 0u;
    if (head == MU_HEAD_C1 || head == MU_HEAD_C3)
        mu_packet_add(p, placeholder, 1u, 0);
    else if (head == MU_HEAD_C2 || head == MU_HEAD_C4)
        mu_packet_add(p, placeholder, 2u, 0);

    mu_packet_add(p, &opcode, 1u, 0);
}

uint32_t mu_packet_finish(mu_packet *p)
{
    uint32_t size = mu_packet_len(p);
    uint8_t head = p->obj[2];

    /* WriteSize (0x00d51c1f): the size field is the total body length. */
    if (head == MU_HEAD_C1 || head == MU_HEAD_C3) {
        p->obj[3] = (uint8_t)(size & 0xffu);
    } else if (head == MU_HEAD_C2 || head == MU_HEAD_C4) {
        p->obj[3] = (uint8_t)((size >> 8) & 0xffu);
        p->obj[4] = (uint8_t)(size & 0xffu);
    }
    return size;
}

void mu_recv_init(mu_recv *r)
{
    r->len = 0u;
}

int mu_recv_push(mu_recv *r, const uint8_t *data, size_t n)
{
    if (r->len + n > MU_RECV_CAP)
        return -1;
    if (n)
        memcpy(&r->buf[r->len], data, n);
    r->len += n;
    return 0;
}

size_t mu_recv_drain(mu_recv *r, mu_frame_cb cb, void *ud)
{
    size_t off = 0u;
    size_t delivered = 0u;

    while (r->len - off >= 3u) {
        mu_frame_info info;
        mu_frame_status st = mu_frame_parse(&r->buf[off], r->len - off, &info);
        if (st == MU_FRAME_BAD) {
            /* Client resets recvlen to 0 on a bad head (0x01290926). */
            r->len = 0u;
            return delivered;
        }
        if (st == MU_FRAME_NEED_MORE)
            break;
        if (cb)
            cb(&r->buf[off], info.size, ud);
        off += info.size;
        ++delivered;
    }

    if (off) {
        memmove(r->buf, &r->buf[off], r->len - off);
        r->len -= off;
    }
    return delivered;
}

uint8_t mu_serial_next(uint8_t *counter)
{
    uint8_t v = *counter;
    *counter = (uint8_t)(v + 1u);
    return v;
}
