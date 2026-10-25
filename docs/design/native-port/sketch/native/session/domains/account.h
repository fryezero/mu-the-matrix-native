/* domains/account.h (sketch, PUBLIC) */
#ifndef MU_DOM_ACCOUNT_H
#define MU_DOM_ACCOUNT_H
#include "../../../reconstructed/ui/ui_server.h"
#include "../../core/mu_charsel.h"
typedef struct mu_session mu_session;

const mu_ui_server_list *mu_session_servers(const mu_session *s);      /* valid from MU_PHASE_SERVER_LIST */
const mu_charsel_list *mu_session_characters(const mu_session *s);     /* valid from MU_PHASE_CHARACTERS */
const mu_charsel_entry *mu_session_character(const mu_session *s, int32_t slot);   /* NULL: empty slot */
#endif
