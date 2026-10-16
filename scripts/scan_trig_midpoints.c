/* Find binary32 arguments whose host binary64 sin/cos result lies within a few
 * binary64 ULPs of a binary32 rounding midpoint. Only such arguments can round
 * differently when two binary64 trig implementations differ by that many ULPs.
 * Output lines: "<sin|cos> <argument bits hex> <distance in binary64 ULPs>".
 * Usage: scan_trig_midpoints [window_ulps] [limit_exclusive]. Default 4, 90112.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void check(const char *name, uint32_t argument, double value, int64_t window)
{
    double magnitude = fabs(value);
    if (!(magnitude >= 0x1p-126) || magnitude > 0x1.fffffep127)
        return;
    uint64_t bits;
    memcpy(&bits, &value, sizeof bits);
    int64_t low = (int64_t)(bits & ((UINT64_C(1) << 29) - 1));
    int64_t distance = llabs(low - (INT64_C(1) << 28));
    if (distance <= window)
        printf("%s %08x %lld\n", name, argument, (long long)distance);
}

int main(int argc, char **argv)
{
    int64_t window = argc > 1 ? atoll(argv[1]) : 4;
    float limit = argc > 2 ? strtof(argv[2], NULL) : 90112.0f;
    for (uint32_t bits = 1; bits < 0x7f800000u; ++bits) {
        float argument;
        memcpy(&argument, &bits, sizeof argument);
        if (argument >= limit)
            break;
        check("sin", bits, sin((double)argument), window);
        check("cos", bits, cos((double)argument), window);
    }
    return 0;
}
