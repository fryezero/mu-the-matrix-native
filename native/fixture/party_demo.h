/* Offline facade over party fixture. Only its model produces membership/bar
 * frames. */
#ifndef MU_PARTY_DEMO_H
#define MU_PARTY_DEMO_H
#include <stddef.h>
#include <stdint.h>
struct mu_social_session;
struct mu_world_players;
int mu_party_demo_open(struct mu_social_session *s);
void mu_party_demo_close(struct mu_social_session *s);
void mu_party_demo_step(struct mu_social_session *s);
int mu_party_demo_action(struct mu_social_session *s, const char *verb, const char *arg);
int mu_party_demo_receive(struct mu_social_session *s, const uint8_t *b, size_t n);
#endif
