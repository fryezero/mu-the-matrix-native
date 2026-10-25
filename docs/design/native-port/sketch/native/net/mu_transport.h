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
 *
 * One client at a time (operator rule, 2026-10-25: one account, one logged-in client). The
 * sockets transport takes the client lock before its first connect and fails with
 * MU_TRANSPORT_LOCKED while another client holds it:
 *   - product: a per-user single-instance lock, plus a refusal while an original main.exe or
 *     MuTheMatrix.exe the user started is running (the user is playing; never touch it);
 *   - agents and live tests (MU_AGENT=1): the shared game lock of mu-mac-tools' GAME-LOCK.md,
 *     whose owner line must equal MU_LOCK_ID, exactly as mu-autologin.sh checks it. The lock
 *     directory comes from MU_GAME_LOCK_DIR (no path is compiled in).
 * The lock is released by mu_transport_free. A second login the service refuses as "already
 * connected" closes the session with MU_CLOSE_ALREADY_CONNECTED instead of retrying.
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

typedef enum mu_transport_status {
    MU_TRANSPORT_OK = 0,
    MU_TRANSPORT_LOCKED,         /* another client holds the client lock (owner line in `error`) */
    MU_TRANSPORT_ERROR
} mu_transport_status;

/* Product transport. `allowed` seeds the allowlist (normally just the connect server). Takes the
 * client lock (see above) before returning; NULL with *status = MU_TRANSPORT_LOCKED when it is held. */
mu_transport *mu_transport_sockets(const mu_endpoint *allowed, size_t count, mu_transport_status *status,
                                   char *error, size_t error_size);

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
