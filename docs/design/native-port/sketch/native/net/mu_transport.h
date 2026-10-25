/* NET-LINK-001 (sketch): the byte medium under a session. Public part.
 *
 * A transport moves bytes between the client and up to MU_LINKS peers. It knows nothing
 * of MU framing, opcodes or crypto. Three implementations, one interface:
 *
 *   mu_transport_sockets   product: nonblocking BSD sockets (kqueue), endpoint allowlist
 *   mu_fixture_transport   tests: in-process loopback to a wire-level fixture server
 *                          (native/fixture/mu_fixture.h; never linked into the product)
 *   mu_transport_replay    gate 3: inbound bytes from a recorded journal at their recorded
 *                          ticks; outbound bytes compared with the recording
 *
 * The allowlist replaces the mu-nonet dyld guard: the sockets transport refuses any
 * connect that is not the configured connect server or an endpoint the session itself
 * learned from the service (F4 03 game-server address, a messenger room's chat server).
 * There is no other path to a socket in the product, which a symbol test checks.
 */
#ifndef MU_TRANSPORT_H
#define MU_TRANSPORT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_endpoint {
    char host[256];              /* DNS name or dotted address */
    uint16_t port;
} mu_endpoint;

typedef struct mu_transport mu_transport;

/* Product transport. `allowed` seeds the allowlist (normally just the connect server). */
mu_transport *mu_transport_sockets(const mu_endpoint *allowed, size_t count, char *error, size_t error_size);

typedef enum mu_replay_mode {
    MU_REPLAY_STRICT = 0,        /* a divergent outbound byte is a failure */
    MU_REPLAY_OBSERVE            /* record divergences, keep feeding the inbound stream */
} mu_replay_mode;
mu_transport *mu_transport_replay(const char *journal_path, mu_replay_mode mode, char *error, size_t error_size);

void mu_transport_free(mu_transport *t);

/* The two calls a front end makes per frame. Neither applies anything to game state.
 * poll: read whatever the peers sent (nonblocking) into per-link buffers; `now_ms` drives
 *       replay timing. Returns the number of links with new bytes or state changes.
 * flush: write queued outbound bytes (partial writes stay queued, like the client's FD_WRITE
 *        drain 0x012906d4). Returns the bytes still pending. */
int mu_transport_poll(mu_transport *t, uint32_t now_ms);
size_t mu_transport_flush(mu_transport *t);

/* Divergence report of a replay transport (empty for the others). */
typedef struct mu_replay_report {
    uint64_t inbound_bytes, outbound_bytes, divergent_frames;
    uint32_t first_divergent_tick;
} mu_replay_report;
void mu_transport_replay_report(const mu_transport *t, mu_replay_report *out);

#ifdef __cplusplus
}
#endif

#endif /* MU_TRANSPORT_H */
