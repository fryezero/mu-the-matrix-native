#ifndef MU_CHARCREATE_H
#define MU_CHARCREATE_H

/* The create-character panel, the delete flow and the system menu of the character select
 * (NATIVE-CHARCREATE-001).
 *
 * The create panel is part of the CharacterSelect movie (Data\Interface\GFx\CharacterSelect.ozg,
 * see charsel_gfx.h); its game side is the same window object (GFx manager +0x22c).  The system
 * menu is the winSystemMenu movie (a KeyWindow, GFx manager window list 0x01d22c60).  The message
 * boxes are queued on the Caution window (GFx manager +0x90) and are reported as calls.  Authored C
 * for:
 *
 *   0x00b49bf4  the create panel shown or hidden (SetClassInfo, SetCreateVisible, the list's show)
 *   0x00b4b684  the class restriction of the rename mode: dead code in this client (no effect)
 *   0x00b4a442  SetSelectedClass: the creation-preview character 0x0a39d780 becomes the class's
 *               NewFace model 0x135 + class, and
 *   0x00b4a4a1  its pose: object angle, scale and the window's camera offset per class
 *   0x00b4a349  SetCreateBoardInfo: the preview's screen rectangle (window +0x88..+0x94)
 *   0x00b49eca  OnEnterCharacterName: the daily limit, the length, the name filters, the allowed
 *               characters, then the create (or rename) request
 *   0x00b4b29d  the name filters: FilterName(kor) 0x0110cb45 (substring) and Filter(kor)
 *               0x0110c9f2 (spaces removed 0x0110c960, MBCS-stepped search 0x0185c95d)
 *   0x00cdb9af  the allowed characters (ASCII letters and digits; CP949 double-byte rules)
 *   0x00b4b31a  UpdateInput: the name cut at 10 bytes
 *   0x00b49d0d  UpdateCreateCount (GlobalText 0x1831 with the creations left)
 *   0x00b4b2d6  the panel's reset; 0x00b4bf25 the list row; 0x00b4c806 / 0x00b49c82 / 0x00b49ca0
 *   0x0122b648  the server's answer to a create request (the character-created handler)
 *   0x00b49967  the window's message-box results (create errors, the three delete steps)
 *   0x00b4a0da  the delete request; 0x012326c4 the server's answer to it
 *   0x00b4a14c  the preview's render (camera, viewport, RenderObject) and its hook 0x00b49cd7
 *   0x0139ca62  the server class code -> class byte
 *   0x0139cc2e  the class name (GlobalText index by skin index; table executed from the client)
 *   0x00c8c8b1  the system menu toggled (Esc, the Menu button); 0x00c8ce3d the scene's windows
 *   0x00c8cd17  the menu's InitText; 0x00c8c6be its events (onLoad, onClose, onExit,
 *               onServerSelectClick, onCharSelectClick, onOptionClick)
 *
 * Every GFx call and every call into another subsystem is reported as one line through the list
 * environment's emit, in client order, as in charsel_gfx.h ("invoke METHOD JSON", "call ADDRESS
 * ARGS").  Extra argument forms: "p" = the creation-preview CHARACTER 0x0a39d780, "p+OFF" a field of
 * it, "w" = the CharacterSelect window, floats as hex bit patterns, strings as JSON.  Message boxes:
 *
 *   call 00b3967c OWNER ID TEXT TITLE BUTTON TEXTTYPE MODE      one button (Caution UI type 1)
 *   call 00b39648 OWNER ID TEXT TITLE BUTTON1 BUTTON2 TEXTTYPE MODE   two buttons (UI type 0)
 *   call 00b3974a OWNER ID TEXT TITLE LENGTH TEXTTYPE MODE      password input (UI type 4)
 *
 * The menu's invokes go to its KeyWindow ("invoke METHOD JSON" as well).
 *
 * scripts/validate_charcreate.py runs the client's instructions in Unicorn and compares these
 * lines, the window fields, the preview record, the character records and the globals. */

#include <stddef.h>
#include <stdint.h>

#include "charsel_gfx.h"

#define MU_CCR_NAME_MAX 10            /* the name field of the packets and the input box */
#define MU_CCR_PREVIEW_MODEL 0x135    /* NewFace01.bmd; class c uses 0x135 + c (Data\Logo\NewFaceNN) */
#define MU_CCR_CLASSES 16

/* CharacterSelect window fields of the create panel and the delete flow. */
typedef struct mu_ccr_window {
    uint8_t create_open;              /* +0x78 the create panel is shown */
    uint8_t flag_79;                  /* +0x79 a delete is pending (blocks the movie's callbacks) */
    int32_t created;                  /* +0x7c characters created today */
    int32_t limit;                    /* +0x80 daily creation limit */
    int32_t board[4];                 /* +0x88..+0x94 preview rectangle x, y, w, h (screen pixels) */
    int32_t delete_target;            /* +0x98 slot being deleted (-1 none) */
    uint8_t rename_mode;              /* +0x9c the panel renames a character */
    float camera_offset[3];           /* +0xb4 preview camera offset (per class) */
} mu_ccr_window;

typedef struct mu_ccr_env {
    const mu_csg_env *gfx;            /* emit, GlobalText, CharactersClient, SelectedHero, shown */
    uint8_t *preview;                 /* CHARACTER 0x0a39d780 (MU_CHARSEL_RECORD bytes) */
    int32_t *protocol_state;          /* 0x06fca2c4 */
    uint8_t *init_scene;              /* InitCharacterScene 0x0bdc5ca2 */
    float *camera_fov;                /* CameraFOV 0x01cf1634 */
    /* Filter(kor) 0x06fbac88 and FilterName(kor) 0x06fbacd0: their string vectors (+0x38) */
    const char *const *filter;
    int32_t filter_count;
    const char *const *filter_name;
    int32_t filter_name_count;
    /* _ismbblead 0x019ac155 under the client's multibyte code page; NULL: no lead bytes */
    int (*lead_byte)(void *context, uint8_t c);
    /* the movie window's origin and scale (0x00aae509, 0x00aae601, 0x00abedc3) */
    float window_x, window_y, window_scale;
    int32_t screen_width, screen_height; /* 0x01cf1624 / 0x01cf1628 */
    uint8_t animation_running;        /* 0x013960d2 (the preview's animation step) returns this */
    uint8_t base_render;              /* 0x00aadcbf (the window base's render) returns this */
    /* system menu */
    int32_t scene;                    /* SceneFlag 0x01d1df70 (0x009b0bc1) */
    uint8_t menu_open;                /* menu window +0x1c (0x00acd949) */
    uint8_t menu_check;               /* 0x00c8cbe2: nothing blocks leaving (saves the macros) */
    uint8_t shutdown_blocked;         /* 0x00c8cfa6 */
} mu_ccr_env;

/* The server's answer to a create request (0x0122b648 reads these packet bytes). */
typedef struct mu_ccr_created {
    uint8_t result;                   /* +0x04: 1 created, 0 name refused, 2 no slot, 5 event period */
    char name[MU_CCR_NAME_MAX];       /* +0x05 */
    uint8_t slot;                     /* +0x0f */
    uint16_t level;                   /* +0x10 */
    uint8_t class_code;               /* +0x12 server class code (0x0139ca62) */
    uint8_t limit;                    /* +0x2b */
    uint8_t created;                  /* +0x2c */
} mu_ccr_created;

/* 0x00b49bf4 */
void mu_ccr_show_create(mu_csg_window *list, mu_ccr_window *w, const mu_ccr_env *e, uint8_t flag);
/* 0x00b4b684 (no effect in this client) */
void mu_ccr_restrict_classes(mu_ccr_window *w, const mu_ccr_env *e);
/* 0x00b4a442 */
void mu_ccr_set_selected_class(mu_ccr_window *w, const mu_ccr_env *e, uint8_t class_index);
/* 0x00b4a4a1 */
void mu_ccr_preview_pose(mu_ccr_window *w, const mu_ccr_env *e);
/* 0x00b4a349 */
void mu_ccr_board_info(mu_ccr_window *w, const mu_ccr_env *e, int32_t x, int32_t y, int32_t width, int32_t height);
/* 0x00b49eca: name = the client's bytes (code page), length = its size */
void mu_ccr_enter_name(mu_ccr_window *w, const mu_ccr_env *e, const char *name, size_t length, int32_t class_index);
/* 0x00b4b29d: 1 when a filter word matches */
int mu_ccr_name_filtered(const mu_ccr_env *e, const char *name, size_t length);
/* 0x00cdb9af: 1 when the name has a character the client refuses */
int mu_ccr_name_invalid(const mu_ccr_env *e, const char *name);
/* 0x00b4b31a */
void mu_ccr_update_input(const mu_ccr_env *e, const char *text);
/* 0x00b49d0d */
void mu_ccr_update_count(mu_ccr_window *w, const mu_ccr_env *e, int32_t created, int32_t limit);
/* 0x00b4b2d6 */
void mu_ccr_reset_create(const mu_ccr_env *e);
/* 0x00b4bf25 */
void mu_ccr_set_row(mu_csg_window *list, int32_t row);
/* 0x00b4c806 */
void mu_ccr_set_target(mu_ccr_window *w, int32_t slot);
/* 0x00b49c82 (CCharSelMainWin's delete confirmation), 0x00b49ca0 */
void mu_ccr_delete_pending(mu_ccr_window *w, int32_t slot);
void mu_ccr_delete_clear(mu_ccr_window *w);
/* 0x0122b648 */
void mu_ccr_created_answer(mu_csg_window *list, mu_ccr_window *w, const mu_ccr_env *e, const mu_ccr_created *p);
/* 0x00b49967: button 0 OK, 1 cancel; text = the input box's text (or NULL) */
void mu_ccr_message_result(mu_csg_window *list, mu_ccr_window *w, const mu_ccr_env *e, int32_t id, int32_t button,
                           const char *text);
/* 0x00b4a0da */
void mu_ccr_delete_request(const mu_ccr_env *e, const char *password);
/* 0x012326c4: result 1 deleted, 0 guild, 3 item block, other wrong password */
void mu_ccr_delete_answer(mu_csg_window *list, mu_ccr_window *w, const mu_ccr_env *e, uint8_t result);
/* 0x00b4a14c */
void mu_ccr_render_preview(mu_ccr_window *w, const mu_ccr_env *e);
/* 0x00b49cd7: returns the hook's AL */
int mu_ccr_render_hook(mu_ccr_window *w, const mu_ccr_env *e);
/* 0x0139ca62 */
uint8_t mu_ccr_class_from_server(uint8_t code);
/* 0x0139cc2e(class, flag): GlobalText index of the class name */
int32_t mu_ccr_class_name_text(uint8_t class_byte, uint8_t flag);

/* The preview's pose per class (0x00b4a4a1, values executed from the client). */
typedef struct mu_ccr_pose {
    float camera_offset[3];
    float angle[3];
    float scale;
    uint8_t sets_angle;               /* 0 for class 6: its case leaves the angle as CreateCharacter set it */
} mu_ccr_pose;
extern const mu_ccr_pose mu_ccr_poses[MU_CCR_CLASSES];

/* System menu (winSystemMenu). */
/* 0x00c8c8b1 */
void mu_csm_toggle(mu_csg_window *list, const mu_ccr_env *e);
/* 0x00c8ce3d */
void mu_csm_scene_windows(mu_csg_window *list, const mu_ccr_env *e, uint8_t flag);
/* 0x00c8cd17 */
void mu_csm_init_text(const mu_ccr_env *e);
/* 0x00c8c6be */
void mu_csm_event(mu_csg_window *list, const mu_ccr_env *e, const char *name);

/* The window's record offsets used here. */
#define MU_CCR_OBJ_ACTION_FLAG 0x3b   /* OBJECT +0x3b, cleared by SetSelectedClass */
#define MU_CCR_OBJ_FLAG_3 0x03        /* OBJECT +0x03, cleared by SetSelectedClass */

#endif
