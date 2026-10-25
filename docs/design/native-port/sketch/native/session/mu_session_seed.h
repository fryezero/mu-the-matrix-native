/* SESSION-CORE-001 (sketch): start a session already in a world, for world TOOLS and tests.
 *
 * Compiled only with -DMU_SESSION_SEED (mu-world, mu-walk, test hosts, dev mu-shell). The
 * product mu-client is built without it and test_native_app.py asserts the symbol is absent.
 *
 * A seed sets exactly what the account flow's join answer would set - phase IN_WORLD, the
 * place, the hero's class/level/name, the selected character - and nothing else: every other
 * piece of state (stats, inventory, skills, quests, other characters, ground items) still
 * arrives as framed bytes from the transport (normally a fixture scenario). It exists because
 * the account and join bodies are not reconstructed yet (NET-ACCOUNT-001); once they are, the
 * shell and its flow tests use real frames end to end, and only the world tools keep seeding,
 * because they never had a login.
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
