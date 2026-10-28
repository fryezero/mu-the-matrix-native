/* SESSION-SKILL-001. Headless and GFx use the same session book. */
#define _POSIX_C_SOURCE 200809L
#include "../world_rt_internal.h"
#include "../../session/mu_session_seed.h"
#include "../../fixture/mu_fixture.h"
#include "../../fixture/skills_demo.h"
#include "../../core/mu_lang.h"
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef struct skills_part { mu_session *session; mu_fixture *fixture; mu_transport *transport; uint32_t tick; int owned; } skills_part;
struct mu_session *mu_world_rt_skill_session(mu_world_rt *a)
{
    skills_part *p = a->part[MU_PART_skills];
    return p ? p->session : NULL;
}
int mu_world_rt_skill_demo_change(mu_world_rt *a,int32_t skill,int forget)
{
    skills_part *p=a->part[MU_PART_skills];
    return p && p->fixture ? mu_skills_demo_change(mu_fixture_behavior_state(p->fixture,"skills"),skill,forget) : 0;
}
static int open_skills(mu_world_rt *a, void *self)
{
    skills_part *p = self;
    p->session = world_rt_characters_session(a);
    if (p->session) {p->fixture=world_rt_characters_fixture(a);return 0;}
    char path[] = "/tmp/mu-skills-XXXXXX", error[512];
    int fd = mkstemp(path); if (fd < 0) return 1;
    FILE *f = fdopen(fd, "w"); if (!f) {close(fd);unlink(path);return 1;}
    fprintf(f, "endpoint game 127.0.0.1:55905\nuse skills\nat 1 skills root %s\nat 1 skills login %d 30\n", a->root, a->walk.hero.class_byte);
    mu_skills_demo_hero(f, a->walk.hero.class_byte, a->map->world,
                        a->walk.hero.tile[0], a->walk.hero.tile[1], a->walk.hero.angle[2]);
    fclose(f);
    mu_fixture_options options = {path, NULL, 20261028};
    p->fixture = mu_fixture_open(&options, error, sizeof error); unlink(path);
    if (!p->fixture) return 1;
    p->owned = 1; p->transport = mu_fixture_transport(p->fixture);
    mu_session_config cfg = {0}; cfg.transport = p->transport; cfg.lang = a->lang;
    mu_fixture_endpoint(p->fixture, "game", &cfg.connect_server);
    mu_session_seed seed = {0}; seed.class_byte = a->walk.hero.class_byte;
    seed.place.world = a->walk.world;
    p->session = mu_session_open_seeded(&cfg, &seed, error, sizeof error);
    if (!p->session) return 1;
    return mu_session_skills_bind(p->session, a->lang, getenv("MU_LANG_DIR"), a->root) != 0;
}
static void tick_skills(mu_world_rt *a, void *self)
{
    skills_part *p=self; if(!p->session)return;
    if(p->owned) {++p->tick;mu_transport_poll(p->transport,p->tick*40);mu_session_pump(p->session,p->tick*40);}
    /* Hero stats remain their domain's context. No local mana spending or regeneration. */
    mu_hero_stats h;mu_session_hero(p->session,&h);
    mu_skill_stats st={.class_byte=h.class_byte,.strength=(uint16_t)h.stats[0],.agility=(uint16_t)h.stats[1],.vitality=(uint16_t)h.stats[2],
                       .energy=(uint16_t)h.stats[3],.command=(uint16_t)h.stats[4],.mana=h.mp,.ag=h.ag};
    mu_session_skills_context(p->session,&st);
    mu_sim sim=mu_session_sim_begin(p->session);mu_session_step(p->session,MU_DOMAIN_SKILLS,&sim);mu_session_sim_end(p->session,&sim);
    if(p->owned)mu_transport_flush(p->transport);
    (void)a;
}
static void close_skills(mu_world_rt *a,void *self)
{
    (void)a;skills_part *p=self;
    if(p->owned) {mu_session_close(p->session);mu_transport_free(p->transport);mu_fixture_close(p->fixture);}
    memset(p,0,sizeof *p);
}
static void report_skills(const mu_world_rt *a,const void *self)
{
    (void)a;const skills_part *p=self;const mu_skill_hero *h=mu_skill_book_hero(mu_session_skills(p->session));
    printf("{\"session_skills\":{\"learned\":%d,\"selected\":%d,\"mana\":%d,\"ag\":%d}}\n",
           h?h->count:0,mu_skill_book_selected(mu_session_skills(p->session)),h?h->mana:0,h?h->ag:0);
}
const mu_world_part_ops mu_part_skills = {
    .name = "skills",
    .state_size = sizeof(skills_part),
    .open = open_skills,
    .tick = tick_skills,
    .close = close_skills,
    .report_summary = report_skills,
};
