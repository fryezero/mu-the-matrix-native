#include "../core/mu_world_haze.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
int main(void)
{
    mu_raster r;
    assert(!mu_raster_init(&r,32,24));
    mu_world_haze h={.world=8};
    for(int i=0;i<2;++i) {
        h.images[i]=(mu_image){1,1,3,malloc(4)};
        memset(h.images[i].rgba,100,3);h.images[i].rgba[3]=255;
    }
    const uint8_t background[4]={20,30,40,255};
    mu_raster_clear(&r,background);
    mu_world_haze_draw_raster(&h,1234,&r);
    for(int i=0;i<32*24;++i) {
        assert(r.color[i*4]==80 && r.color[i*4+1]==90 && r.color[i*4+2]==90);
    }
    h.world=57;mu_raster_clear(&r,background);mu_world_haze_draw_raster(&h,-1234,&r);
    assert(r.color[0]==100 && r.color[1]==110 && r.color[2]==130);
    h.world=0;mu_raster_clear(&r,background);mu_world_haze_draw_raster(&h,1234,&r);
    for(int i=0;i<32*24;++i) assert(!memcmp(r.color+i*4,background,4));
    h.world=8;free(h.images[0].rgba);free(h.images[1].rgba);
    memset(h.images,0,sizeof h.images);mu_raster_clear(&r,background);mu_world_haze_draw_raster(&h,1234,&r);
    for(int i=0;i<32*24;++i) assert(!memcmp(r.color+i*4,background,4));
    mu_raster_free(&r);
    return 0;
}
