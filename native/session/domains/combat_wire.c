/* SESSION-COMBAT-001. Bounded default-world record bodies and plaintext builder inputs.
 * Engine/UI/effect services are outside these functions; see client-combat.md. */
#include "combat_wire.h"
#include <math.h>
#include <string.h>
static uint16_t be16(const uint8_t *p) { return (uint16_t)((p[0] << 8) | p[1]); }
static uint32_t u32(const uint8_t *p) { uint32_t v; memcpy(&v,p,4); return v; }
static void put32(uint8_t *p,uint32_t v) { memcpy(p,&v,4); }
static void putfloat(uint8_t *p,float v) { memcpy(p,&v,4); }
int mu_combat_damage_body(const uint8_t *p,size_t n,uint8_t *c,uint8_t *a,uint16_t hero,mu_combat_damage *d)
{
    if(n<24 || !c) return 0;
    memset(d,0,sizeof *d);
    uint16_t key=be16(p+3); d->key=key&0x7fff; d->shock=(uint8_t)(key>>15);
    d->amount=(int32_t)u32(p+8); d->shield=(int32_t)u32(p+20); d->type=p[13]&15;
    d->flags[0]=(p[13]>>4)&1; d->flags[1]=(p[13]>>5)&1;
    d->flags[2]=(p[13]>>6)&1; d->flags[3]=(p[13]>>7)&1;
    d->flags[4]=p[12]&1; d->flags[5]=(p[12]>>1)&1; d->flags[6]=(p[12]>>2)&1;
    d->flags[7]=(uint8_t)(p[16]==1);
    if(d->key==hero && a) {
        uint32_t hp=u32(a+0x68)-(uint32_t)d->amount, sd=u32(a+0x78)-(uint32_t)d->shield;
        put32(a+0x68,(int32_t)hp<0?0:hp); put32(a+0x78,(int32_t)sd<0?0:sd);
    }
    uint16_t last=(uint16_t)d->amount; memcpy(c+0x14a,&last,2);
    return 1;
}
int mu_combat_die_body(const uint8_t *p,size_t n,uint8_t *c)
{
    if(n<9 || !c) return 0;
    put32(c+0x3230,0); c[0x3234]=0; c[0x23]=1; c[0x38]=0; c[0x2a]=p[6];
    uint16_t skill=be16(p+5);
    c[0x325c]=(uint8_t)(skill==40 || skill==59 || skill==392);
    return 1;
}
int mu_combat_action_body(const uint8_t *p,size_t n,uint8_t *c,int16_t target,int has_target,float angle)
{
    if(n<9 || !c || (p[6]!=0x78 && p[6]!=0x79)) return 0;
    putfloat(c+0x33c0,has_target?angle:((float)p[5]-1.0f)*45.0f);
    c[0x38]=0;
    putfloat(c+0x33ac,(float)(int32_t)u32(c+0x180)*100.0f+50.0f);
    putfloat(c+0x33b0,(float)(int32_t)u32(c+0x184)*100.0f+50.0f);
    c[0x21]=1; putfloat(c+0x3324,0); memcpy(c+0x40,&target,2);
    return 1;
}
size_t mu_combat_attack_request(uint8_t out[7],uint16_t key,uint8_t dir,int blocked)
{
    if(blocked) return 0;
    uint8_t b[]={0xc1,7,0x43,(uint8_t)(key>>8),(uint8_t)key,0x78,dir}; memcpy(out,b,7); return 7;
}
size_t mu_combat_cast_request(uint8_t out[7],uint8_t x,uint8_t y,uint8_t skill,int type)
{
    if(type==11) { uint8_t b[]={0xc1,7,0xc9,0,x,y,skill};memcpy(out,b,7);return 7; }
    uint8_t b[]={0xc1,6,0xd7,x,y,skill};memcpy(out,b,6);return 6;
}
static uint8_t direction(int dx,int dy)
{
    static const int delta[8][2]={{-1,-1},{-1,0},{-1,1},{0,1},{1,1},{1,0},{1,-1},{0,-1}};
    for(uint8_t i=0;i<8;++i) if(dx==delta[i][0] && dy==delta[i][1]) return i;
    return 0;
}
size_t mu_combat_move_request(uint8_t out[16],uint16_t hero,const uint8_t x[15],const uint8_t y[15],uint8_t count,
                              uint8_t tx,uint8_t ty,float angle,int blocked,int32_t *delay)
{
    if(blocked) return 0;
    *delay=count<=2?0:count==3?5:((int32_t)count-2)*3+10;
    if(!hero || !count) return 0;
    if(count>=15) count=14;
    memset(out,0,16);out[0]=0xc1;out[2]=0xa2;out[3]=x[0];out[4]=y[0];
    uint8_t dir=0;
    for(unsigned i=1;i<count;++i) {
        dir=direction((int)x[i]-x[i-1],(int)y[i]-y[i-1]);
        if(i&1) out[5+(i+1)/2]=(uint8_t)(dir<<4); else out[5+(i+1)/2]+=dir;
    }
    if(count==1) {
        float v=((angle+22.5f)/360.0f)*8.0f+1.0f;
        int32_t i=isfinite(v) && v>=-2147483648.0f && v<2147483648.0f?(int32_t)v:INT32_MIN;
        dir=(uint8_t)((uint8_t)i&7);
    } else {
        /* The client retains the preceding segment direction when no final delta matches. */
        uint8_t last=direction((int)tx-x[count-1],(int)ty-y[count-1]);
        int dx=(int)tx-x[count-1],dy=(int)ty-y[count-1];
        if((dx || dy) && dx>=-1 && dx<=1 && dy>=-1 && dy<=1) dir=last;
    }
    out[5]=(uint8_t)((dir<<4)+(count-1));out[1]=(uint8_t)(6+count/2);return out[1];
}
