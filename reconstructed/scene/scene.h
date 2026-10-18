#ifndef MU_SCENEMGR_H
#define MU_SCENEMGR_H

/* The client's scene manager (NATIVE-SHELL-001, docs/research/client-scene-manager.md).
 *
 * Authored C for the routines that own the scene-state global SceneFlag
 * [0x01d1df70] and move it between the client's scenes:
 *
 *   2 intro/title   0x0185ad63  startup loading under the title screen, then 3
 *   3 login         frame driver 0x01851d39; first tick 0x01851804 (world 0x5e)
 *   4 loading       0x01851adc  one loading-screen frame, then 6
 *   5 character     frame driver 0x01851d39 (reconstructed/charsel)
 *   6 main game     frame driver 0x01851d39
 *
 * Every call these routines make into another subsystem goes through the
 * host (mu_scenemgr_host.call) as a mu_scenemgr_call record named by the callee's
 * client address, and every byte they read or write in an object they do not
 * own goes through host.peek / host.poke. The native client implements the
 * calls it needs (textures, music, the loading screen) and ignores the rest;
 * scripts/validate_scene.py compares the record stream and the globals with
 * the client's own instructions run in Unicorn.
 *
 * Pointer conventions in call records:
 *   - objects returned by host calls are opaque handles (the host's values);
 *   - client globals passed by address use their client address (for
 *     example the notification 0x00a05a22 gets ecx = MU_SCENE_G_STATE);
 *   - stack buffers are MU_SCENE_STACK; their contents, when they matter
 *     (paths, music names), are in the record's text.
 * Network sends inside these routines (the protocol is out of scope) are one
 * record with routine MU_SCENE_NET_SEND.
 */

#include <stdint.h>

/* SceneFlag values. */
enum {
    MU_SCENE_INTRO = 2,
    MU_SCENE_LOGIN = 3,
    MU_SCENE_LOADING = 4,
    MU_SCENE_CHARACTER = 5,
    MU_SCENE_MAIN = 6
};

/* Worlds the scenes open (0x01cf15fc). */
#define MU_SCENE_LOGIN_WORLD 0x5e        /* Data/World95, set by 0x01851804 */
#define MU_SCENE_CHARACTER_WORLD 0x5d    /* Data/World94, set by 0x01851540 */

/* Protocol-state values [0x06fca2c4] the scenes test (set by the network
 * layer's handlers; the names are readings of the tests, static). */
#define MU_SCENE_PROTOCOL_LOGIN_OK 0x14      /* scene-3 tick: request the list, go to 5 */
#define MU_SCENE_PROTOCOL_CHARACTERS 0x33    /* scene-5 tick/render run from this value on */

/* Music table index of data\music\login_theme.mp3 (array 0x01cf1680). */
#define MU_SCENE_MUSIC_LOGIN 32

/* Client addresses used as identities. */
#define MU_SCENE_G_STATE 0x01d1df70u         /* SceneFlag */
#define MU_SCENE_G_LOG 0x06fc9ec0u           /* the client's log object */
#define MU_SCENE_G_HERO 0x01d1df1cu          /* Hero pointer */
#define MU_SCENE_STACK 0x5354414bu           /* a stack buffer or local object */
#define MU_SCENE_NET_SEND 0x4e455453u        /* one network packet (out of scope) */

/* Callees (client addresses). */
#define MU_SC_UI_MANAGER 0x011e228bu         /* CUIMng instance */
#define MU_SC_LOAD_BITMAP 0x0185baacu        /* LoadBitmap(path, index, filter, wrap, check, fullpath) */
#define MU_SC_DELETE_BITMAP 0x0185bc1bu      /* DeleteBitmap(index, 0) */
#define MU_SC_PLAY_MP3 0x0120f602u           /* PlayMp3(std::string) */
#define MU_SC_STOP_MP3 0x0120f5a0u           /* StopMp3(std::string) */
#define MU_SC_SPRINTF 0x009619ddu
#define MU_SC_MEMSET 0x0194cd00u
#define MU_SC_STRCPY 0x01983a90u
#define MU_SC_STRLEN 0x0195a4b0u
#define MU_SC_STRNCMP 0x01983b90u
#define MU_SC_RAND 0x01989721u
#define MU_SC_NEW 0x0191ba7bu                /* operator new */
#define MU_SC_NOTIFY_STATE 0x00a05a22u       /* SceneFlag observer, ecx = &SceneFlag */
#define MU_SC_BEGIN_OPENGL 0x0184adc7u
#define MU_SC_BEGIN_BITMAP 0x0184f793u
#define MU_SC_END_BITMAP 0x0184f8d7u
#define MU_SC_AFTER_2D 0x0184b6ddu
#define MU_SC_GL_CLEAR_COLOR 0x01a7c6ccu     /* import slots */
#define MU_SC_GL_CLEAR 0x01a7c6e8u
#define MU_SC_SWAP_BUFFERS 0x01a7c148u
#define MU_SC_GET_TICK_COUNT 0x01a7c49cu
#define MU_SC_LOADING_CTOR 0x00cdb6cau       /* CLoadingScene (0x2a8 bytes) */
#define MU_SC_LOADING_CREATE 0x00cdb74cu
#define MU_SC_LOADING_RENDER 0x00cdb94fu
#define MU_SC_VCALL 0x56434c4cu              /* virtual call: args[0] = vtable offset, then the arguments */
#define MU_SC_INTRO 0x0185ad63u
#define MU_SC_LOADING 0x01851adcu
#define MU_SC_FRAME 0x01851d39u
#define MU_SC_OPEN_WORLD 0x0182876eu
#define MU_SC_TITLE_CREATE 0x011e230du
#define MU_SC_TITLE_RENDER 0x011e2c8cu
#define MU_SC_TITLE_RELEASE 0x011e2bc3u
#define MU_SC_OPEN_BASIC_DATA 0x0182049eu
#define MU_SC_MOVE_MAIN_CAMERA 0x0185498eu

#define MU_SCENE_CALL_ARGS 8

typedef struct mu_scenemgr_call {
    uint32_t routine;                     /* callee address (or a MU_SCENE_* pseudo id) */
    uint32_t ecx;                         /* this pointer of thiscall callees, else 0 */
    int32_t count;                        /* stack argument words */
    uint32_t args[MU_SCENE_CALL_ARGS];
    const char *text;                     /* string argument, when the callee takes one */
} mu_scenemgr_call;

typedef struct mu_scenemgr_host {
    void *user;
    /* returns EAX of the callee */
    uint32_t (*call)(void *user, const mu_scenemgr_call *call);
    /* object bytes: size 1, 2 or 4 */
    uint32_t (*peek)(void *user, uint32_t address, int32_t size);
    void (*poke)(void *user, uint32_t address, uint32_t value, int32_t size);
} mu_scenemgr_host;

/* The globals these routines read and write (client addresses in comments). */
typedef struct mu_scenemgr_globals {
    int32_t scene;                 /* 0x01d1df70 SceneFlag */
    int32_t protocol;              /* 0x06fca2c4 */
    int32_t world;                 /* 0x01cf15fc */
    int32_t world_folder;          /* 0x01cf1600 */
    int32_t selected_hero;         /* 0x01cf1864 */
    int32_t loading_world;         /* 0x0b437c14 LoadingWorld */
    int32_t send_counter;          /* 0x06fc9e4c (read: > 31 makes the dispatcher send) */
    int32_t remember_id;           /* 0x01cf0fac (0: copy the saved account name) */
    int32_t id_length;             /* 0x0b4371b0 */
    int32_t id_field_1118;         /* 0x01cf1118 */
    int32_t id_present;            /* 0x0b436578 */
    int32_t field_1110;            /* 0x01cf1110 */
    uint32_t frame_tick;           /* 0x0bdc5e64 */
    float login_fade;              /* 0x0bdc5b80 */
    uint8_t init_login;            /* 0x0bdc5b86 */
    uint8_t init_loading;          /* 0x0bdc5b87 */
    uint8_t init_character;        /* 0x0bdc5ca2 */
    uint8_t init_main;             /* 0x0bdc5ca3 */
    uint8_t gl_cache_597c;         /* 0x0bdc597c (cleared before BeginOpengl) */
    uint8_t loop_flag_2d1e;        /* 0x01d22d1e (cleared every loop) */
    uint8_t login_flag_5eb8;       /* 0x0bdc5eb8 */
    uint8_t login_flag_5b7b;       /* 0x0bdc5b7b */
    uint8_t login_flag_656e;       /* 0x0b43656e */
    uint8_t login_flag_656f;       /* 0x0b43656f */
    uint8_t login_flag_6570;       /* 0x0b436570 */
    uint8_t login_flag_1109;       /* 0x01cf1109 */
    uint8_t login_flag_71e1;       /* 0x0b4371e1 */
    uint32_t server_address;       /* 0x01cf1858 (char *) */
    uint16_t server_port;          /* 0x01cf185c */
    uint32_t music_login;          /* 0x01cf1680[32] (char *, data\music\login_theme.mp3) */
    uint32_t id_buffer;            /* 0x0b436580: account-name buffer (address) */
    float view_far;                /* 0x01cf1630 CameraViewFar (NATIVE-LOGIN-001: written by the login render) */
} mu_scenemgr_globals;

/* Which routine the dispatcher runs for a SceneFlag value. */
enum { MU_SCENE_RUN_NONE = 0, MU_SCENE_RUN_INTRO, MU_SCENE_RUN_LOADING, MU_SCENE_RUN_FRAME };
int mu_scenemgr_dispatch_target(int32_t scene);

/* Scene dispatcher 0x01859d8a(hdc), called by the WinMain loop whenever the
 * message queue is empty: the per-loop service calls, the scene routine
 * (intro, loading or the frame driver, passed to the host as a call), then
 * the observer call with the (possibly new) SceneFlag. The network send of
 * the tail (SendCounter > 31) is one MU_SCENE_NET_SEND record. */
void mu_scenemgr_dispatch(const mu_scenemgr_host *host, mu_scenemgr_globals *g, uint32_t hdc);

/* Intro/title scene 0x0185ad63(hdc): the title-screen textures 0x7b81..0x7b8e
 * (variant from 0x0095f75d()->+4), CreateTitleSceneUI, the startup data
 * loader 0x0182049e (which renders the title screen with progress 0..8 of 9),
 * the final title frame (9 of 9), the texture release, SceneFlag = 3 and the
 * frame tick. The ResourceGuard check at its start is opaque (calls recorded;
 * its failure branch is unreachable: an unconditional jump skips it). */
void mu_scenemgr_intro(const mu_scenemgr_host *host, mu_scenemgr_globals *g, uint32_t hdc);

/* Login scene creation 0x01851804 (the scene-3 tick's first step):
 * world 0x5e (World95), OpenWorld, the login data, CUIMng::CreateLoginScene,
 * protocol 0, the server connection call (network, recorded), the saved
 * account name, MoveMainCamera, fade 0 and PlayMp3(login theme). */
void mu_scenemgr_login_create(const mu_scenemgr_host *host, mu_scenemgr_globals *g);

/* Tail of the scene-3 tick 0x01857236 (0x01857621..0x018576a7): when the
 * network layer has set protocol 0x14 (login accepted), the character-list
 * request, SceneFlag = 5 and the character-scene preparation. */
void mu_scenemgr_login_tick_tail(const mu_scenemgr_host *host, mu_scenemgr_globals *g);

/* Frame-driver music block 0x0185276c..0x0185280c (every rendered frame,
 * after the cap): PlayMp3(login theme) in scenes 3 and 5, StopMp3 otherwise. */
void mu_scenemgr_frame_music(const mu_scenemgr_host *host, const mu_scenemgr_globals *g);

/* 0x0185a75a(start): start = 0 asks the server to join with SelectedHero
 * (Enter in character select; network, one MU_SCENE_NET_SEND record) and
 * stores the selection in the GFx state; start = 1 (the server's answer)
 * copies the selected character into the Hero, clears InitLoading and sets
 * SceneFlag = 4. */
void mu_scenemgr_start_loading(const mu_scenemgr_host *host, mu_scenemgr_globals *g, int start);

/* Loading scene 0x01851adc(hdc): first call loads Interface\LSBg0<v>_1..4
 * (v = rand() % 1 + 1, i.e. 1), stops the login music and creates the
 * CLoadingScene object at CUIMng+0x6598; every call renders one frame
 * (BeginOpengl, clear, BeginBitmap, CLoadingScene::Render, EndBitmap, swap),
 * destroys the object, sets SceneFlag = 6 and frees the four textures. The
 * world itself is loaded elsewhere (the join-map handler and the first
 * scene-6 tick); the loading frame stays on screen meanwhile. */
void mu_scenemgr_loading(const mu_scenemgr_host *host, mu_scenemgr_globals *g, uint32_t hdc);

/* ---- the login scene's 3D part (NATIVE-LOGIN-001, docs/research/client-login-scene.md) ---- */

/* Callees of the scene-3 tick head and render (names: client calls are named
 * by address; the descriptive names are readings, see the research note). */
#define MU_SC_CAMERA_RECORD 0x0098647bu      /* camera-record manager singleton: +0xc record, +0x10 far scale */
#define MU_SC_SCREEN_WIDTH 0x016bc355u       /* window width in pixels */
#define MU_SC_CREATE_FRUSTUM 0x016cba24u     /* CreateFrustrum(aspect, &position, 0), vector in text */
#define MU_SC_GL_COLOR3F 0x01a7c76cu         /* import slot */
#define MU_SC_RENDER_TERRAIN 0x016cd468u
#define MU_SC_RENDER_OBJECTS 0x016d5020u
#define MU_SC_RENDER_OBJECTS_AFTER 0x016d6949u
#define MU_SC_FRAME_LIGHT 0x016ca4fau         /* frame-light copy of the logic step */
#define MU_SC_MOVE_OBJECTS 0x016d82c7u
#define MU_SC_MOVE_CHARACTERS 0x0137a7ceu
#define MU_SC_RENDER_CHARACTERS 0x0137a3c2u
#define MU_SC_MOVE_CHARACTER_CAMERA 0x01854529u
#define MU_SC_PUSH_IDENTITY 0x0184a699u
#define MU_SC_POP_MATRIX 0x0184a6abu
#define MU_SC_RENDER_SPRITES 0x0169270eu     /* ecx 0x0a3da070 (sprite list; CreateSprite 0x01692eb7) */
#define MU_SC_RENDER_PARTICLES 0x0159123fu   /* ecx 0x0a3a9adc (billboard quads) */

/* Login render 0x01857ed9, its 3D part up to BeginBitmap (0x01857ed9..0x0185810e).
 * Returns 0 before the scene is created (InitLogIn [0x0bdc5b86] clear; the
 * client returns 0 then), else 1. In order: the fog byte cleared,
 * MoveMainCamera, glColor3f(1,1,1), glClearColor(0,0,0,1), BeginOpengl(0, 0,
 * 640, 480), CreateFrustrum(width / 640, camera-record position, 0); unless
 * the credit window is open (CUIMng+0x4648, byte +0xc): CameraViewFar = 2400 *
 * Distance * Z_Distance * scale (0x0098ac45 inlined), RenderTerrain(0),
 * RenderCharacters, 0x00c9e4e3, RenderObjects, 0x01589b56(0), RenderEffects
 * (0x015181fa on the pool 0x0a4ca430), 0x01692887, 0x01538145, 0x00c9fd8d(0),
 * RenderObjects_AfterCharacter, 0x00b990b0()->0x00eb0dee; then the identity
 * push, RenderSprites(0), RenderParticles(0), pop and BeginBitmap. The 2D part
 * that follows is reconstructed/ui's login overlay (mu_ui_login_overlay). */
int mu_scenemgr_login_render_3d(const mu_scenemgr_host *host, mu_scenemgr_globals *g);

/* Login tick 0x01857236 up to MoveCharacterCamera (0x01857236..0x01857322):
 * the creation 0x01851804 on the first step; unless the credit window is open,
 * the frame-light copy, MoveObjects, 0x00c9e24a, MoveJoints (0x01537a43),
 * MoveCharacters, 0x0106bcc5 on 0x009c104e(1), MoveEffects (0x0150ddb1),
 * 0x01589b06, MoveParticles (0x0159122d), 0x0106bcc5 on 0x009c104e(0),
 * 0x00c9eb04, 0x00b990b0()->0x00eb0d64, 0x009c2aea()->0x009b9913, the GFx
 * update 0x00ac9613(SceneFlag) and MoveCharacterCamera. Returns 1 when that
 * block ran, 0 when the credit window is open (the client then goes on with
 * its GFx branch at 0x01857448, not reconstructed here). The creation runs as
 * a host call (MU_SC_LOGIN_CREATE) so the host can run mu_scenemgr_login_create. */
#define MU_SC_LOGIN_CREATE 0x01851804u
int mu_scenemgr_login_tick_head(const mu_scenemgr_host *host, mu_scenemgr_globals *g);

/* Return to character select, the network handler 0x0125294e subcode 1
 * after its answer (static reading, not executed): SceneFlag = 5,
 * InitCharacterScene = InitMainScene = 0, protocol 0. */
void mu_scenemgr_return_to_character(mu_scenemgr_globals *g);

#endif
