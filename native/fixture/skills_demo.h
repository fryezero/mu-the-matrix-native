#ifndef MU_SKILLS_DEMO_H
#define MU_SKILLS_DEMO_H
#include <stdint.h>
#include <stdio.h>
struct mu_fixture;
void *mu_fixture_behavior_state(struct mu_fixture *, const char *);
/* Dev-tool command into the independent fixture model. Replies remain inbound frames. */
int mu_skills_demo_change(void *state, int32_t skill, int forget);
/* World tools seed only class/place. Supply the existing progress fixture's
 * baseline stats and full resources as inbound frames, before any skill use.
 * This is offline demo policy, not an account/join packet reconstruction. */
static inline void mu_skills_demo_hero(FILE *out, int cls, int world, int x, int y, float angle)
{
    int dir = ((int)(angle / 45.0f) % 8 + 8) % 8 + 1;
    fprintf(out, "use progress class=%d latency=0\nat 1 progress join\n"
                 "at 1 progress respawn map=%d x=%d y=%d dir=%d\n", cls, world, x, y, dir);
}
#endif
