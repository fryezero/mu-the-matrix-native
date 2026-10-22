/* The GFx interface layer of the native client (NATIVE-GFX-002, NATIVE-GFX-003).
 *
 * Plays the client's GFx windows (converted movies, native/gfx/gfxconvert.py
 * --bridge) through mugfx (Ruffle with the GFx patch series) over a host's
 * 3D view, and plays the game side of their boundary the way the client's
 * GFx manager and window handlers do (docs/research/client-hud.md,
 * docs/research/native-gfx.md):
 *
 *   main                bottom bar: HP/MP orbs, SD/AG bars, EXP bar
 *                       (mcExpBar), skill hotkeys (mcSkillHotKey), item hotkeys
 *                       (mcItemHotKey), menu buttons; its onHotKey opens windows;
 *   InventoryFrame      8 x 8 page over the reconstructed item grid
 *                       (reconstructed/hud/inv_grid.c) with pick/drop, right
 *                       click (requestItemSlotClickR) and hover tooltips;
 *   InfoPopup           item and skill tooltips (SetInfoPopup with the HTML the
 *                       host's tooltip pipeline builds);
 *   CharacterInfoFrame  character window filled from the hero values, stat
 *                       points spent through its "+" buttons (onClickButton);
 *   chat                chat window: Enter opens the input, typed text goes to
 *                       the movie's text field, Enter sends; local echo.
 *
 * mugfx is loaded at run time (dlopen), so a host builds without Rust; when
 * the library or the movies are missing, mu_gfx_layer_open fails cleanly.
 * Players are sized to each window's bounds (mugfx_set_view) and, with
 * `shared`, render into IOSurfaces that the GL compositor samples directly
 * (macOS); otherwise frames are read back and uploaded.  Only movies that
 * changed are rendered.
 *
 * NATIVE-GFX-003: when the movie directory holds base.swf, the bar, chat
 * and the other HUD movies run as in the client: one base movie (base.swf ->
 * ExternalBase.swf) whose UI loader loads the movies of the client's list
 * (LoadFrameFiles, static reading of the UIFrame handler 0x00c8f05d:
 * ImageData; Tooltip, Popups; main; ItemDurability, Chat, AlarmFrame,
 * topmenu, bufflist; hudPlayerName, hudMap, hudNotice), so the skill icons
 * (ImageData + the skill data the game sends to ASData) and the item hotkey
 * icons (the game's render target image0) appear.  Without base.swf the
 * layer plays main.swf and chat.swf on their own (NATIVE-GFX-002).  The
 * item windows get the client's placement (registry alignment, SetScale
 * below 700 pixels) and the host can draw the item models over them
 * (items callback, the per-window item pass 0x00abfcca).
 *
 * The movies and every render are client-derived and stay local. */
#ifndef MU_GFX_LAYER_H
#define MU_GFX_LAYER_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_gfx_layer mu_gfx_layer;

/* NATIVE-NPC-001 adds the NPC windows: npcdialogue (NpcDialogue.swf), NpcShop
 * and StorageInven; they are optional (opened when the movie is converted). */
/* NATIVE-SKILL-001 adds SkillInfoPopup (the skill tooltip) and SkillStampFrame (the Skill Imprint window that
 * puts skills on the bar), optional as well. */
enum { MU_GFX_MAIN, MU_GFX_INVENTORY, MU_GFX_TOOLTIP, MU_GFX_CHARACTER, MU_GFX_CHAT, MU_GFX_NPC_DIALOG,
       MU_GFX_NPC_SHOP, MU_GFX_STORAGE, MU_GFX_QUEST_PROGRESS, MU_GFX_MY_QUEST, MU_GFX_SKILL_POPUP,
       MU_GFX_SKILL_STAMP, MU_GFX_MOVE_COMMAND, MU_GFX_MOVIES };
/* NATIVE-MAP-001 adds MoveCommand (the Move window, optional); its callbacks and the base movie's other channels
 * (hudMap's showMap / baseMovie) go to the host's map hooks (mu_gfx_layer_set_map_hooks). */
/* NATIVE-QUEST-001 adds NpcQuestProgress (MU_GFX_QUEST_PROGRESS) and MyQuestInfo (MU_GFX_MY_QUEST), optional
 * like the NPC windows.  The layer does not drive them itself: the host runs the client's window code
 * (reconstructed/quest) and passes its invokes through mu_gfx_layer_invoke / mu_gfx_layer_show; the movies'
 * callbacks go to cfg.quest_call. */

/* Character values the windows show (demo values until a game feeds them). */
typedef struct mu_gfx_hero {
    char name[32], class_name[32];
    int32_t level, master_level, points;
    int32_t hp, max_hp, mp, max_mp, sd, max_sd, ag, max_ag;
    int64_t exp, exp_max;
    int32_t strength, agility, vitality, energy, command;
    int64_t zen, ruud;
} mu_gfx_hero;

/* The InfoPopup HTML for an item (the client's tooltip pipeline, see
 * reconstructed/hud/tooltip_html.c); returns 0 and writes UTF-8 HTML, or
 * non-zero to use the layer's minimal built-in tooltip. */
typedef int (*mu_gfx_tooltip_fn)(void *user, int32_t code, int32_t level, char *html, size_t cap);

/* One item model to draw over a window (NATIVE-GFX-003): the slot call of
 * the reconstructed slot pass 0x00ab6130 in 640 x 480 units for a stage of
 * stage_w x stage_h points, and the cell rectangle in stage points (top-left
 * origin).  select: the cursor is over the item (RenderItem3D spins it);
 * held: the item hangs at the cursor (RenderObjectScreen enlarges it 1.4x). */
typedef struct mu_gfx_item_draw {
    int32_t item;               /* layer item index */
    int32_t code, level, excellent;
    float slot[4];              /* x, y, w, h in 640 x 480 units */
    int32_t page_type, page_flag, type8_seen, frame_id;
    float rect[4];              /* stage points, top-left origin */
    float frame_scale;          /* window SetScale / 100 (handler +0x58) */
    float alpha;
    int select, held;
} mu_gfx_item_draw;

/* Draw item models over the current GL framebuffer.  The layer calls it
 * right after the window's movie, as the client's per-window item pass
 * 0x00abfcca does; the callee sets up glOrtho(0, stage_w, 0, stage_h, 20,
 * 2000) over the whole viewport (stage points; the viewport is in pixels). */
typedef void (*mu_gfx_items_fn)(void *user, const mu_gfx_item_draw *items, int n, int32_t stage_w, int32_t stage_h);

/* Render the item hotkey icons into the game image `image0` (w x h pixels,
 * RGBA rows bottom-up as glReadPixels returns them: the client renders them
 * into a GL texture and the bar's ItemHotKey draws it flipped).  Each item's
 * rect is its render rectangle in that image, top-left origin.  Returns 0
 * when it drew, else the layer draws stand-ins. */
typedef int (*mu_gfx_icons_fn)(void *user, const mu_gfx_item_draw *items, int n, uint8_t *rgba, int32_t w,
                               int32_t h);

/* A skill as the game sends it to the data movie (ASData skill.setSkillAll,
 * static reading of 0x00c5ebaa: Index, Magic_Icon, Name, Delay,
 * SkillUseType, MasteryType). */
typedef struct mu_gfx_skill {
    int32_t index, icon, delay, use_type, mastery;
    char name[64];
} mu_gfx_skill;

/* GlobalText[index] for the labels the client takes from Data\Lang.mpr
 * (NATIVE-LANG-001: native/core/mu_lang.c over the local plaintext); NULL
 * when unknown, then the layer keeps its stand-in. */
typedef const char *(*mu_gfx_text_fn)(void *user, int32_t index);

typedef struct mu_gfx_layer_config {
    const char *movie_dir;      /* main.swf, InventoryFrame.swf, ... */
    const char *lib_path;       /* libmugfx; NULL: $MU_GFX_LIB, then next to the executable / repository build */
    int32_t width, height;      /* window pixels (the movies' stage) */
    int shared;                 /* IOSurface sharing (macOS; a GL context must be current) */
    int full_stage;             /* 1: every player covers the whole window (no per-window views) */
    int demo;                   /* 1: animate the demo hero values (orbs, bars) */
    mu_gfx_tooltip_fn tooltip;
    void *tooltip_user;
    FILE *log;                  /* callbacks and invokes, or NULL */
    double scale;               /* window pixels per point (Retina 2); 0 = 1.  The movies lay
                                   themselves out in points, as in a 1x window of that size */
    /* NATIVE-GFX-003 */
    mu_gfx_items_fn items;      /* item models over the item windows (NULL: coloured stand-ins) */
    mu_gfx_icons_fn icons;      /* item hotkey icons (NULL: stand-ins) */
    void *items_user;
    int standalone;             /* 1: play main/chat on their own even when base.swf is present */
    int double_buffer;          /* shared: two surfaces per movie, no GPU wait before drawing
                                   (frames may show one frame late) */
    /* NATIVE-LANG-001 */
    mu_gfx_text_fn text;        /* GlobalText (menu, window and chat labels); NULL: stand-ins */
    void *text_user;
    /* NATIVE-NPC-001: demo price of an item (user = tooltip_user); selling gives a third. NULL: 0 */
    int64_t (*price)(void *user, int32_t code, int32_t level);
    /* NATIVE-LANG-002 (user = tooltip_user):
     * dialog_choice: npcdialogue's onClickSelectBtn(index); returns 1 when the host handled it (it re-sends the
     *   dialogue with mu_gfx_layer_npc_dialog or closes it), 0 for the layer's demo paging;
     * buff_tooltip: the InfoPopup HTML of a buff (the bufflist's onTooltip); 0 on success. */
    int (*dialog_choice)(void *user, int index);
    int (*buff_tooltip)(void *user, int32_t buff, char *html, size_t cap);
    /* price_ex: the client's ItemValue with its goldType (0 buy, 1 sell; reconstructed/price); preferred over
     * price for the shop list and selling.  tooltip_ex: the tooltip with its context (MU_GFX_TIP_*): the item
     * of NpcShop gets the buy line, an inventory item while NpcShop is open the sell line. */
    int64_t (*price_ex)(void *user, int32_t code, int32_t level, int gold_type);
    int (*tooltip_ex)(void *user, int32_t code, int32_t level, int context, char *html, size_t cap);
    /* NATIVE-QUEST-001 (user = tooltip_user):
     * quest_call: a callback of NpcQuestProgress / MyQuestInfo (name, JSON arguments; CloseWindow included);
     * dialog_wrapped: npcdialogue's NPCDialogTextWidth text (the client keeps it at +0x1d68);
     * window_key: a key the bar did not take (window hotkeys); returns 1 when the host used it. */
    void (*quest_call)(void *user, int movie, const char *name, const char *args_json);
    void (*dialog_wrapped)(void *user, const char *text);
    int (*window_key)(void *user, int vk);
} mu_gfx_layer_config;
enum { MU_GFX_TIP_PLAIN = 0, MU_GFX_TIP_SHOP, MU_GFX_TIP_SELL };

mu_gfx_layer *mu_gfx_layer_open(const mu_gfx_layer_config *config, char *error, size_t error_size);
void mu_gfx_layer_close(mu_gfx_layer *layer);
void mu_gfx_layer_resize(mu_gfx_layer *layer, int32_t width, int32_t height);

void mu_gfx_layer_set_hero(mu_gfx_layer *layer, const mu_gfx_hero *hero);
/* Skills the data movie knows (sent to ASData with skill.setSkillAll). */
void mu_gfx_layer_set_skills(mu_gfx_layer *layer, const mu_gfx_skill *skills, int n);
/* 1 when the HUD runs as the client's base movie (base.swf), 0 standalone. */
int mu_gfx_layer_base_mode(const mu_gfx_layer *layer);
/* Instance path of a HUD channel ("UIFrame", "ASData", "main", "chat", ...)
 * as the movies reported it, "" when unknown. */
const char *mu_gfx_layer_channel_path(const mu_gfx_layer *layer, const char *channel);
/* The location the top menu shows (map name, hero cell). */
void mu_gfx_layer_set_location(mu_gfx_layer *layer, const char *map, int x, int y);
/* IME composition text (SDL TEXTEDITING) shown in the chat input; "" ends it. */
int mu_gfx_layer_compose(mu_gfx_layer *layer, const char *utf8, int cursor);
const mu_gfx_hero *mu_gfx_layer_hero(const mu_gfx_layer *layer);
/* Put an item into the first free place of the inventory page (0x00ad49fb);
 * returns its index or -1 when it does not fit. */
int mu_gfx_layer_add_item(mu_gfx_layer *layer, int32_t code, int32_t level, int32_t width, int32_t height,
                          const char *name);

/* Input in window pixels.  mouse kind 0 move, 1 down, 2 up, 3 wheel (button =
 * lines); button 0 left, 1 right, 2 middle.  Returns 1 when the interface
 * took the event (the 3D world must not see it). */
int mu_gfx_layer_mouse(mu_gfx_layer *layer, int kind, int button, double x, double y);
/* Keys: Windows/Flash virtual key codes; mods 1 shift, 2 ctrl/cmd, 4 alt.
 * Returns 1 when the interface used the key (text entry, window hotkeys). */
int mu_gfx_layer_key(mu_gfx_layer *layer, int down, int vk, uint32_t codepoint, int mods);
int mu_gfx_layer_text(mu_gfx_layer *layer, const char *utf8);
/* 1 while a text field (chat input) has the keyboard. */
int mu_gfx_layer_text_active(const mu_gfx_layer *layer);
/* Cursor shape the movie under the mouse asked for: 0 arrow, 1 hand, 2 I-beam. */
int mu_gfx_layer_cursor(const mu_gfx_layer *layer);

void mu_gfx_layer_toggle(mu_gfx_layer *layer, int movie);
void mu_gfx_layer_show(mu_gfx_layer *layer, int movie, int open);
int mu_gfx_layer_is_open(const mu_gfx_layer *layer, int movie);
/* Chat: add a line (type 1 normal, 3 system, ...) as the server echo would. */
void mu_gfx_layer_chat(mu_gfx_layer *layer, int type, const char *name, const char *message);
/* Run a JSON-argument GFx invoke on a movie (tests, scripted runs). */
const char *mu_gfx_layer_invoke(mu_gfx_layer *layer, int movie, const char *path, const char *method,
                                const char *args_json);
/* NATIVE-MAP-001: the map host (world/world_gfx_map.c).  channel: a base-movie channel event the layer does not
 * play itself (channel name, the JSON arguments); window: a MoveCommand callback (UIInit and CloseWindow
 * included); key: a window hotkey before the layer's own (1 = used).  NULL detaches. */
typedef struct mu_gfx_map_hooks {
    void *user;
    void (*channel)(void *user, const char *channel, const char *args_json);
    void (*window)(void *user, int movie, const char *name, const char *args_json);
    int (*key)(void *user, int vk);
} mu_gfx_map_hooks;
void mu_gfx_layer_set_map_hooks(mu_gfx_layer *layer, const mu_gfx_map_hooks *hooks);
/* NATIVE-NAMES-001: set an AS2 property (path "a.b._x", JSON value) on a movie;
 * returns non-zero when the player accepted it. */
int mu_gfx_layer_set_variable(mu_gfx_layer *layer, int movie, const char *path, const char *value_json);
/* An AS2 property as JSON (valid until the next call), NULL when unavailable. */
const char *mu_gfx_layer_get_variable(mu_gfx_layer *layer, int movie, const char *path);
/* Called with each line the chat input sends (after the local echo). */
void mu_gfx_layer_set_chat_hook(mu_gfx_layer *layer, void (*hook)(void *user, const char *text), void *user);
/* The instance path of a movie's window (e.g. "_level0.g_mcInventory"). */
const char *mu_gfx_layer_path(const mu_gfx_layer *layer, int movie);
/* Window-pixel centre of an inventory cell (scripted input). */
int mu_gfx_layer_cell_center(const mu_gfx_layer *layer, int32_t cell, double *x, double *y);
/* View rectangle of a movie's player in stage points (pixels / scale). */
void mu_gfx_layer_view(const mu_gfx_layer *layer, int movie, int32_t rect[4]);

/* Advance the movies by dt (ms) and run the 40 ms game steps (feeds). */
void mu_gfx_layer_advance(mu_gfx_layer *layer, double dt_ms);
/* Render the movies that changed (GL context current when shared). */
void mu_gfx_layer_render(mu_gfx_layer *layer);
/* Composite the windows over the current GL framebuffer (OpenGL 2.1;
 * leaves matrices and the touched state as it found them). */
void mu_gfx_layer_draw_gl(mu_gfx_layer *layer);
/* Composite over an RGBA buffer (top row first) on the CPU: headless runs
 * without GL.  Renders the players by read-back. */
void mu_gfx_layer_composite(mu_gfx_layer *layer, uint8_t *rgba, int32_t width, int32_t height);

typedef struct mu_gfx_layer_stats {
    long renders[MU_GFX_MOVIES];
    double render_ms[MU_GFX_MOVIES], capture_ms[MU_GFX_MOVIES], upload_ms[MU_GFX_MOVIES];
    int32_t view[MU_GFX_MOVIES][4];
    long callbacks, invokes, steps, view_changes, gpu_waits;
    double gpu_wait_ms;         /* shared: total wait for the GPU before compositing */
    int shared;
} mu_gfx_layer_stats;
void mu_gfx_layer_stats_get(const mu_gfx_layer *layer, mu_gfx_layer_stats *out);

/* Inventory state for tests: held item index (-1 none), item cell, count. */
int mu_gfx_layer_held(const mu_gfx_layer *layer);
int mu_gfx_layer_item_cell(const mu_gfx_layer *layer, int item);
int mu_gfx_layer_item_count(const mu_gfx_layer *layer);
/* Items on the inventory page now (sold or stored ones are gone; NATIVE-NPC-001). */
int mu_gfx_layer_items_placed(const mu_gfx_layer *layer);
/* The item draws the inventory's item pass would hand to the items
 * callback now (slot pass outputs); returns the count. */
int mu_gfx_layer_item_draws(mu_gfx_layer *layer, mu_gfx_item_draw *out, int max);
/* Last chat line sent by the player ("" when none). */
const char *mu_gfx_layer_last_sent(const mu_gfx_layer *layer);

/* ---- NATIVE-LANG-002: the bufflist and the character window rows ----
 *
 * mu_gfx_layer_add_buff sends the bufflist's addBuff object (BuffType, isDebuff, isCashBuff, BuffDetailType for
 * non-debuffs; the host computes it as the client's handler 0x00c5f278 does, core/mu_lang); buffs added before
 * the movie loaded are sent at its onLoad.  The movie's onTooltip(BuffType, x, y) asks cfg.buff_tooltip. */
typedef struct mu_gfx_buff {
    int32_t buff;
    int is_debuff, is_cash, has_detail;
    int32_t detail;
} mu_gfx_buff;
int mu_gfx_layer_add_buff(mu_gfx_layer *layer, const mu_gfx_buff *buff);
int mu_gfx_layer_buff_count(const mu_gfx_layer *layer);

/* The character window's rows (CharacterInfoSetup through the row builder 0x00b3dedc, in its order).  label and
 * value are the HTML the client's line builder 0x00ab4dc0 makes of the label (colour) and of the value; the
 * layer fills the value of the rows it knows (value_key) from the hero, "-" otherwise. */
enum { MU_GFX_ROW_NONE = 0, MU_GFX_ROW_CLASS, MU_GFX_ROW_LEVEL, MU_GFX_ROW_POINTS, MU_GFX_ROW_STRENGTH,
       MU_GFX_ROW_AGILITY, MU_GFX_ROW_VITALITY, MU_GFX_ROW_ENERGY, MU_GFX_ROW_COMMAND, MU_GFX_ROW_DAMAGE };
typedef struct mu_gfx_char_row {
    int32_t type, id, sort, button, color, value_color, value_key;
    char label[128];            /* plain text (the layer builds the HTML) */
} mu_gfx_char_row;
void mu_gfx_layer_set_char_rows(mu_gfx_layer *layer, const mu_gfx_char_row *rows, int n);

/* ---- NPC windows (NATIVE-NPC-001, docs/research/client-npc-interaction.md) ----
 *
 * The client opens them from its talk-result handler (ReceiveTalk
 * 0x01280659); the invokes follow the window handlers' static readings:
 * npcdialogue's open 0x00be842c (SetTitle with the NPC name,
 * VisibleContribute(0), SetDialogueMentDivide(text, ";") -> the movie's
 * NPCDialogTextWidth callback -> SetDialogueMent per page,
 * SetSelectBtnContent "1. ...;2. ...;", SetPosLeftCenter); NpcShop and
 * StorageInven are slot windows like the inventory (8 x 15 pages over the
 * reconstructed item grid; NpcShop 0x00ab7277(8, 8, 15, 5), StorageInven
 * (9, 8, 15, 1)); NpcShop's Open 0x00bf0354 also opens the inventory.
 * Buying, selling and the vault moves are LOCAL DEMO actions (the server
 * decides them in the real game). */
typedef struct mu_gfx_slot_item {
    int32_t code, level, width, height;
    int64_t price;              /* demo price shown in the tooltip's caller / log */
    char name[64];
} mu_gfx_slot_item;

typedef struct mu_gfx_npc_dialog {
    const char *title;          /* the NPC's name (Npcname) */
    const char *text;           /* the dialogue text, lines separated by ';' as in the client (pages are cut by the
                                   movie's width callback) */
    const char *options[13];    /* select buttons (the movie has 13) */
    int noptions;
    int hide_contribute;        /* VisibleContribute(0): the dialogue NPCs 0x248, 0x2fc, 0x2fd, 0x3ab, 0x3ac */
} mu_gfx_npc_dialog;

int mu_gfx_layer_npc_dialog(mu_gfx_layer *layer, const mu_gfx_npc_dialog *dialog);
int mu_gfx_layer_npc_shop(mu_gfx_layer *layer, const char *title, int repair, int tabs, const mu_gfx_slot_item *items,
                          int n);
int mu_gfx_layer_storage(mu_gfx_layer *layer, const char *title, const mu_gfx_slot_item *items, int n);
/* Closes the NPC windows (the talk result's close-all does this first). */
void mu_gfx_layer_npc_close(mu_gfx_layer *layer);
/* The open NPC window (MU_GFX_NPC_DIALOG, MU_GFX_NPC_SHOP or MU_GFX_STORAGE) or -1. */
int mu_gfx_layer_npc_window(const mu_gfx_layer *layer);
/* Scripted demo actions: "buy" slot, "sell" inventory cell, "take" slot,
 * "put" inventory cell, "option" n, "next", "close"; NATIVE-LANG-002: "tip" slot
 * and "tipinv" inventory cell show the tooltip.  Returns 1 when done. */
int mu_gfx_layer_npc_action(mu_gfx_layer *layer, const char *verb, int arg);
/* Last demo action ("" none) and the dialogue state for reports. */
const char *mu_gfx_layer_npc_last(const mu_gfx_layer *layer);
/* Sets the last NPC action note (hosts: NATIVE-LANG-002's dialogue requests). */
void mu_gfx_layer_npc_note(mu_gfx_layer *layer, const char *note);
int mu_gfx_layer_npc_page(const mu_gfx_layer *layer, int *pages);
/* Window-pixel centre of a slot of NpcShop/StorageInven (scripted input), and
 * the item count of those windows. */
int mu_gfx_layer_slot_center(const mu_gfx_layer *layer, int movie, int32_t cell, double *x, double *y);
int mu_gfx_layer_slot_items(const mu_gfx_layer *layer, int movie);
/* The item draws the slot window's item pass hands to the items callback now. */
int mu_gfx_layer_slot_draws(mu_gfx_layer *layer, int movie, mu_gfx_item_draw *out, int max);

/* ---- skills (NATIVE-SKILL-001, docs/research/client-skills.md) ----
 *
 * With a skill host the layer plays the game side of the bar and the skill windows as the client does
 * (static readings of the handlers; the routines behind the host are reconstructed/skill):
 *   - every 40 ms step the host's bar feed (0x00c58797) may give a SetSkillSlot argument for
 *     main.mcSkillHotKey; onSelectSkill goes to the host (CurrentSkill, 0x00c70f4b), which the next feed
 *     shows (the client never calls setSelectSkill); mu_gfx_layer_skill_delay sends onUseSkillDelay;
 *   - onSkillTooltip / offSkillTooltip (0x00c7070d / 0x00c708dc): SkillInfoPopup's
 *     SetInfoPopupSkillStamp(x + w/2, y, 0, 0, title, body, 0) with the host's tooltip, then shown;
 *   - onOpenSkillWindow (the bar's selected slot, 0x00c70f1b) and the U key (the key scan 0x00efcea8)
 *     toggle SkillStampFrame (handler 0x00c1f99c): InitText/InitButton/InitStampExplain at creation
 *     (0x00c1fb1b), UpdateSkillPage/SetStampDamage/SetSkillSlotSize at open (0x00c2008b); its slots
 *     report requestSkillSlotInfo (20 rectangles: 0..4 bar slots, 5..19 the learned page), a drag
 *     reports requestSkillSlotDragStart/End, the game asks CheckOverSlot and the movie answers
 *     DragEndSlotIndex_Mouse(target) (0x00c2226c applies it through the host); Save/Cancel/close.
 * The host draws the skill icons over SkillStampFrame (the game draws them in the client, 0x01097130). */
typedef struct mu_gfx_skill_icon {
    int32_t slot;                     /* SkillStampFrame slot 0..19 */
    int32_t skill;                    /* 0: empty */
    float rect[4];                    /* stage points, top-left origin */
    float delay;                      /* remaining / total of the skill's delay (0 none) */
} mu_gfx_skill_icon;
typedef struct mu_gfx_skill_host {
    void *user;
    int (*feed)(void *user, char *json, size_t cap);
    void (*select)(void *user, int slot, int skill);
    int (*tooltip)(void *user, int32_t skill, char *title, size_t title_cap, char *body, size_t body_cap);
    void (*stamp_open)(void *user, int open);        /* 1 opened; 0 closed without saving (the host restores) */
    int32_t (*stamp_skill)(void *user, int slot);    /* the skill window slot `slot` shows now */
    int (*stamp_page)(void *user, int which, int delta);  /* which 0: learned page, 1: select page; returns it */
    int (*stamp_drop)(void *user, int from, int to); /* 1 the bar changed, -1 "not learned", 0 nothing */
    void (*stamp_save)(void *user);
    float (*delay_left)(void *user, int32_t skill);
    void (*icons)(void *user, const mu_gfx_skill_icon *icons, int n, int32_t stage_w, int32_t stage_h);
} mu_gfx_skill_host;
void mu_gfx_layer_set_skill_host(mu_gfx_layer *layer, const mu_gfx_skill_host *host);
/* onUseSkillDelay({skill, delaytime}) on the bar (StartSkillDelay 0x01696aca sends it). */
void mu_gfx_layer_skill_delay(mu_gfx_layer *layer, int32_t skill, int32_t delay_ms);
/* Scripted window actions: "open", "close", "drag" from to, "over" slot, "out", "save", "cancel", "page"
 * delta, "select" delta, "tip" bar slot (the bar's onSkillTooltip).  Returns 1 when done. */
int mu_gfx_layer_skill_action(mu_gfx_layer *layer, const char *verb, int a, int b);
const char *mu_gfx_layer_skill_last(const mu_gfx_layer *layer);
/* The window icons the host would draw now (tests); returns the count. */
int mu_gfx_layer_skill_icons(const mu_gfx_layer *layer, mu_gfx_skill_icon *out, int max);

#ifdef __cplusplus
}
#endif

#endif
