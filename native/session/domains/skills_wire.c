#include "skills_wire.h"
#include <string.h>
size_t mu_skills_save_request(uint8_t *out, size_t cap, const int32_t slots[10], const uint8_t settings[17])
{
    if (!out || cap < 41 || !slots || !settings) return 0;
    out[0]=0xc1;out[1]=41;out[2]=1;out[3]=0x30;
    for(int i=0;i<10;++i) {
        uint16_t id=(uint16_t)slots[i];
        int key=(i+1)%10;
        out[4+2*key]=(uint8_t)(id>>8);
        out[5+2*key]=(uint8_t)id;
    }
    memcpy(out+24,settings,17);
    return 41;
}
