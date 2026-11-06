#ifndef MU_SKILLS_DEMO_H
#define MU_SKILLS_DEMO_H
#include <stdint.h>
#include <stdio.h>
struct mu_fixture;
void *mu_fixture_behavior_state(struct mu_fixture *, const char *);
/* Dev-tool command into the independent fixture model. Replies remain inbound frames. */
int mu_skills_demo_change(void *state, int32_t skill, int forget);
/* APP-POLISH-005: the offline session's join data for the fixture server (OFFLINE DEMO data, not an
 * account/join packet reconstruction).  skills_file: list/keys lines (mu_skill_demo_load), NULL: the
 * built-in lists; has_stats: the hero's join stats at `level`, else the class start stats at level 1. */
typedef struct mu_skills_demo_join {
    const char *skills_file;
    int has_stats;
    int level, stats[5], points;
} mu_skills_demo_join;

/* The skills fixture's login lines; the demo file is loaded before the login answer. */
static inline void mu_skills_demo_login(FILE *out, const char *root, int cls, const mu_skills_demo_join *join)
{
    fprintf(out, "use skills\nat 1 skills root %s\n", root);
    if (join && join->skills_file && join->skills_file[0])
        fprintf(out, "at 1 skills file %s\n", join->skills_file);
    fprintf(out, "at 1 skills login %d 30\n", cls);
}

/* World tools seed only class/place. Supply the existing progress fixture's
 * baseline stats (or the session's join stats) and full resources as inbound frames,
 * before any skill use.  This is offline demo policy, not an account/join packet reconstruction. */
static inline void mu_skills_demo_hero(FILE *out, int cls, int world, int x, int y, float angle,
                                       const mu_skills_demo_join *join)
{
    int dir = ((int)(angle / 45.0f) % 8 + 8) % 8 + 1;
    fprintf(out, "use progress class=%d latency=0", cls);
    if (join && join->has_stats)
        fprintf(out, " level=%d points=%d str=%d agi=%d vit=%d ene=%d cmd=%d", join->level > 0 ? join->level : 1,
                join->points, join->stats[0], join->stats[1], join->stats[2], join->stats[3], join->stats[4]);
    fprintf(out, "\nat 1 progress join\nat 1 progress respawn map=%d x=%d y=%d dir=%d\n", world, x, y, dir);
}
#endif
