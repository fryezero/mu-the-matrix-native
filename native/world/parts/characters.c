/* SESSION-VIEWPORT-001. One MoveCharacters walk over leased session records.
 * The --players compatibility option opens a loopback fixture, never a second
 * client-side feed. Monsters retain their separate lane until VIEWPORT-MONSTER. */
#define _POSIX_C_SOURCE 200809L
#include "../world_rt_internal.h"
#include "../../session/mu_session.h"
#include "../../session/mu_session_seed.h"
#include "../../fixture/mu_fixture.h"
#include "../../fixture/characters_demo.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef struct characters_part {
    mu_session *session;
    mu_fixture *fixture;
    mu_transport *transport;
    void *demo;
    uint32_t tick;
} characters_part;

static void record_action(void *context, int32_t slot, uint16_t action, uint16_t prior)
{
    characters_part *p = context;
    if (slot < 0 || slot >= MU_CHARACTERS_MAX) return;
    mu_sim sim = mu_session_sim_begin(p->session);
    if (sim.used[slot]) {
        sim.characters[slot].action = action;
        sim.characters[slot].prior_action = prior;
    }
    mu_session_sim_end(p->session, &sim);
}

static int characters_open(mu_world_rt *a, void *self)
{
    characters_part *p=self;
    if(!a->players)return 0;
    char path[]="/tmp/mu-characters-XXXXXX";
    int fd=mkstemp(path);
    if(fd<0)return 1;
    FILE *file=fdopen(fd,"w");
    if(!file) {close(fd);unlink(path);return 1;}
    fprintf(file,"endpoint game 127.0.0.1:55902\nuse characters x=%d y=%d file=%s\n",
            a->walk.hero.tile[0],a->walk.hero.tile[1],a->players_file);
    fclose(file);
    mu_fixture_options options={path,NULL,0x9a7e2026u};
    char error[1024]={0};
    p->fixture=mu_fixture_open(&options,error,sizeof error);
    unlink(path);
    if(!p->fixture) {fprintf(stderr,"characters: %s\n",error);return 1;}
    p->transport=mu_fixture_transport(p->fixture);
    mu_session_config cfg={0};
    mu_fixture_endpoint(p->fixture,"game",&cfg.connect_server);
    cfg.transport=p->transport;cfg.build=&MU_PINNED_BUILD;cfg.proof=mu_proof_not_required();
    mu_session_seed seed={0};
    seed.place.world=a->map->world;
    seed.place.tile[0]=a->walk.hero.tile[0];seed.place.tile[1]=a->walk.hero.tile[1];
    p->session=mu_session_open_seeded(&cfg,&seed,error,sizeof error);
    if(!p->session) {fprintf(stderr,"characters: %s\n",error);return 1;}
    mu_world_port port;
    mu_world_players_port(a->players,&port);
    mu_session_attach_world(p->session,&port);
    a->players->session=p->session;
    a->players->record_action=record_action;
    a->players->record_context=p;
    p->demo=mu_fixture_behavior_instance(p->fixture,"characters");
    return 0;
}

static void characters_close(mu_world_rt *a, void *self)
{
    if (a->players) {
        a->players->session=NULL;
        a->players->record_action=NULL;
        a->players->record_context=NULL;
    }
    characters_part *p=self;
    if(p->session) {mu_session_detach_world(p->session);mu_session_close(p->session);}
    if(p->transport)mu_transport_free(p->transport);
    if(p->fixture)mu_fixture_close(p->fixture);
    memset(p, 0, sizeof *p);
}

static void characters_tick(mu_world_rt *a, void *self)
{
    characters_part *p=self;
    if(!p->session)return;
    if(p->tick)mu_characters_demo_observe(p->demo,a->players);
    mu_transport_poll(p->transport,++p->tick*40u);
    mu_session_pump(p->session,p->tick*40u);
    mu_characters_view view=mu_session_characters(p->session);
    mu_world_players_sync(a->players,&view);
    mu_sim sim=mu_session_sim_begin(p->session);
    a->players->leased_records=sim.characters;
    for(int32_t i=0;i<sim.character_count;++i) {
        if(!sim.used[i])continue;
        for(int32_t k=0;k<a->players->count;++k)
            if(a->players->list[k].key==sim.characters[i].key) {
                mu_world_players_step_one(a->players,k,&sim.characters[i]);break;
            }
    }
    a->players->leased_records=NULL;
    mu_session_sim_end(p->session,&sim);
    ++a->players->steps;
}

const mu_world_part_ops mu_part_characters = {
    .name = "characters",
    .state_size = sizeof(characters_part),
    .open = characters_open,
    .close = characters_close,
    .tick = characters_tick,
};
