#include "../session/mu_session_seed.h"
#include "../fixture/mu_fixture.h"
#include "../core/mu_lang.h"
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv)
{
    if(argc<3)return 2;
    char error[512];mu_fixture_options options={argv[1],NULL,20261028};
    mu_fixture *fx=mu_fixture_open(&options,error,sizeof error);if(!fx)return 3;
    mu_transport *transport=mu_fixture_transport(fx);mu_session_config cfg={0};cfg.transport=transport;
    mu_fixture_endpoint(fx,"game",&cfg.connect_server);mu_session_seed seed={0};seed.class_byte=129;
    mu_session *s=mu_session_open_seeded(&cfg,&seed,error,sizeof error);if(!s)return 4;
    mu_lang *lang=mu_lang_load(argv[2]);mu_session_skills_bind(s,lang,argv[2],argv[2]);
    mu_skill_book *book=mu_session_skills(s);
    mu_world_port port={0};port.world=0;mu_session_attach_world(s,&port);
    for(uint32_t tick=1;tick<=12;++tick) {
        mu_transport_poll(transport,tick*40);mu_session_pump(s,tick*40);
        if(tick==3) {mu_session_detach_world(s);if(mu_session_attached_world(s,NULL))return 5;}
        if(tick==4 && argc>3 && !strcmp(argv[3],"master")) {
            mu_intent in={.kind=MU_INTENT_SKILL_MASTER_LEARN};in.u.skill_master_learn.skill=330;
            mu_session_submit(s,&in);
        }
        if(tick==7)mu_session_skills_bind(s,lang,argv[2],argv[2]);
        mu_sim sim=mu_session_sim_begin(s);
        mu_session_step(s,MU_DOMAIN_SKILLS,&sim);
        if(argc>3 && !strcmp(argv[3],"poison"))((mu_skill_hero *)mu_skill_book_hero(book))->skills[0]^=1;
        mu_session_sim_end(s,&sim);
        if(tick==2 && mu_skill_book_master_env(book)->points!=100)return 6;
        mu_transport_flush(transport);
    }
    mu_skill_stats context={.class_byte=129};mu_session_skills_context(s,&context);
    const mu_skill_hero *h=mu_skill_book_hero(book);mu_session_status st;mu_session_status_get(s,&st);
    printf("{\"same\":%d,\"count\":%d,\"first\":%u,\"mana\":%d,\"ag\":%d,\"unbound\":%u,\"key\":%d,\"master\":%u,\"master_points\":%d,\"points\":%d}\n",
           book==mu_session_skills(s),h->count,h->skills[0],h->mana,h->ag,st.unhandled,
           mu_skill_book_hotkeys(book)->slots[1],mu_master_level(mu_skill_book_master(book),330),mu_skill_book_master_env(book)->points,mu_skill_tree4_window(mu_session_skills_tree4(s))->points);
    mu_session_close(s);mu_lang_free(lang);mu_transport_free(transport);mu_fixture_close(fx);return 0;
}
