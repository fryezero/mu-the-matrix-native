/* Reconstructed tooltip-text formatter cases (NATIVE-HUD-001).
 *
 * 0x00f1098a(this, ret, fmt, line, &color, type, item, item_level, -1)
 * formats one itemtooltiptext line (NATIVE-DATA-001/002: the text's `type`
 * field selects the case) with sprintf into a 0x100-byte buffer and may
 * change the line colour.  The builder 0x00f0eb44 calls it for each of an
 * itemtooltip record's 15 lines.  This file restates the cases for the
 * types below, which carry most installed lines; other types return
 * MU_TTF_UNSUPPORTED.
 *
 * Values the cases take from other systems are inputs (mu_ttf_inputs):
 * item requirement getters (0x00cd27eb strength, 0x00cd2832 agility,
 * 0x00cd2879 energy, 0x00cd298d level; they consult server rules and code
 * special cases), the hero (0x01d1df1c: level + master level 0x00a00367,
 * strength +0x18a, agility +0x18c, energy +0x190), the harmony/socket stat
 * reduction 0x00f13774, the socket defense bonus (0x011df8b9) and the
 * harmony defense bonus (0x00cbc335), and two item-kind predicates.
 */
#ifndef MU_HUD_TOOLTIP_FORMAT_H
#define MU_HUD_TOOLTIP_FORMAT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_ttf_item {
    uint8_t durability;         /* +0x38 */
    uint8_t max_durability;     /* +0x39 */
    uint8_t field_3a;           /* +0x3a (low 6 bits: an option level) */
    uint16_t defense;           /* +0x22 */
    int32_t magic_power;        /* +0x28 */
    uint8_t attack_speed;       /* Item.bmd +0x266 */
} mu_ttf_item;

typedef struct mu_ttf_inputs {
    uint16_t req_strength, req_agility, req_energy, req_level;   /* 0x00cd27eb/2832/2879/298d */
    uint8_t special_level_item; /* 0x00f1425b: code 0x1a1e and others */
    int32_t special_level;      /* 0x00f142b1 */
    int32_t hero_level;         /* 0x00a00367 */
    uint16_t hero_strength, hero_agility, hero_energy;   /* hero +0x18a, +0x18c, +0x190 */
    int32_t stat_cut_strength, stat_cut_agility;         /* 0x00f13774 outputs (first and second) */
    int32_t socket_defense;     /* 0x011df8b9 result (+0x24 when its flag +0x34 is set, else 0) */
    int32_t harmony_defense;    /* sum of the two 0x00cbc335 values when harmony type 3 is active, else 0 */
    uint8_t kind_a_3, kind_b_f; /* item kind A == 3, kind B == 0xf */
    int32_t manager_1c;         /* tooltip manager +0x1c */
} mu_ttf_inputs;

enum { MU_TTF_UNSUPPORTED = -1 };

/* Formats line `line` of type `type`.  `out` gets the buffer contents
 * (at most 0xff bytes plus terminator); *color may change.  Type 5 also
 * writes text_color[line] and the "lacking" types 201..205 write
 * text_color[line - 1] (the requirement line above turns red), as the
 * client writes TextListColor (text_color may be NULL).  Returns 0, or
 * MU_TTF_UNSUPPORTED for other types. */
int mu_tooltip_format(char out[0x100], const char *fmt, int32_t type, const mu_ttf_item *item,
                      int32_t item_level, const mu_ttf_inputs *in, int32_t line, int32_t *color,
                      int32_t *text_color);

#ifdef __cplusplus
}
#endif

#endif
