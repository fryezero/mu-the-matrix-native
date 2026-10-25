/* NET-LINK-001: connections over links (see mu_conn.h). */
#include "mu_conn.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void conn_reset(mu_conn *c)
{
    mu_recv_init(&c->rx);
    c->open = 0;
    c->stopped = 0;
    c->pend_count = 0;
    c->pend_next = 0;
    c->pend_off[0] = 0;
}

int mu_net_init(mu_net *n, mu_transport *t, char *error, size_t error_size)
{
    memset(n, 0, sizeof *n);
    if (!t) {
        if (error_size)
            snprintf(error, error_size, "mu_net_init: no transport");
        return -1;
    }
    n->transport = t;
    n->decode = mu_net_decode_plain;
    n->wrap = NULL;
    for (int k = 0; k < MU_CONN_KINDS; ++k) {
        n->conns[k].kind = (mu_conn_kind)k;
        n->conns[k].link = -1;
        n->conns[k].channel = -1;
        conn_reset(&n->conns[k]);
    }
    return 0;
}

void mu_net_free(mu_net *n)
{
    for (int k = 0; k < MU_CONN_KINDS; ++k)
        mu_net_close(n, (mu_conn_kind)k);
}

mu_net *mu_net_create(mu_transport *t, char *error, size_t error_size)
{
    mu_net *n = malloc(sizeof *n);
    if (!n)
        return NULL;
    if (mu_net_init(n, t, error, error_size) != 0) {
        free(n);
        return NULL;
    }
    return n;
}

void mu_net_destroy(mu_net *n)
{
    if (!n)
        return;
    mu_net_free(n);
    free(n);
}

int mu_net_allow(mu_net *n, const mu_endpoint *e)
{
    return mu_link_allow(n->transport, e);
}

int mu_net_connect(mu_net *n, mu_conn_kind k, const mu_endpoint *e)
{
    if (k < 0 || k >= MU_CONN_KINDS)
        return -1;
    mu_net_close(n, k);
    mu_conn *c = &n->conns[k];
    conn_reset(c);
    c->link = mu_link_open(n->transport, e);
    return c->link >= 0 ? 0 : -1;
}

void mu_net_close(mu_net *n, mu_conn_kind k)
{
    if (k < 0 || k >= MU_CONN_KINDS)
        return;
    mu_conn *c = &n->conns[k];
    if (c->link >= 0)
        mu_link_close(n->transport, c->link);
    c->link = -1;
    conn_reset(c);
}

mu_link_state mu_net_state(mu_net *n, mu_conn_kind k, int *error_code)
{
    if (error_code)
        *error_code = 0;
    if (k < 0 || k >= MU_CONN_KINDS || n->conns[k].link < 0)
        return MU_LINK_CLOSED;
    mu_link_state st = mu_link_state_of(n->transport, n->conns[k].link, error_code);
    if (st == MU_LINK_OPEN)
        n->conns[k].open = 1;
    return st;
}

mu_decode_status mu_conn_pull(mu_conn *c, mu_transport *t, size_t *got)
{
    *got = 0;
    if (c->stopped || c->rx.len >= MU_RECV_CAP) {
        /* 0x0129079e: cmp [this+0x4014], 0x2000; jl read - else the overflow log and return */
        c->stopped = 1;
        return MU_DECODE_OVERFLOW;
    }
    size_t room = MU_RECV_CAP - c->rx.len;
    uint8_t chunk[MU_RECV_CAP];
    size_t n = mu_link_read(t, c->link, chunk, room);
    if (n > room)
        n = room;   /* a link must not return more than asked; never trust it with the ring */
    if (n && mu_recv_push(&c->rx, chunk, n) == 0)
        *got = n;
    return MU_DECODE_OK;
}

static void pend_cb(const uint8_t *frame, size_t size, void *ud)
{
    mu_conn *c = ud;
    uint32_t at = c->pend_off[c->pend_count];
    /* every frame comes out of the 0x2000 ring of one drain, so the total fits pend */
    if ((size_t)at + size > sizeof c->pend || c->pend_count >= MU_RECV_CAP)
        return;
    memcpy(&c->pend[at], frame, size);
    c->pend_count++;
    c->pend_off[c->pend_count] = (uint16_t)(at + size);
}

mu_decode_status mu_net_decode_plain(mu_net *n, mu_conn_kind k, const uint8_t *frame, size_t size, mu_frame *out)
{
    (void)n;
    out->conn = k;
    out->length = (uint32_t)size;
    memcpy(out->bytes, frame, size);
    /* a handler of a short frame reads zeros past its end, not the previous frame's bytes */
    memset(out->bytes + size, 0, sizeof out->bytes - size);
    out->head = size ? frame[0] : 0;
    uint32_t hlen = size ? mu_frame_header_len(frame[0]) : 0;
    if (!hlen || size < (size_t)hlen + 1u) {
        out->opcode = 0;
        out->encrypted = 0;
        return MU_DECODE_BAD;
    }
    out->opcode = frame[hlen];
    if (frame[0] == MU_HEAD_C3 || frame[0] == MU_HEAD_C4) {
        out->encrypted = 1;
        return MU_DECODE_CRYPTO;
    }
    out->encrypted = 0;
    return MU_DECODE_OK;
}

int mu_net_next(mu_net *n, mu_conn_kind k, mu_frame *out, mu_decode_status *status)
{
    mu_decode_status local;
    if (!status)
        status = &local;
    *status = MU_DECODE_OK;
    if (k < 0 || k >= MU_CONN_KINDS)
        return 0;
    mu_conn *c = &n->conns[k];
    if (c->link < 0)
        return 0;
    for (;;) {
        if (c->pend_next < c->pend_count) {
            uint32_t at = c->pend_off[c->pend_next], end = c->pend_off[c->pend_next + 1];
            c->pend_next++;
            if (c->pend_next == c->pend_count) {
                c->pend_next = c->pend_count = 0;
                /* pend is reused by the next drain; the frame is copied out below first */
            }
            mu_decode_fn decode = n->decode ? n->decode : mu_net_decode_plain;
            *status = decode(n, k, &c->pend[at], end - at, out);
            n->frames_in++;
            return 1;
        }
        size_t got = 0;
        mu_decode_status pst = mu_conn_pull(c, n->transport, &got);
        if (pst == MU_DECODE_OVERFLOW) {
            *status = MU_DECODE_OVERFLOW;
            return 0;
        }
        n->bytes_in += got;
        c->pend_off[0] = 0;
        mu_recv_drain(&c->rx, pend_cb, c);
        if (!c->pend_count && !got)
            return 0;
    }
}

int mu_net_send(mu_net *n, mu_conn_kind k, mu_packet *p, int encrypted)
{
    if (k < 0 || k >= MU_CONN_KINDS || n->conns[k].link < 0)
        return MU_SEND_NOT_OPEN;
    if (p->overflow)
        return MU_SEND_OVERFLOW;
    uint32_t size = mu_packet_finish(p);
    const uint8_t *frame = &p->obj[2];
    if (encrypted) {
        if (!n->wrap)
            return MU_SEND_NEEDS_CRYPTO;
        uint8_t wire[MU_PACKET_OBJ + 64u];
        size_t wsize = sizeof wire;
        if (n->wrap(n, k, frame, size, 0, wire, &wsize) != 0)
            return MU_SEND_NEEDS_CRYPTO;
        if (mu_link_write(n->transport, n->conns[k].link, wire, wsize) != 0)
            return MU_SEND_NOT_OPEN;
        n->bytes_out += wsize;
    } else {
        if (mu_link_write(n->transport, n->conns[k].link, frame, size) != 0)
            return MU_SEND_NOT_OPEN;
        n->bytes_out += size;
    }
    n->frames_out++;
    return MU_SEND_OK;
}
