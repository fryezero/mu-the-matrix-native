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

/* 0x01285995..0x012859b4 calls 0x00a00192 with a sign-extended packet word.
 * This field is +0x34, distinct from the progression counter at +0x30. */
int mu_skills_master_points_apply(uint8_t *attr, size_t cap, const uint8_t *frame, size_t n)
{
    if (!attr || cap < 0x38 || !frame || n < 8) return 0;
    int32_t points = (int16_t)((uint16_t)frame[6] | (uint16_t)frame[7] << 8);
    memcpy(attr + 0x34, &points, sizeof points);
    return 1;
}
