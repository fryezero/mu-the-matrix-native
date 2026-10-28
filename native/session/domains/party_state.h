#ifndef MU_PARTY_STATE_H
#define MU_PARTY_STATE_H
#include "party.h"
typedef struct mu_dom_party
{
    mu_party members;
    int32_t pending, request_key;
    uint32_t invitations;
} mu_dom_party;
#endif
