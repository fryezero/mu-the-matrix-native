/* SESSION-SKILL-001. Reconstructed skill bodies are unchanged. */
#include "../session_internal.h"
#include "skills_wire.h"
#ifdef MU_SESSION_SEED
#include "../mu_session_seed.h"
#endif
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/* Window effects survive world detachment as ordered, chunked cues, like the quest domain. */
static void window_cue(mu_session *s,const char *movie,const char *method,const char *args)
{
    size_t n=strlen(args),at=0;
    do {
        mu_cue c={.kind=MU_CUE_WINDOW};c.u.window.verb=MU_WINDOW_INVOKE;
        snprintf(c.u.window.movie,sizeof c.u.window.movie,"%s",movie);
        snprintf(c.u.window.method,sizeof c.u.window.method,"%s",method);
        size_t take=n-at;if(take>=sizeof c.u.window.json)take=sizeof c.u.window.json-1;
        c.u.window.args[1]=at==0;memcpy(c.u.window.json,args+at,take);at+=take;c.u.window.args[0]=at<n;
        mu_session_cue(s,&c);
    }while(at<n);
}
static const char *skill_text(void *u,int32_t id) {return mu_session_global_text(u,id);}
static void master_invoke(void *u,const char *name,const char *args) {window_cue(u,"skills-master",name,args);}
static void tree_invoke(void *u,const char *name,const char *args) {window_cue(u,"skills-fourth",name,args);}
static void master_message(void *u,int owner,const char *args) {(void)owner;window_cue(u,"skills-master","message",args);}
static void tree_message(void *u,const char *args) {window_cue(u,"skills-fourth","message",args);}
static void master_confirm(void *u,int id,const char *args) {(void)id;window_cue(u,"skills-master","confirm",args);}
static void tree_confirm(void *u,int id,const char *args) {(void)id;window_cue(u,"skills-fourth","confirm",args);}

mu_skill_book *mu_session_skills(const mu_session *s) { return s ? s->skills.book : NULL; }
mu_skill_tree4 *mu_session_skills_tree4(const mu_session *s) { return s ? s->skills.tree4 : NULL; }
int mu_session_skills_last_cast(const mu_session *s) { return s ? s->skills.last_cast : MU_SKILL_CAST_NONE; }
int mu_session_skills_bind(mu_session *s, const struct mu_lang *lang, const char *dir, const char *root)
{
    if (!s) return -1;
    if (s->skills.received) return 0; /* Never replace replicated state on a window/world rebind. */
    if (s->skills.tree4) mu_skill_tree4_close(s->skills.tree4);
    if (s->skills.book) mu_skill_book_close(s->skills.book);
    if(lang)s->cfg.lang=lang;
    s->skills.book = mu_skill_book_open(lang, dir, root);
    s->skills.tree4 = mu_skill_tree4_open(dir, s->skills.book);
    if (!s->skills.book || !s->skills.tree4) return -1;
    mu_master_env *e=mu_skill_book_master_env(s->skills.book);
    e->user=s;e->text=skill_text;e->invoke=master_invoke;e->msgbox=master_message;e->confirm=master_confirm;
    mu_skill_tree4_host host={s,skill_text,tree_invoke,tree_message,tree_confirm};
    mu_skill_tree4_set_host(s->skills.tree4,&host);
    mu_skill_book_enter(s->skills.book, s->skills.class_byte);
    mu_skill_tree4_enter(s->skills.tree4, s->skills.class_byte & 15);
    return 0;
}
void mu_session_skills_context(mu_session *s, const mu_skill_stats *st)
{
    if (s && s->skills.book) {
        if (st) mu_skill_book_set_stats(s->skills.book, st);
        mu_hero_stats hero;mu_session_hero(s,&hero);
        mu_master_env *e=mu_skill_book_master_env(s->skills.book);
        e->points=mu_prg_i32(s->hero.attr, MU_PRG_A_M34);e->level_sum=hero.level+hero.master_level;
        e->exp=(uint64_t)hero.master_exp;e->next_exp=(uint64_t)hero.master_next_exp;
    }
}
static uint32_t read32(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int complete_frame(const mu_session *s,const mu_frame *f)
{
    size_t n=f->length;const uint8_t *p=f->bytes;unsigned sub=s->route.sub;
    if(f->head!=0xc1 && f->head!=0xc2)return 0;
    if(f->opcode==0xa0 && sub==0x20) {
        if(n<7)return 0;
        return p[5]>=0xfe?n>=10:n>=7+4u*p[5];
    }
    if(f->opcode==0xa0 && sub==0x10)return n>=12 && read32(p+8)<=(n-12)/16;
    if(f->opcode==0x7e && sub==2)return n>=11 && read32(p+7)<=(n-11)/12;
    if(f->opcode==0x7e && sub==6)return n>=9 && read32(p+5)<=(n-9)/11;
    return 1;
}
mu_apply skills_apply(mu_session *s, const mu_frame *f)
{
    if (f->opcode == 0x7e && s->route.sub == 7) return MU_APPLY_UNDECODED;
    if (!s->skills.book || !complete_frame(s,f)) return MU_APPLY_IGNORED;
    mu_master_env *env=mu_skill_book_master_env(s->skills.book);
    env->points=mu_prg_i32(s->hero.attr, MU_PRG_A_M34);
    int r = f->opcode == 0xa0 ? mu_skill_book_receive(s->skills.book, f->bytes, f->length)
                             : mu_skill_tree4_receive(s->skills.tree4, f->bytes, f->length);
    if (!r) return MU_APPLY_IGNORED;
    if(f->opcode==0xa0 && s->route.sub==0x14) {
        /* 0x01285995 -> 0x00a00192: the answer writes CharacterAttribute +0x34. */
        mu_skills_master_points_apply(s->hero.attr, sizeof s->hero.attr, f->bytes, f->length);
        mu_session_touch(s,MU_DOMAIN_HERO);
    }
    s->skills.received = 1;
    mu_session_touch(s, MU_DOMAIN_SKILLS);
    return MU_APPLY_DONE;
}
/* Plain packet fields only. The offline transport's explicit plaintext lane bypasses keyed AddData.
 * Until NET-DECODE, requests for other transports remain unsent. */
static mu_submit send_request(mu_session *s, const uint8_t *b, size_t n, int encrypted)
{
    mu_submit r = {MU_SUBMIT_REFUSED, -1};
    if (!n) return r;
    extern mu_submit mu_combat_send_plain(mu_session *, const uint8_t *, size_t, int);
    return mu_combat_send_plain(s, b, n, encrypted);
}
mu_submit skills_select(mu_session *s, const mu_intent *in)
{
    int r = mu_skill_book_select_slot(s->skills.book, in->u.skill_select.slot);
    if (r) mu_session_touch(s, MU_DOMAIN_SKILLS);
    return (mu_submit){r ? MU_SUBMIT_SENT : MU_SUBMIT_REFUSED, -1};
}
mu_submit skills_save(mu_session *s, const mu_intent *in)
{
    mu_skill_book_stamp_save(s->skills.book);
    uint8_t b[41]; int32_t slots[10];
    const mu_skill_stamp_mgr *stamp = mu_skill_book_stamp_mgr(s->skills.book);
    for (int i=0;i<10;++i) slots[i]=stamp->slots[i]?stamp->slots[i]->learned:-1;
    size_t n=mu_skills_save_request(b,sizeof b,slots,in->u.skill_save_keys.options);
    mu_session_touch(s, MU_DOMAIN_SKILLS);
    return send_request(s, b, n, 0);
}
mu_submit skills_cast(mu_session *s, const mu_intent *in)
{
    int32_t events[2][2]; int n = 0, potion = 0;
    s->skills.last_cast = mu_skill_book_cast(s->skills.book, in->u.skill_cast.skill, events, &n, &potion);
    if (s->skills.last_cast != MU_SKILL_CAST_OK) return (mu_submit){MU_SUBMIT_REFUSED, -1};
    for (int i = 0; i < n; ++i) {
        mu_cue c = {.kind = MU_CUE_WINDOW};
        strcpy(c.u.window.movie, "skills"); strcpy(c.u.window.method, "delay");
        c.u.window.args[0] = events[i][0]; c.u.window.args[1] = events[i][1];
        mu_session_cue(s, &c);
    }
    mu_intent cast = {.kind = MU_INTENT_COMBAT_CAST};
    cast.u.combat_cast.x = in->u.skill_cast.x; cast.u.combat_cast.y = in->u.skill_cast.y;
    cast.u.combat_cast.skill = (uint8_t)in->u.skill_cast.skill; cast.u.combat_cast.type = in->u.skill_cast.type;
    extern mu_submit combat_cast(mu_session *, const mu_intent *);
    return combat_cast(s, &cast);
}
mu_submit skills_master(mu_session *s, const mu_intent *in)
{
    uint8_t b[8]; size_t n = mu_master_request(b, sizeof b, in->u.skill_master_learn.skill);
    return send_request(s, b, n, 0);
}
mu_submit skills_tree4(mu_session *s, const mu_intent *in)
{
    uint8_t b[9]; size_t n = mu_t4_request(b, sizeof b, in->u.skill_tree4_learn.group,
                                        in->u.skill_tree4_learn.skill, in->u.skill_tree4_learn.index);
    return send_request(s, b, n, 0);
}
mu_submit skills_side(mu_session *s, const mu_intent *in)
{
    uint8_t b[7]; size_t n = mu_t4_side_request(b, sizeof b, in->u.skill_tree4_side.category,
                                            in->u.skill_tree4_side.slot, in->u.skill_tree4_side.level);
    return send_request(s, b, n, 0);
}
void mu_dom_skills_init(mu_session *s)
{
    s->skills.last_cast = MU_SKILL_CAST_NONE;
    (void)mu_session_skills_bind(s, s->cfg.lang, getenv("MU_LANG_DIR"), NULL);
}
void mu_dom_skills_free(mu_session *s)
{
    mu_skill_tree4_close(s->skills.tree4); mu_skill_book_close(s->skills.book);
}
void mu_dom_skills_step(mu_session *s, const mu_sim *sim)
{
    (void)sim;
    mu_session_skills_context(s, NULL);
    uint32_t dt = s->now - s->skills.last_tick; s->skills.last_tick = s->now;
    mu_skill_book_tick(s->skills.book, (int32_t)(dt > 10000 ? 10000 : dt));
}
void mu_dom_skills_zones(const mu_session *s, mu_audit_zones *z)
{
    const mu_skill_hero *h = mu_skill_book_hero(s->skills.book);
    if (h) mu_audit_add(z, "skills.hero", (const uint8_t *)h, offsetof(mu_skill_hero, count), sizeof h->count + sizeof h->skills, MU_ZONE_REPLICATED, "learned skills and delays");
    mu_master_tree *m=mu_skill_book_master(s->skills.book);
    if(m) {
        mu_audit_add(z,"skills.master",m->state,0,sizeof m->state,MU_ZONE_REPLICATED,"ranks and spent points");
        mu_audit_add(z,"skills.master.count",(const uint8_t *)&m->nlearned,0,sizeof m->nlearned,MU_ZONE_REPLICATED,"learned count");
        for(int i=0;i<m->nlearned;++i) {
            const mu_master_learned *e=&m->learned[i];
            mu_audit_add(z,"skills.master.skill",(const uint8_t *)&e->skill,0,4,MU_ZONE_REPLICATED,"skill");
            mu_audit_add(z,"skills.master.level",&e->e.level,0,1,MU_ZONE_REPLICATED,"level");
            mu_audit_add(z,"skills.master.values",(const uint8_t *)&e->e.value,0,8,MU_ZONE_REPLICATED,"value and next");
            mu_audit_add(z,"skills.master.flag",&e->e.flag,0,1,MU_ZONE_REPLICATED,"flag");
        }
    }
    mu_t4_window *w=mu_skill_tree4_window(s->skills.tree4);
    if(w) {
        mu_audit_add(z,"skills.fourth.points",(const uint8_t *)&w->points,0,4,MU_ZONE_REPLICATED,"points");
        for(int g=0;g<w->ngroups;++g)for(int i=0;i<w->groups[g].nnodes;++i) {
            const mu_t4_node *node=&w->groups[g].nodes[i];
            mu_audit_add(z,"skills.fourth.node",(const uint8_t *)&node->skill,0,18,MU_ZONE_REPLICATED,"skill level values availability");
        }
        for(int i=0;i<MU_T4_SIDE;++i) {
            const mu_t4_side_entry *e=&w->side_entry[i];
            mu_audit_add(z,"skills.fourth.side.id",&e->category,0,3,MU_ZONE_REPLICATED,"category slot level");
            mu_audit_add(z,"skills.fourth.side.values",(const uint8_t *)&e->value,0,8,MU_ZONE_REPLICATED,"value next");
        }
    }
    const mu_skill_hotkeys *k = mu_skill_book_hotkeys(s->skills.book);
    if (k) mu_audit_add(z, "skills.keys", (const uint8_t *)k, 0, sizeof *k, MU_ZONE_REPLICATED, "saved keys");
}
#ifdef MU_SESSION_SEED
void mu_dom_skills_seed(mu_session *s, const struct mu_session_seed *seed)
{
    s->skills.class_byte = seed->class_byte;
    mu_skill_book_enter(s->skills.book, seed->class_byte);
    mu_skill_tree4_enter(s->skills.tree4, seed->class_byte & 15);
}
#endif
