/* SESSION-COMBAT-001. Plaintext fixture only; keyed wire construction remains separate. */
#include "../session_internal.h"
#include <string.h>
#ifdef MU_SESSION_SEED
#include "../mu_session_seed.h"
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
    unsigned count=f->bytes[4]<75?f->bytes[4]:75;
    if(f->length<5+19*count) return MU_APPLY_IGNORED;
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
    uint8_t raw[0x3700]={0};mu_combat_die_body(f->bytes,f->length,raw);
    if(i>=0) {
        mu_rp_character *c=&s->characters.records[i];c->dead=raw[0x23];c->movement=raw[0x38];
        c->field_3230=0;c->transformed=0;s->combat.killing_skill[i]=raw[0x2a];
        mu_session_touch(s,MU_DOMAIN_CHARACTERS);
    } else {s->hero.record[0x23]=1;s->hero.record[0x38]=0;mu_session_touch(s,MU_DOMAIN_HERO);}
    mu_combat_frame_event e={.kind=2,.key=key,.skill=key_at(f->bytes+5)};event(s,&e);return MU_APPLY_DONE;
}
mu_apply combat_action(mu_session *s,const mu_frame *f)
{
    if(f->length<9 || f->head!=0xc1 || (f->bytes[6]!=0x78 && f->bytes[6]!=0x79)) return MU_APPLY_IGNORED;
    uint16_t key=key_at(f->bytes+3),target=key_at(f->bytes+7);int32_t i=mu_session_character_index(s,key);
    if(i<0) return MU_APPLY_IGNORED;
    mu_rp_character *c=&s->characters.records[i];c->movement=0;c->angle[2]=((float)f->bytes[5]-1)*45;
    c->position[0]=(float)c->tile[0]*100+50;c->position[1]=(float)c->tile[1]*100+50;
    /* Target-facing geometry is supplied by the attached presentation; absent targets retain packet direction. */
    mu_session_touch(s,MU_DOMAIN_CHARACTERS);
    mu_combat_frame_event e={.kind=3,.key=key,.target=target};event(s,&e);return MU_APPLY_DONE;
}
static mu_submit send_plain(mu_session *s,uint8_t *b,size_t n,int encrypted)
{
    mu_submit r={MU_SUBMIT_REFUSED,-1};if(!n) return r;
    /* Only seed/tool builds can submit requests to loopback using the existing verified AddData. Product must not
     * send them as real wire bytes, since AddData's keyed layer is explicitly out of this lane. */
#ifndef MU_SESSION_SEED
    (void)s;(void)b;(void)encrypted;return r;
#else
    if(!mu_endpoint_is_loopback(&s->cfg.connect_server)) return r;
    mu_packet p;mu_packet_begin(&p,b[0],b[2]);mu_packet_add(&p,b+3,n-3,1);
    r.status=mu_session_send(s,&p,encrypted)==MU_SEND_OK?MU_SUBMIT_SENT:MU_SUBMIT_NOT_NOW;return r;
#endif
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
