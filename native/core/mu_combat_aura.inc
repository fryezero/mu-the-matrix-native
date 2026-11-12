/* RENDER-EFFECTS-028: authored hero-only aura fixture. Included by mu_combat.c.
 * Buff lifetime is a demo clock, never a cast result or authoritative value. */
static uint32_t aura_presence(mu_combat *c)
{
    if(c->hero_dead) { c->aura_expiry[0]=c->aura_expiry[1]=0; return 0; }
    return (c->step<c->aura_expiry[0] ? MU_AURA_DEFENSE : 0u) |
           (c->step<c->aura_expiry[1] ? MU_AURA_ATTACK : 0u);
}
static void aura_cast(mu_combat *c,int32_t skill)
{
    if(c->aura_duration>0 && (skill==27 || skill==28) && !c->hero_dead)
        c->aura_expiry[skill==27 ? 0 : 1]=c->step+c->aura_duration;
}
static void aura_step(mu_combat *c)
{
    uint32_t buffs=aura_presence(c);
    c->jenv.ambient_clock=c->step;
    for(int i=0;i<5;++i)
        (void)mu_aura_move(&c->aura_joints[i],buffs,&c->jenv,i,c->time_step);
}
static int aura_bone(void *ctx,int32_t bone,float p[3])
{
    mu_combat *c=ctx; mu_character *h=c->hero_character;
    if(!h || !h->player_loaded || !h->player_bones || bone<0 || bone>=h->player_bone_count ||
       h->player_bmd.bones[bone].dummy) { ++c->aura_refused; return 0; }
    const float zero[3]={0};
    mu_pt_transform_position(h->player_bones+12*bone,zero,p,1,h->params.scale,c->walk->hero.position);
    return 1;
}
static void aura_call(void *ctx,const mu_jt_call *call)
{
    mu_combat *c=ctx; ++c->aura_requests;
    if(call->routine==MU_JT_CALL_SPRITE) {
        if(c->aura_sprite_count<11) c->aura_sprites[c->aura_sprite_count++]=*call;
        else ++c->aura_refused;
    } else if(call->routine==MU_JT_CALL_JOINT) {
        mu_aura_input in={0}; in.owner=MU_COMBAT_HERO_OBJECT;
        memcpy(in.position,call->position,sizeof in.position); memcpy(in.angle,call->angle,sizeof in.angle);
        for(int i=0;i<5;++i) if(!c->aura_joints[i].live) {
            if(mu_aura_create(&c->aura_joints[i],&in,&c->jenv)) { ++c->aura_created; return; }
            break;
        }
        ++c->aura_refused;
    }
}
static void aura_draw_plan(mu_combat *c)
{
    c->aura_sprite_count=0;
    const uint32_t buffs=aura_presence(c);
    if(!buffs) return;
    mu_aura_input in={0}; in.buffs=buffs; in.owner=MU_COMBAT_HERO_OBJECT; in.key=-1;
    /* Explicit fixture link bones, the Player right/left default links. No equipment selector. */
    in.link[0]=33; in.link[1]=42;
    memcpy(in.position,c->walk->hero.position,sizeof in.position);
    memcpy(in.angle,c->walk->hero.angle,sizeof in.angle);
    for(int i=0;i<5;++i) in.existing4|=c->aura_joints[i].live;
    mu_jt_env e=c->jenv; e.call=aura_call;
    const mu_aura_env env={&e,aura_bone}; mu_aura_plan(&in,&env);
}
typedef struct aura_quad_sink {
    mu_joint_quad *quads,current;
    int32_t count,max,corner,bitmap;
    float rgb[3];
} aura_quad_sink;
static void aq_state(void *v,int32_t a,int32_t b) { (void)v;(void)a;(void)b; }
static void aq_bind(void *v,int32_t b) { ((aura_quad_sink*)v)->bitmap=b; }
static void aq_color(void *v,float r,float g,float b) { aura_quad_sink *s=v;s->rgb[0]=r;s->rgb[1]=g;s->rgb[2]=b; }
static void aq_begin(void *v,int32_t mode) { (void)mode;((aura_quad_sink*)v)->corner=0; }
static void aq_tex(void *v,float u,float t) { aura_quad_sink *s=v;if(s->corner<4) {s->current.uv[s->corner][0]=u;s->current.uv[s->corner][1]=t;} }
static void aq_vertex(void *v,const float p[3]) { aura_quad_sink *s=v;if(s->corner<4)memcpy(s->current.position[s->corner],p,3*sizeof(float));++s->corner; }
static void aq_end(void *v) {
    aura_quad_sink *s=v;if(s->corner!=4 || s->count>=s->max)return;
    mu_joint_quad *q=&s->quads[s->count++];*q=s->current;q->bitmap=s->bitmap;q->render_type=1;memcpy(q->color,s->rgb,sizeof q->color);
}
static int32_t aura_quads(mu_combat *c,mu_joint_quad *quads,int32_t max)
{
    aura_quad_sink sink={0};sink.quads=quads;sink.max=max;
    const mu_jt_gl gl={&sink,aq_state,aq_bind,aq_color,aq_begin,aq_tex,aq_vertex,aq_end};
    mu_jt_env env=c->jenv;env.call=aura_call;
    for(int i=0;i<5;++i) (void)mu_aura_render(&c->aura_joints[i],0,c->map ? c->map->time : 0,&env,&gl);
    return sink.count;
}
