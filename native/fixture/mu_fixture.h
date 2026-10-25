/* FIXTURE-001: the wire-level fixture server - the demo servers, re-plumbed as test fixtures that
 * speak real MU frames through the same transport interface the product uses.
 *
 * NOT part of the product. Built into the dev session library (libmusession.a), linked only into
 * mu-session and tests (later mu-world / mu-walk and dev builds of mu-client / mu-shell).
 *
 * What the fixture does on the server side of each connection:
 *   - accepts the client's links at the endpoints the scenario declares (anything else is refused,
 *     like the product allowlist) through the loopback transport, or listens on 127.0.0.1 for a
 *     client that connects over TCP (mu_fixture_serve; loopback addresses only);
 *   - dechunks the client's requests with the verified dechunker (mu_recv) and undoes the client's
 *     XorData (mu_send_xor_decode over every byte after the opcode);
 *   - hands each request, in the client's layout, to the scenario's behaviours;
 *   - sends their answers as framed bytes. C1/C2 only: C3/C4 need the server half of the
 *     CryptoModule (NET-CRYPTO-001 / NET-DECODE-001), and an encrypted request is counted as
 *     undecodable.
 *
 * Scenario format (native/fixture/scenarios/<name>.scn, authored and synthetic):
 *   # comment
 *   endpoint ROLE HOST:PORT        ROLE: connect | game | chat
 *   use BEHAVIOUR key=value ...    instantiate a behaviour (behaviors/<name>.c)
 *   join key=value ...             the seed of a world tool's session (world= tile=x,y angle= class= level=
 *                                  name= slot=); read by mu-session, not by the fixture
 *   at TICK BEHAVIOUR COMMAND ...  a timed command for a behaviour (e.g. at 5 progress kill 12)
 *   at TICK send ROLE HEX...       a raw C1/C2 frame from the server
 *   at TICK close ROLE             the server closes that connection
 *   at TICK client VERB ...        a client-side action, run by mu-session (submit, attach, detach, lease, ...)
 *   expect KEY OP VALUE            a check mu-session makes at the end (OP: = != < <= > >=)
 * TICK is the fixture step: one per transport poll.
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
    const char *scenario;            /* path of the .scn file */
    const char *game_root;           /* item/monster tables behaviours may look up (none needed today) */
    uint32_t seed;                   /* every behaviour's rng derives from it: runs are reproducible */
} mu_fixture_options;

mu_fixture *mu_fixture_open(const mu_fixture_options *o, char *error, size_t error_size);
void mu_fixture_close(mu_fixture *f);

/* In-process: the transport a session uses to reach this fixture. The fixture is stepped from the
 * transport's poll (server time = the poll's now_ms; one step per poll). The fixture keeps
 * ownership: free the transport (mu_transport_free) before mu_fixture_close. */
mu_transport *mu_fixture_transport(mu_fixture *f);

/* Out-of-process: serve the scenario on a loopback TCP port for one client connection, stepping
 * every step_ms until the client closes or `seconds` pass. Returns 0 after a session, -1 on an error
 * (message in the report's last_error). */
int mu_fixture_serve(mu_fixture *f, const char *host, uint16_t port, uint32_t seconds, uint32_t step_ms);

typedef struct mu_fixture_report {
    uint64_t requests, answers, undecodable_requests, refused_connects;
    uint32_t behaviors, steps;
    char last_error[128];
} mu_fixture_report;
void mu_fixture_report_get(const mu_fixture *f, mu_fixture_report *out);

/* The scenario's endpoint for a role ("connect", "game", "chat"); -1 when it declares none. */
int mu_fixture_endpoint(const mu_fixture *f, const char *role, mu_endpoint *out);

/* The scenario lines meant for the client side (mu-session). */
typedef struct mu_scenario_line {
    uint32_t tick;
    int number;                      /* line number in the file */
    char text[240];                  /* "submit add_stat 0", "hero.level = 2", the join arguments */
} mu_scenario_line;
typedef struct mu_fixture_script {
    const mu_scenario_line *client;  /* "at TICK client ..." (text after "client "), in file order */
    size_t nclient;
    const mu_scenario_line *expect;  /* "expect ..." */
    size_t nexpect;
    const mu_scenario_line *join;    /* NULL without a join line */
} mu_fixture_script;
void mu_fixture_script_get(const mu_fixture *f, mu_fixture_script *out);

/* key=value lookup in scenario arguments ("latency=2 class=0x21"); the fallback when absent */
int32_t mu_fx_arg_int(const char *args, const char *key, int32_t fallback);
int mu_fx_arg_str(const char *args, const char *key, char *out, size_t cap);

/* The behaviours compiled in (generated list), for `mu-session behaviors`. */
size_t mu_fixture_behavior_names(const char *const **names);

#ifdef __cplusplus
}
#endif

#endif /* MU_FIXTURE_H */
