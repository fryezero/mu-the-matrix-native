#define _POSIX_C_SOURCE 200809L
#include "../session/mu_session.h"
#include "../session/mu_session_seed.h"
#include "../fixture/mu_fixture.h"
#include "layout_CHARACTER.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>

static int projection(void)
{
    uint8_t raw[MU_LAYOUT_CHARACTER_SIZE],again[MU_LAYOUT_CHARACTER_SIZE];
    mu_rp_character c,d;
    unsigned fields=0;
    for(unsigned seed=1;seed<=100;++seed) {
        memset(&c,0,sizeof c);memset(&d,0,sizeof d);
        uint8_t *b=(uint8_t *)&c;
        for(size_t i=0;i<sizeof c;++i)b[i]=(uint8_t)(i*31+seed);
        c.skill=(int16_t)c.skill;
        memset(raw,0xa5,sizeof raw);memset(again,0xa5,sizeof again);
        if(!mu_character_project(&c,raw,sizeof raw)||!mu_character_restore(&d,raw,sizeof raw))return 1;
#define MU_BIND(field, member, size) \
        if(memcmp(&c.member,&d.member,size))return 2; else if(seed==1)++fields;
#include "../session/domains/characters_projection.def"
#undef MU_BIND
        if(!mu_character_project(&d,again,sizeof again)||memcmp(raw,again,sizeof raw))return 4;
        if(raw[0x100]!=0xa5||raw[0x144]!=0xa5)return 5;
        if(mu_character_project(&c,raw,sizeof raw-1)||mu_character_restore(&d,raw,sizeof raw-1))return 6;
    }
    printf("{\"projection_cases\":100,\"fields\":%u}\n",fields);
    return 0;
}

int main(int argc,char **argv)
{
    if(argc==2&&!strcmp(argv[1],"projection"))return projection();
    if(argc<2)return 2;
    char error[1024]={0};mu_fixture_options o={argv[1],NULL,7};
    mu_fixture *f=mu_fixture_open(&o,error,sizeof error);
    if(!f){fprintf(stderr,"%s\n",error);return 2;}
    mu_transport *t=mu_fixture_transport(f);mu_session_config cfg={0};
    mu_fixture_endpoint(f,"game",&cfg.connect_server);cfg.transport=t;
    cfg.build=&MU_PINNED_BUILD;cfg.proof=mu_proof_not_required();
    mu_session_seed seed={0};seed.place.world=0;
    mu_session *s=mu_session_open_seeded(&cfg,&seed,error,sizeof error);
    if(!s)return 2;
    int capacity_mode = argc > 2 && !strcmp(argv[2], "capacity");
    unsigned limit = capacity_mode ? 420u : 20u;
    for(unsigned tick=1;tick<=limit;++tick){
        mu_transport_poll(t,tick*40);mu_session_pump(s,tick*40);
        mu_characters_view v=mu_session_characters(s);
        unsigned count=0;
        for(int i=0;i<v.capacity;++i){
            if(!v.used[i])continue;
            ++count;const mu_rp_character *c=&v.records[i];
            if (capacity_mode) continue;
            if (c->kind == 2) printf("{\"monster_tick\":%u,\"key\":%d,\"model\":%d,\"server_class\":%d,\"level\":%u,\"max_hp\":%u,\"hp\":%u}\n", tick,c->key,c->model,c->class_word,c->level,c->max_hp,c->hp);
            printf("{\"tick\":%u,\"slot\":%d,\"key\":%d,\"class\":%u,\"generation\":%u,\"equipment_revision\":%u,\"helper\":%u,\"helper_slot\":%d,\"x\":%d,\"y\":%d,\"dead\":%u,\"store\":%u}\n",
                tick,i,c->key,c->class_byte,v.generation[i],v.equipment_revision[i],c->helper,c->slots[10].type,c->tile[0],c->tile[1],c->dead,v.store_open[i]);
        }
        if (!capacity_mode) printf("{\"tick\":%u,\"count\":%u,\"rev\":%u}\n",tick,count,mu_session_rev(s,MU_DOMAIN_CHARACTERS));
        if (capacity_mode && tick == 400) {
            mu_sim sim = mu_session_sim_begin(s); mu_session_sim_end(s, &sim);
        }
        if (capacity_mode && tick == limit) {
            int32_t slot = mu_session_character_index(s, 1000);
            printf("{\"capacity\":%u,\"overflow_ignored\":%d,\"reused_slot\":%d,\"generation\":%u}\n",
                count,mu_session_character_index(s,401)==-1,slot,slot>=0?v.generation[slot]:0);
        }
        if(argc>2&&!strcmp(argv[2],"bad-lease")&&count){
            mu_sim sim=mu_session_sim_begin(s);sim.characters[0].class_byte^=1;mu_session_sim_end(s,&sim);
        }
    }
    mu_session_close(s);mu_transport_free(t);mu_fixture_close(f);return 0;
}
