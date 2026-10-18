/* Reconstructed tooltip-text formatter cases (see tooltip_format.h).  The
 * client's sprintf is the C library's; here snprintf with the same format
 * (the itemtooltiptext formats use %d, %s and %%). */
#include "tooltip_format.h"

#include <stdio.h>
#include <string.h>

#pragma clang diagnostic ignored "-Wformat-nonliteral"
#pragma clang diagnostic ignored "-Wformat-security"

static void fmt1(char *out, const char *fmt, int32_t a)
{
    snprintf(out, 0x100, fmt, a);
}

static void lacking(int32_t *color, int32_t *text_color, int32_t line)
{
    *color = 2;
    if (text_color)
        text_color[line - 1] = *color;
}

int mu_tooltip_format(char out[0x100], const char *fmt, int32_t type, const mu_ttf_item *item,
                      int32_t item_level, const mu_ttf_inputs *in, int32_t line, int32_t *color,
                      int32_t *text_color)
{
    memset(out, 0, 0x100);
    switch (type) {
    case 1:                                            /* 0x00f10f2e */
        fmt1(out, fmt, item->durability);
        return 0;
    case 2: {                                          /* 0x00f10f4d */
        int32_t bonus = in->socket_defense + in->harmony_defense;
        fmt1(out, fmt, (int32_t)item->defense + bonus);
        if (bonus != 0)
            *color = 3;
        else if (in->kind_a_3 && !in->kind_b_f && (item->field_3a & 0x3f) > 0)
            *color = 1;
        return 0;
    }
    case 4:                                            /* 0x00f11076 */
        snprintf(out, 0x100, fmt, (int32_t)item->durability, (int32_t)item->max_durability);
        return 0;
    case 5: {                                          /* 0x00f1109d */
        int32_t req = in->special_level_item ? in->special_level : (int32_t)in->req_level;
        fmt1(out, fmt, req);
        if (in->hero_level < req) {
            *color = 2;
            if (text_color)
                text_color[line] = *color;
        }
        return 0;
    }
    case 6: {                                          /* 0x00f11160 */
        int32_t v = (int32_t)in->req_strength - in->stat_cut_strength;
        if (v > 0)
            fmt1(out, fmt, v);
        return 0;
    }
    case 7: {                                          /* 0x00f111c7 */
        int32_t v = (int32_t)in->req_agility - in->stat_cut_agility;
        if (v > 0)
            fmt1(out, fmt, v);
        return 0;
    }
    case 9:                                            /* 0x00f11260 */
        if (in->req_energy > 0)
            fmt1(out, fmt, in->req_energy);
        return 0;
    case 11:                                           /* 0x00f112c4 */
        fmt1(out, fmt, item->magic_power);
        return 0;
    case 13:                                           /* 0x00f113c1 */
        if (in->manager_1c != -1 || item_level >= 5)
            snprintf(out, 0x100, fmt);                 /* sprintf(buf, fmt): fmt is the format */
        return 0;
    case 101:                                          /* 0x00f11656 */
        fmt1(out, fmt, item->attack_speed);
        return 0;
    case 201: {                                        /* 0x00f120e0 */
        int32_t req = in->special_level_item ? in->special_level : (int32_t)in->req_level;
        if (in->hero_level < req) {
            fmt1(out, fmt, req - in->hero_level);
            lacking(color, text_color, line);
        }
        return 0;
    }
    case 202:                                          /* 0x00f12201 */
        if ((int32_t)in->hero_strength < (int32_t)in->req_strength - in->stat_cut_strength) {
            fmt1(out, fmt, (int32_t)in->req_strength - (int32_t)in->hero_strength - in->stat_cut_strength);
            lacking(color, text_color, line);
        } else if (in->stat_cut_strength != 0) {
            *color = 3;
        }
        return 0;
    case 203:                                          /* 0x00f122ce */
        if ((int32_t)in->hero_agility < (int32_t)in->req_agility - in->stat_cut_agility) {
            fmt1(out, fmt, (int32_t)in->req_agility - (int32_t)in->hero_agility - in->stat_cut_agility);
            lacking(color, text_color, line);
        } else if (in->stat_cut_agility != 0) {
            *color = 3;
        }
        return 0;
    case 205:                                          /* 0x00f1242e */
        if ((int32_t)in->hero_energy < (int32_t)in->req_energy) {
            fmt1(out, fmt, (int32_t)in->req_energy - (int32_t)in->hero_energy);
            lacking(color, text_color, line);
        }
        return 0;
    default:
        return MU_TTF_UNSUPPORTED;
    }
}
