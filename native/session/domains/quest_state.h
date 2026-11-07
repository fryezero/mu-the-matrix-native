#ifndef MU_QUEST_STATE_H
#define MU_QUEST_STATE_H
#include "quest.h"
typedef struct mu_dom_quest
{
    mu_quest_data data;
    mu_quest_client client;
    int ready, sent, send_failed;
    /* REGRESS-001: seed builds only, see mu_session_quest_offline_local; NULL: the lane is off */
    int (*in_process)(const struct mu_transport *t);
} mu_dom_quest;
#endif
