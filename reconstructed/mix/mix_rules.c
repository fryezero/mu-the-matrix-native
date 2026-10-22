#include "mix_rules.h"
#include <limits.h>
#include <math.h>
#include <string.h>

#ifndef MU_MIX_MUTANT
#define MU_MIX_MUTANT 0
#endif
static uint32_t u32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int32_t i32(const uint8_t *p) { return (int32_t)u32(p); }
static int32_t i16(const uint8_t *p) { return (int16_t)((uint16_t)p[0] | (uint16_t)p[1]<<8); }
static void put(uint8_t *p, int32_t v) {
    for (int k=0;k<4;k++) p[k]=(uint8_t)((uint32_t)v >> (8*k));
}
static int between(int32_t n, int32_t lo, int32_t hi) { return n>=lo && n<=hi; }
static int range(const uint8_t *s, int off, const uint8_t *c, int low) {
    return between(i32(s+off),i32(c+low),i32(c+low+4));
}
int mu_mix_matches(const uint8_t *s, const uint8_t *c) {
    if (!s || !c) return 0;
    if (!range(s,0x10,c,0x1c) || !range(s,0x1c,c,0x34)) return 0;
    if (!(i32(c+0x2c)==0 && i32(c+0x30)==255)) {
        if (!range(s,0x18,c,0x2c)) return 0;
    } else if (!range(s,0x14,c,0x24)) return 0;
    uint32_t have=u32(s+0x2c),need=u32(c+0x44);
    uint32_t mask=MU_MIX_MUTANT==2 ? 0x3f : 0xbf;
    if ((have & need & mask)!=(need & mask) || (have & 0x40)!=(need & 0x40)) return 0;
    if ((i32(c+4)||i32(c+8)) && !range(s,4,c,4)) return 0;
    int a=i32(c+0xc)||i32(c+0x10),b=i32(c+0x14)||i32(c+0x18);
    if (a||b) {
        if (a && !range(s,8,c,0xc)) return 0;
        if (b && !range(s,0xc,c,0x14)) return 0;
    } else if (!between(i32(s),i16(c),i16(c+2))) return 0;
    return 1;
}
static int conditions(const uint8_t *r) {
    return r && i32(r+0x39c)>=0 && i32(r+0x39c)<=MU_MIX_MAX_CONDITIONS;
}
int32_t mu_mix_repeats(const uint8_t *s,int32_t n,const uint8_t *r) {
    if (!r || r[0x15b]==1) return 1;
    if (!conditions(r) || n<0 || n>32 || (!s && n)) return 0;
    int32_t result=1;
    for (int j=0;j<i32(r+0x39c);j++) {
        const uint8_t *c=r+0x15c+j*72;
        int32_t count=0;
        for (int k=0;k<n;k++) if(mu_mix_matches(s+k*100,c)) count=(int32_t)((uint32_t)count+u32(s+k*100+0x20));
        int32_t min=i32(c+0x3c);
        if(min>0) count=(int32_t)((uint32_t)((int32_t)((uint32_t)count-1u)/min)+1u);
        if(count>result) result=count;
    }
    return result;
}
int mu_mix_extra(int32_t k,const uint8_t *r) {
    static const int offsets[12]={-1,0x14d,0x14e,0x14f,0x150,0x151,0x154,0x154,0x158,0x159,0x15a,0x154};
    if(!r || k<1 || k>11) return 0;
    if(MU_MIX_MUTANT==9 && k>=6) return 0;
    if(k==6||k==7||k==11) return i32(r+0x154)==(k==6?0x15:k==7?0x67:0x7a);
    return r[offsets[k]]=='A';
}
int mu_mix_ready(uint8_t *s,int32_t n,const uint8_t *r) {
    if(!s || n<=0 || n>32 || !conditions(r)) return 0;
    for(int k=0;k<n;k++) put(s+k*100+0x24,i32(s+k*100+0x20));
    int32_t repeat=mu_mix_repeats(s,n,r);
    int hit=0;
    for(int j=0;j<i32(r+0x39c);j++) {
        const uint8_t *c=r+0x15c+j*72;
        if(i32(c+0x3c)!=0) hit=0;
        int32_t used=0,maximum=(int32_t)(u32(c+0x40)*(uint32_t)repeat);
        for(int k=0;k<n;k++) {
            uint8_t *p=s+k*100;
            int32_t left=i32(p+0x24);
            if(!mu_mix_matches(p,c)||left<=0 || maximum<(int32_t)((uint32_t)left+(uint32_t)used)) continue;
            if(left>=maximum) { used=(int32_t)((uint32_t)used+(uint32_t)maximum); put(p+0x24,(int32_t)((uint32_t)left-(uint32_t)maximum)); }
            else { used=(int32_t)((uint32_t)used+(uint32_t)left); put(p+0x24,0); }
            hit=1;
        }
        int32_t minimum=(int32_t)(u32(c+0x3c)*(uint32_t)repeat);
        if(!hit || minimum>used) return 0;
    }
    for(int k=0;k<n;k++) if(i32(s+k*100+0x24)>0 &&
        (repeat>1 || !mu_mix_extra(i32(s+k*100+0x48),r))) return 0;
    return MU_MIX_MUTANT==3 ? 0 : 1;
}

typedef struct parser { const uint8_t *r; const mu_mix_values *v; int at,n,depth,ok; } parser;
static int shape_expression(parser *p);
static int shape_atom(parser *p) {
    if(p->at>=p->n || ++p->depth>32) return 0;
    int t=i32(p->r+0x48+p->at*8);++p->at;
    if(t==7) {
        if(p->at>=p->n || i32(p->r+0x48+p->at*8)!=5) return 0;
        ++p->at;
    }
    if(t==5||t==7) {
        if(!shape_expression(p) || p->at>=p->n || i32(p->r+0x48+p->at*8)!=6) return 0;
        ++p->at;
    } else if(t!=0 && !(t>=0x20 && t<=0x28) && t!=0x40) return 0;
    --p->depth;return 1;
}
static int shape_term(parser *p) {
    if(!shape_atom(p)) return 0;
    while(p->at<p->n) {
        int t=i32(p->r+0x48+p->at*8);
        if(t!=3 && t!=4) break;
        ++p->at;if(!shape_atom(p)) return 0;
    }
    return 1;
}
static int shape_expression(parser *p) {
    if(!shape_term(p)) return 0;
    while(p->at<p->n) {
        int t=i32(p->r+0x48+p->at*8);
        if(t!=1 && t!=2) break;
        ++p->at;if(!shape_term(p)) return 0;
    }
    return 1;
}
static float expression(parser *p);
static float atom(parser *p) {
    if(p->at>=p->n || ++p->depth>32) {p->ok=0;return 0;}
    int type=i32(p->r+0x48+p->at*8);
    float value=0;
    const mu_mix_values *v=p->v;
    switch(type) {
    case 0: memcpy(&value,p->r+0x4c+p->at*8,4); break;
    case 5: ++p->at;value=expression(p);break;
    case 7:
        p->at+=2;value=expression(p);
        if(!isfinite(value)) {p->ok=0;break;}
        /* CVTTSS2SI's indefinite integer is INT_MIN, also for overflow. */
        if(value>=2147483648.0f || value< -2147483648.0f) value=-2147483648.0f;
        else value=(float)(int32_t)value;
        if(MU_MIX_MUTANT==8) value=0;
        break;
    case 0x20:value=(float)v->max_rate;break;
    case 0x21:value=(float)v->total;break;
    case 0x22:value=(float)v->wing;break;
    case 0x23:value=(float)v->excellent;break;
    case 0x24:value=(float)v->equipment;break;
    case 0x25:value=(float)v->ancient;break;
    case 0x26:value=(float)v->first_value;break;
    case 0x27:value=(float)v->other;break;
    case 0x28:value=(float)v->bonus;break;
    case 0x40:value=(float)v->first_level;break;
    default:p->ok=0;break;
    }
    ++p->at;--p->depth;
    if(!isfinite(value)) p->ok=0;
    return value;
}
static float term(parser *p) {
    float value=0;
    while(p->ok && p->at<p->n) {
        int t=i32(p->r+0x48+p->at*8);
        if(t==6||t==1||t==2) return value;
        if(t==3||t==4) {
            ++p->at;float rhs=atom(p);
            if(t==3 || MU_MIX_MUTANT==7) value=value*rhs; else if(rhs!=0) value=value/rhs;else p->ok=0;
        } else value=atom(p);
        if(!isfinite(value)) p->ok=0;
    }
    return value;
}
static float expression(parser *p) {
    float value=0;
    while(p->ok && p->at<p->n) {
        int t=i32(p->r+0x48+p->at*8);
        if(t==6) break;
        if(t==1||t==2) { ++p->at;float rhs=term(p);value=t==1?value+rhs:value-rhs; }
        else value=term(p);
        if(!isfinite(value)) p->ok=0;
    }
    return value;
}
int mu_mix_formula(const uint8_t *r,const mu_mix_values *v,float *out,int32_t *cursor) {
    if(!r||!v||!out||!cursor || i32(r+0x44)<0 || i32(r+0x44)>32) return 0;
    parser p={r,v,0,i32(r+0x44),0,1};
    if(p.n && (!shape_expression(&p)||p.at!=p.n)) return 0;
    p.at=0;p.depth=0;
    float x=expression(&p);
    if(!isfinite(x)) p.ok=0;
    *out=x;*cursor=p.at;return p.ok;
}
uint32_t mu_mix_rate(uint32_t x,uint32_t cap,uint32_t bless,uint32_t life,uint32_t charm,int ab,int al,int sc) {
    if(x>cap) x=cap;
    if(ab) x+=bless;
    if(al) x+=life;
    if(sc && charm>0) x-=5;
    uint32_t limit=MU_MIX_MUTANT==4 ? 99u : 100u;
    return x>limit ? limit : x;
}
uint32_t mu_mix_cost(uint8_t type,uint32_t base,uint32_t repeats,uint32_t rate) {
    if(type=='A'||type=='C') return base*repeats;
    if(type=='B') return (MU_MIX_MUTANT==5 ? 1u : rate)*base*repeats;
    /* 'D' reads the harmony option table. Its host needs that table. */
    return 0;
}
