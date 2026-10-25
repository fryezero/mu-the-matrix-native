/* SESSION-CORE-001 (sketch): typed intents, the only way a view asks for change.
 *
 * An intent names what the player (or a scene) wants in domain terms: no opcodes, no bytes.
 * mu_session_submit turns it into the client's own local checks plus the reconstructed
 * request builder. A kind whose builder is not reconstructed yet returns
 * MU_SUBMIT_UNRECOVERED: the type exists so views can be written against it, but no bytes
 * are invented (evidence rule).
 *
 * Adding a kind: one line in the owning domain's domains/<d>.intents
 *     MU_INTENT_KIND(ADD_STAT, add_stat, struct { int32_t stat; })
 * plus the MU_SUBMIT row in ops/<d>.ops and the submit function in domains/<d>.c. The enum
 * and the payload union below are GENERATED from every domains/*.intents (shown hand-written
 * here for readability), so parallel domain work never edits this file; a kind without a
 * MU_SUBMIT route fails test_session_routes.py.
 */
#ifndef MU_INTENT_H
#define MU_INTENT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* A credential that can only be consumed by the login encoder. It has no getter: the journal,
 * logs and reports cannot serialize it. mu_secret_set copies and mu_session_submit zeroes the
 * intent's copy after encoding. */
typedef struct mu_secret {
    uint8_t opaque_[64];
    uint8_t length_;
} mu_secret;
void mu_secret_set(mu_secret *s, const char *utf8);   /* truncates to the client's field width */
void mu_secret_wipe(mu_secret *s);

typedef enum mu_store {          /* where an item sits */
    MU_STORE_INVENTORY = 0, MU_STORE_EQUIPMENT, MU_STORE_WAREHOUSE, MU_STORE_TRADE, MU_STORE_PERSONAL_SHOP,
    MU_STORE_MIX, MU_STORE_EVENT_INVENTORY, MU_STORE_EXTENSION_BAG
} mu_store;

typedef enum mu_intent_kind {
    /* account (domain account) */
    MU_INTENT_CHOOSE_SERVER = 1, MU_INTENT_LOGIN, MU_INTENT_REQUEST_CHARACTERS, MU_INTENT_CREATE_CHARACTER,
    MU_INTENT_DELETE_CHARACTER, MU_INTENT_JOIN, MU_INTENT_LEAVE_WORLD, MU_INTENT_LOGOUT, MU_INTENT_KEEPALIVE,
    /* hero motion and combat (domains map, combat) */
    MU_INTENT_WALK, MU_INTENT_ATTACK, MU_INTENT_CAST, MU_INTENT_GATE, MU_INTENT_WARP,
    /* items (domains inventory, ground) */
    MU_INTENT_PICK_UP, MU_INTENT_DROP, MU_INTENT_MOVE_ITEM, MU_INTENT_USE_ITEM, MU_INTENT_BUY, MU_INTENT_SELL,
    MU_INTENT_REPAIR, MU_INTENT_MIX,
    /* npc */
    MU_INTENT_TALK, MU_INTENT_CLOSE_TALK,
    /* progress, skills, options */
    MU_INTENT_ADD_STAT, MU_INTENT_SAVE_SKILL_KEYS, MU_INTENT_MASTER_POINT, MU_INTENT_SAVE_OPTIONS,
    /* windows whose handler state is session-owned (quest windows, the stat window, messenger rooms):
     * the GFx view forwards the window event, the session runs the reconstructed window handler on its
     * state (which may also send a request). One generated kind per such window, from the meta line of
     * native/gfx/windows/<movie>.c, routed by MU_SUBMIT like any other kind (no second table by id). */
    MU_INTENT_WINDOW_QUEST_PROGRESS, MU_INTENT_WINDOW_QUEST_INFO, MU_INTENT_WINDOW_CHARACTER,
    MU_INTENT_WINDOW_ROOM,
    /* social */
    MU_INTENT_CHAT, MU_INTENT_WHISPER, MU_INTENT_PARTY, MU_INTENT_TRADE, MU_INTENT_FRIEND, MU_INTENT_MAIL,
    MU_INTENT_ROOM,
    /* later systems add their kinds here (guild, duel, gens, event entrance, personal shop, siege, ...) */
    MU_INTENT_KINDS
} mu_intent_kind;

typedef struct mu_intent {
    mu_intent_kind kind;
    union {
        struct { int32_t group, slot; } choose_server;
        struct { char account[11]; mu_secret password; } login;      /* field widths: NET-ACCOUNT-001 */
        struct { char name[11]; uint8_t class_code; } create_character;
        struct { int32_t slot; mu_secret confirm; } delete_character;   /* the client asks for a code */
        struct { int32_t slot; } join;
        /* the hero's path as the client sends it (SendMove 0x016b5cd0 reads the PATH_t); the world has
         * already started walking locally, as the client does */
        struct { int32_t from[2]; uint8_t dirs[16]; int32_t count; } walk;
        struct { int16_t target_key; uint8_t action; uint8_t direction; } attack;
        struct { int32_t skill; int16_t target_key; int32_t tile[2]; } cast;
        struct { int32_t gate; } gate;
        struct { int32_t move_key; } warp;                               /* MoveCommand row key */
        struct { int16_t item_key; } pick_up;
        struct { mu_store from; int32_t cell; int32_t tile[2]; } drop;
        struct { mu_store from; int32_t from_cell; mu_store to; int32_t to_cell; } move_item;
        struct { int32_t cell; int32_t target_cell; } use_item;
        struct { int32_t shop_cell; } buy;
        struct { int32_t cell; } sell;
        struct { int32_t cell; int all; } repair;
        struct { int32_t recipe; int32_t mix_type; } mix;
        struct { int16_t npc_key; } talk;
        struct { int32_t stat; } add_stat;                               /* 0..4 */
        struct { int32_t keys[10]; } save_skill_keys;
        struct { int32_t skill; } master_point;
        struct { uint32_t window; int32_t event; int32_t a, b; char text[128]; } window_event;
        struct { int32_t channel; char text[100]; } chat;
        struct { char to[11]; char text[100]; } whisper;
        struct { int32_t verb; int16_t key; } party;                     /* invite / answer / leave / kick */
        struct { int32_t verb; int16_t key; int64_t money; } trade;
        struct { int32_t verb; char name[11]; } friend_;
        struct { int32_t verb; uint32_t letter; char to[11]; char title[33]; char text[1001]; } mail;
        struct { int32_t verb; uint32_t room; char text[100]; char name[11]; } room;
    } u;
} mu_intent;

#ifdef __cplusplus
}
#endif

#endif /* MU_INTENT_H */
