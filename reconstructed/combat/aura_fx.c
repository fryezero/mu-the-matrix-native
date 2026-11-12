/* RENDER-EFFECTS-028. Persistent visuals only; no buff values or stat state. */
#include "aura_fx.h"
#include "../record-math/record_math.h"
#include <math.h>
#include <string.h>
static void copy(float d[3], const float s[3]) { memcpy(d,s,3*sizeof(float)); }
static void emit(const mu_jt_env *e, const mu_jt_call *c) { if(e && e->call) e->call(e->context,c); }
void mu_aura_plan(const mu_aura_input *in, const mu_aura_env *env)
{
    const mu_jt_env *e=env->joint;
    const int attack=(in->buffs & (MU_AURA_ATTACK|MU_AURA_COMBINED|MU_AURA_ATTACK_UP))!=0;
    const int defense=(in->buffs & (MU_AURA_DEFENSE|MU_AURA_DEFENSE_UP))!=0;
    if((!attack && !defense) || (in->buffs & MU_AURA_HIDDEN)) return;
    if(attack) {
        for(int n=0;n<2;++n) {
            const float pulse=(float)((e && e->rand ? e->rand(e->context) : 0)%30+70)*0.01f;
            mu_jt_call c={0}; c.routine=MU_JT_CALL_SPRITE; c.type=0x7f67;
            c.owner=in->owner; c.scale=1.5f; c.range=4;
            c.light[0]=pulse; c.light[1]=pulse*0.3f; c.light[2]=pulse*0.2f;
            const int offsets[3]={0,-6,-7};
            for(int k=0;k<3;++k) {
                if(!env->bone || !env->bone(e->context,in->link[n]+offsets[k],c.position)) goto attachments;
                emit(e,&c);
            }
        }
    }
attachments:
    if(in->existing4 || in->existing9) return;
    mu_jt_call c={0}; c.routine=MU_JT_CALL_JOINT; c.type=0x472; c.subtype=4;
    c.owner=in->owner; c.scale=20.0f; c.arg7=-1; c.arg8=0; c.range=in->key;
    copy(c.position,in->position); copy(c.target,in->position); copy(c.angle,in->angle);
    for(int n=0;n<5;++n) emit(e,&c);
}
int mu_aura_create(mu_jt_joint *j, const mu_aura_input *in, const mu_jt_env *env)
{
    if(!mu_jt_create(j,0x472,in->position,in->position,in->angle,1,in->owner,20.0f,
                     0xffff,0,0,0xffff,0,env)) return 0;
    j->subtype=4; j->lifetime=10000; j->max_tails=30; j->tex_type=0x7fdd;
    j->light[0]=0.4f; j->light[1]=0.8f; j->light[2]=0.2f;
    return 1;
}
int mu_aura_move(mu_jt_joint *j, uint32_t buffs, const mu_jt_env *env, int32_t index, float step)
{
    if(j->type!=0x472 || j->subtype!=4) return 0;
    if(!j->live) return 1;
    float m[12]={0};
    if(j->moving) {
        mu_angle_matrix(j->angle,m);
        if(j->velocity!=0.0f) {
            float v[3]={0,-j->velocity,0},r[3]; mu_vector_rotate(v,m,r);
            for(int k=0;k<3;++k) j->position[k]+=r[k];
        }
    }
    const mu_jt_object *o=env && env->object ? env->object(env->context,j->target) : NULL;
    if(j->target<0) goto tail;
    if(!o || !o->live || !(buffs & (MU_AURA_DEFENSE|MU_AURA_DEFENSE_UP|MU_AURA_COMBINED))) {
        j->live=0; j->lifetime=0; goto tail;
    }
    j->lifetime=100;
    for(int i=j->num_tails-1;i>=0;--i)
        for(int c=0;c<4;++c)
            for(int k=0;k<3;++k) j->tails[i][c][k]-=j->target_position[k];
    copy(j->target_position,o->position); j->target_position[2]+=10.0f;
    for(int i=j->num_tails-1;i>=0;--i)
        for(int c=0;c<4;++c)
            for(int k=0;k<3;++k) j->tails[i][c][k]+=j->target_position[k];
    const uint32_t clock=(uint32_t)(env ? env->ambient_clock : 0);
    const uint32_t phase=(uint32_t)index*0xd1e3u+(index%2 ? clock : 0u-clock);
    const float a=(float)(int32_t)(phase+0xd903u)*0.048f;
    const float b=(float)(int32_t)phase*0.0613f;
    const float c=(float)(int32_t)(phase+0x2b67u)*0.1113f;
    const float sn=(float)sin((double)a), x=sn*(float)cos((double)b), y=sn*(float)sin((double)b);
    const float z=(float)cos((double)a), sc=(float)sin((double)c), co=(float)cos((double)c);
    j->position[0]=(co*y-sc*z)*80.0f+j->target_position[0];
    j->position[1]=(sc*y+co*z)*80.0f+j->target_position[1];
    j->position[2]=x*120.0f+(110.0f+j->target_position[2]);
tail:
    if(j->tail_update) mu_jt_tail_shift(j,m);
    j->time+=step; --j->lifetime; if(j->lifetime<0) j->live=0;
    return 1;
}
/* RenderJoints 0x0158a5a4: per-tail height fade and midpoint flare. Geometry
 * and all common UV/state rules remain the shared, compared joint renderer. */
typedef struct aura_gl {
    const mu_jt_gl *gl;
    const mu_jt_env *env;
    const mu_jt_joint *j;
    int tail, face, faces;
} aura_gl;
static void ag_state(void *v,int32_t w,int32_t a) { aura_gl *s=v; if(s->gl->state)s->gl->state(s->gl->context,w,a); }
static void ag_bind(void *v,int32_t b) { aura_gl *s=v; if(s->gl->bind)s->gl->bind(s->gl->context,b); }
static void ag_color(void *v,float r,float g,float b) { aura_gl *s=v; if(s->gl->color3)s->gl->color3(s->gl->context,r,g,b); }
static void ag_begin(void *v,int32_t mode)
{
    aura_gl *s=v; const mu_jt_joint *j=s->j;
    if(s->face==0) {
        const mu_jt_object *o=s->env && s->env->object ? s->env->object(s->env->context,j->target) : NULL;
        float light[3]={1,1,1};
        if(o) {
            const float fade=(j->tails[s->tail][0][2]-(o->position[2]+50.0f))*0.01f;
            for(int k=0;k<3;++k) light[k]=fade>0.0f ? j->light[k]-fade : j->light[k];
        }
        ag_color(v,light[0],light[1],light[2]);
        if(s->tail==j->num_tails/2) {
            mu_jt_call c={0}; c.routine=MU_JT_CALL_SPRITE; c.type=0x7fdd;
            c.owner=-1; c.scale=0.7f; c.range=4; copy(c.light,light);
            for(int corner=0;corner<4;++corner)
                for(int k=0;k<3;++k) c.position[k]=j->tails[s->tail][corner][k]+c.position[k];
            for(int k=0;k<3;++k)c.position[k]=0.25f*c.position[k];
            emit(s->env,&c);
        }
    }
    if(s->gl->begin)s->gl->begin(s->gl->context,mode);
    if(++s->face==s->faces) { s->face=0; ++s->tail; }
}
static void ag_tex(void *v,float u,float t) { aura_gl *s=v; if(s->gl->texcoord)s->gl->texcoord(s->gl->context,u,t); }
static void ag_vertex(void *v,const float p[3]) { aura_gl *s=v; if(s->gl->vertex)s->gl->vertex(s->gl->context,p); }
static void ag_end(void *v) { aura_gl *s=v; if(s->gl->end)s->gl->end(s->gl->context); }
int mu_aura_render(const mu_jt_joint *j,uint8_t mode,float clock,const mu_jt_env *env,const mu_jt_gl *gl)
{
    if(j->type!=0x472 || j->subtype!=4 || !gl || j->target<0 || !env || !env->object || !env->object(env->context,j->target))return 0;
    aura_gl s={gl,env,j,0,0,(int)((j->faces&1)!=0)+(int)((j->faces&2)!=0)};
    const mu_jt_gl wrapped={&s,ag_state,ag_bind,ag_color,ag_begin,ag_tex,ag_vertex,ag_end};
    return mu_jt_render(j,mode,clock,&wrapped);
}
