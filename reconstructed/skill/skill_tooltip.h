#ifndef MU_SKILL_TOOLTIP_H
#define MU_SKILL_TOOLTIP_H

/* The skill tooltip (NATIVE-SKILL-001, docs/research/client-skills.md).
 *
 *   main.onSkillTooltip  0x00c7070d: the stamp manager's entry of the hovered skill (0x01096aa7), the
 *                        SkillInfoPopup handler (GfxMgr + 0x218) shows it at (x + w/2, y) (0x00c1ef6b)
 *   builder              0x0117da56 (this = the SkillTooltipText table 0x0117d758, map<u16, record*> at
 *                        +4): fills the classic text list (TextList 0x10c76988, 80 lines of 0xff bytes,
 *                        TextListColor 0x10c7b938, TextBold 0x10c7ba78)
 *   text wrap            0x011ffb3a -> 0x011ff794 -> 0x01193941 (lines cut by GDI width)
 *   value text           0x0117eab5 with 0x0117efb7 / 0x0117eedc / 0x0117ef2c / 0x0117ee8e
 *   popup                0x00c1f2b0: title = line 0, body = lines 1..n-1 through the HTML line builder
 *                        0x00ab4dc0 ("\n" lines give <BR>), both ANSI -> UTF-8, then
 *                        SetInfoPopupSkillStamp("%d %d %d %d %s %s %d", x, y, w, h, title, body, 0)
 *
 * The builder begins with a call into a runtime module (0x0117db7a -> 0x10b3efb0, 72 NOP bytes, the
 * same patch as the item tooltip builder's header): opaque.  Entries of TextListColor/TextBold the
 * builder does not write keep whatever an earlier tooltip left; this C leaves them 0 (set[] marks the
 * written ones).
 *
 * sprintf: the client's 0x009619dd (vsprintf) is the formatting boundary; mu_skill_format restates the
 * conversions the tables use (d i u x X c s f F e E g G %%, flags, width, precision). */

#include <stddef.h>
#include <stdint.h>

#include "skill_table.h"
#include "skill_use.h"

#ifdef __cplusplus
extern "C" {
#endif

#define MU_SKILL_TIP_LINES 80
#define MU_SKILL_TIP_WIDTH 0xff

typedef struct mu_skill_tip_text {    /* SkillTooltipText.bmd record (808 bytes; reconstructed/data layout) */
    uint16_t skill;                   /* +0x000 */
    char name[256];                   /* +0x002 */
    int32_t name_color;               /* +0x104 */
    int32_t condition1;               /* +0x108 0 always, 1 learned, 2 not learned (0x0117ea69) */
    char text1[256];                  /* +0x10c */
    int32_t color1;                   /* +0x20c */
    int32_t condition2;               /* +0x210 */
    char text2[256];                  /* +0x214 */
    int32_t color2;                   /* +0x314 */
    int32_t value_a, value_b;         /* +0x318, +0x31c (-1: none) */
    int32_t value_float;              /* +0x320 */
    int32_t value_cap;                /* +0x324 (-1: none) */
} mu_skill_tip_text;
/* Decode a record from its 808 bytes. */
void mu_skill_tip_text_decode(const uint8_t raw[808], mu_skill_tip_text *out);

typedef struct mu_skill_tip_env {
    const mu_skill_env *skills;       /* table, class index, base skill, class tree */
    void *user;
    const char *(*text)(void *u, int32_t index);                 /* GlobalText 0x0095f027 */
    const mu_skill_tip_text *(*tip)(void *u, uint16_t skill);    /* the table's map at +4 */
    /* GetSkillInformation(skill, 1, NULL, &mana, &distance, &ag) */
    void (*info)(void *u, int32_t skill, int32_t *mana, int32_t *distance, int32_t *ag);
    /* master-skill manager: 0x00bb1e55 [0], 0x00bb1df9 [0], 0x00bb1ca1 [0] */
    int (*master_is)(void *u, int32_t skill);
    int (*master_kind)(void *u, int32_t skill);
    float (*master_float)(void *u, int32_t skill);
    float (*formula)(void *u, int32_t quotient, int32_t remainder, int32_t stat);  /* 0x0117b5eb [0] */
    /* GetTextExtentPointA's cx of text[0..n) on the interface font (the wrap's measure) */
    int32_t (*measure)(void *u, const char *text, int32_t n);
    float text_scale;                 /* [0x06fbcd94]: the wrap width factor */
} mu_skill_tip_env;

typedef struct mu_skill_tip_input {
    int32_t base, learned;            /* the stamp manager entry +0 / +4 (0: not learned) */
    uint8_t stamped;                  /* +8 */
    int32_t imprint_level;            /* the builder's second argument (SkillStampFrame handler +0x80, truncated) */
    int16_t weapon_index;             /* hero + 0x19ac (Force Wave's title) */
    uint16_t weapon_word;             /* [0x01d1df18] + 0x1bb8 */
    int32_t skill_damage;             /* [0x01d1df18] -> 0x00a01692(skill) */
    float option_13, option_7e;       /* 0x009953ef(0x13) / (0x7e) -> 0x009e0782 */
    int32_t damage_bonus;             /* [0x06fb4528] */
    uint16_t strength, agility, vitality, energy, command;   /* [0x01d1df1c] + 0x18a.. */
    uint16_t stat_19c;                /* [0x01d1df1c] + 0x19c (added to vitality for the formula) */
} mu_skill_tip_input;

typedef struct mu_skill_tip {
    char lines[MU_SKILL_TIP_LINES][256];
    int32_t color[MU_SKILL_TIP_LINES], bold[MU_SKILL_TIP_LINES];
    uint8_t set[MU_SKILL_TIP_LINES];  /* the builder wrote color/bold of that line */
    int count;
    int32_t mastery;                  /* the popup's second argument (record +0x50, as a byte) */
} mu_skill_tip;

/* 0x0117da56: returns 1 and fills `out` (count lines), or 0 when there is no tooltip (no SkillTooltipText
 * record, or the skill is absent from Skill(Kor)). */
int mu_skill_tooltip_build(const mu_skill_tip_env *env, const mu_skill_tip_input *in, mu_skill_tip *out);

/* 0x011ff794 + 0x01193941: cut `text` at '#' (each piece gets a leading space) and by width (width *
 * text_scale, GDI cx of the prefix), at most max_lines lines of `stride` bytes.  Returns the line count. */
int mu_skill_wrap(const mu_skill_tip_env *env, const char *text, int32_t width, char *out, int max_lines,
                  int stride);

/* 0x00c1f2b0 before the UTF-8 conversion: title and body HTML. */
void mu_skill_tooltip_html(const mu_skill_tip *tip, char *title, size_t title_cap, char *body, size_t body_cap);

/* The client's sprintf for one argument of a table format: kind 'i' (int), 'f' (double), 's' (string),
 * or 0 (no argument).  Returns the length written (out always terminated when cap > 0). */
size_t mu_skill_format(char *out, size_t cap, const char *fmt, int kind, int32_t ivalue, double fvalue,
                       const char *svalue);

#ifdef __cplusplus
}
#endif

#endif
