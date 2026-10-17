/* NATIVE-NET-001: Mu The Matrix client network protocol layer.
 *
 * Platform-neutral C reconstruction of the framing and send-side obfuscation
 * that the client's own game code performs around its ws2_32 calls. It carries
 * no client bytes, no Windows or x86 dependency and no server impersonation; it
 * only documents the protocol so a native client can later speak it.
 *
 * Evidence: restored main.exe first section (SHA-256
 * 2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724). The
 * reconstructed routines below are validated bit-exact against the client's
 * actual instructions under Unicorn by scripts/validate_protocol.py. See
 * docs/research/client-net-protocol.md for addresses and the C3/C4 cipher
 * boundary.
 */
#ifndef MU_PROTOCOL_H
#define MU_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* MU packet head bytes. C1/C2 are plaintext; C3/C4 carry a payload the client
 * additionally runs through its CryptoModule (a documented boundary, see the
 * finding doc). The size-field rules are identical between C1/C3 and C2/C4. */
#define MU_HEAD_C1 0xC1u /* 1-byte size,   plaintext   */
#define MU_HEAD_C2 0xC2u /* 2-byte size,   plaintext   */
#define MU_HEAD_C3 0xC3u /* 1-byte size,   CryptoModule */
#define MU_HEAD_C4 0xC4u /* 2-byte size,   CryptoModule */

/* The client packet buffer is 0x145c bytes: a 2-byte little-endian length word
 * followed by up to 0x145a body bytes (client guard at 0x00d51cae). */
#define MU_PACKET_CAP 0x145au
#define MU_PACKET_OBJ 0x145cu

/* nRecv (0x01290792) accumulates into a 0x2000-byte ring before dispatch. */
#define MU_RECV_CAP 0x2000u

typedef enum {
    MU_FRAME_OK = 0,      /* a complete frame is present */
    MU_FRAME_NEED_MORE,   /* valid head but not all bytes have arrived yet */
    MU_FRAME_BAD          /* head is not C1..C4, or declared size is <= 0 */
} mu_frame_status;

typedef struct {
    uint8_t  head;        /* C1..C4 */
    uint32_t size;        /* total frame length, header included */
    uint32_t header_len;  /* 2 for C1/C3, 3 for C2/C4 */
    uint32_t payload_off; /* first payload byte (== header_len) */
    int      encrypted;   /* 1 for C3/C4 (CryptoModule payload) */
} mu_frame_info;

/* Classify the frame at the front of `buf`. `avail` is how many bytes are
 * readable. Mirrors the client receive loop (0x01290892) and the size reader
 * used on both paths. */
mu_frame_status mu_frame_parse(const uint8_t *buf, size_t avail, mu_frame_info *out);

/* Header length / size-field width for a head byte (0 if not a MU head). */
uint32_t mu_frame_header_len(uint8_t head);

/* The client's 32-byte send obfuscation key (XorData, 0x00d5205e table). */
extern const uint8_t MU_SEND_XOR_KEY[32];

/* XorData (0x00d52055). Operates on a packet *object*: obj[0..1] is the
 * little-endian size word and obj[2..] is the body. For i in [start, end):
 *   obj[i+2] ^= obj[i+1] ^ key[i & 31]
 * so each body byte is chained onto the previous (already-encoded) body byte,
 * seeded from the size word's high byte at i==start. Encode runs ascending;
 * decode is its exact inverse and runs descending. */
void mu_send_xor_encode(uint8_t *obj, size_t start, size_t end);
void mu_send_xor_decode(uint8_t *obj, size_t start, size_t end);

/* Faithful port of the client packet builder (CProtocol, 0x00d51b91 family). */
typedef struct {
    uint8_t  obj[MU_PACKET_OBJ]; /* [0..1] size word, [2..] body */
    uint32_t overflow;           /* set when an add was rejected (guard hit) */
} mu_packet;

/* Init (0x00d52133) + Begin (0x00d51baf): clear, lay down head, reserve the
 * size field, then the opcode byte. */
void mu_packet_begin(mu_packet *p, uint8_t head, uint8_t opcode);

/* AddData (0x00d51c9b): append `len` body bytes; if `encode`, apply XorData to
 * exactly the appended range. Returns 0 on success, -1 if it would overflow
 * 0x145a (the client silently drops in that case). */
int mu_packet_add(mu_packet *p, const uint8_t *data, size_t len, int encode);

/* WriteSize (0x00d51c1f): patch the C1/C2 size field with the current body
 * length. Returns the total serialized length (body length). After this call
 * p->obj[2..total) is the wire frame. */
uint32_t mu_packet_finish(mu_packet *p);

/* Current body length (the client's size word). */
uint32_t mu_packet_len(const mu_packet *p);

/* Receive stream dechunker, mirroring nRecv's accumulate-and-split loop. */
typedef struct {
    uint8_t buf[MU_RECV_CAP];
    size_t  len;
} mu_recv;

typedef void (*mu_frame_cb)(const uint8_t *frame, size_t size, void *ud);

void mu_recv_init(mu_recv *r);

/* Append received bytes. Returns 0 on success, -1 on buffer overflow (the
 * client logs "Receive Packet Buffer Overflow" at 0x012907a8 and stops). */
int mu_recv_push(mu_recv *r, const uint8_t *data, size_t n);

/* Pop every complete frame currently buffered, in order, invoking `cb`.
 * Returns the number of frames delivered. Leftover partial bytes stay buffered.
 * A non-MU head byte clears the buffer (client resets recvlen to 0). */
size_t mu_recv_drain(mu_recv *r, mu_frame_cb cb, void *ud);

/* Packet serial counters (g_byPacketSerialSend 0x6fca01d /
 * g_byPacketSerialRecv 0x6fca01e): a byte that post-increments each packet. */
uint8_t mu_serial_next(uint8_t *counter);

#ifdef __cplusplus
}
#endif

#endif /* MU_PROTOCOL_H */
