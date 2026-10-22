/* Offline social session. Server policy/demo answers are separate from reconstructed receive logic. */
#ifndef MU_SOCIAL_SESSION_H
#define MU_SOCIAL_SESSION_H
#include "../../reconstructed/social/social.h"
struct mu_world_players;
typedef struct mu_social_session {
    mu_party party;
    mu_trade trade;
    mu_social_friends friends;
    struct mu_world_players *players;
    char hero[11], target[11], pending_name[11], last[192];
    int32_t world, x, y, server, pending, incoming, request_key, steps, revision, result_due;
    int32_t inventory[2], received_items, completed, declined;
    int32_t vitals[9][2]; /* DEMO server HP/MP percentages, hero then --players */
    int64_t zen;
    int (*trade_commit)(void *user); /* OFFLINE host inventory transaction, before balances/results change. */
    void *trade_user;
} mu_social_session;
void mu_social_init(mu_social_session *s, const char *hero, struct mu_world_players *players);
void mu_social_step(mu_social_session *s, int32_t world, int32_t x, int32_t y);
/* target/party/trade, incoming-party/incoming-trade, accept/decline, leave/kick,
 * offer/remove/zen/ok/partner-ok/cancel, friend/unfriend, all OFFLINE DEMO requests. */
int mu_social_action(mu_social_session *s, const char *verb, const char *arg);
#endif
