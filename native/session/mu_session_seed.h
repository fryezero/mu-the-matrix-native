/* SESSION-CORE-001: start a session already in a world, for world TOOLS and tests.
 *
 * Compiled only with -DMU_SESSION_SEED (mu-session, test hosts, later mu-world / mu-walk and a dev
 * mu-shell). The product build has no seed symbol (native/tests/test_session_core.py checks the
 * product variant of the library).
 *
 * A seed sets exactly what the account flow's join answer would set - phase IN_WORLD, the place,
 * the hero's class/level/name, the selected character - and nothing else: every other piece of
 * state still arrives as framed bytes from the transport (normally a fixture scenario). The
 * seeded session's link is the GAME connection, opened to cfg->connect_server (in a fixture run:
 * the scenario's game endpoint), because a seeded session has already hopped. It exists because
 * the account and join bodies are not reconstructed yet (NET-ACCOUNT-001).
 */
#ifndef MU_SESSION_SEED_H
#define MU_SESSION_SEED_H
#ifndef MU_SESSION_SEED
#error "mu_session_seed.h is for tools and tests only"
#endif
#include "mu_session.h"

typedef struct mu_session_seed {
    mu_place place;
    uint8_t class_byte;
    int32_t level;
    char name[11];
    int32_t slot;
} mu_session_seed;

mu_session *mu_session_open_seeded(const mu_session_config *cfg, const mu_session_seed *seed, char *error,
                                   size_t error_size);
#endif
