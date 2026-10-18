/* The client's scene manager (NATIVE-SHELL-001). See scene.h and
 * docs/research/client-scene-manager.md. */
#include "scene.h"

#include <stdarg.h>
#include <stddef.h>

/* ---- host helpers ---- */

static uint32_t callv(const mu_scenemgr_host *h, uint32_t routine, uint32_t ecx, const char *text, int32_t count,
                      va_list list)
{
    mu_scenemgr_call c;
    c.routine = routine;
    c.ecx = ecx;
    c.count = count;
    c.text = text;
    for (int32_t i = 0; i < MU_SCENE_CALL_ARGS; ++i)
        c.args[i] = i < count ? va_arg(list, uint32_t) : 0u;
    return h->call(h->user, &c);
}

/* cdecl/stdcall callee with `count` stack words */
static uint32_t call(const mu_scenemgr_host *h, uint32_t routine, int32_t count, ...)
{
    va_list list;
    va_start(list, count);
    uint32_t r = callv(h, routine, 0, NULL, count, list);
    va_end(list);
    return r;
}

/* thiscall callee */
static uint32_t call_this(const mu_scenemgr_host *h, uint32_t routine, uint32_t ecx, int32_t count, ...)
{
    va_list list;
    va_start(list, count);
    uint32_t r = callv(h, routine, ecx, NULL, count, list);
    va_end(list);
    return r;
}

/* callee whose argument (the first stack word unless noted) is a string */
static uint32_t call_text(const mu_scenemgr_host *h, uint32_t routine, uint32_t ecx, const char *text, int32_t count,
                          ...)
{
    va_list list;
    va_start(list, count);
    uint32_t r = callv(h, routine, ecx, text, count, list);
    va_end(list);
    return r;
}

static uint32_t peek(const mu_scenemgr_host *h, uint32_t address, int32_t size)
{
    return h->peek(h->user, address, size);
}

static void poke(const mu_scenemgr_host *h, uint32_t address, uint32_t value, int32_t size)
{
    h->poke(h->user, address, value, size);
}

/* `if (SceneFlag != value) { SceneFlag = value; notify(&SceneFlag); }`
 * (the client's setter pattern, inlined at every writer). */
static void set_scene(const mu_scenemgr_host *h, mu_scenemgr_globals *g, int32_t value)
{
    if (g->scene == value)
        return;
    g->scene = value;
    call_this(h, MU_SC_NOTIFY_STATE, MU_SCENE_G_STATE, 0);
}

/* PlayMp3/StopMp3 take a std::string built from the music table entry
 * (constructor 0x0094997e and destructor 0x0094f183 around the call are
 * not part of the record). */
static void music(const mu_scenemgr_host *h, uint32_t routine, uint32_t name)
{
    call(h, routine, 1, name);
}

/* LoadBitmap(path, index, filter, wrap, check = 1, fullpath = 0) */
static void load_bitmap(const mu_scenemgr_host *h, const char *path, uint32_t index, uint32_t filter, uint32_t wrap)
{
    call_text(h, MU_SC_LOAD_BITMAP, 0, path, 6, MU_SCENE_STACK, index, filter, wrap, 1u, 0u);
}

/* ---- dispatcher 0x01859d8a ---- */

int mu_scenemgr_dispatch_target(int32_t scene)
{
    switch (scene) {
    case MU_SCENE_INTRO: return MU_SCENE_RUN_INTRO;
    case MU_SCENE_LOADING: return MU_SCENE_RUN_LOADING;
    case MU_SCENE_LOGIN:
    case MU_SCENE_CHARACTER:
    case MU_SCENE_MAIN: return MU_SCENE_RUN_FRAME;
    default: return MU_SCENE_RUN_NONE;
    }
}

void mu_scenemgr_dispatch(const mu_scenemgr_host *h, mu_scenemgr_globals *g, uint32_t hdc)
{
    uint32_t service = call(h, 0x00c74245u, 0);
    call_this(h, 0x01185472u, service, 0);
    g->loop_flag_2d1e = 0;
    call_this(h, 0x00aef92du, 0x01d22c60u, 0);
    if (g->scene == MU_SCENE_MAIN) {
        /* a string compare whose result is unused (both branches join) */
        uint32_t object = call(h, 0x00cd4ea8u, 0);
        uint32_t record = call_this(h, 0x00cd5d29u, object, 1, 0u);
        call(h, MU_SC_STRNCMP, 3, record + 0x210u, 0x01af702cu, 2u);
    }
    switch (mu_scenemgr_dispatch_target(g->scene)) {
    case MU_SCENE_RUN_INTRO: call(h, MU_SC_INTRO, 1, hdc); break;
    case MU_SCENE_RUN_LOADING: call(h, MU_SC_LOADING, 1, hdc); break;
    case MU_SCENE_RUN_FRAME: call(h, MU_SC_FRAME, 1, hdc); break;
    default: break;
    }
    uint32_t scene = (uint32_t)g->scene;
    uint32_t observer = call(h, 0x00ac3bf7u, 0);
    call_this(h, 0x00ac9be9u, observer, 1, scene);
    if (g->send_counter > 0x1f) {
        call(h, MU_SCENE_NET_SEND, 0);   /* C1 packet built on the stack (protocol out of scope) */
        call(h, 0x0120f6d4u, 0);
    }
}

/* ---- intro / title 0x0185ad63 ---- */

static const char *const TITLE_PATHS[8] = {
    "Interface\\New_lo_back_01.jpg", "Interface\\New_lo_back_02.jpg", "Interface\\MU_TITLE.tga",
    "Interface\\lo_121518.tga", "Interface\\New_lo_webzen_logo.tga", "Interface\\lo_lo.jpg",
    "Interface\\lo_back_s5_03.jpg", "Interface\\lo_back_s5_04.jpg"};
static const char *const TITLE_BATTLE[6] = {
    "Interface\\MuBattle_loading01.jpg", "Interface\\MuBattle_loading02.jpg", "Interface\\MuBattle_loading03.jpg",
    "Interface\\MuBattle_loading04.jpg", "Interface\\MuBattle_loading05.jpg", "Interface\\MuBattle_loading06.jpg"};
static const char *const TITLE_S5[6] = {
    "Interface\\lo_back_s5_im01.jpg", "Interface\\lo_back_s5_im02.jpg", "Interface\\lo_back_s5_im03.jpg",
    "Interface\\lo_back_s5_im04.jpg", "Interface\\lo_back_s5_im05.jpg", "Interface\\lo_back_s5_im06.jpg"};

void mu_scenemgr_intro(const mu_scenemgr_host *h, mu_scenemgr_globals *g, uint32_t hdc)
{
    call_this(h, 0x01206785u, MU_SCENE_G_LOG, 1, 0xbu);
    /* ResourceGuard on data\local\Gameguard.csr (opaque) */
    call_this(h, 0x0185cf00u, MU_SCENE_STACK, 0);
    call_this(h, 0x0185d160u, MU_SCENE_STACK, 1, MU_SCENE_STACK);
    call_text(h, MU_SC_SPRINTF, 0, "data\\local\\Gameguard.csr", 2, MU_SCENE_STACK, 0x01ac8198u);
    call_this(h, 0x0185daa0u, MU_SCENE_STACK, 1, MU_SCENE_STACK);   /* (std::string temporaries not recorded) */
    uint32_t ui = call(h, MU_SC_UI_MANAGER, 0);
    call(h, 0x016a5524u, 1, 1u);
    call(h, 0x012b0e65u, 0);
    for (uint32_t i = 0; i < 8; ++i)
        load_bitmap(h, TITLE_PATHS[i], 0x7b81u + i, 0x2601u, i == 5 ? 0x2901u : 0x2900u);
    uint32_t config = call(h, 0x0095f75du, 0);
    int battle = peek(h, config + 4u, 1) == 1u;
    for (uint32_t i = 0; i < 6; ++i)
        load_bitmap(h, battle ? TITLE_BATTLE[i] : TITLE_S5[i], 0x7b89u + i, 0x2601u, 0x2900u);
    load_bitmap(h, "Interface\\newui_black_letter_box.jpg", 0x7c80u, 0x2601u, 0x2900u);
    call_this(h, MU_SC_TITLE_CREATE, ui, 0);
    g->gl_cache_597c = 0;
    call(h, 0x0184a990u, 1, 1u);
    call(h, MU_SC_OPEN_BASIC_DATA, 1, hdc);   /* renders the title screen with progress 0..8 of 9 */
    call(h, 0x0182a0dau, 0);                   /* CreateFonts */
    uint32_t options = call(h, 0x00f2bb92u, 0);
    call_this(h, 0x00f2951eu, options, 0);
    uint32_t ui2 = call(h, MU_SC_UI_MANAGER, 0);
    call_this(h, MU_SC_TITLE_RENDER, ui2, 3, hdc, 9u, 9u);
    call_this(h, MU_SC_TITLE_RELEASE, ui, 0);
    for (uint32_t i = 0; i < 6; ++i)
        call(h, MU_SC_DELETE_BITMAP, 2, 0x7b81u + i, 0u);
    for (uint32_t i = 6; i < 14; ++i)
        call(h, MU_SC_DELETE_BITMAP, 2, 0x7b81u + i, 0u);
    set_scene(h, g, MU_SCENE_LOGIN);
    call_this(h, 0x01206888u, MU_SCENE_G_LOG, 2, 0xbu, 1u);
    g->frame_tick = call(h, MU_SC_GET_TICK_COUNT, 0);
    call_this(h, 0x0185d0a0u, MU_SCENE_STACK, 0);   /* ResourceGuard destructor */
}

/* ---- login scene creation 0x01851804 ---- */

void mu_scenemgr_login_create(const mu_scenemgr_host *h, mu_scenemgr_globals *g)
{
    call_this(h, 0x01206785u, MU_SCENE_G_LOG, 1, 0xfu);
    g->login_flag_5eb8 = 1;
    g->world = MU_SCENE_LOGIN_WORLD;
    g->world_folder = MU_SCENE_LOGIN_WORLD;
    call(h, MU_SC_OPEN_WORLD, 1, (uint32_t)g->world);
    call(h, 0x0182a34cu, 0);                               /* login-scene data (textures, models) */
    call_this(h, 0x011e2dc0u, call(h, MU_SC_UI_MANAGER, 0), 0);   /* CUIMng::CreateLoginScene */
    g->protocol = 0;
    call(h, 0x0121c055u, 2, g->server_address, (uint32_t)g->server_port);   /* connect (network) */
    g->login_flag_5b7b = 1;
    g->login_flag_656f = 0;
    g->login_flag_656e = 0;
    g->login_flag_6570 = 0;
    g->login_flag_1109 = 1;
    call(h, 0x016a5524u, 1, 1u);
    if (g->remember_id == 0) {
        uint32_t options = call(h, 0x00f2efe9u, 0);
        uint32_t saved = call_this(h, 0x00f2f47fu, options, 0);
        call(h, MU_SC_STRCPY, 2, g->id_buffer, saved);
        g->id_length = (int32_t)call(h, MU_SC_STRLEN, 1, g->id_buffer);
        g->id_field_1118 = 10;
        g->id_present = g->id_length != 0;
    }
    g->field_1110 = 2;
    g->login_flag_71e1 = 1;
    call(h, MU_SC_MOVE_MAIN_CAMERA, 0);
    g->login_fade = 0.0f;
    uint32_t gfx = call(h, 0x00ac3bf7u, 0);
    call_this(h, 0x00b95a14u, peek(h, gfx + 0xa0u, 4), 1, 0u);
    music(h, MU_SC_PLAY_MP3, g->music_login);
    gfx = call(h, 0x00ac3bf7u, 0);
    call_this(h, 0x00b49bf4u, peek(h, gfx + 0x22cu, 4), 1, 0u);
    gfx = call(h, 0x00ac3bf7u, 0);
    call_this(h, 0x00b4b848u, peek(h, gfx + 0x22cu, 4), 1, 0u);
    call_this(h, 0x01206888u, MU_SCENE_G_LOG, 2, 0xfu, 1u);
}

/* ---- scene-3 tick tail 0x01857621..0x018576a7 ---- */

void mu_scenemgr_login_tick_tail(const mu_scenemgr_host *h, mu_scenemgr_globals *g)
{
    if (g->protocol != MU_SCENE_PROTOCOL_LOGIN_OK)
        return;
    call_text(h, 0x01206598u, 0, "> Request Character list\r\n", 2, MU_SCENE_G_LOG, 0x01af6f54u);
    uint32_t sender = call(h, 0x00988c5cu, 0);
    call_this(h, 0x00988d22u, sender, 3, 0u, 0u, 0u);   /* the character-list request (network) */
    set_scene(h, g, MU_SCENE_CHARACTER);
    call(h, 0x01287a66u, 0);
    uint32_t value = call_this(h, 0x008e7f90u, 0x01d1df24u, 0);
    call(h, 0x00aab55du, 1, value);
    call(h, 0x0182a4f1u, 0);
    call(h, 0x0137c276u, 1, 0xffffffffu);
}

/* ---- frame-driver music block 0x0185276c..0x0185280c ---- */

void mu_scenemgr_frame_music(const mu_scenemgr_host *h, const mu_scenemgr_globals *g)
{
    if (g->scene == MU_SCENE_LOGIN || g->scene == MU_SCENE_CHARACTER)
        music(h, MU_SC_PLAY_MP3, g->music_login);
    else
        music(h, MU_SC_STOP_MP3, g->music_login);
}

/* ---- start loading 0x0185a75a ---- */

void mu_scenemgr_start_loading(const mu_scenemgr_host *h, mu_scenemgr_globals *g, int start)
{
    uint32_t selected = (uint32_t)g->selected_hero;
    uint32_t table = call(h, 0x0095f6dbu, 0);
    uint32_t c = call_this(h, 0x009a13f4u, table, 1, selected);
    if (!start) {
        if (!c)
            return;
        call(h, MU_SCENE_NET_SEND, 0);   /* join request with the character's name (protocol out of scope) */
        uint32_t gfx = peek(h, call(h, 0x00ac3bf7u, 0) + 0x22cu, 4);
        poke(h, gfx + 0x98u, (uint32_t)g->selected_hero, 4);
        return;
    }
    if (!c)
        return;
    if (peek(h, c + 0x14u, 1) & 1u) {
        call_this(h, 0x011e3598u, call(h, MU_SC_UI_MANAGER, 0), 2, 0x84u, 0u);   /* message box 0x84 */
        return;
    }
    uint32_t hero = peek(h, MU_SCENE_G_HERO, 4);
    call_this(h, 0x00a00031u, hero, 1, peek(h, c + 0x144u, 2));
    hero = peek(h, MU_SCENE_G_HERO, 4);
    poke(h, hero + 0x187u, peek(h, c + 0x12u, 1), 1);
    hero = peek(h, MU_SCENE_G_HERO, 4);
    poke(h, hero + 0x188u, peek(h, c + 0x13u, 1), 1);
    uint32_t name = call_this(h, 0x0129deaau, c, 0);
    call_this(h, 0x00a0033eu, peek(h, MU_SCENE_G_HERO, 4), 1, name);
    call(h, MU_SC_STRCPY, 2, peek(h, MU_SCENE_G_HERO, 4) + 0x88u, c + 0x44u);
    call(h, 0x0182a85eu, 0);
    g->init_loading = 0;
    set_scene(h, g, MU_SCENE_LOADING);
    uint32_t gfx = peek(h, call(h, 0x00ac3bf7u, 0) + 0x22cu, 4);
    call_this(h, 0x00b4c117u, gfx, 0);
    gfx = peek(h, call(h, 0x00ac3bf7u, 0) + 0x22cu, 4);
    poke(h, gfx + 0x49u, 0, 1);
    gfx = peek(h, call(h, 0x00ac3bf7u, 0) + 0x22cu, 4);
    call_this(h, 0x00b49bf4u, gfx, 1, 0u);
    gfx = peek(h, call(h, 0x00ac3bf7u, 0) + 0x22cu, 4);
    call_this(h, MU_SC_VCALL, gfx, 1, 0x44u);
    uint32_t state = call(h, 0x009a595bu, 0);
    poke(h, state + 0xcu, 0, 1);
}

/* ---- loading scene 0x01851adc ---- */

void mu_scenemgr_loading(const mu_scenemgr_host *h, mu_scenemgr_globals *g, uint32_t hdc)
{
    uint32_t ui = call(h, MU_SC_UI_MANAGER, 0);
    if (!g->init_loading) {
        g->loading_world = 9999999;
        g->init_loading = 1;
        int32_t r = (int32_t)call(h, MU_SC_RAND, 0);
        int32_t variant = r % 1 + 1;   /* always 1 */
        call(h, MU_SC_MEMSET, 3, MU_SCENE_STACK, 0u, 0x100u);
        for (int32_t i = 0; i < 4; ++i) {
            static const char format[] = "Interface\\LSBg0%d_%d.JPG";
            char path[32] = "Interface\\LSBg0?_?.JPG";
            path[15] = (char)('0' + variant % 10);
            path[17] = (char)('0' + (i + 1) % 10);
            call_text(h, MU_SC_SPRINTF, 0, format, 4, MU_SCENE_STACK, 0x01af6f70u, (uint32_t)variant,
                      (uint32_t)(i + 1));
            load_bitmap(h, path, 0x7b81u + (uint32_t)i, 0x2601u, 0x2900u);
        }
        music(h, MU_SC_STOP_MP3, g->music_login);
        uint32_t memory = call(h, MU_SC_NEW, 1, 0x2a8u);
        uint32_t object = memory ? call_this(h, MU_SC_LOADING_CTOR, memory, 0) : 0u;
        poke(h, ui + 0x6598u, object, 4);
        call_this(h, MU_SC_LOADING_CREATE, peek(h, ui + 0x6598u, 4), 0);
    }
    g->gl_cache_597c = 0;
    call(h, MU_SC_BEGIN_OPENGL, 4, 0u, 0u, 640u, 480u);
    call(h, MU_SC_GL_CLEAR_COLOR, 4, 0u, 0u, 0u, 0x3f800000u);
    call(h, MU_SC_GL_CLEAR, 1, 0x4100u);
    call(h, MU_SC_BEGIN_BITMAP, 0);
    call_this(h, MU_SC_LOADING_RENDER, peek(h, ui + 0x6598u, 4), 0);
    call(h, MU_SC_END_BITMAP, 0);
    call(h, MU_SC_AFTER_2D, 0);
    call(h, MU_SC_SWAP_BUFFERS, 1, hdc);
    uint32_t object = peek(h, ui + 0x6598u, 4);
    if (object) {
        call_this(h, MU_SC_VCALL, object, 2, 0u, 1u);   /* scalar deleting destructor */
        poke(h, ui + 0x6598u, 0, 4);
    }
    set_scene(h, g, MU_SCENE_MAIN);
    for (uint32_t i = 0; i < 4; ++i)
        call(h, MU_SC_DELETE_BITMAP, 2, 0x7b81u + i, 0u);
    call(h, 0x016a5524u, 1, 1u);
}

/* ---- return to character select (0x0125294e subcode 1, static) ---- */

void mu_scenemgr_return_to_character(mu_scenemgr_globals *g)
{
    g->scene = MU_SCENE_CHARACTER;
    g->init_character = 0;
    g->init_main = 0;
    g->login_flag_5eb8 = 0;
    g->protocol = 0;
}
