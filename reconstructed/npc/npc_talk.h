/* The client's NPC talk: the window its talk-result handler opens per result
 * code, and the talk case's local rules (NATIVE-NPC-001,
 * docs/research/client-npc-interaction.md).
 *
 * Pinned inputs: restored text capture09 (2bd5f2e9...3724) at 0x00401000 and
 * the second image section run10 (c985e2e6...a0672f) at 0x01a7c000.
 *
 * ReceiveTalk 0x01280659(packet, encrypted) is the receive handler of the
 * server's talk answer (dispatcher 0x01287ead case 0xdf).  The network side
 * is out of scope: this module restates what the handler does with the
 * packet's bytes once it arrived.  mu_npc_talk_result reproduces every call
 * the handler makes, in order, with its arguments; scripts/validate_npc.py
 * runs the client's instructions in Unicorn and compares the call lists
 * (verified).  The talk-case rules below the dispatch are static readings
 * of MoveHero's Action case 2 (0x0169901c..0x0169c094). */
#ifndef MU_NPC_TALK_H
#define MU_NPC_TALK_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Client callees the handler reaches (thiscall unless noted). */
#define MU_TALK_IS_VISIBLE 0x00aae6f9u     /* GFx window: visible? (no args) */
#define MU_TALK_CLOSE_ALL 0x00ac9c74u      /* GFx manager: close the windows (no args) */
#define MU_TALK_NEWUI_CLOSE 0x00f2b53du    /* legacy NewUI manager: close all (no args) */
#define MU_TALK_NEWUI_OPEN 0x00f2abcdu     /* legacy NewUI manager: open window (id) */
#define MU_TALK_NEWUI_GET 0x00f2c102u      /* legacy NewUI manager: a window object (no args) */
#define MU_TALK_NEWUI_SET 0x00ef00b4u      /* that window: set (index) */
#define MU_TALK_ENTRANCE_MODE 0x00b04bd2u  /* EventMapEntranceUI: mode (n) */
#define MU_TALK_ENTRANCE_SET 0x00b04dedu   /* EventMapEntranceUI: (3, index, flag, 0, 1) */
#define MU_TALK_OBJ_6FC9EB0 0x011e04c7u    /* object [0x06fc9eb0]: (0xe) */
#define MU_TALK_SCALP_FLAG 0x00bd0006u     /* MixAttributeScalp: (result == 8) */
#define MU_TALK_MIXSEL_18 0x00bd72a3u      /* MixSel methods of results 0x18, 0x26, 0x27 */
#define MU_TALK_MIXSEL_26 0x00bd7408u
#define MU_TALK_MIXSEL_27 0x00bd709cu
#define MU_TALK_EC_25 0x00baeb44u          /* handler at manager +0xec (no movie, ctor 0xbae3a4) */
#define MU_TALK_DUELWATCH 0x00b54793u      /* duelwatch: open (no args) */
#define MU_TALK_TOGGLE 0x00aae767u         /* GFx window: show (no args) */
#define MU_TALK_DIALOGUE_NPC 0x00fdc96cu   /* NPC dialogue manager 0x01ec9858: set NPC (class) */
#define MU_TALK_DIALOGUE_OPEN 0x00be842cu  /* npcdialogue handler: open (no args) */
#define MU_TALK_CALL_19 0x0121405eu        /* cdecl (pointer to a local), result 0x19 */
#define MU_TALK_LOCAL_DTOR 0x01287617u     /* its local's destructor (this = the local) */
#define MU_TALK_SHOP_FLAG_OBJ 0x00aabe9bu  /* cdecl getter; result 0x22 sets byte +4 of it */
#define MU_TALK_SHOP_TABS 0x00bf17c2u      /* NpcShop: (packet[0xb]) */
#define MU_TALK_SND_PLAY 0x00a6ac96u       /* cdecl SND_Play(id, object, loop) */
#define MU_TALK_SET_CURSOR 0x01a7c870u     /* import slot: user32 SetCursorPos(x, y) */
#define MU_TALK_PACKET_BEGIN 0x00d51bafu   /* packet builder (local): Begin(head, opcode) */
#define MU_TALK_PACKET_ADD 0x00d51c9bu     /* AddData(byte value (recorded), 1, 1) */
#define MU_TALK_PACKET_SEND 0x00d51d4fu    /* Send(1, 0) */
#define MU_TALK_VTABLE(slot) (0x80000000u | (uint32_t)(slot))   /* virtual call through the window's vtable */
#define MU_TALK_WRITE 0x90000000u          /* recorded memory write: args (address, value) */

/* `self` tags: a GFx window is its slot offset in the GFx manager
 * (0x00ac3bf7(); the registry 0x00ac4a79 fills the slots); the others: */
#define MU_TALK_SELF_NONE 0u
#define MU_TALK_SELF_MANAGER 0xffffu
#define MU_TALK_SELF_NEWUI 0xfffeu         /* 0x00f2bb92() */
#define MU_TALK_SELF_DIALOGUE 0xfffdu      /* 0x01ec9858 */
#define MU_TALK_SELF_6FC9EB0 0xfffcu       /* [0x06fc9eb0] */
#define MU_TALK_SELF_SHOP_FLAG 0xfffbu     /* 0x00aabe9b() */
#define MU_TALK_SELF_NEWUI_WINDOW 0xfffau  /* the object 0x00f2c102 returns */
#define MU_TALK_SELF_PACKET 0xfff9u        /* the local packet builder */
#define MU_TALK_SELF_LOCAL 0xfff8u         /* a stack local (result 0x19) */

#define MU_TALK_MIX_TYPE 0x01ec8d78u       /* global the mix results write before opening MixInventoryFrame */

typedef struct mu_talk_input {
    const uint8_t *packet;      /* the answer: [3] result, [4]/[5] entrance index, [0xb] shop tabs, [0xc] entrance flag */
    size_t length;
    int encrypted;              /* second argument: 0 = the packet did not come through the C3/C4 decryption */
    int entrance_visible;       /* EventMapEntranceUI (+0x2ac) visible: the handler then keeps the other windows */
    int has_b0, has_b4, has_ac; /* manager slots +0xb0 MixGoblinSel, +0xb4 MixAttributeScalp, +0xac MixSel non-null */
    int32_t hero_x, hero_y;     /* hero tile (character +0x180/+0x184), read by result 0x23 */
    int32_t cursor_lock;        /* [0x01cf0fc0]: non-zero skips SetCursorPos */
    int32_t mouse_x, mouse_y;   /* [0x0bdc5ad8], [0x0bdc5adc] */
    int32_t screen_w, screen_h; /* [0x01cf1624], [0x01cf1628] */
} mu_talk_input;

#define MU_TALK_ARGS 6
typedef struct mu_talk_event {
    uint32_t callee;            /* client address, MU_TALK_VTABLE(slot) or MU_TALK_WRITE */
    uint32_t self;              /* manager slot offset or MU_TALK_SELF_* */
    int32_t n;
    uint32_t args[MU_TALK_ARGS];
} mu_talk_event;

#define MU_TALK_EVENTS 24
typedef struct mu_talk_output {
    mu_talk_event events[MU_TALK_EVENTS];
    int32_t count;
    int32_t returned;           /* the handler's return value (EAX) */
} mu_talk_output;

/* Runs the handler's logic: every call (and the two memory writes) in the
 * order the client makes them. */
void mu_npc_talk_result(const mu_talk_input *in, mu_talk_output *out);

/* What a result code opens, for a native host (derived from the same
 * dispatch; names are the GFx registry's movie names). */
typedef enum mu_talk_kind {
    MU_TALK_KIND_NONE = 0,      /* 0xff, 0x12, 0x24, 0x38: nothing besides the common tail */
    MU_TALK_KIND_OPEN,          /* GFx window vtable +0x40 (Open) */
    MU_TALK_KIND_SHOW,          /* GFx window 0x00aae767 */
    MU_TALK_KIND_METHOD,        /* a handler method (see `method`) */
    MU_TALK_KIND_DIALOGUE,      /* npcdialogue with the dialogue NPC `dialogue` */
    MU_TALK_KIND_NEWUI,         /* legacy NewUI window `arg` */
    MU_TALK_KIND_ENTRANCE,      /* EventMapEntranceUI */
    MU_TALK_KIND_PACKET,        /* answers with a packet (result 0x0d) */
    MU_TALK_KIND_OTHER          /* results 0x05, 0x19 */
} mu_talk_kind;

typedef struct mu_talk_window {
    mu_talk_kind kind;
    uint16_t slot;              /* GFx manager slot (0: none) */
    const char *movie;          /* registry movie name, or "" */
    uint32_t method;            /* MU_TALK_KIND_METHOD/SHOW: callee */
    int32_t arg;                /* method/NewUI argument (-1 none) */
    int32_t dialogue;           /* dialogue NPC class (-1 none) */
    int32_t mix_type;           /* value written to MU_TALK_MIX_TYPE (-1 none) */
    int shop;                   /* 1: NpcShop (default results, and 0x22) */
} mu_talk_window;

void mu_npc_talk_window(uint8_t result, mu_talk_window *out);

/* Registry movie name of a GFx manager slot ("" when the slot has no movie
 * or is not one the talk handler uses). */
const char *mu_npc_slot_movie(uint16_t slot);

/* ---- MoveHero's talk case (Action case 2, 0x0169901c), static readings ---- */

/* NpcShop 0x00bf172e(flag) before the talk request: 1 (repair allowed) for
 * NPC classes 243, 246, 251, 416, 578, 686, 687, else 0. */
int mu_npc_repair_shop(int32_t npc_class);

/* Local refusals before the talk request (GlobalText messages, no packet):
 *   DivideWindow (+0x250) visible            -> GlobalText 0x148c, nothing sent;
 *   class 238 (Chaos Goblin) below level 10  -> GlobalText 0x297 with "%d" = 10;
 *   class != 0 and MUMix (+0x290) visible     -> GlobalText 0xfd8.
 * Returns the GlobalText index or -1 when the talk goes on. */
typedef struct mu_talk_gate {
    int32_t npc_class, hero_level;
    int divide_visible, mumix_visible;
} mu_talk_gate;
int32_t mu_npc_talk_refusal(const mu_talk_gate *gate);

#ifdef __cplusplus
}
#endif

#endif
