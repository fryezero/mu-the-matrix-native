#ifndef MU_SKILLS_DEMO_H
#define MU_SKILLS_DEMO_H
#include <stdint.h>
struct mu_fixture;
void *mu_fixture_behavior_state(struct mu_fixture *, const char *);
/* Dev-tool command into the independent fixture model. Replies remain inbound frames. */
int mu_skills_demo_change(void *state, int32_t skill, int forget);
#endif
