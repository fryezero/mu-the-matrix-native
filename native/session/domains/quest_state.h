#ifndef MU_QUEST_STATE_H
#define MU_QUEST_STATE_H
#include "quest.h"
typedef struct mu_dom_quest
{
    mu_quest_data data;
    mu_quest_client client;
    int ready, sent, send_failed;
} mu_dom_quest;
#endif
