/* FIXTURE-001 (sketch): the wire-level fixture server - the demo servers, re-plumbed as test
 * fixtures that speak real C1-C4 bytes through the same transport the product uses.
 *
 * NOT part of the product. Built into libmufixture.a, linked only into test tools, mu-world /
 * mu-walk (which have no live mode), and dev builds of mu-client/mu-shell (`--fixture FILE`).
 * test_native_app.py asserts the shipped mu-client contains no mu_fixture_* symbol.
 *
 * What the fixture does on the server side of each connection:
 *   - accepts the client's links at the endpoints the scenario names (connect server, game
 *     servers, chat server) through a loopback transport, or listens on 127.0.0.1 for
 *     black-box runs of the shipped app binary;
 *   - dechunks and decodes the client's requests with the same mu_conn code in the server role
 *     (mu_crypto_new_server_side: the client's C3/C4 really are encrypted and decrypted);
 *   - hands each request, post-decrypt and in the client's layout, to the scenario's behaviors;
 *   - sends their answers as framed bytes: C1/C2 plain, C3/C4 through the CryptoModule with
 *     the serial, exactly what the client's decode stage expects.
 *
 * Every frame a behavior sends must have a dispatcher row whose apply function exists; a
 * behavior may only emit frame layouts the reconstruction has recovered. Until a body is
 * recovered (e.g. the 0x13 monster viewport), the behavior that needs it is absent and the
 * scenario says so; no feed bypasses the dispatcher any more.
 */
#ifndef MU_FIXTURE_H
#define MU_FIXTURE_H

#include <stddef.h>
#include <stdint.h>

#include "../net/mu_transport.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_fixture mu_fixture;

typedef struct mu_fixture_options {
    const char *scenario;            /* native/fixture/scenarios/<name>.scn (authored, synthetic, committed) */
    const char *game_root;           /* item/monster tables the behaviors look up (synthetic root in CI) */
    uint32_t seed;                   /* every behavior's rng derives from it: runs are reproducible */
} mu_fixture_options;

mu_fixture *mu_fixture_open(const mu_fixture_options *o, char *error, size_t error_size);
void mu_fixture_close(mu_fixture *f);

/* In-process: the transport a session uses to reach this fixture. The fixture is stepped from
 * the transport's poll (server time = the poll's now_ms), so one call order drives both ends. */
mu_transport *mu_fixture_transport(mu_fixture *f);

/* Out-of-process: serve the scenario on a TCP port for the shipped app (gate-5 install/restart
 * tests, signed-binary smoke). Blocks; tools/mu_fixture_server.c wraps it. */
int mu_fixture_serve(mu_fixture *f, const char *host, uint16_t port, uint32_t seconds);

typedef struct mu_fixture_report {
    uint64_t requests, answers, undecodable_requests;
    uint32_t behaviors;
    char last_error[128];
} mu_fixture_report;
void mu_fixture_report_get(const mu_fixture *f, mu_fixture_report *out);

#ifdef __cplusplus
}
#endif

#endif /* MU_FIXTURE_H */
