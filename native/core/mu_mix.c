#include "mu_mix.h"
#include "mu_data.h"
#include "../../reconstructed/mix/mix_rules.h"
#include "../../reconstructed/mix/item_actions.h"
#include "../../reconstructed/mix/item_services.h"
#include "../../reconstructed/price/item_price.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct mu_mix_book { mu_data_table rows, items; size_t offsets[22]; int counts[22]; };
static uint32_t word(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static void put(uint8_t *p,uint32_t v) { for(int k=0;k<4;k++)p[k]=(uint8_t)(v>>(8*k)); }
mu_mix_book *mu_mix_book_open(const char *root) {
    if(!root) return NULL;
    mu_mix_book *b=calloc(1,sizeof *b);if(!b)return NULL;
    char path[4096];snprintf(path,sizeof path,"%s/Data/Local/Mix.bmd",root);
    if(mu_data_load(path,NULL,&b->rows) || b->rows.result.status!=MU_DATA_OK) goto fail;
    snprintf(path,sizeof path,"%s/Data/Local/Item.bmd",root);
    if(mu_data_load(path,NULL,&b->items) || b->items.result.status!=MU_DATA_OK) goto fail;
    size_t at=88;
    for(int g=0;g<22;g++) {
        int32_t n=(int32_t)word(b->rows.bytes+g*4);
        if(n<0 || n>3000 || (size_t)n>(b->rows.size-at)/928)goto fail;
        b->offsets[g]=at;b->counts[g]=n;at+=(size_t)n*928;
    }
    return b;
fail:mu_mix_book_close(b);return NULL;
}
void mu_mix_book_close(mu_mix_book *b) {
    if(b){mu_data_free(&b->rows);mu_data_free(&b->items);free(b);}
}
int mu_mix_book_jewel(mu_mix_book *b,int jewel,const mu_mix_item *it,int visible) {
    mu_item r;
    if(!b || !it || it->code<0 || mu_item_find(&b->items,(uint32_t)it->code,&r))return 0;
    mu_jewel_target t={it->code,it->level,it->option,r.record[0x250],r.record[0x251],r.record[0x252],
                        (uint8_t)it->durability,(uint8_t)it->period};
    return mu_jewel_allowed(jewel,&t,visible);
}
int mu_mix_book_quote(mu_mix_book *b,int group,const mu_mix_item *items,int n,mu_mix_quote *out) {
    if(!out)return 0;
    memset(out,0,sizeof *out);out->recipe=-1;
    snprintf(out->title,sizeof out->title,"Chaos Machine");
    snprintf(out->detail,sizeof out->detail,"Place ingredients in the mix window.");
    if(!b || group<0 || group>=22 || !b->counts[group]) {
        snprintf(out->detail,sizeof out->detail,"Mix table unavailable for this mode.");return 0;
    }
    if(n<1 || n>32 || !items)return 1;
    uint8_t sources[3200]={0};int ns=0;
    for(int k=0;k<n;k++) {
        mu_item rec;uint8_t raw[300]={0},s[100];
        const mu_mix_item *it=&items[k];
        if(it->code<0 || it->level<0 || it->level>15 || it->option!=0 ||
           mu_item_find(&b->items,(uint32_t)it->code,&rec))goto unsupported;
        put(raw+0x10,(uint32_t)it->code);put(raw+0x14,(uint32_t)(it->level<<3)|(uint32_t)(it->option&3));
        raw[0x3a]=(uint8_t)((it->option&4)<<4);raw[0x38]=(uint8_t)it->durability;
        raw[0x92]=(uint8_t)it->period;raw[0x98]=(uint8_t)(it->excellent!=0);
        mu_price_item pi;mu_price_item_init(&pi);
        pi.code=it->code;pi.level=it->level;pi.durability=(uint8_t)it->durability;
        pi.excellent=(uint8_t)it->excellent;
        uint32_t value=mu_mix_value(it->code,(uint32_t)mu_item_price(rec.record,&pi,MU_PRICE_BUY,NULL));
        if(!mu_mix_source_make(s,raw,rec.record,value))goto unsupported;
        /* Scalar branch of 0x00d08e38. Harmony vector merging stays outside
         * this adapter. The client's equality includes the current count. */
        ns=mu_mix_group_add(sources,ns,s,value,(uint8_t)it->durability);if(ns<0)goto unsupported;
    }
    const uint8_t *rows=b->rows.bytes+b->offsets[group];
    int selected=mu_mix_select(sources,ns,rows,b->counts[group],0);
    if(selected<0){snprintf(out->detail,sizeof out->detail,"No matching recipe.");return 1;}
    const uint8_t *r=rows+selected*928;out->recipe=selected;
    snprintf(out->title,sizeof out->title,"Chaos Machine - recipe %d",selected);
    if(!mu_mix_ready(sources,ns,r)) {
        snprintf(out->detail,sizeof out->detail,"Recipe identified. Ingredients are incomplete.");return 1;
    }
    if((r[0x3c]!='A' && r[0x3c]!='B' && r[0x3c]!='C') || r[0x14c]=='L')goto unsupported;
    mu_mix_values v;mu_mix_values_make(&v,sources,ns);v.max_rate=(int32_t)word(r+0x148);
    mu_mix_first_values(&v,sources,ns,r);
    float formula;int32_t cursor;
    if(!mu_mix_formula(r,&v,&formula,&cursor) || formula<0 || (double)formula>=4294967296.0)goto unsupported;
    uint16_t levels[32]={0};
    for(int k=0;k<ns;k++) {
        mu_item rec;if(!mu_item_find(&b->items,word(sources+k*100),&rec))
            levels[k]=(uint16_t)((uint16_t)rec.record[0x254]|(uint16_t)rec.record[0x255]<<8);
    }
    mu_mix_additions add;mu_mix_additions_make(&add,sources,ns,levels);
    out->rate=mu_mix_rate((uint32_t)formula,word(r+0x148),add.bless,add.life,add.charm,r[0x14d]=='A',r[0x14f]=='A',
                          r[0x151]=='A'||r[0x159]=='A'||r[0x15a]=='A');
    out->cost=mu_mix_cost(r[0x3c],word(r+0x40),(uint32_t)mu_mix_repeats(sources,ns,r),out->rate);
    out->ready=out->supported=1;
    snprintf(out->detail,sizeof out->detail,"Success rate: %u%%<br>Zen: %u<br>Offline demo server decides the result.",out->rate,out->cost);
    return 1;
unsupported:
    snprintf(out->detail,sizeof out->detail,"This recipe uses a rule not supported by the preview.");return 1;
}

int mu_mix_book_store(mu_mix_book *b,const mu_mix_item *it) {
    mu_item r;uint8_t raw[300]={0};
    if(!b || !it || it->code<0 || it->level<0 || it->level>15 ||
       it->durability<0 || it->durability>255 || it->period<0 || it->period>255 ||
       mu_item_find(&b->items,(uint32_t)it->code,&r))return 0;
    put(raw+0x10,(uint32_t)it->code);put(raw+0x14,(uint32_t)(it->level<<3));
    raw[0x38]=(uint8_t)it->durability;raw[0x92]=(uint8_t)it->period;
    /* +70 bound-item state is absent from the demo snapshot, supplied as 0. */
    return mu_personal_store_register(r.record,raw);
}
int mu_mix_book_repair(mu_mix_book *b,const mu_mix_item *it,int npc,int32_t *cost,int32_t *maximum) {
    if(cost)*cost=0;if(maximum)*maximum=0;
    mu_item r;
    if(!b || !it || it->code<0 || it->level<0 || it->level>15 || it->option!=0 ||
       it->durability<0 || it->durability>255 || it->period!=0 ||
       mu_item_find(&b->items,(uint32_t)it->code,&r))return 0;
    mu_item_attributes attr;mu_item_attributes_read(r.record,&attr);
    mu_item_state st={0};st.code=it->code;st.level=it->level;st.period=(uint8_t)it->period;st.excellent=(uint8_t)it->excellent;
    if(mu_item_repair_ban(&attr,&st))return 0;
    uint8_t max=mu_item_max_durability(&attr,&st);
    if(maximum)*maximum=max;
    if(!max || it->durability>=max)return 0;
    mu_price_item pi;mu_price_item_init(&pi);pi.code=it->code;pi.level=it->level;
    pi.durability=(uint8_t)it->durability;pi.max_durability=max;pi.excellent=(uint8_t)it->excellent;
    pi.period=(uint8_t)it->period;
    mu_repair_state repair={npc!=0,npc!=0,1,0};int shown=0;
    int32_t value=mu_item_repair_price(r.record,&pi,NULL,&repair,&shown);
    if(!shown || value<0)return 0;
    if(cost)*cost=value;
    return 1;
}
