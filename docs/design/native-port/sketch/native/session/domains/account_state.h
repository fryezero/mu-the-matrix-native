/* domains/account_state.h (sketch, PRIVATE): connect server, login, character list.
 * Moves here from client/offline-session.* (whose demo rules become fixture/behaviors/account.c). */
#ifndef MU_DOM_ACCOUNT_STATE_H
#define MU_DOM_ACCOUNT_STATE_H
#include "../../../reconstructed/ui/ui_server.h"
#include "../../core/mu_charsel.h"
#include "../../net/mu_transport.h"

typedef struct mu_dom_account {
    mu_ui_server_list servers;           /* F4 06, parsed by the client's list parser (0x010721d4) */
    int32_t group, slot;                 /* CHOOSE_SERVER */
    mu_endpoint game_server;             /* F4 03 ReceiveServerConnect */
    int32_t login_result;                /* F1 01 result byte */
    mu_charsel_list characters;          /* the character-list answer (CreateHero per entry) */
    int32_t created_today, create_limit; /* from the list packet (the client checks the daily limit itself) */
    int32_t selected_slot;
} mu_dom_account;
#endif
