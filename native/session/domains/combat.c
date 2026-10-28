/* SESSION-COMBAT-001. Plaintext fixture only; keyed wire construction remains separate. */
#include "../session_internal.h"
#include "../../../reconstructed/movement/client_movement.h"
#include <string.h>
#ifdef MU_SESSION_SEED
#include "../mu_session_seed.h"
#include "../../fixture/mu_fixture.h"
#endif
static uint16_t key_at(const uint8_t *p) { return (uint16_t)((p[0]<<8)|p[1]); }
static void event(mu_session *s,mu_combat_frame_event *e)
{
    ++s->combat.count[e->kind];e->seq=s->combat.next++;s->combat.events[e->seq%MU_COMBAT_HISTORY]=*e;
    mu_session_touch(s,MU_DOMAIN_COMBAT);
}
size_t mu_session_combat_events(const mu_session *s,uint64_t *cursor,mu_combat_frame_event *out,size_t cap,uint32_t *lost)
{
    *lost=0;uint64_t first=s->combat.next>MU_COMBAT_HISTORY?s->combat.next-MU_COMBAT_HISTORY:0;
    if(*cursor<first) {*lost=(uint32_t)(first-*cursor);*cursor=first;}
    size_t n=0;while(*cursor<s->combat.next && n<cap) out[n++]=s->combat.events[(*cursor)++%MU_COMBAT_HISTORY];
    return n;
}
uint64_t mu_session_combat_count(const mu_session *s,unsigned kind) { return kind<5?s->combat.count[kind]:0; }
uint16_t mu_session_combat_hero_key(const mu_session *s) { return s->combat.hero_key; }
/* Temporary 0x20 handoff for the fight fixture. Full ground ownership is SESSION-ITEMS-001. */
mu_apply combat_drop(mu_session *s,const mu_frame *f)
{
    if(f->head!=0xc2 || f->length<5) return MU_APPLY_IGNORED;
    unsigned count=f->bytes[4];
    if(f->length<5+19*count) return MU_APPLY_IGNORED;
    if(count>75) count=75;
    for(unsigned i=0;i<count;++i) {
        mu_combat_frame_event e={.kind=4};memcpy(e.drop,f->bytes+5+i*19,19);event(s,&e);
    }
    return count?MU_APPLY_DONE:MU_APPLY_IGNORED;
}
mu_apply combat_damage(mu_session *s,const mu_frame *f)
{
    if(f->length<24 || f->head!=0xc1) return MU_APPLY_IGNORED;
    uint16_t key=key_at(f->bytes+3)&0x7fff;
    int32_t i=mu_session_character_index(s,key);int hero=key==s->combat.hero_key;
    if(i<0 && !hero) return MU_APPLY_IGNORED;
    uint8_t raw[0x3700]={0};
    mu_combat_frame_event e={.kind=1,.key=key};
    mu_combat_damage_body(f->bytes,f->length,raw,hero?s->hero.attr:NULL,s->combat.hero_key,&e.damage);
    if(i>=0) s->combat.last_damage[i]=(uint16_t)e.damage.amount;
    if(hero) mu_session_touch(s,MU_DOMAIN_HERO);
    event(s,&e);return MU_APPLY_DONE;
}
mu_apply combat_die(mu_session *s,const mu_frame *f)
{
    if(f->length<9 || f->head!=0xc1) return MU_APPLY_IGNORED;
    uint16_t key=key_at(f->bytes+3);int32_t i=mu_session_character_index(s,key);
    if(i<0 && key!=s->combat.hero_key) return MU_APPLY_IGNORED;
    uint8_t raw[0x3700]={0};
    if(i>=0)mu_character_project(&s->characters.records[i],raw,sizeof raw);
    else memcpy(raw,s->hero.record,sizeof s->hero.record);
    mu_combat_die_body(f->bytes,f->length,raw);
    if(i>=0) {
        mu_character_restore(&s->characters.records[i],raw,sizeof raw);
        s->combat.killing_skill[i]=raw[0x2a];s->combat.death_flag[i]=raw[0x325c];
        mu_session_touch(s,MU_DOMAIN_CHARACTERS);
    } else {memcpy(s->hero.record,raw,sizeof s->hero.record);mu_session_touch(s,MU_DOMAIN_HERO);}
    mu_combat_frame_event e={.kind=2,.key=key,.skill=key_at(f->bytes+5)};event(s,&e);return MU_APPLY_DONE;
}
mu_apply combat_action(mu_session *s,const mu_frame *f)
{
    if(f->length<9 || f->head!=0xc1 || (f->bytes[6]!=0x78 && f->bytes[6]!=0x79)) return MU_APPLY_IGNORED;
    uint16_t key=key_at(f->bytes+3),target=key_at(f->bytes+7);int32_t i=mu_session_character_index(s,key);
    if(i<0) return MU_APPLY_IGNORED;
    mu_rp_character *c=&s->characters.records[i];
    int32_t ti=mu_session_character_index(s,target);
    int has_target=ti>=0 || target==s->combat.hero_key;
    int32_t hero_tile[2];float hero_position[3],hero_angle[3];
    mu_session_hero_motion(s,hero_tile,hero_position,hero_angle);
    int32_t tx=ti>=0?s->characters.records[ti].tile[0]:hero_tile[0];
    int32_t ty=ti>=0?s->characters.records[ti].tile[1]:hero_tile[1];
    float angle=has_target?mu_create_angle((float)c->tile[0],(float)c->tile[1],(float)tx,(float)ty):0;
    uint8_t raw[0x3700]={0};mu_character_project(c,raw,sizeof raw);
    mu_combat_action_body(f->bytes,f->length,raw,(int16_t)(ti>=0?ti:-1),has_target,angle);
    mu_character_restore(c,raw,sizeof raw);
    s->combat.attack_time[i]=raw[0x21];s->combat.target_index[i]=(int16_t)ti;
    memcpy(&s->combat.voice[i],raw+0x3324,4);
    mu_session_touch(s,MU_DOMAIN_CHARACTERS);
    mu_combat_frame_event e={.kind=3,.key=key,.target=target};event(s,&e);return MU_APPLY_DONE;
}
static mu_submit send_plain(mu_session *s,uint8_t *b,size_t n,int encrypted)
{
    mu_submit r={MU_SUBMIT_REFUSED,-1};if(!n) return r;
    /* Plain AddData only. Never enter keyed AddData, decode or the crypto wrap here. */
    mu_packet p;mu_packet_begin(&p,b[0],b[2]);mu_packet_add(&p,b+3,n-3,0);
#ifdef MU_SESSION_SEED
    if(!encrypted && mu_fixture_is_transport(s->cfg.transport) && mu_endpoint_is_loopback(&s->cfg.connect_server)) {
        r.status=mu_session_send(s,&p,0)==MU_SEND_OK?MU_SUBMIT_SENT:MU_SUBMIT_NOT_NOW;
        return r;
    }
#endif
    mu_packet_finish(&p);
    mu_journal_frame_out(s->cfg.journal,s->tick,s->now,s->conn_main,p.obj+2,(uint32_t)n,MU_SEND_NEEDS_CRYPTO,encrypted);
    ++s->unsent;
    r.status=MU_SUBMIT_NOT_NOW;
    return r;
}
mu_submit combat_attack(mu_session *s,const mu_intent *in)
{
    uint8_t b[7];size_t n=mu_combat_attack_request(b,in->u.combat_attack.target,in->u.combat_attack.direction,0);
    return send_plain(s,b,n,0);
}
mu_submit combat_cast(mu_session *s,const mu_intent *in)
{
    uint8_t b[7];size_t n=mu_combat_cast_request(b,in->u.combat_cast.x,in->u.combat_cast.y,in->u.combat_cast.skill,in->u.combat_cast.type);
    return send_plain(s,b,n,1);
}
mu_submit combat_move(mu_session *s,const mu_intent *in)
{
    uint8_t b[16];int32_t delay;
    size_t n=mu_combat_move_request(b,s->combat.hero_key,in->u.combat_move.x,in->u.combat_move.y,in->u.combat_move.count,
                                  in->u.combat_move.target_x,in->u.combat_move.target_y,in->u.combat_move.angle,0,&delay);
    return send_plain(s,b,n,0);
}
void mu_dom_combat_init(mu_session *s) { memset(&s->combat,0,sizeof s->combat); }
void mu_dom_combat_free(mu_session *s) { (void)s; }
void mu_dom_combat_step(mu_session *s,const mu_sim *sim) { (void)s;(void)sim; }
void mu_dom_combat_zones(const mu_session *s,mu_audit_zones *z)
{ mu_audit_add(z,"combat",(const uint8_t *)&s->combat,0,sizeof s->combat,MU_ZONE_REPLICATED,"handler outputs"); }
#ifdef MU_SESSION_SEED
void mu_dom_combat_seed(mu_session *s,const struct mu_session_seed *seed) { s->combat.hero_key=(uint16_t)(seed->slot+1); }
#endif
