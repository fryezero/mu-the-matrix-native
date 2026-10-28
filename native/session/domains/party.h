/* Session-owned display-only party records. No character stats are written. */
#ifndef MU_SESSION_PARTY_H
#define MU_SESSION_PARTY_H
#include "../../../reconstructed/social/social.h"
typedef struct mu_session mu_session;
typedef struct mu_party_view
{
    const mu_party *members;
    int32_t pending, request_key;
    uint32_t invitations;
} mu_party_view;
mu_party_view mu_session_party(const mu_session *s);
#endif
