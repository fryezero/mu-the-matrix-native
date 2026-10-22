#include "mix_rules.h"
#include <limits.h>
#include <string.h>

#ifndef MU_MIX_MUTANT
#define MU_MIX_MUTANT 0
#endif
static uint32_t u32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int32_t i32(const uint8_t *p) { return (int32_t)u32(p); }
static void put(uint8_t *p, uint32_t v) { for(int k=0;k<4;k++) p[k]=(uint8_t)(v>>(8*k)); }
static int chaos(const uint8_t *s) { int32_t c=i32(s); return c==0x406 || c==0x806 || c==0xa07; }
static int valid(const uint8_t *r) { return i32(r+0x39c)>=0 && i32(r+0x39c)<=8; }
uint32_t mu_mix_value(int32_t code,uint32_t buy) {
    if(MU_MIX_MUTANT==17)return buy;
    switch(code) {
    case 0x180f:return 40000;
    case 0x1c0d:return 100000;
    case 0x1c0e:return 70000;
    case 0x1c16:return 450000;
    case 0x1863:case 0x1994:case 0x1995:case 0x1996:case 0x1c10:return 0;
    default:return buy;
    }
}
int mu_mix_same(const uint8_t *a, const uint8_t *b) {
    static const int fields[]={0,4,8,12,16,32,20,24,44};
    if(!a || !b || a[0x3d]!=b[0x3d]) return 0;
    for(size_t j=0;j<sizeof fields/sizeof *fields;j++) if(u32(a+fields[j])!=u32(b+fields[j])) return 0;
    return 1;
}
int mu_mix_group_add(uint8_t *s,int n,const uint8_t *source,uint32_t value,uint8_t durability) {
    if(!s || !source || n<0 || n>=32)return -1;
    int j=0;for(;j<n;j++)if(mu_mix_same(s+j*100,source))break;
    if(j<n) {
        put(s+j*100+0x20,u32(s+j*100+0x20)+(source[0x3d]?(uint32_t)durability:1u));
        uint32_t sub=u32(source+0xc);
        if(MU_MIX_MUTANT==16)sub=0x38;
        put(s+j*100+0x30,u32(s+j*100+0x30)+value*((sub==0x38||sub==0x3a)?(uint32_t)durability:1u));
    } else {memcpy(s+n*100,source,100);n++;}
    return n;
}
/* 0x00d0c374, intersection of a group's candidates with one source. */
static int accepts(const uint8_t *s, const uint8_t *r) {
    if(mu_mix_extra(i32(s+0x48),r)) return 1;
    for(int j=0;j<i32(r+0x39c);j++) {
        const uint8_t *c=r+0x15c+j*72;
        if(!mu_mix_matches(s,c) || (int32_t)((uint32_t)r[0x15b]*u32(c+0x40))<i32(s+0x20)) continue;
        if(r[0x14c]=='L' && j==0 && !s[0x34]) continue;
        if(r[0x14c]=='J' && i32(c+0x3c) && !chaos(s) && !s[0x40]) continue;
        if(s[0x3f] && i32(r+4)!=501) continue;
        return 1;
    }
    return 0;
}
int32_t mu_mix_score(uint8_t *s, int32_t n, const uint8_t *r) {
    if(!s || n<1 || n>32 || !r || !valid(r)) return 0;
    int32_t left[8]={0}; uint32_t score=0,weight=0;
    for(int j=0;j<i32(r+0x39c);j++) left[j]=i32(r+0x19c+j*72);
    for(int k=0;k<n;k++) put(s+k*100+0x24,u32(s+k*100+0x20));
    for(int j=0;j<i32(r+0x39c);j++) {
        const uint8_t *c=r+0x15c+j*72;
        for(int k=0;k<n;k++) {
            uint8_t *p=s+k*100;
            if(!mu_mix_matches(p,c) || i32(p+0x24)<=0 || r[0x14c]=='H' || r[0x14c]=='I') continue;
            if(i32(p)==0x180f || i32(p+0x24)>i32(c+0x40)) weight=1;
            else weight=j==0?(MU_MIX_MUTANT==15?9u:10u):j==1?5u:3u;
            score+=weight;
            if(i32(p+0x24)>0 && left[j]>0) {
                left[j]=(int32_t)((uint32_t)left[j]-u32(p+0x24));
                int32_t used=i32(p+0x24)<i32(c+0x40)?i32(p+0x24):i32(c+0x40);
                put(p+0x24,u32(p+0x24)-(uint32_t)used);
            }
            if(u32(p+0x2c)&u32(c+0x44)) score+=5;
        }
    }
    for(int k=0;k<n;k++) if(i32(s+k*100+0x24)>0 && !mu_mix_extra(i32(s+k*100+0x48),r)) return 0;
    return (int32_t)score;
}
int32_t mu_mix_select(uint8_t *s,int32_t n,const uint8_t *rows,int32_t nr,int force) {
    if(!s || n<1 || n>32 || !rows || nr<1 || nr>3000) return -1;
    for(int j=0;j<nr;j++) if(!valid(rows+j*928) || i32(rows+j*928)!=j) return -1;
    if(nr==1 && !force) {
        for(int k=0;k<n;k++) for(int j=0;j<i32(rows+0x39c);j++) {
            const uint8_t *c=rows+0x15c+j*72;
            int32_t code=i32(s+k*100);
            int16_t lo=(int16_t)((uint16_t)c[0]|(uint16_t)c[1]<<8),hi=(int16_t)((uint16_t)c[2]|(uint16_t)c[3]<<8);
            if(code>=lo && code<=hi && i32(s+k*100+0x20)>(int32_t)((uint32_t)rows[0x15b]*u32(c+0x40))) return -1;
        }
        return 0;
    }
    int candidates=0;
    uint8_t ok[3000];
    for(int j=0;j<nr;j++) {
        ok[j]=1;
        for(int k=0;k<n;k++) if(!accepts(s+k*100,rows+j*928)) {ok[j]=0;break;}
        candidates+=ok[j];
    }
    int32_t best=-1,least=INT_MAX;
    for(int j=0;j<nr;j++) if(ok[j]) {
        const uint8_t *r=rows+j*928;
        if(r[0x14c]=='J' && candidates>1) {
            int found=0;
            for(int k=0;k<n;k++) if(chaos(s+k*100)) found=1;
            if(!found) continue;
        }
        int required=0;
        for(int c=0;c<i32(r+0x39c);c++) if(i32(r+0x198+c*72)) required++;
        if(required<least) {least=required;best=j;}
        else if(required==least && best>=0) {
            int32_t old=mu_mix_score(s,n,rows+best*928),current=mu_mix_score(s,n,r);
            if(MU_MIX_MUTANT==12 ? current>=old : current>old) best=j;
        }
    }
    return best;
}
void mu_mix_values_make(mu_mix_values *v,const uint8_t *s,int32_t n) {
    if(!v) return;
    memset(v,0,sizeof *v);
    if(!s || n<1 || n>32) return;
    for(int k=0;k<n;k++) {
        const uint8_t *p=s+k*100; uint32_t value=u32(p+0x30),flags=u32(p+0x2c);
        v->total+=value;
        if(flags&1) v->excellent+=value;
        if(p[0x3c]) v->equipment+=value;
        if(p[0x3e]) v->wing+=value;
        if(flags&4) v->ancient+=value;
        if(!p[0x40]) v->other+=value;
        int32_t code=i32(p);
        if(code==0x1863 || code==0x1994 || code==0x1995 || code==0x1996)
            v->bonus+=5u*(p[0x3d]?u32(p+0x20):1u);
    }
}
void mu_mix_first_values(mu_mix_values *v,const uint8_t *s,int32_t n,const uint8_t *r) {
    if(!v || !s || !r || n<1 || n>32 || !valid(r) || !i32(r+0x39c))return;
    for(int k=0;k<n;k++)if(mu_mix_matches(s+k*100,r+0x15c)) {
        v->first_value=u32(s+k*100+0x10);v->first_level=i32(s+k*100+0x38);
        if(MU_MIX_MUTANT==13)break;
    }
}
void mu_mix_additions_make(mu_mix_additions *v,const uint8_t *s,int32_t n,const uint16_t *levels) {
    if(!v)return;
    memset(v,0,sizeof *v);
    if(!s || n<1 || n>32)return;
    for(int k=0;k<n;k++) {
        int32_t extra=i32(s+k*100+0x48);
        if(extra==1)v->bless+=u32(s+k*100+0x20);
        else if(extra==3 && levels)v->life+=levels[k];
        else if(extra==5 || (MU_MIX_MUTANT!=14 && (extra==9 || extra==10)))v->charm++;
    }
}
