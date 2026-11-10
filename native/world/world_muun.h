#ifndef MU_WORLD_MUUN_H
#define MU_WORLD_MUUN_H
#include <stdio.h>
struct mu_world_rt;
struct mu_world_draw;
typedef struct mu_world_muun mu_world_muun;
/* Opt-in authored hero companion only (MU_MUUN_FIXTURE), with its own model/effect scene. */
int mu_world_muun_open(struct mu_world_rt *rt, mu_world_muun **out);
void mu_world_muun_close(mu_world_muun *m);
void mu_world_muun_tick(struct mu_world_rt *rt, mu_world_muun *m);
void mu_world_muun_soft(struct mu_world_rt *rt, mu_world_muun *m, struct mu_world_draw *draw);
void mu_world_muun_report(const mu_world_muun *m, FILE *out);
#ifndef MU_WORLD_NO_GL
void mu_world_muun_gl(struct mu_world_rt *rt, mu_world_muun *m, struct mu_world_draw *draw);
void mu_world_muun_gl_teardown(mu_world_muun *m);
#endif
#endif
