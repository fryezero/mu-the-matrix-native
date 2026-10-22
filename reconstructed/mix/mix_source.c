#include "mix_rules.h"
#include <string.h>

#ifndef MU_MIX_MUTANT
#define MU_MIX_MUTANT 0
#endif
static uint32_t word(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static uint32_t half(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8; }
static void put(uint8_t *p,uint32_t v) { for(int k=0;k<4;k++)p[k]=(uint8_t)(v>>(8*k)); }
static int oneof(int k,const int *list,size_t n) { for(size_t j=0;j<n;j++)if(k==list[j])return 1;return 0; }
int mu_mix_source_make(uint8_t *out,const uint8_t *it,const uint8_t *r,uint32_t value) {
    if(!out||!it||!r || word(it+0x10)>0x2c00 || half(it+0x6e) || word(it+0xe4) || word(it+0xe8) || it[0x3d]>8) return 0;
    memset(out,0,100);
    uint32_t code=word(it+0x10),kind=r[0x250],sub=r[0x251],type=r[0x252],flags=0;
    put(out,code);put(out+4,type);put(out+8,kind);put(out+0xc,sub);
    put(out+0x10,(word(it+0x14)>>3)&15);put(out+0x18,half(it+0x5e));put(out+0x1c,it[0x38]);
    for(int k=0;k<16;k++)if(r[0x291+k])put(out+0x28,word(out+0x28)|(1u<<k));
    for(int k=0;k<it[0x3d];k++) {
        uint32_t opt=half(it + 0x3e + k*2),v=half(it + 0x4e + k*2);
        if(opt<=4)put(out+0x14,v);
        if(opt==6)put(out+0x14,v*4);
        if(opt==5)put(out+0x38,v);
    }
    if(it[0x98]==1||type==6||type==8)flags|=1;
    if(type==3){flags|=2;out[0x42]=it[0x72];}
    if(it[0x3b]&0x33)flags|=4;
    if(sub==0x2b)flags|=0x20;
    if(sub==0x4d)flags|=0x40;
    static const int equipment[]={1,3,0xe,0xf,0x12,0x13,0x1b,0x21,0x37,0x2d,0x2e,0x2f,0x30,0x31,0x38};
    if(oneof((int)kind,equipment,sizeof equipment/sizeof *equipment)||sub==0x2b)out[0x3c]=1;
    static const int compound[]={0x2d,0x2e,0x2f,0x30,0x31,0x38};
    if((oneof((int)kind,compound,sizeof compound/sizeof *compound) || (MU_MIX_MUTANT==11 && kind==0x37)) && (flags&4))out[0x44]=1;
    if(code==0x1a25 && it[0x3a])out[0x43]=1;
    if((kind==0x13||kind==4||kind==2) && type!=2)out[0x41]=1;
    if(sub==0x38)out[0x40]=1;
    if(type==2){flags|=0x10;flags&=~2u;}
    static const int wings[]={0x17,0x18,0x1a,0x1b,0x1c,0x19,0x4c,0x6a};
    if(oneof((int)sub,wings,sizeof wings/sizeof *wings)){out[0x3e]=1;flags&=~1u;}
    else if(type==5)out[0x3f]=1;
    if(!flags)flags=0x80;
    put(out+0x2c,flags);out[0x34]=1;
    uint32_t extra=0;
    if(code==0x1c35)extra=1;
    else if(code==0x1c60||code==0x289d)extra=2;
    else if(code==0x1cbd)extra=3;
    else if(code==0x1cbe||code==0x2610)extra=4;
    else if(kind==0x17)extra=5;
    else if(sub==0x15)extra=6;
    else if(sub==0x67)extra=7;
    else if(sub==0x7a)extra=11;
    else if(kind==0x20)extra=8;
    else if(kind==0x39)extra=9;
    else if(kind==0x3a)extra=10;
    if(MU_MIX_MUTANT==6 && extra==1)extra=0;
    put(out+0x48,extra);
    int stack=r[0x2af]>1||sub==0x38||kind==0x1d;
    out[0x3d]=(uint8_t)stack;
    uint32_t count=stack ? (kind==0x1d?word(it+0x120):it[0x38]) : extra==1?it[0x38]:1u;
    put(out+0x20,count);
    if(sub==0x38||sub==0x3a||sub==0x5c)value*=count;
    put(out+0x30,value);
    return 1;
}
