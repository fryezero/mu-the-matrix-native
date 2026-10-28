#include "../session/mu_session.h"
#include "../session/mu_session_seed.h"
#include "../fixture/mu_fixture.h"
#include <stdio.h>

int main(int argc,char **argv)
{
    if(argc!=2)return 2;
    char error[1024]={0};mu_fixture_options o={argv[1],NULL,7};
    mu_fixture *f=mu_fixture_open(&o,error,sizeof error);
    if(!f){fprintf(stderr,"%s\n",error);return 2;}
    mu_transport *t=mu_fixture_transport(f);mu_session_config cfg={0};
    mu_fixture_endpoint(f,"game",&cfg.connect_server);cfg.transport=t;
    cfg.build=&MU_PINNED_BUILD;cfg.proof=mu_proof_not_required();
    mu_session_seed seed={0};seed.place.world=0;seed.place.tile[0]=120;seed.place.tile[1]=120;
    mu_session *s=mu_session_open_seeded(&cfg,&seed,error,sizeof error);
    if(!s)return 2;
    for(unsigned tick=1;tick<=200;++tick){
        mu_transport_poll(t,tick*40);mu_session_pump(s,tick*40);
        mu_sim sim=mu_session_sim_begin(s);mu_session_sim_end(s,&sim);
    }
    mu_characters_view v=mu_session_characters(s);
    for(int i=0;i<v.capacity;++i)if(v.used[i]) {
        const mu_rp_character *c=&v.records[i];
        printf("{\"key\":%d,\"dead\":%u,\"movement\":%u,\"angle\":%.3f,\"x\":%.1f,\"y\":%.1f}\n",
            c->key,c->dead,c->movement,c->angle[2],c->position[0],c->position[1]);
    }
    uint64_t cursor=0;uint32_t lost=0;mu_combat_frame_event events[MU_COMBAT_HISTORY];
    size_t count=mu_session_combat_events(s,&cursor,events,MU_COMBAT_HISTORY,&lost);
    printf("{\"events\":%zu,\"lost\":%u,\"cursor\":%llu,\"damage\":%llu,\"die\":%llu,\"action\":%llu,\"first_seq\":%llu}\n",
        count,lost,(unsigned long long)cursor,(unsigned long long)mu_session_combat_count(s,1),
        (unsigned long long)mu_session_combat_count(s,2),(unsigned long long)mu_session_combat_count(s,3),
        (unsigned long long)(count?events[0].seq:0));
    mu_session_close(s);mu_transport_free(t);mu_fixture_close(f);return 0;
}
