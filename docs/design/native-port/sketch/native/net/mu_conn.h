/* NET-DECODE-001 (sketch): connections, the decode stage and the send wrap.
 * Private to native/session and native/fixture (include audit).
 *
 * mu_net is the client's socket class + packet queue + serials + CryptoModule, for the
 * whole session: the client keeps ONE send and ONE receive serial (g_byPacketSerialSend
 * 0x06fca01d, g_byPacketSerialRecv 0x06fca01e) across its connections; whether they reset
 * on the connect-server -> game-server hop is recovered, not assumed (TODO below).
 *
 * Receive path per connection:
 *   link bytes -> mu_recv_push/mu_recv_drain (verified, native/core/mu_protocol)
 *              -> mu_decode (0x01221b94: C1/C2 as is; C3/C4 decrypt with g_dec + serial check)
 *              -> mu_frame, exactly the bytes and arguments 0x01287ead receives
 * Send path:
 *   mu_packet (verified builder, XorData inside AddData) -> mu_wrap (0x00d51e8c: serial,
 *   g_enc for C3/C4) -> link
 */
#ifndef MU_CONN_H
#define MU_CONN_H

#include "../core/mu_protocol.h"   /* moved into CORE_SRC by NET-LINK-001; CBMC reruns */
#include "mu_crypto.h"
#include "mu_link.h"

typedef enum mu_conn_kind {
    MU_CONN_CONNECT = 0,         /* connect server: server list, F4 03 */
    MU_CONN_GAME,                /* game server: everything after the hop */
    MU_CONN_CHAT,                /* messenger room server (room answer: address[16] + ticket; inference) */
    MU_CONN_KINDS
} mu_conn_kind;

/* What the dispatcher is called with: the post-decode frame in the layout the client's
 * handlers were verified with, plus the dispatcher's arguments. Never leaves native/session. */
typedef struct mu_frame {
    mu_conn_kind conn;
    uint8_t head;                /* as delivered to the dispatcher (TODO(NET-DECODE-001): does 0x01221b94 rewrite C3->C1?) */
    uint8_t opcode;              /* the dispatcher's first argument */
    int encrypted;               /* its fourth argument: 1 when the frame came through Decrypt */
    uint32_t length;             /* its third argument */
    uint8_t bytes[MU_PACKET_OBJ];/* its second argument (the client's buffer bound) */
    uint32_t tick;               /* session tick at arrival (journal, barrier) */
} mu_frame;

typedef struct mu_conn {
    mu_conn_kind kind;
    mu_link_id link;
    mu_recv rx;
    int32_t channel;             /* the CryptoModule channel this connection uses: TODO(NET-DECODE-001) */
    int open;
} mu_conn;

typedef struct mu_net {
    mu_transport *transport;     /* not owned */
    mu_conn conns[MU_CONN_KINDS];
    mu_crypto *crypto;
    uint8_t serial_send, serial_recv;
} mu_net;

int mu_net_init(mu_net *n, mu_transport *t, char *error, size_t error_size);
void mu_net_free(mu_net *n);

int mu_net_connect(mu_net *n, mu_conn_kind k, const mu_endpoint *e);  /* allow + open; closes a previous link of k */
void mu_net_close(mu_net *n, mu_conn_kind k);

typedef enum mu_decode_status {
    MU_DECODE_OK = 0,
    MU_DECODE_SERIAL,            /* the serial check failed ("Decrypt error" path) */
    MU_DECODE_CRYPTO,            /* Decrypt refused (no context, bad length) */
    MU_DECODE_BAD                /* not a frame the client would dispatch */
} mu_decode_status;

/* 0x01221b94 for one dechunked frame. Pure apart from the serial and the crypto contexts it
 * advances, exactly as the client's. Verified under Unicorn (scripts/validate_decode.py) and
 * bounded by a CBMC harness like mu_protocol.c's. */
mu_decode_status mu_decode(mu_net *n, mu_conn_kind k, const uint8_t *frame, size_t size, mu_frame *out);

/* Pops the next decoded frame of connection k (dechunking what the link has), or returns 0. */
int mu_net_next(mu_net *n, mu_conn_kind k, mu_frame *out, mu_decode_status *status);

/* 0x00d51e8c + send 0x012905d4: finish p, apply the C3/C4 wrap when `encrypted`, queue on k's link. */
int mu_net_send(mu_net *n, mu_conn_kind k, mu_packet *p, int encrypted);

#endif /* MU_CONN_H */
