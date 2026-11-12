#include "secondary.h"
/* 0x009bfabd, inserted for keys 0..389 by 0x009bfd63. */
int32_t mu_mv_riding_action(int32_t a)
{
    switch (a) {
    case 1: case 2: case 3: case 7: case 10: case 11: case 12: case 13: case 14:
    case 15: case 16: case 17: case 19: case 21: case 22: case 23: case 24: case 26:
    case 29: case 31: case 32: case 33: case 34: case 35: case 36: case 38: case 39:
    case 40: case 41: case 42: case 43: case 44: case 45: case 46: case 156:
    case 218: case 219: case 220: case 221: case 222: case 224: case 225: case 226: case 227:
    case 315: case 316: case 317: case 318: case 319: case 320: case 321: case 322:
    case 323: case 324: case 325: case 326: case 327: return 0;
    case 65: case 66: case 67: case 68: case 69: case 71: case 72: case 73: case 74:
    case 75: case 76: case 77: case 98: case 100: case 101: case 102: case 103:
    case 104: case 105: case 106: case 107: case 108: case 109: return 2;
    case 248: case 249: case 280: case 281: case 282: case 285: case 286: case 287:
    case 288: case 289: case 290: case 291: case 292: case 293: case 294: case 295:
    case 296: case 297: case 298: case 299: case 300: case 301: case 303: return 4;
    default: return -1;
    }
}
float mu_mv_riding_scale(int32_t model)
{
    if (model == 0x5cb || model == 0x5cc) return 0.6f;
    if (model >= 0x5cd && model <= 0x5d2) return 0.9f;
    return 1.0f;
}
float mu_mv_riding_speed(int32_t model, int32_t action)
{
    if (action == 2) {
        if (model == 0x5cb || model == 0x5cc) return 0.8f;
        if (model >= 0x5cd && model <= 0x5d2) return 0.4f;
    }
    return 0.3f;
}
int mu_mv_riding_admit(int owner, int hidden, int object, int live, int buff26,
                     int32_t selected, int32_t item, int predicate)
{
    return owner && !hidden && object && live == 1 && !buff26 && selected == item && !predicate;
}
void mu_mv_riding_attachment(const float matrix[12], float scale, float out[3])
{
    for (int k = 0; k < 3; ++k) out[k] = matrix[k * 4 + 3] * scale;
}
