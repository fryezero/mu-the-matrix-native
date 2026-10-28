/* SESSION-VIEWPORT-001. One MoveCharacters walk over leased session records.
 * The --players compatibility option opens a loopback fixture, never a second
 * client-side feed. VIEWPORT-MONSTER-001 shares this feed and loop with actors. */
#define _POSIX_C_SOURCE 200809L
#include "../world_rt_internal.h"
#include "../../session/mu_session.h"
#include "../../core/mu_session_audio.h"
#include "../../core/mu_lang.h"
#include "../../session/mu_session_seed.h"
#include "../../fixture/mu_fixture.h"
#include "../../fixture/characters_demo.h"
#include "../../fixture/monsters_demo.h"
#include "../../fixture/combat_demo.h"
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
    mu_world_players services;
    mu_cue_cursor audio_cursor;
    uint32_t audio_rng;
} characters_part;

void world_rt_actors_sync(mu_world_rt *a);

static void hero_motion(void *context,int32_t tile[2],float position[3],float angle[3])
{
    mu_world_players *p=context;const mu_hero *h=&p->walk->hero;
    memcpy(tile,h->tile,sizeof h->tile);memcpy(position,h->position,sizeof h->position);
    memcpy(angle,h->angle,sizeof h->angle);
}

static void place_hero(void *context,const mu_place *place)
{
    mu_world_players *p=context;mu_walk *w=p->walk;
    mu_walk_stop(w);
    memcpy(w->hero.tile,place->tile,sizeof w->hero.tile);
    w->hero.position[0]=(float)place->tile[0]*100+50;
    w->hero.position[1]=(float)place->tile[1]*100+50;
    w->hero.position[2]=mu_request_terrain_height(p->map->height,p->map->attributes,p->map->water_height,
        6,w->hero.position[0],w->hero.position[1]);
    w->hero.angle[2]=place->angle;
}

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
    if (a->actors.session) {
        p->session = a->actors.session; p->fixture = a->actors.fixture;
        p->transport = a->actors.transport; p->tick = 1;
        goto attach;
    }
    if(!a->players)return 0;
    char path[]="/tmp/mu-characters-XXXXXX";
    int fd=mkstemp(path);
    if(fd<0)return 1;
    FILE *file=fdopen(fd,"w");
    if(!file) {close(fd);unlink(path);return 1;}
    fprintf(file,"endpoint game 127.0.0.1:55902\nuse characters x=%d y=%d file=%s\n",
            a->walk.hero.tile[0],a->walk.hero.tile[1],a->players_file);
    fprintf(file,"use skills\nat 1 skills root %s\nat 1 skills login %d 30\n",a->root,a->walk.hero.class_byte);
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
    seed.class_byte=a->walk.hero.class_byte;
    seed.place.world=a->map->world;
    seed.place.tile[0]=a->walk.hero.tile[0];seed.place.tile[1]=a->walk.hero.tile[1];
    p->session=mu_session_open_seeded(&cfg,&seed,error,sizeof error);
    if(!p->session) {fprintf(stderr,"characters: %s\n",error);return 1;}
    mu_session_skills_bind(p->session,a->lang,getenv("MU_LANG_DIR"),a->root);
attach:
    p->audio_rng = 0x41554432u;
    p->services.map = a->map; p->services.walk = &a->walk;
    mu_world_port port;
    mu_world_players_port(a->players ? a->players : &p->services,&port);
    port.hero_motion=hero_motion;port.place_hero=place_hero;
    mu_session_detach_world(p->session);
    mu_session_attach_world(p->session,&port);
    if (a->players) {
    a->players->session=p->session;
    a->players->record_action=record_action;
    a->players->record_context=p;
    }
    p->demo=mu_fixture_behavior_state(p->fixture,"characters");
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
    if (p->session && a->actors.session == p->session) {
        a->actors.session = NULL; a->actors.transport = NULL; a->actors.fixture = NULL;
    }
    memset(p, 0, sizeof *p);
}

struct mu_fixture *world_rt_characters_fixture(mu_world_rt *a)
{
    characters_part *p=a->part[MU_PART_characters];return p?p->fixture:NULL;
}

mu_session *world_rt_characters_session(mu_world_rt *a)
{
    characters_part *p = a->part[MU_PART_characters];
    return p ? p->session : NULL;
}

void world_rt_characters_audio_drain(mu_world_rt *a)
{
    characters_part *p = a->part[MU_PART_characters];
    if (p) mu_session_audio_drain(p->session, &p->audio_cursor, a->has_sound ? a->sound.host : NULL);
}

static void characters_tick(mu_world_rt *a, void *self)
{
    characters_part *p=self;
    if(!p->session)return;
    /* Preserve combat's presentation sink through the single motion lease. */
    if (a->combat && a->has_actors) {
        mu_sim old = mu_session_sim_begin(p->session);
        for (int32_t k = 0; k < a->actors.count; ++k) {
            const mu_world_actor *actor = &a->actors.list[k]; int32_t i = actor->session_slot;
            if (!old.used[i] || old.characters[i].key != actor->session_key) continue;
            memcpy(old.characters[i].position, actor->position, sizeof actor->position);
            memcpy(old.characters[i].angle, actor->angle, sizeof actor->angle);
            memcpy(old.characters[i].tile, actor->tile, sizeof actor->tile);
            old.characters[i].movement = actor->moving;
        }
        mu_session_sim_end(p->session, &old);
    }
    if(p->tick && a->players)mu_characters_demo_observe(p->demo,a->players);
    if(a->has_actors) mu_monsters_demo_observe(mu_fixture_behavior_state(p->fixture,"monsters"), &a->actors);
    if(a->has_actors)mu_combat_demo_observe(mu_fixture_behavior_state(p->fixture,"combat"),&a->actors,a->walk.hero.tile[0],a->walk.hero.tile[1]);
    mu_transport_flush(p->transport);
    mu_transport_poll(p->transport,++p->tick*40u);
    mu_session_pump(p->session,p->tick*40u);
    world_rt_actors_sync(a);
    mu_characters_view view=mu_session_characters(p->session);
    if(a->players) mu_world_players_sync(a->players,&view);
    mu_sim sim=mu_session_sim_begin(p->session);
    if(a->players) a->players->leased_records=sim.characters;
    for(int32_t i=0;i<sim.character_count;++i) {
        if(!sim.used[i])continue;
        for(int32_t k=0;a->has_actors && k<a->actors.count;++k)
            if(a->actors.list[k].session_slot==i && a->actors.list[k].session_key==sim.characters[i].key) {
                mu_world_actor *actor = &a->actors.list[k];
                mu_world_actors_step_one(&a->actors,k,&sim.characters[i]);
                if (sim.characters[i].live) {
                    int32_t model = actor->actor.spec.model_index;
                    int32_t random = 0;
                    if (model == 0xa0b || model == 0xa06) {
                        /* Audio-only MSVC rand stream. Never consume the visual RNG. */
                        p->audio_rng = p->audio_rng * 214013u + 2531011u;
                        random = (int32_t)((p->audio_rng >> 16) & 0x7fffu);
                    }
                    float frame = actor->player ? mu_model_frame(&actor->player->player) : mu_actor_frame(&actor->actor);
                    mu_session_npc_voice(p->session, model, random, sim.characters[i].action, frame, -1);
                }
                break;
            }
        for(int32_t k=0;a->players && k<a->players->count;++k)
            if(a->players->list[k].key==sim.characters[i].key) {
                mu_world_players_step_one(a->players,k,&sim.characters[i]);break;
            }
    }
    if(a->players) a->players->leased_records=NULL;
    mu_session_sim_end(p->session,&sim);
    world_rt_characters_audio_drain(a);
    if(a->players) ++a->players->steps;
    if(a->has_actors) ++a->actors.steps;
}

const mu_world_part_ops mu_part_characters = {
    .name = "characters",
    .state_size = sizeof(characters_part),
    .open = characters_open,
    .close = characters_close,
    .tick = characters_tick,
};
