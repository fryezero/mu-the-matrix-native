#include "item_services.h"
#include <stddef.h>
static uint32_t u32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
int mu_personal_store_ban(const uint8_t *r,const uint8_t *it) {
    if(!r || !it)return 1;
    int32_t code=(int32_t)u32(it+0x10);
    unsigned level=(u32(it+0x14)>>3)&15;
    if(code>=0 && code<=0x2c00 && r[0x251]==0x2b && !it[0x38])return 1;
    if(it[0x92]==1)return 1;
    if((code==0x1a14 && level!=0) || (code==0x1c0b && level==13) || (code==0x1c1a && level!=0))return 1;
    if(code==0x1c15 && level==3)return 0;
    return !r[0x2aa];
}
int mu_personal_store_register(const uint8_t *r,const uint8_t *it) {
    if(!r || !it)return 0;
    int32_t code=(int32_t)u32(it+0x10);
    int valid=code>=0 && code<=0x2c00;
    unsigned bound=(unsigned)it[0x70]|(unsigned)it[0x71]<<8;
    if(valid && (r[0x250]==5 || r[0x251]==0x4f || r[0x251]==0x2e) && bound==1)return 0;
    if(valid && r[0x251]==0x2f && it[0x38]==254)return 0;
    return !mu_personal_store_ban(r,it);
}
int mu_repair_toggle(int state) { return state==1 ? 2:1; }
void mu_repair_request(uint8_t out[5],uint8_t slot,uint8_t mode) {
    out[0]=0xc1;out[1]=5;out[2]=0xb1;out[3]=slot;out[4]=mode;
}
