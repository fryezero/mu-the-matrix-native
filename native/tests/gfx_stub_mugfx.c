/* A stand-in libmugfx for the GFx layer's portable tests (NATIVE-GFX-002/003).
 *
 * Implements the mugfx ABI 3 without Ruffle: each "movie" is a small state
 * machine that answers the layer the way the converted client movies do
 * (static readings of their ActionScript, docs/research/native-gfx.md):
 * InventoryFrame reports UIInit/requestSlotInfo/requestWindowPos and turns
 * clicks on its 8 x 8 page into requestItemSlotClick/ClickR/Over/Out; main
 * reports onLoad on onFileLoad and onHotKey from onKeyUp; chat reports
 * onLoad, keeps a text buffer and reports onEnterText from onPushText; the
 * other windows report UIInit.  NATIVE-GFX-003: "base" plays the client's
 * base movie (static readings, docs/research/native-gfx3.md): it reports
 * base/UIFrame/ASData onLoad at start, loads the LoadFrameFiles list
 * (main and Chat report onLoad with their paths, alarmframe, topmenu and bufflist
 * too, then UIFrame onFileLoad) and is the bar and the chat at once;
 * mugfx_set_image logs the drawn rows of the image, mugfx_resolve looks in
 * the movie's directory, mugfx_ime logs.  NATIVE-NPC-001: NpcDialogue reports
 * UIInit and answers SetDialogueMentDivide(text, sep) with NPCDialogTextWidth
 * (lines cut at 40 characters and at the separator); NpcShop and
 * StorageInven are slot windows like InventoryFrame (8 x 15 cells, slot
 * origin 24.75,70 from their window position).
 * NATIVE-CHARSEL-003: "CharacterSelect" reports UIInit, keeps
 * the rows of SetSelectText and the row of SelectIndex, places its list as SetSelectVisible does
 * (x = width - 227 - 50, y = height / 8, rows 55 high) and turns a press on a row into
 * OnCharSelectedClick, a second press on the same row without a move away into OnCharSelectedDClick too
 * (CLIK's itemDoubleClick).  NATIVE-CHARCREATE-001: CharacterSelect's create panel (SetCreateVisible,
 * SetClassInfo -> SetSelectedClass with the ClassType of InitClassInfo, SetCreateBoardInfo -> the render
 * rectangle, the class buttons, the name box, OK -> OnEnterCharacterName, Cancel -> OnClickCreateCancel, Enter
 * in the name box), "Caution" (SetVisible, SetUIType; its buttons -> OnClickBtnOK / OnClickBtnCancel, the
 * input boxes keep typed text; a release outside the password box reports onClickCautionInputCancel as the
 * real movie does) and "winSystemMenu" (attachMovie + onFileLoad -> onLoad / onOpenWindow, openWindow /
 * closeWindow, its buttons -> onExit, onServerSelectClick, onCharSelectClick, onOptionClick, onClose);
 * fixed synthetic geometry, the control paths answer _x/_y/_width/_height.  NATIVE-SKILL-001: SkillInfoPopup
 * reports UIInit; SkillStampFrame reports UIInit, 20 requestSkillSlotInfo, requestSkillSlotSize and
 * requestWindowPos, answers CheckOverSlot with DragEndSlotIndex_Mouse(the target set by testDropTarget) and
 * raises testCall callbacks like base.  Calls made from inside a callback are queued
 * and run afterwards, as mugfx does.  Every invoke is appended to the file
 * named by $MUGFX_STUB_LOG.  Synthetic: no client data. */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../gfx/mugfx/include/mugfx.h"

typedef struct pending { MuGfx *g; char path[128], method[64], *args; } pending;

struct MuGfx {
    char name[64];
    char dir[1024];
    mugfx_callback cb;
    void *user;
    int stage_w, stage_h, vx, vy, vw, vh;   /* stage and view in points */
    double scale;                          /* viewport pixels per point */
    int visible, rendered;
    float win_x, win_y;
    int hover, press, last_vk, edit;
    char text[256];
    char reply[512];
    uint64_t calls;
    /* CharacterSelect (NATIVE-CHARSEL-003) */
    int cs_rows, cs_selected, cs_last_row;
    /* NATIVE-CHARCREATE-001 */
    int cs_create, cs_class, cs_classes[16], cs_nclasses;
    int cu_type, menu_attached, menu_open;
    /* NATIVE-SKILL-001: SkillStampFrame's drop target (testDropTarget) */
    int drop_target;
};

/* NATIVE-CHARCREATE-001: synthetic geometry (stage points) */
static void cc_panel(const MuGfx *g, double *x, double *y)
{
    *x = g->stage_w / 2.0 - 250.0;
    *y = g->stage_h / 2.0 - 220.0;
}

typedef struct ctl { const char *name; double x, y, w, h; } ctl;
static const ctl CC_CONTROLS[] = {
    {"btnOK", 230, 400, 60, 20}, {"btnCancel", 300, 400, 60, 20}, {"tiCharacterName", 20, 400, 150, 20},
    {"mcCharacterRender", 20, 40, 200, 200}};
static const ctl CU_CONTROLS[] = {
    {"btnCaution1", 20, 100, 60, 20}, {"btnCaution2", 100, 100, 60, 20},
    {"btnCaution3", 60, 100, 60, 20}, {"btnInputOk", 20, 120, 60, 20},
    {"btnInputCancel", 100, 120, 60, 20}, {"tiInput", 20, 60, 150, 20}};
static const ctl MENU_CONTROLS[] = {
    {"_btnExit", 50, 60, 120, 25}, {"_btnServerSelect", 50, 100, 120, 25}, {"_btnOption", 50, 140, 120, 25},
    {"_btnCharSelect", 50, 180, 120, 25}, {"_btnClose", 80, 230, 60, 25}};

static int in_ctl(const ctl *c, double ox, double oy, double sx, double sy)
{
    return sx >= ox + c->x && sx < ox + c->x + c->w && sy >= oy + c->y && sy < oy + c->y + c->h;
}

static const char *ctl_variable(const ctl *list, size_t n, const char *path, char *out, size_t cap)
{
    for (size_t i = 0; i < n; ++i) {
        const char *at = strstr(path, list[i].name);
        if (!at)
            continue;
        const char *field = at + strlen(list[i].name);
        double v = !strcmp(field, "._x") ? list[i].x : !strcmp(field, "._y") ? list[i].y
                 : !strcmp(field, "._width") ? list[i].w : !strcmp(field, "._height") ? list[i].h : -1;
        if (v < 0)
            continue;
        snprintf(out, cap, "%.1f", v);
        return out;
    }
    return NULL;
}

static int is(const MuGfx *g, const char *name);

/* CharacterSelect's list rectangle in stage points */
static void cs_list(const MuGfx *g, double r[4])
{
    r[0] = g->stage_w - 227.0 - 50.0;
    r[1] = g->stage_h / 8.0;
    r[2] = 227.0;
    r[3] = 55.0 * 10;
}

static int cs_row(const MuGfx *g, double sx, double sy)
{
    double r[4];
    cs_list(g, r);
    if (sx < r[0] || sx >= r[0] + r[2] || sy < r[1] || sy >= r[1] + r[3])
        return -1;
    return (int)((sy - r[1]) / 55.0);
}

static int in_cb;
static pending queue[64];
static int nqueue;

static void logline(const char *fmt, const char *a, const char *b, const char *c, const char *d)
{
    const char *path = getenv("MUGFX_STUB_LOG");
    if (!path)
        return;
    FILE *f = fopen(path, "a");
    if (!f)
        return;
    fprintf(f, fmt, a, b, c, d);
    fputc('\n', f);
    fclose(f);
}

static void call(MuGfx *g, const char *name, const char *args)
{
    if (!g->cb)
        return;
    g->calls++;
    int was = in_cb;
    in_cb = 1;
    g->cb(g->user, name, args);
    in_cb = was;
}

static void callf(MuGfx *g, const char *name, const char *fmt, double a, double b)
{
    char args[256];
    snprintf(args, sizeof args, fmt, a, b);
    call(g, name, args);
}

static int is(const MuGfx *g, const char *name) { return !strcmp(g->name, name); }
/* NATIVE-NPC-001: the NPC slot windows (8 x 15 cells at 24.75,70 from the window). */
static int is_slotwin(const MuGfx *g) { return is(g, "NpcShop") || is(g, "StorageInven") || is(g,"MixInventoryFrame"); }
/* The base movie plays the bar and the chat (NATIVE-GFX-003). */
static int is_bar(const MuGfx *g) { return is(g, "main") || is(g, "base"); }
static int is_chat(const MuGfx *g) { return is(g, "chat") || is(g, "base"); }

/* Content rectangle of a movie in stage pixels (what getBounds reports). */
static void bounds(const MuGfx *g, float r[4])
{
    if (is(g, "InventoryFrame")) { r[0] = g->win_x; r[1] = g->win_y; r[2] = 332; r[3] = 639; }
    else if (is(g, "main") || is(g, "base")) { r[0] = 179; r[1] = 658; r[2] = 921; r[3] = 145; }
    else if (is(g, "chat")) { r[0] = 0; r[1] = 562; r[2] = 610; r[3] = 130; }
    else if (is(g, "CharacterInfoFrame")) { r[0] = 0; r[1] = 0; r[2] = 350; r[3] = 640; }
    else if (is_slotwin(g) || is(g, "NpcDialogue")) { r[0] = g->win_x; r[1] = g->win_y; r[2] = 320; r[3] = 620; }
    else { r[0] = 900; r[1] = 300; r[2] = 200; r[3] = 100; }
}

static void stage_point(const MuGfx *g, double x, double y, double *sx, double *sy)
{
    *sx = x / g->scale + g->vx;
    *sy = y / g->scale + g->vy;
}

static int cell_at(const MuGfx *g, double sx, double sy)
{
    double oy = is_slotwin(g) ? 70.0 : 370.0, rows = is_slotwin(g) ? 15 : 8;
    double cx = (sx - g->win_x - 24.75) / 26.0, cy = (sy - g->win_y - oy) / 26.0;
    if (cx < 0 || cy < 0 || cx >= 8 || cy >= rows)
        return -1;
    return (int)cy * 8 + (int)cx;
}

/* NpcDialogue: SetDialogueMentDivide(text, sep) -> NPCDialogTextWidth(lines, wrapped). */
static void dialogue_divide(MuGfx *g, const char *args)
{
    char text[2048] = "", sep = ';';
    const char *p = strchr(args, '"');
    size_t n = 0;
    if (p) {
        for (p++; *p && *p != '"' && n + 1 < sizeof text; p++) {
            if (*p == '\\' && p[1])
                p++;
            text[n++] = *p;
        }
        text[n] = 0;
        const char *q = *p ? strchr(p + 1, '"') : NULL;   /* the separator argument */
        if (q && q[1] && q[1] != '"')
            sep = q[1];
    }
    char w[3000];
    size_t o = 0;
    int lines = 1, col = 0;
    for (size_t i = 0; text[i] && o + 4 < sizeof w; i++) {
        if (text[i] == sep || col == 40) {
            w[o++] = '\\';
            w[o++] = 'n';
            lines++;
            col = 0;
            if (text[i] == sep)
                continue;
        }
        if (text[i] == '"' || text[i] == '\\')
            w[o++] = '\\';
        w[o++] = text[i];
        col++;
    }
    w[o] = 0;
    char out[3100];
    snprintf(out, sizeof out, "[%d,\"%s\"]", lines, w);
    call(g, "NPCDialogTextWidth", out);
}

static const char *run_invoke(MuGfx *g, const char *path, const char *method, const char *args)
{
    logline("%s %s.%s %s", g->name, path, method, args);
    snprintf(g->reply, sizeof g->reply, "null");
    if (!strcmp(method, "getBounds")) {
        float r[4];
        bounds(g, r);
        snprintf(g->reply, sizeof g->reply, "{\"xMax\":%.1f,\"xMin\":%.1f,\"yMax\":%.1f,\"yMin\":%.1f}", r[0] + r[2],
                 r[0], r[1] + r[3], r[1]);
    } else if (is(g, "CharacterSelect") && !strcmp(method, "SetSelectText")) {
        g->cs_rows = 0;
        for (const char *q = strstr(args, "\"type\""); q; q = strstr(q + 1, "\"type\""))
            g->cs_rows++;
    } else if (is(g, "CharacterSelect") && !strcmp(method, "SelectIndex")) {
        g->cs_selected = atoi(args + 1);
    } else if (is(g, "CharacterSelect") && !strcmp(method, "InitClassInfo")) {
        g->cs_nclasses = 0;
        for (const char *q = strstr(args, "\"ClassType\":"); q && g->cs_nclasses < 16;
             q = strstr(q + 1, "\"ClassType\":"))
            g->cs_classes[g->cs_nclasses++] = atoi(q + 12);
    } else if (is(g, "CharacterSelect") && !strcmp(method, "SetClassInfo")) {
        int slot = atoi(args + 1);
        g->cs_class = slot >= 0 && slot < g->cs_nclasses ? g->cs_classes[slot] : 0;
        callf(g, "SetSelectedClass", "[%.1f]", g->cs_class, 0);
    } else if (is(g, "CharacterSelect") && !strcmp(method, "SetCreateVisible")) {
        g->cs_create = atoi(args + 1) != 0;
        g->edit = g->cs_create;   /* tiCharacterName.SetFocus */
    } else if (is(g, "CharacterSelect") && !strcmp(method, "SetCharacterName")) {
        const char *q = strchr(args, '"');
        g->text[0] = 0;
        if (q)
            sscanf(q + 1, "%255[^\"]", g->text);
    } else if (is(g, "CharacterSelect") && !strcmp(method, "SetCreateBoardInfo")) {
        double px, py;
        cc_panel(g, &px, &py);
        callf(g, "SetCreateBoardInfo", "[%.1f,%.1f,200.0,200.0]", px + 20, py + 40);
    } else if (is(g, "Caution") && !strcmp(method, "SetUIType")) {
        g->cu_type = atoi(args + 1);
        g->edit = g->cu_type == 3 || g->cu_type == 4;
        g->text[0] = 0;
    } else if (is(g, "winSystemMenu") && !strcmp(method, "attachMovie")) {
        g->menu_attached = 1;
    } else if (is(g, "winSystemMenu") && !strcmp(method, "onFileLoad") && g->menu_attached) {
        call(g, "winSystemMenu", "[\"onLoad\",\"_level0.mcSystemMenu\"]");
        g->menu_open = 0;   /* KeyWindow.onLoadEvents -> closeWindow */
        call(g, "winSystemMenu", "[\"onOpenWindow\",false]");
    } else if (is(g, "winSystemMenu") && !strcmp(method, "openWindow")) {
        if (!g->menu_open) {
            g->menu_open = 1;
            call(g, "winSystemMenu", "[\"onOpenWindow\",true]");
        }
    } else if (is(g, "winSystemMenu") && !strcmp(method, "closeWindow")) {
        if (g->menu_open) {
            g->menu_open = 0;
            call(g, "winSystemMenu", "[\"onOpenWindow\",false]");
        }
    } else if (is(g, "base") && !strcmp(method, "LoadFrameFiles")) {
        if (strstr(args, "\"main\""))
            call(g, "main", "[\"onLoad\",\"_level0.base.UI.mcBottomFrame.main_1.mc\"]");
        if (strstr(args, "\"Chat\""))
            call(g, "chat", "[\"onLoad\",\"_level0.base.UI.mcBottom.Chat_2.instance96\"]");
        if (strstr(args, "\"AlarmFrame\""))
            call(g, "alarmframe", "[\"onLoad\",\"_level0.base.UI.mcBottom.AlarmFrame_3.instance104\"]");
        if (strstr(args, "\"topmenu\""))
            call(g, "topmenu", "[\"onLoad\",\"_level0.base.UI.mcBottom.topmenu_4.instance147\"]");
        if (strstr(args, "\"bufflist\""))   /* NATIVE-LANG-002: the channel name and path the real movie reports */
            call(g, "bufflist", "[\"onLoad\",\"_level0.base.UI.mcBottom.bufflist_5.BuffList\"]");
        call(g, "UIFrame", "[\"onFileLoad\",{}]");
    } else if (is(g, "SkillStampFrame") && !strcmp(method, "testDropTarget")) {
        g->drop_target = atoi(args + 1);
    } else if (is(g, "SkillStampFrame") && !strcmp(method, "CheckOverSlot")) {
        /* the slot under the mouse (CheckOverSlot's hitTest loop) */
        char a[32];
        snprintf(a, sizeof a, "[%d.0]", g->drop_target);
        call(g, "DragEndSlotIndex_Mouse", a);
    } else if (is(g, "SkillStampFrame") && !strcmp(method, "SetSkillSlotSize")) {
        call(g, "requestSkillSlotSize", "[26.0,37.0]");
    } else if (is(g, "winQuestSummary") && !strcmp(method, "onFileLoad")) {
        call(g, "QuestSummary", "[\"onLoad\",\"_level0.win\"]");
        call(g, "QuestSummary", "[\"onOpenWindow\",false]");
    } else if (!strcmp(method,"testFocus")) {
        g->edit=1;g->text[0]=0;
    } else if (!strcmp(method,"testStoreSubmit") && is(g,"PersonalShopRegister")) {
        char a[128];snprintf(a,sizeof a,"[%s,0,0]",g->text[0]?g->text:"0");call(g,"OnClickOk",a);
    } else if (!strcmp(method, "testCall")) {
        /* test hook: the movie raises a callback, e.g. a menu button's onHotKey */
        char name[64] = "", rest[400] = "";
        if (sscanf(args, "[\"%63[^\"]\",%399[^\n]", name, rest) == 2) {
            size_t n = strlen(rest);
            if (n && rest[n - 1] == ']')
                rest[n - 1] = 0;
            char wrapped[420];
            snprintf(wrapped, sizeof wrapped, "[%s]", rest);
            call(g, name, wrapped);
        }
    } else if (is(g, "main")) {
        if (!strcmp(method, "onFileLoad"))
            call(g, "main", "[\"onLoad\",\"_level0.mc\"]");
    } else if (is_chat(g)) {
        if (!strcmp(method, "onFileLoad"))
            call(g, "chat", "[\"onLoad\",\"_level0.mc\"]");
        else if (!strcmp(method, "getText"))
            snprintf(g->reply, sizeof g->reply, "\"%s\"", g->text);
        else if (!strcmp(method, "OpenEditText")) {
            g->edit = 1;
            call(g, "fscommand", "[\"TextInput\",\"focusIn\"]");
        } else if (!strcmp(method, "CloseEditText")) {
            g->edit = 0;
            g->text[0] = 0;
            call(g, "fscommand", "[\"TextInput\",\"focusOut\"]");
        } else if (!strcmp(method, "onPushText")) {
            char msg[400];
            snprintf(msg, sizeof msg, "[\"onEnterText\",{\"text\":\"%s\",\"type\":1.0,\"wisper\":\"\"}]", g->text);
            g->text[0] = 0;
            call(g, "chat", msg);
        }
    } else if (is(g, "InventoryFrame")) {
        if (!strcmp(method, "SetAlign")) {
            g->win_x = (float)(g->stage_w - 332);
            g->win_y = 20;
            callf(g, "requestWindowPos", "[%.1f,%.1f]", g->win_x, g->win_y);
        } else if (!strcmp(method, "SetVisible")) {
            g->visible = strstr(args, "true") != NULL;
        }
    } else if (is(g, "NpcDialogue") && !strcmp(method, "SetDialogueMentDivide")) {
        dialogue_divide(g, args);
    } else if (!strcmp(method, "SetVisible")) {
        g->visible = strstr(args, "true") != NULL;
    }
    return g->reply;
}

static void drain(void)
{
    while (!in_cb && nqueue) {
        pending p = queue[0];
        memmove(queue, queue + 1, (size_t)(nqueue - 1) * sizeof queue[0]);
        nqueue--;
        run_invoke(p.g, p.path, p.method, p.args);
        free(p.args);
    }
}

int mugfx_abi_version(void) { return MUGFX_ABI_VERSION; }

void mugfx_adapter(char *out, size_t cap) { snprintf(out, cap, "stub"); }

MuGfx *mugfx_open(const char *path, int width, int height, char *err, size_t cap)
{
    MuGfx *g = calloc(1, sizeof *g);
    if (!g) {
        snprintf(err, cap, "out of memory");
        return NULL;
    }
    const char *base = strrchr(path, '/');
    snprintf(g->name, sizeof g->name, "%s", base ? base + 1 : path);
    snprintf(g->dir, sizeof g->dir, "%.*s", base ? (int)(base - path) : 1, base ? path : ".");
    char *dot = strstr(g->name, ".swf");
    if (dot)
        *dot = 0;
    g->stage_w = g->vw = width;
    g->stage_h = g->vh = height;
    g->scale = 1.0;
    g->hover = g->press = -1;
    return g;
}

MuGfx *mugfx_open_shared(const char *path, int width, int height, char *err, size_t cap)
{
    (void)path; (void)width; (void)height;
    snprintf(err, cap, "stub: no IOSurface");
    return NULL;
}

void mugfx_close(MuGfx *g) { free(g); }

void mugfx_set_callback(MuGfx *g, mugfx_callback cb, void *user)
{
    g->cb = cb;
    g->user = user;
}

void mugfx_start(MuGfx *g)
{
    if (is(g, "base")) {
        /* base.swf's onLoad loads ExternalBase.swf, whose onLoad reports
         * the UI frame and the data manager. */
        call(g, "base", "[\"onLoad\"]");
        call(g, "UIFrame", "[\"onLoad\",\"_level0.base.UI\"]");
        call(g, "ASData", "[\"onLoad\",\"_level0.base.DataMan\"]");
    } else if (is(g, "InventoryFrame")) {
        call(g, "UIInit", "[\"g_mcInventory\"]");
        call(g, "requestSlotInfo", "[24.75,370.0,26.0,26.0,0.0]");
        g->win_x = 348;
        g->win_y = 40;
        call(g, "requestWindowPos", "[348.0,40.0]");
    } else if (is(g, "InfoPopup")) {
        call(g, "UIInit", "[\"g_mcInfoPopup\"]");
    } else if (is(g, "CharacterInfoFrame")) {
        call(g, "UIInit", "[\"g_CharacterInfoFrame\"]");
    } else if (is(g, "NpcDialogue")) {
        call(g, "UIInit", "[\"g_mcNpcDialogue\"]");
        g->win_x = 20;
        g->win_y = 100;
        call(g, "requestWindowPos", "[20.0,100.0]");
    } else if (is_slotwin(g)) {
        call(g, "UIInit", is(g, "NpcShop") ? "[\"g_mcNpcShop\"]" : is(g,"MixInventoryFrame") ? "[\"g_mcMixInventory\"]" : "[\"g_mcStorageInven\"]");
        call(g, "requestSlotInfo", "[24.75,70.0,26.0,26.0,0.0]");
        g->win_x = 45;
        g->win_y = 21;
        call(g, "requestWindowPos", "[45.0,21.0]");
    } else if (is(g,"MixGoblinSel")) {
        call(g,"UIInit","[\"g_mcMixGoblinSel\"]");
    } else if (is(g,"PersonalShopProductList") || is(g,"PersonalShopRegister") || is(g,"PersonalShopPurchase")) {
        char a[96];snprintf(a,sizeof a,"[\"g_%s\"]",g->name);call(g,"UIInit",a);
    } else if (is(g, "SkillInfoPopup")) {
        call(g, "UIInit", "[\"g_mcSkillInfoPopup\"]");
    } else if (is(g, "MasterSkillTree") || is(g, "SkillTree4th") || is(g, "SkillTree5th") || is(g, "MoveCommand")) {
        char a[96];
        snprintf(a, sizeof a, "[\"g_%s\"]", g->name);
        call(g, "UIInit", a);
    } else if (is(g, "SkillStampFrame")) {
        /* NATIVE-SKILL-001: onLoadUI's reports (synthetic geometry: 5 bar slots below 3 rows of 5) */
        call(g, "UIInit", "[\"g_mcSkillStampFrame\"]");
        for (int i = 0; i < 20; i++) {
            char a[64];
            double x = 43.0 + 53.0 * (i % 5), y = i < 5 ? 376.0 : 158.0 + 53.0 * ((i - 5) / 5);
            snprintf(a, sizeof a, "[%.1f,%.1f,0.0,%d.0]", x, y, i);
            call(g, "requestSkillSlotInfo", a);
        }
        call(g, "requestSkillSlotSize", "[26.0,37.0]");
        call(g, "requestStampRelativePosition", "[16.0,-2.0]");
        g->win_x = 8;
        g->win_y = 0;
        call(g, "requestWindowPos", "[8.0,0.0]");
    } else if (is(g, "Trade") || is(g, "FriendMenu") || is(g, "FriendWindow")) {
        /* NATIVE-SOCIAL-001: old GFx social windows report UIInit in onLoadUI. */
        char args[96];
        snprintf(args, sizeof args, "[\"%s\"]", g->name);
        call(g, "UIInit", args);
    } else if (is(g, "NpcQuestProgress") || is(g, "MyQuestInfo") || is(g, "NpcJobChangeQuest") ||
               is(g, "QuestProgressInfo")) {
        char args[96];
        snprintf(args, sizeof args, "[\"%s\"]", g->name);
        call(g, "UIInit", args);
    } else if (is(g, "CharacterSelect")) {
        g->cs_last_row = -1;
        call(g, "UIInit", "[\"g_mcCharacterSelect\"]");
        call(g, "requestWindowPos", "[0.0,0.0]");
    }
    drain();
}

void mugfx_advance(MuGfx *g, double dt) { (void)g; (void)dt; drain(); }

int mugfx_needs_render(MuGfx *g) { return !g->rendered; }

int mugfx_render(MuGfx *g, uint8_t *rgba, size_t cap)
{
    size_t need = (size_t)(g->vw * g->scale) * (size_t)(g->vh * g->scale) * 4;
    if (cap < need)
        return -2;
    memset(rgba, 0, need);
    g->rendered = 1;
    return 0;
}

int mugfx_render_shared(MuGfx *g, int wait) { (void)g; (void)wait; return -2; }

void mugfx_gpu_wait(void) {}

void *mugfx_iosurface(MuGfx *g, int *w, int *h, uint32_t *seed) { (void)g; (void)w; (void)h; (void)seed; return NULL; }

const char *mugfx_invoke(MuGfx *g, const char *path, const char *method, const char *args)
{
    if (in_cb) {
        if (nqueue < 64) {
            pending *p = &queue[nqueue++];
            p->g = g;
            snprintf(p->path, sizeof p->path, "%s", path);
            snprintf(p->method, sizeof p->method, "%s", method);
            p->args = strdup(args ? args : "[]");
        }
        return NULL;
    }
    const char *r = run_invoke(g, path, method, args ? args : "[]");
    static char copy[512];
    snprintf(copy, sizeof copy, "%s", r);
    drain();
    return copy;
}

int mugfx_set_variable(MuGfx *g, const char *path, const char *value) { (void)g; (void)path; (void)value; return 0; }

const char *mugfx_get_variable(MuGfx *g, const char *path)
{
    static char cv[64];
    if (is(g, "CharacterSelect") && strstr(path, "mcCharacterCreate")) {
        double px, py;
        cc_panel(g, &px, &py);
        int n;
        const char *b = strstr(path, "btnClass");
        if (b && sscanf(b, "btnClass%d", &n) == 1) {
            const char *f = strchr(b, '.');
            double v = !f ? -1 : !strcmp(f, "._x") ? 300 : !strcmp(f, "._y") ? 40 + 20.0 * n
                     : !strcmp(f, "._width") ? 100 : !strcmp(f, "._height") ? 18 : -1;
            if (v < 0)
                return "null";
            snprintf(cv, sizeof cv, "%.1f", v);
            return cv;
        }
        if (!strcmp(strstr(path, "mcCharacterCreate"), "mcCharacterCreate._x")) { snprintf(cv, sizeof cv, "%.1f", px); return cv; }
        if (!strcmp(strstr(path, "mcCharacterCreate"), "mcCharacterCreate._y")) { snprintf(cv, sizeof cv, "%.1f", py); return cv; }
        const char *r = ctl_variable(CC_CONTROLS, sizeof CC_CONTROLS / sizeof CC_CONTROLS[0], path, cv, sizeof cv);
        return r ? r : "null";
    }
    if ((is(g, "CharacterSelect") || is(g, "Caution")) && (!strcmp(path, "_level0.g_mcCharacterSelect._x") ||
        !strcmp(path, "_level0.g_mcCharacterSelect._y") || !strcmp(path, "_level0.g_mcCaution._x") ||
        !strcmp(path, "_level0.g_mcCaution._y")))
        return "0.0";
    if (is(g, "Caution")) {
        if (!strcmp(path, "_level0.g_mcCaution.mcCaution._x") || !strcmp(path, "_level0.g_mcCaution.mcInput._x"))
            return "500.0";
        if (!strcmp(path, "_level0.g_mcCaution.mcCaution._y") || !strcmp(path, "_level0.g_mcCaution.mcInput._y"))
            return "300.0";
        if (!strcmp(path, "_level0.g_mcCaution.mcCaution.mcBottom._x") ||
            !strcmp(path, "_level0.g_mcCaution.mcCaution.mcBottom._y"))
            return "0.0";
        const char *r = ctl_variable(CU_CONTROLS, sizeof CU_CONTROLS / sizeof CU_CONTROLS[0], path, cv, sizeof cv);
        return r ? r : "null";
    }
    if (is(g, "winSystemMenu")) {
        if (!strcmp(path, "_level0.mcSystemMenu._x")) return "500.0";
        if (!strcmp(path, "_level0.mcSystemMenu._y")) return "200.0";
        const char *r = ctl_variable(MENU_CONTROLS, sizeof MENU_CONTROLS / sizeof MENU_CONTROLS[0], path, cv,
                                     sizeof cv);
        return r ? r : "null";
    }
    if (is(g, "CharacterSelect")) {
        static char v[64];
        double r[4];
        cs_list(g, r);
        if (strstr(path, "mcCharacterSelectList._x")) snprintf(v, sizeof v, "%.1f", r[0]);
        else if (strstr(path, "mcCharacterSelectList._y")) snprintf(v, sizeof v, "%.1f", r[1]);
        else if (strstr(path, "mcCharacterSelectList._width")) snprintf(v, sizeof v, "%.1f", r[2]);
        else if (strstr(path, "mcCharacterSelectList.rowHeight")) snprintf(v, sizeof v, "55");
        else if (strstr(path, "selectedIndex")) snprintf(v, sizeof v, "%d", g->cs_selected);
        else snprintf(v, sizeof v, "null");
        return v;
    }
    if (strstr(path, "mcNPCShop") || strstr(path, "mcStorageInven") || strstr(path,"mcMixInventory")) {
        if (strstr(path, "isSlot0._y")) return "70";
        if (strstr(path, "isSlot8._y")) return "96";
    }
    if (strstr(path, "isSlot0._x")) return "24.75";
    if (strstr(path, "isSlot1._x")) return "50.75";
    if (strstr(path, "isSlot0._y")) return "370";
    if (strstr(path, "isSlot8._y")) return "396";
    (void)g;
    return "null";
}

int mugfx_hit_test(MuGfx *g, double x, double y)
{
    double sx, sy;
    stage_point(g, x, y, &sx, &sy);
    float r[4];
    bounds(g, r);
    if (is(g, "CharacterSelect")) {
        double px, py;
        cc_panel(g, &px, &py);
        if (g->cs_create && sx >= px && sx < px + 420 && sy >= py && sy < py + 440)
            return 1;
        return cs_row(g, sx, sy) >= 0;
    }
    if (is(g, "Caution"))
        return g->visible;   /* modal */
    if (is(g, "winSystemMenu"))
        return g->menu_open && sx >= 500 && sx < 800 && sy >= 200 && sy < 500;
    if ((is(g, "InventoryFrame") || is_slotwin(g) || is(g, "NpcDialogue")) && !g->visible)
        return 0;
    if (is(g, "chat") && !g->edit)
        return 0;   /* the chat view is hitTestDisable while not editing */
    if (is(g, "base") && g->edit && sx < 610 && sy >= 562 && sy < 692)
        return 1;   /* the editing chat inside the base movie */
    return sx >= r[0] && sy >= r[1] && sx < r[0] + r[2] && sy < r[1] + r[3];
}

int mugfx_mouse(MuGfx *g, int kind, int button, double x, double y)
{
    double sx, sy;
    stage_point(g, x, y, &sx, &sy);
    if (is(g, "CharacterSelect") && g->cs_create && kind == 1 && button == 0) {
        double px, py;
        cc_panel(g, &px, &py);
        for (int n = 0; n < g->cs_nclasses; ++n)
            if (sx >= px + 300 && sx < px + 400 && sy >= py + 40 + 20.0 * n && sy < py + 58 + 20.0 * n) {
                g->cs_class = g->cs_classes[n];   /* OnSelectedClass -> SetClassInfo(slot) */
                callf(g, "SetSelectedClass", "[%.1f]", g->cs_class, 0);
                drain();
                return 1;
            }
        if (in_ctl(&CC_CONTROLS[0], px, py, sx, sy)) {
            char a[400];
            snprintf(a, sizeof a, "[\"%s\",%d.0]", g->text, g->cs_class);
            call(g, "OnEnterCharacterName", a);
            drain();
            return 1;
        }
        if (in_ctl(&CC_CONTROLS[1], px, py, sx, sy)) {
            call(g, "OnClickCreateCancel", "[\"\"]");
            drain();
            return 1;
        }
    }
    if (is(g, "Caution") && g->visible) {
        if (kind == 1 && button == 0) {
            int input = g->cu_type == 3 || g->cu_type == 4;
            const ctl *ok = input ? &CU_CONTROLS[3] : g->cu_type == 1 ? &CU_CONTROLS[2] : &CU_CONTROLS[0];
            const ctl *cancel = input ? &CU_CONTROLS[4] : g->cu_type == 0 ? &CU_CONTROLS[1] : NULL;
            if (in_ctl(ok, 500, 300, sx, sy)) {
                char a[400];
                if (input)
                    snprintf(a, sizeof a, "[\"%s\"]", g->text);
                call(g, "OnClickBtnOK", input ? a : "[]");
            } else if (cancel && in_ctl(cancel, 500, 300, sx, sy)) {
                call(g, "OnClickBtnCancel", "[]");
            }
        } else if (kind == 2 && g->cu_type == 4 && !in_ctl(&CU_CONTROLS[5], 500, 300, sx, sy)) {
            call(g, "onClickCautionInputCancel", "[]");   /* the real movie's onMouseUp */
        }
        drain();
        return 1;
    }
    if (is(g, "winSystemMenu") && g->menu_open) {
        static const char *const EVENTS[5] = {"onExit", "onServerSelectClick", "onOptionClick", "onCharSelectClick",
                                              "onClose"};
        if (kind == 1 && button == 0)
            for (int i = 0; i < 5; ++i)
                if (in_ctl(&MENU_CONTROLS[i], 500, 200, sx, sy)) {
                    char a[96];
                    snprintf(a, sizeof a, "[\"%s\",{}]", EVENTS[i]);
                    call(g, "winSystemMenu", a);
                    break;
                }
        drain();
        return 1;
    }
    if (is(g, "CharacterSelect")) {
        int row = cs_row(g, sx, sy);
        if (kind == 0 && row != g->cs_last_row)
            g->cs_last_row = -1;
        if (kind == 1 && button == 0 && row >= 0 && row < g->cs_rows) {
            g->cs_selected = row;
            callf(g, "OnCharSelectedClick", "[%.1f]", row, 0);
            if (row == g->cs_last_row) {
                callf(g, "OnCharSelectedDClick", "[%.1f]", row, 0);
                g->cs_last_row = -1;
            } else {
                g->cs_last_row = row;
            }
        }
        drain();
        return row >= 0;
    }
    if (!(is(g, "InventoryFrame") || is_slotwin(g)) || !g->visible) {
        drain();
        return 0;
    }
    int cell = cell_at(g, sx, sy);
    if (kind == 0 && cell != g->hover) {
        if (g->hover >= 0)
            callf(g, "requestItemSlotOut", "[%.1f]", g->hover, 0);
        if (cell >= 0)
            callf(g, "requestItemSlotOver", "[%.1f]", cell, 0);
        g->hover = cell;
    } else if (kind == 1) {
        g->press = cell;
        if (cell < 0 && sx >= g->win_x + 300 && sy < g->win_y + 30)
            g->press = 1000;   /* the close button */
    } else if (kind == 2) {
        if (g->press == 1000 && sx >= g->win_x + 300 && sy < g->win_y + 30)
            call(g, "CloseWindow", "[]");
        else if (cell >= 0 && cell == g->press)
            callf(g, button == 1 ? "requestItemSlotClickR" : "requestItemSlotClick", "[%.1f]", cell, 0);
        g->press = -1;
    }
    drain();
    return 1;
}

int mugfx_cursor(MuGfx *g) { return g->hover >= 0 ? 1 : 0; }

int mugfx_key(MuGfx *g, int kind, int vk, uint32_t cp, int mods)
{
    (void)cp; (void)mods;
    if (kind == 0)
        g->last_vk = vk;
    if (kind == 0 && vk == 8 && g->edit && g->text[0])
        g->text[strlen(g->text) - 1] = 0;
    if (kind == 0 && vk == 13 && is(g, "CharacterSelect") && g->cs_create) {   /* tiCharacterName pushEnter */
        char a[400];
        snprintf(a, sizeof a, "[\"%s\",%d.0]", g->text, g->cs_class);
        call(g, "OnEnterCharacterName", a);
        drain();
    }
    return 0;
}

int mugfx_text(MuGfx *g, const char *utf8)
{
    (void)is_bar;
    if (!g->edit)
        return 0;
    if (is(g, "CharacterSelect") && strlen(g->text) >= 10)
        return 1;   /* SetInputBoxLength(10): maxChars */
    strncat(g->text, utf8, sizeof g->text - strlen(g->text) - 1);
    return 1;
}

int mugfx_text_focus(MuGfx *g) { return g->edit; }

int mugfx_set_view(MuGfx *g, int stage_w, int stage_h, int x, int y, int w, int h, double scale)
{
    g->scale = scale > 0 ? scale : 1.0;
    g->stage_w = stage_w;
    g->stage_h = stage_h;
    if (w > 0 && h > 0) {
        g->vx = x; g->vy = y; g->vw = w; g->vh = h;
    } else {
        g->vx = g->vy = 0; g->vw = stage_w; g->vh = stage_h;
    }
    g->rendered = 0;
    return 0;
}

void mugfx_size(MuGfx *g, int *w, int *h)
{
    if (w) *w = (int)(g->vw * g->scale);
    if (h) *h = (int)(g->vh * g->scale);
}

void mugfx_stats(MuGfx *g, MuGfxStats *out)
{
    memset(out, 0, sizeof *out);
    out->external_calls = g->calls;
}

int mugfx_register_font(const char *name, const char *path, int style) { (void)name; (void)path; (void)style; return 0; }

const char *mugfx_fonts_used(MuGfx *g) { (void)g; return ""; }

/* ---- ABI 3 (NATIVE-GFX-003) ---- */

int mugfx_set_image(MuGfx *g, const char *name, int w, int h, const uint8_t *rgba, int stride)
{
    if (stride <= 0)
        stride = w * 4;
    int x0 = w, x1 = -1, y0 = h, y1 = -1;
    long opaque = 0;
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++)
            if (rgba[(size_t)y * (size_t)stride + (size_t)x * 4 + 3]) {
                opaque++;
                if (x < x0) x0 = x;
                if (x > x1) x1 = x;
                if (y < y0) y0 = y;
                if (y > y1) y1 = y;
            }
    char line[256];
    snprintf(line, sizeof line, "%dx%d opaque %ld rows %d..%d cols %d..%d", w, h, opaque, y0, y1, x0, x1);
    logline("%s set_image %s %s%s", g->name, name, line, "");
    return 0;
}

int mugfx_resolve(MuGfx *g, const char *name, char *out, size_t cap)
{
    char path[2048];
    const char *file = strrchr(name, '\\');
    snprintf(path, sizeof path, "%s/%s", g->dir, file ? file + 1 : name);
    FILE *f = fopen(path, "rb");
    if (!f)
        return -1;
    fclose(f);
    snprintf(out, cap, "%s", path);
    return (int)strlen(out);
}

int mugfx_ime(MuGfx *g, const char *utf8, int cursor, int commit)
{
    char c[32];
    snprintf(c, sizeof c, "%d %d", cursor, commit);
    logline("%s ime \"%s\" %s%s", g->name, utf8 ? utf8 : "", c, "");
    return 1;
}

int mugfx_set_double_buffer(MuGfx *g, int on) { (void)g; (void)on; return -2; }
