/* Synthetic choreography only. No session record writes. */
#ifndef MU_CHARACTERS_DEMO_H
#define MU_CHARACTERS_DEMO_H
#include "../core/mu_world_players.h"
typedef struct mu_fixture mu_fixture;
int mu_characters_parse_player(mu_world_player_spec *s, char *line, int number, char *error, size_t cap);
/* The fixture observes presentation motion to retain the old demo's arrival/range
 * choreography. Every authoritative answer still crosses the loopback as a frame. */
void mu_characters_demo_observe(void *self, const mu_world_players *players);
void *mu_fixture_behavior_state(mu_fixture *fixture, const char *name);
#endif
