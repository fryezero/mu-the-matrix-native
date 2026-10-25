/* NET-LINK-001: the byte medium under a session. Public part.
 *
 * A transport moves bytes between the client and up to MU_LINKS peers. It knows nothing
 * of MU framing, opcodes or crypto. Three implementations, one interface:
 *
 *   mu_transport_sockets   product: nonblocking BSD sockets (kqueue on macOS, poll(2) on other
 *                          hosts), the endpoint allowlist and the client lock
 *   mu_fixture_transport   tests: in-process loopback to a wire-level fixture server
 *                          (native/fixture/mu_fixture.h; never linked into the product), built on
 *                          the loopback hook mu_transport_wrap (mu_link.h)
 *   mu_transport_replay    gate 3: inbound bytes from a recorded journal. NOT IMPLEMENTED in
 *                          NET-LINK-001: it returns NULL with an explanation (see the handoff)
 *
 * The allowlist replaces the mu-nonet dyld guard: the sockets transport refuses any connect
 * that is not the configured connect server or an endpoint the session itself learned from the
 * service (F4 03 game-server address, a messenger room's chat server, added with mu_link_allow).
 * A refused connect never reaches connect(2): the link reports MU_LINK_REFUSED.
 *
 * One client at a time (operator rule, 2026-10-25: one account, one logged-in client). The
 * sockets transport takes the client lock before returning and fails with
 * MU_TRANSPORT_LOCKED while another client holds it:
 *   - always: a per-user single-instance lock (flock(2) on MU_CLIENT_LOCK_PATH, default
 *     $HOME/Library/Application Support/MuTheMatrixNative/client.lock on macOS,
 *     $HOME/.mu-the-matrix-native.lock elsewhere), plus a refusal while a process whose
 *     name or argument list names main.exe or MuTheMatrix.exe runs (the user is playing the
 *     original client; never touch it). MU_CLIENT_PROCESS_NAMES (comma list) replaces the two
 *     names, for tests that must not depend on the owner's machine;
 *   - agents and live tests (MU_AGENT=1): additionally the shared game lock of mu-mac-tools'
 *     GAME-LOCK.md. The directory comes from MU_GAME_LOCK_DIR (no path is compiled in); its
 *     owner file's first line must equal MU_LOCK_ID, exactly as mu-autologin.sh checks it. The
 *     transport only checks that lock; acquiring and releasing it stays with the agent.
 * The lock is released by mu_transport_free (and by the kernel at process exit). The owner
 * line of whoever holds a lock is copied into `error`.
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
/* Not implemented yet: returns NULL and says so in `error` (no abort). */
mu_transport *mu_transport_replay(const char *journal_path, mu_replay_mode mode, char *error, size_t error_size);

void mu_transport_free(mu_transport *t);

/* The two calls a front end makes per frame. Neither applies anything to game state.
 * poll: read whatever the peers sent (nonblocking) into per-link buffers and advance connects;
 *       `now_ms` drives fixture and replay timing. Returns the number of links with new bytes or
 *       state changes.
 * flush: write queued outbound bytes (partial writes stay queued, like the client's FD_WRITE
 *        drain 0x012906d4). Returns the bytes still pending. */
int mu_transport_poll(mu_transport *t, uint32_t now_ms);
size_t mu_transport_flush(mu_transport *t);

/* Endpoint parsing for configuration and tools: "host:port". Returns 0 on success. */
int mu_endpoint_parse(mu_endpoint *e, const char *text);
/* Whether the host names the loopback interface (127.0.0.0/8, ::1, localhost). Tools that must
 * never reach the network check this before they create a sockets transport. */
int mu_endpoint_is_loopback(const mu_endpoint *e);

/* Counters for reports and the "never connects elsewhere" tests. */
typedef struct mu_transport_counters {
    uint64_t bytes_in, bytes_out;
    uint32_t links_opened, links_refused, connects_attempted;
} mu_transport_counters;
void mu_transport_counters_get(const mu_transport *t, mu_transport_counters *out);

/* Divergence report of a replay transport (zero for the others). */
typedef struct mu_replay_report {
    uint64_t inbound_bytes, outbound_bytes, divergent_frames;
    uint32_t first_divergent_tick;
} mu_replay_report;
void mu_transport_replay_report(const mu_transport *t, mu_replay_report *out);

#ifdef __cplusplus
}
#endif

#endif /* MU_TRANSPORT_H */
