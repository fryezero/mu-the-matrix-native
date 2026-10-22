/* Synthetic state adapter for the private original-instruction validator. */
#include "../core/mu_social_messages.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
/* Scalar state is marshalled explicitly, independent of production struct layout. */
void mu_social_receive_probe(const uint32_t a[18], const uint8_t *packet, size_t size, uint32_t out[32],
                             char address[16]) {
    mu_social_messages *m = calloc(1, sizeof *m);
    mu_social_messages_init(m, "Hero");
    m->next_ui = a[16];
    m->parent_visible = (int)a[4];
    m->fee_exempt = (int)a[5];
    if (a[11])
        snprintf(m->pending_peers[0], 11, "PeerABCDEF");
    if (a[3] && a[3] != UINT32_MAX) {
        mu_local_room *r = m->rooms;
        r->ui = a[3];
        r->number = 0x1111;
        r->ticket = 0x22223333;
        r->connection = 1;
        r->shown = (int)a[4];
        snprintf(r->peer, 11, "PeerABCDEF");
        snprintf(r->address, 16, "192.0.2.9");
    }
    int windows = 0;
    if (a[10] && a[12])
        m->windows[windows++] = (mu_local_window){.ui = a[12], .kind = 1, .shown = 1};
    if (a[9])
        m->windows[windows++] = (mu_local_window){.ui = a[9], .letter = a[13], .kind = 2, .shown = 1};
    if (a[6]) {
        m->letter_count = 1;
        m->letters[0].header.id = a[13];
        m->letters[0].read_ui = a[9];
        m->letters[0].pending = (int)a[8];
    }
    if (a[7]) {
        m->cache[0].used = 1;
        m->cache[0].id = a[13];
        size_t n = a[17] > 1000 ? 1000 : a[17];
        memset(m->cache[0].text, 'Q', n);
    }
    if (a[8]) {
        mu_social_messages_pending_track(m, a[13]);
        mu_social_messages_pending_bind(m, a[13], a[9]);
    }
    int ret = 0;
    switch (a[0]) {
    case 0:
        ret = mu_social_messages_receive(m, 0x83, packet, size);
        break;
    case 1:
        ret = mu_social_messages_receive(m, 0x41, packet, size);
        break;
    case 2:
        ret = mu_social_messages_receive(m, 0xa2, packet, size);
        break;
    case 3:
        ret = mu_social_messages_read_request(m, a[13]);
        break;
    case 4:
        ret = mu_social_messages_receive(m, 0xec, packet, size);
        break;
    case 5:
        ret = mu_social_messages_pending_track(m, a[13]);
        break;
    case 6:
        mu_social_messages_pending_close(m, a[13]);
        break;
    case 7:
        mu_social_messages_pending_bind(m, a[13], a[12]);
        break;
    case 8:
        ret = (int32_t)mu_social_messages_pending_get(m, a[13]);
        break;
    }
    memset(out, 0, 32 * sizeof *out);
    memset(address, 0, 16);
    out[0] = m->next_ui;
    out[1] = m->active_ui;
    out[2] = (uint32_t)m->notice;
    out[3] = (uint32_t)m->notice_fee;
    out[4] = (uint32_t)m->requests;
    out[5] = (uint32_t)m->mailbox_revision;
    out[6] = (uint32_t)ret;
    out[7] = m->pending_peers[0][0] != 0;
    for (int i = 0; i < MU_LOCAL_ROOMS; i++)
        if (m->rooms[i].ui) {
            mu_local_room *r = m->rooms + i;
            out[8]++;
            out[9] = r->ui;
            out[10] = r->number;
            out[11] = r->ticket;
            out[12] = (uint32_t)r->shown;
            out[13] = r->connection;
            snprintf(address, 16, "%s", r->address);
        }
    out[29] = m->request.data[2];
    out[14] = (uint32_t)m->letter_count;
    if (m->letter_count)
        out[15] = m->letters[0].header.read;
    for (int i = 0; i < MU_LOCAL_MAIL; i++) {
        if (m->cache[i].used && m->cache[i].id == a[13]) {
            out[16] = 1;
            out[17] = (uint32_t)strlen(m->cache[i].text);
        }
        if (m->pending_reads[i].used && m->pending_reads[i].id == a[13]) {
            out[18] = 1;
            out[19] = m->pending_reads[i].ui;
        }
    }
    for (int i = 0; i < MU_LOCAL_WINDOWS; i++)
        if (m->windows[i].ui) {
            const mu_local_window *w = m->windows + i;
            out[20]++;
            if (w->ui == a[12] && w->kind == 1)
                out[21] = 1;
            if (w->ui == a[9])
                out[22] = 1;
            if (w->ui == a[16]) {
                out[23] = 1;
                out[24] = (uint32_t)strlen(w->body);
            }
        }
    mu_social_messages_destroy(m);
    free(m);
}
