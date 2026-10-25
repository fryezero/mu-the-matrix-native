/* NET-LINK-001: connections over links - the receive dechunker per connection, the decode stage
 * hook and the send path. Private to native/net, native/session and native/fixture (include
 * audit, scripts/audit_includes.py).
 *
 * mu_net is the client's socket class + packet queue + serials + CryptoModule, for the whole
 * session: the client keeps ONE send and ONE receive serial (g_byPacketSerialSend 0x06fca01d,
 * g_byPacketSerialRecv 0x06fca01e) across its connections; whether they reset on the
 * connect-server -> game-server hop is NET-DECODE-001's question, not assumed here.
 *
 * Receive path per connection:
 *   link bytes -> mu_conn_pull: at most 0x2000 - buffered bytes per read, and the client's stop
 *                 when 0x2000 bytes are buffered (0x01290792: "Receive Packet Buffer Overflow"
 *                 at 0x012907a8 instead of reading)
 *              -> mu_recv_push / mu_recv_drain (verified, native/core/mu_protocol.c)
 *              -> n->decode: the decode stage 0x01221b94. NET-LINK-001 installs the C1/C2
 *                 pass-through (mu_net_decode_plain); a C3/C4 frame is MU_DECODE_CRYPTO until
 *                 NET-DECODE-001 sets n->decode to its mu_decode (crypto lane, decode.c)
 *              -> mu_frame, the bytes and arguments 0x01287ead receives
 * Send path:
 *   mu_packet (verified builder, XorData inside AddData) -> Send 0x00d51d4f -> its wrap 0x00d51e87:
 *   Send's first argument 0 sends the built bytes as they are (raw send 0x00d52159); non-zero adds
 *   the serial and the CryptoModule (C3/C4, 0x018df500 on g_enc). The second argument promotes the
 *   head to C2/C4. Static reading of 0x00d51e97..0x00d51fce (handoff SESSION-CORE-001). The
 *   encrypted path needs n->wrap from NET-DECODE-001; without it mu_net_send refuses and writes
 *   nothing.
 */
#ifndef MU_CONN_H
#define MU_CONN_H

#include "../core/mu_protocol.h"   /* in CORE_SRC since NET-LINK-001; verify-protocol-cbmc reruns */
#include "mu_link.h"

struct mu_crypto;                  /* native/net/mu_crypto.h (NET-CRYPTO-001, crypto lane); NULL until it lands */

typedef enum mu_conn_kind {
    MU_CONN_CONNECT = 0,         /* connect server: server list, F4 03 */
    MU_CONN_GAME,                /* game server: everything after the hop */
    MU_CONN_CHAT,                /* messenger room server (room answer: address[16] + ticket; inference) */
    MU_CONN_KINDS
} mu_conn_kind;

/* What the dispatcher is called with: the post-decode frame in the layout the client's
 * handlers were verified with, plus the dispatcher's arguments. Never leaves native/session.
 * bytes holds up to MU_RECV_CAP: the dechunker can deliver any frame that fits its 0x2000 ring
 * (the client's packet queue 0x01291777 capacity is NET-DISPATCH-001's to recover). */
typedef struct mu_frame {
    mu_conn_kind conn;
    uint8_t head;                /* as delivered to the dispatcher (NET-DECODE-001: does 0x01221b94 rewrite C3->C1?) */
    uint8_t opcode;              /* the dispatcher's first argument */
    int encrypted;               /* its fourth argument: 1 when the frame came through Decrypt */
    uint32_t length;             /* its third argument */
    uint8_t bytes[MU_RECV_CAP];  /* its second argument */
    uint32_t tick;               /* session tick at arrival (journal, barrier) */
} mu_frame;

typedef enum mu_decode_status {
    MU_DECODE_OK = 0,
    MU_DECODE_SERIAL,            /* the serial check failed ("Decrypt error" path) */
    MU_DECODE_CRYPTO,            /* Decrypt refused or not available (no CryptoModule before NET-DECODE-001) */
    MU_DECODE_BAD,               /* not a frame the client would dispatch (shorter than its header + opcode) */
    MU_DECODE_OVERFLOW           /* the client's 0x2000 receive guard: the connection stops receiving */
} mu_decode_status;

typedef struct mu_net mu_net;
typedef mu_decode_status (*mu_decode_fn)(mu_net *n, mu_conn_kind k, const uint8_t *frame, size_t size,
                                         mu_frame *out);
/* The send wrap 0x00d51e87 for Send(1, wide): from the built frame to the bytes on the wire. */
typedef int (*mu_wrap_fn)(mu_net *n, mu_conn_kind k, const uint8_t *frame, size_t size, int wide, uint8_t *out,
                          size_t *out_size);

typedef struct mu_conn {
    mu_recv rx;                  /* first member: the CBMC harness link_pull.c indexes it from the object start */
    mu_conn_kind kind;
    mu_link_id link;
    int32_t channel;             /* the CryptoModule channel this connection uses: NET-DECODE-001 */
    int open;                    /* the link reported MU_LINK_OPEN */
    int stopped;                 /* the 0x2000 guard was hit: nothing more is read (the client's stop) */
    /* frames one drain cut, waiting to be decoded in order (a drain delivers every complete frame) */
    uint8_t pend[MU_RECV_CAP];
    uint16_t pend_off[MU_RECV_CAP + 1u];
    uint32_t pend_count, pend_next;
} mu_conn;

struct mu_net {
    mu_transport *transport;     /* not owned */
    mu_conn conns[MU_CONN_KINDS];
    struct mu_crypto *crypto;    /* NET-CRYPTO-001 */
    mu_decode_fn decode;         /* mu_net_decode_plain until NET-DECODE-001 */
    mu_wrap_fn wrap;             /* NULL until NET-DECODE-001: encrypted sends are refused */
    uint8_t serial_send, serial_recv;
    uint64_t frames_in, frames_out, bytes_in, bytes_out;
};

int mu_net_init(mu_net *n, mu_transport *t, char *error, size_t error_size);
void mu_net_free(mu_net *n);
/* Heap versions for hosts that cannot embed the struct (ctypes tests). */
mu_net *mu_net_create(mu_transport *t, char *error, size_t error_size);
void mu_net_destroy(mu_net *n);

/* Opens connection k (closing a previous link of k). It does NOT add e to the allowlist: the transport
 * refuses (MU_LINK_REFUSED) an endpoint that is neither the configured one nor one the session added with
 * mu_net_allow after learning it from the service (F4 03, a room's chat server). */
int mu_net_connect(mu_net *n, mu_conn_kind k, const mu_endpoint *e);
int mu_net_allow(mu_net *n, const mu_endpoint *e);
void mu_net_close(mu_net *n, mu_conn_kind k);
mu_link_state mu_net_state(mu_net *n, mu_conn_kind k, int *error_code);

/* One read step of connection k: asks the link for at most MU_RECV_CAP - rx.len bytes and pushes
 * them; with MU_RECV_CAP bytes already buffered it reads nothing and returns MU_DECODE_OVERFLOW
 * (sticky: the connection is stopped). Returns MU_DECODE_OK otherwise; *got the bytes read. */
mu_decode_status mu_conn_pull(mu_conn *c, mu_transport *t, size_t *got);

/* 0x01221b94 for C1/C2: the frame as it is. C3/C4: MU_DECODE_CRYPTO (no CryptoModule here). */
mu_decode_status mu_net_decode_plain(mu_net *n, mu_conn_kind k, const uint8_t *frame, size_t size, mu_frame *out);

/* Pops the next decoded frame of connection k (pulling and dechunking what the link has), or
 * returns 0 with *status MU_DECODE_OK when nothing is complete. Returns 1 with a non-OK *status
 * for a frame that did not decode (out->bytes/length still hold its raw bytes), and 0 with
 * MU_DECODE_OVERFLOW once the connection stopped. */
int mu_net_next(mu_net *n, mu_conn_kind k, mu_frame *out, mu_decode_status *status);

typedef enum mu_send_status {
    MU_SEND_OK = 0,
    MU_SEND_NOT_OPEN = -1,       /* no open link for the connection */
    MU_SEND_NEEDS_CRYPTO = -2,   /* Send(1, ..) without n->wrap: nothing written */
    MU_SEND_OVERFLOW = -3        /* the builder refused an add (0x145a guard); the client drops it */
} mu_send_status;

/* Send 0x00d51d4f: WriteSize (mu_packet_finish), then the wrap by `encrypted` (Send's first
 * argument), then queue on k's link. The serial advances only on the encrypted path. */
int mu_net_send(mu_net *n, mu_conn_kind k, mu_packet *p, int encrypted);

#endif /* MU_CONN_H */
