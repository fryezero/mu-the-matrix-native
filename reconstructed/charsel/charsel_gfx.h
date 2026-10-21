#ifndef MU_CHARSEL_GFX_H
#define MU_CHARSEL_GFX_H

/* The character-select GFx window of the client (NATIVE-CHARSEL-003).
 *
 * The list of characters on the right of the select screen, its selection
 * arrows and the create-character panel are the movie CharacterSelect
 * (Data\Interface\GFx\CharacterSelect.ozg).  The game side is the window
 * object at GFx manager +0x22c (0x00ac3bf7()->+0x22c) and its callback
 * handler (vtable 0x01a8b520, +0x10 = the window).  Authored C for:
 *
 *   0x00b4b82c  fill and show (CreateCharacterScene, a character exists)
 *   0x00b4b848  show(flag): SelectIndex, SetSelectVisible, SetCharSelArrow
 *   0x00b4b927  the list: SetSelectText with ten rows built from the
 *               CharactersClient records behind the row -> slot map +0xa8
 *   0x00b4bd6c  a row clicked (enter: double click): selection or the
 *               create-character panel, CCharSelMainWin UpdateDisplay, entry
 *   0x00b4bed3  SelectIndex(slot)
 *   0x00b4bfc2  the reorder arrows (onCharSelArrow)
 *   0x00b4c1df  the movie's callbacks (ExternalInterface.call)
 *   0x00b4915b  the window's initialisation: SetInputBoxLength, InitText,
 *               InitStat, InitClassInfo (0x00b4aef1, 16 classes), SetClassInfo,
 *               SetnumViewableSelctedWin
 *   0x00ab4dc0  the HTML text helper (colour table, "&lt;", <font>), and
 *   0x0096fe90  its RGBA variant (static readings, see the .c file).
 *
 * Every GFx call and every call into another subsystem is reported in
 * client order as one text line through env->emit:
 *
 *   invoke METHOD JSON      a GFx Invoke on the window's movie; JSON is the
 *                           argument array (the value API's objects and
 *                           arrays, or the printf-style format's arguments);
 *   call ADDRESS ARGS       a call into a routine that is not part of this
 *                           reconstruction (hex address, decimal or rN
 *                           arguments; rN = the character record of
 *                           CharactersClient index N).
 *
 * scripts/validate_charsel_gfx.py runs the client's instructions in Unicorn
 * with the GFx value API stubbed and compares these lines, the window state
 * and the selection globals. */

#include <stddef.h>
#include <stdint.h>

#include "charsel.h"

#define MU_CSG_ROWS 10
#define MU_CSG_CLASSES 16
#define MU_CSG_LINE 16384   /* InitClassInfo with the real class texts is about 6 KB */

/* The window fields these routines use. */
typedef struct mu_csg_window {
    int32_t row;                     /* +0xa0 selected row */
    int32_t count;                   /* +0xa4 rows the account may use (the arrow bound) */
    uint8_t slots[MU_CSG_ROWS];      /* +0xa8 row -> CharactersClient index (0xff: none) */
} mu_csg_window;

typedef struct mu_csg_env {
    void *context;
    mu_charsel_character_fn character;                      /* CharactersClient (0x0095f6db + 0x009a13f4) */
    const char *(*global_text)(void *context, int32_t index); /* GlobalText 0x0095f027 / 0x011753c3 */
    const char *(*class_name)(void *context, int32_t class_byte); /* 0x0139cc2e(class, 1) */
    /* The character's name (std::string at CHARACTER +0x3658, read through
     * 0x0129deaa); NULL: the record's inline short string. */
    const char *(*name)(void *context, const uint8_t *record);
    void (*emit)(void *context, const char *line);
    int32_t *selected;               /* SelectedHero 0x01cf1864 */
    int32_t *shown;                  /* the shown character 0x01cf1154 */
    uint8_t slot_mode;               /* 0x0095f75d()->+4: the account's slot limit applies */
    int32_t slot_limit;              /* 0x010a5cf2()->+0x44 */
    uint8_t enter_refused;           /* CCharSelMainWin 0x009a5029 returns 1 */
    uint8_t gfx_busy;                /* GFx manager +0x90 -> 0x00aae6f9() */
    uint8_t window_flag_79;          /* window +0x79 (0x009a59f6) */
    uint8_t base_ready;              /* 0x00aadbc3() (the window's base initialisation) */
} mu_csg_env;

/* A callback argument as the movie passes it (GFx value: number, bool or string). */
typedef struct mu_csg_arg {
    int type;                        /* 3 number (also bool), 4 string (0x00aad334 types) */
    double number;
    const char *string;
} mu_csg_arg;

/* 0x00b4b927 */
void mu_csg_build_list(mu_csg_window *w, const mu_csg_env *env);
/* 0x00b4b848 */
void mu_csg_show(mu_csg_window *w, const mu_csg_env *env, uint8_t flag);
/* 0x00b4b82c: build_list, then show(1) */
void mu_csg_fill_and_show(mu_csg_window *w, const mu_csg_env *env);
/* 0x00b4bed3 */
void mu_csg_select_index(mu_csg_window *w, const mu_csg_env *env, int32_t slot);
/* 0x00b4bd6c (row is unsigned in the client: anything outside 0..9 returns) */
void mu_csg_select_row(mu_csg_window *w, const mu_csg_env *env, int32_t row, uint8_t enter);
/* 0x00b4bfc2 (up: the movie's argument, true for the upper arrow) */
void mu_csg_arrow(mu_csg_window *w, const mu_csg_env *env, uint8_t up);
/* 0x00b4c1df: the movie called `name` with `count` arguments. */
void mu_csg_callback(mu_csg_window *w, const mu_csg_env *env, const char *name, const mu_csg_arg *args,
                     int32_t count);
/* 0x00b4915b: returns the client's AL (0 when the base initialisation failed). */
int mu_csg_init(mu_csg_window *w, const mu_csg_env *env);

/* 0x00ab4dc0(out, text, colour, bold): "" for "" and "\n"; '<' -> "&lt;";
 * "<font color='C'>T</font><br>" (bold 1: "<b>T</b>"); C from the 22-entry
 * table (index 3 #FFCC19, out of range #FFFFFF). Returns out. */
char *mu_csg_html(char *out, size_t cap, const char *text, uint32_t colour, uint8_t bold);
/* 0x0096fe90(out, text, rgba, bold, ...): the same with "#rrggbb" from an
 * R | G<<8 | B<<16 word and no "<br>". */
char *mu_csg_html_rgba(char *out, size_t cap, const char *text, uint32_t rgba, uint8_t bold);

/* The class table of InitClassInfo (0x00b4aef1 -> 0x00b4b546 per entry). */
typedef struct mu_csg_class {
    int32_t button, type, name_gt;
    int32_t strength, dexterity, vitality, energy, charisma, explain_gt;
    uint8_t cannot_create;
} mu_csg_class;
extern const mu_csg_class mu_csg_classes[MU_CSG_CLASSES];

#endif
