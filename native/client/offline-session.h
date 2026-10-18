#ifndef MU_OFFLINE_SESSION_H
#define MU_OFFLINE_SESSION_H

/* Offline demo session for mu-client (NATIVE-SHELL-001).
 *
 * The client's scenes wait for the network layer at four points:
 *   - the server list (CServerListManager, shown when the list arrives);
 *   - the login answer (protocol state 0x14, then the character-list request);
 *   - the character list (protocol state 0x33 and the CreateHero calls);
 *   - the join-map answer (0x0185a75a(1), the world and the hero position).
 * In the real client all four come from the server through the network
 * protocol, which is outside this project's scope (no encryption, no login
 * packets, no server connection). This provider answers them locally from
 * demo files so the native scene flow can run end to end:
 *
 *   servers FILE        server list, `mu-render ui servers --list` format
 *   characters FILE     character list, `mu-charsel --list` format
 *   join SLOT WORLD X,Y [ANGLE]   where the character with SLOT enters
 *
 * Relative FILE paths are taken next to the session file. The login accepts
 * any input: nothing typed is kept (the front end counts keystrokes for the
 * masked display only) and nothing is sent anywhere. */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/ui/ui_server.h"
#include "../core/mu_charsel.h"

#define MU_OFFLINE_PATH 1024
#define MU_OFFLINE_JOINS 10

typedef struct mu_offline_join {
    int32_t slot, world, tile[2];
    float angle;
} mu_offline_join;

typedef struct mu_offline_session {
    char servers_path[MU_OFFLINE_PATH];      /* empty: built-in list */
    char characters_path[MU_OFFLINE_PATH];   /* empty: mu_charsel_list_default */
    mu_ui_server_list servers;
    mu_charsel_list characters;
    mu_offline_join joins[MU_OFFLINE_JOINS];
    int32_t join_count;
    /* what the network layer would have told the client so far */
    int32_t protocol;           /* 0, 0x14 after the login, 0x33 with the list */
    int32_t server_group, server_slot;   /* the chosen server (-1 none) */
    int32_t logins;             /* accepted logins (no credentials kept) */
} mu_offline_session;

/* Built-in demo data: a synthetic server list and mu_charsel_list_default. */
void mu_offline_session_default(mu_offline_session *s);
/* Loads a session file (see above). root resolves character item paths.
 * Returns 0 or 1 with a message. */
int mu_offline_session_load(mu_offline_session *s, const char *path, const char *root, char *error,
                            size_t error_size);
/* Server list file parser (notice / group / server lines). */
int mu_offline_session_parse_servers(const char *text, mu_ui_server_list *list, char *error, size_t error_size);

/* The four network answers. */
void mu_offline_session_choose_server(mu_offline_session *s, int32_t group, int32_t slot);
int32_t mu_offline_session_login(mu_offline_session *s);          /* any input: returns 0x14 */
int32_t mu_offline_session_character_list(mu_offline_session *s); /* returns 0x33 */
/* The join answer for a character slot: its world and tile (default
 * Lorencia 133,127 facing 0 when the file has no join line). */
mu_offline_join mu_offline_session_join(const mu_offline_session *s, int32_t slot);
/* The list entry of a slot, or NULL. */
const mu_charsel_entry *mu_offline_session_character(const mu_offline_session *s, int32_t slot);

#endif
