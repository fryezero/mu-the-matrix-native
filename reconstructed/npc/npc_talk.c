/* NPC talk result and talk-case rules (NATIVE-NPC-001); see npc_talk.h. */
#include "npc_talk.h"

#include <string.h>

/* GFx manager slots the handler uses, with the registry's movie names
 * (0x00ac4a79: each registration stores the handler at the slot and
 * registers the movie name). */
static const struct { uint16_t slot; const char *movie; } SLOTS[] = {
    {0x0a8, "MixInventoryFrame"}, {0x0ac, "MixSel"},         {0x0b0, "MixGoblinSel"},
    {0x0b4, "MixAttributeScalp"}, {0x0e0, "duelwatch"},      {0x0ec, ""},
    {0x0f0, "npcdialogue"},       {0x0f4, "NpcShop"},        {0x100, "StorageInven"},
    {0x164, "PersonalShop"},      {0x1ac, "MuunExchange"},   {0x1d4, "OrdealSquareBattleEnter"},
    {0x1fc, "RuudShopFrame"},     {0x204, "ElementalMix"},   {0x208, "SocketMix"},
    {0x20c, "GuardianMix"},       {0x260, "HarmonyMix"},     {0x264, "HarmonyMix"},
    {0x270, "ExchangeLuckCoin"},  {0x2ac, "EventMapEntranceUI"}};

const char *mu_npc_slot_movie(uint16_t slot)
{
    for (size_t i = 0; i < sizeof SLOTS / sizeof SLOTS[0]; i++)
        if (SLOTS[i].slot == slot)
            return SLOTS[i].movie;
    return "";
}

static void emit(mu_talk_output *out, uint32_t callee, uint32_t self, int n, uint32_t a0, uint32_t a1, uint32_t a2,
                 uint32_t a3, uint32_t a4)
{
    if (out->count >= MU_TALK_EVENTS)
        return;
    mu_talk_event *e = &out->events[out->count++];
    memset(e, 0, sizeof *e);
    e->callee = callee;
    e->self = self;
    e->n = n;
    e->args[0] = a0;
    e->args[1] = a1;
    e->args[2] = a2;
    e->args[3] = a3;
    e->args[4] = a4;
}

#define CALL0(out, callee, self) emit(out, callee, self, 0, 0, 0, 0, 0, 0)
#define CALL1(out, callee, self, a) emit(out, callee, self, 1, (uint32_t)(a), 0, 0, 0, 0)
#define OPEN(out, slot) CALL0(out, MU_TALK_VTABLE(0x40), slot)

static uint8_t byte_at(const mu_talk_input *in, size_t i)
{
    return in->packet && i < in->length ? in->packet[i] : 0;
}

/* The NPC dialogue windows: 0x00fdc96c(class) on the manager 0x01ec9858,
 * then the npcdialogue handler's open 0x00be842c. */
static void dialogue(mu_talk_output *out, uint32_t npc)
{
    CALL1(out, MU_TALK_DIALOGUE_NPC, MU_TALK_SELF_DIALOGUE, npc);
    CALL0(out, MU_TALK_DIALOGUE_OPEN, 0x0f0);
}

/* The mix results: write the mix type, open MixInventoryFrame. */
static void mix(mu_talk_output *out, uint32_t type)
{
    emit(out, MU_TALK_WRITE, MU_TALK_SELF_NONE, 2, MU_TALK_MIX_TYPE, type, 0, 0, 0);
    OPEN(out, 0x0a8);
}

static void shop_default(const mu_talk_input *in, mu_talk_output *out)
{
    CALL1(out, MU_TALK_SHOP_TABS, 0x0f4, byte_at(in, 0xb));
    OPEN(out, 0x0f4);
}

static void entrance(const mu_talk_input *in, mu_talk_output *out)
{
    /* Result 0x23: index = packet[4] * 60 + packet[5]; in the hero area
     * x 0x34..0x4b, y 0xe4..0xfa the legacy NewUI window 0x3f opens and its
     * window object gets the index; elsewhere EventMapEntranceUI mode 3. */
    uint32_t index = (uint32_t)byte_at(in, 4) * 0x3c + byte_at(in, 5);
    int inside_x = in->hero_x >= 0x34 && in->hero_x <= 0x4b;
    int inside_y = in->hero_y >= 0xe4 && in->hero_y <= 0xfa;
    if (inside_x && inside_y) {
        CALL1(out, MU_TALK_NEWUI_OPEN, MU_TALK_SELF_NEWUI, 0x3f);
        CALL0(out, MU_TALK_NEWUI_GET, MU_TALK_SELF_NEWUI);
        CALL1(out, MU_TALK_NEWUI_SET, MU_TALK_SELF_NEWUI_WINDOW, index);
        return;
    }
    CALL1(out, MU_TALK_ENTRANCE_MODE, 0x2ac, 3);
    emit(out, MU_TALK_ENTRANCE_SET, 0x2ac, 5, 3, index, byte_at(in, 0xc) ? 1u : 0u, 0, 1);
}

static void dispatch(const mu_talk_input *in, mu_talk_output *out, uint8_t r)
{
    switch (r) {
#ifdef MU_MUT_TALK_STORAGE
    case 0x02: OPEN(out, 0x104); return;                                   /* planted mistake */
#else
    case 0x02: OPEN(out, 0x100); return;                                   /* StorageInven */
#endif
    case 0x03: if (in->has_b0) OPEN(out, 0x0b0); return;                   /* MixGoblinSel */
    case 0x04: CALL1(out, MU_TALK_ENTRANCE_MODE, 0x2ac, 2); return;
    case 0x05: CALL1(out, MU_TALK_OBJ_6FC9EB0, MU_TALK_SELF_6FC9EB0, 0xe); return;
    case 0x06: CALL1(out, MU_TALK_ENTRANCE_MODE, 0x2ac, 1); return;
    case 0x07: OPEN(out, 0x20c); return;                                   /* GuardianMix */
    case 0x08: case 0x09:                                                  /* MixAttributeScalp */
        CALL0(out, MU_TALK_CLOSE_ALL, MU_TALK_SELF_MANAGER);
        if (in->has_b4) {
            CALL1(out, MU_TALK_SCALP_FLAG, 0x0b4, r == 8 ? 1u : 0u);
            OPEN(out, 0x0b4);
        }
        return;
    case 0x0c: CALL1(out, MU_TALK_NEWUI_OPEN, MU_TALK_SELF_NEWUI, 0x17); return;
    case 0x0d:                                                             /* answers with packet 0x83 {2} */
        emit(out, MU_TALK_PACKET_BEGIN, MU_TALK_SELF_PACKET, 2, 0xc1, 0x83, 0, 0, 0);
        emit(out, MU_TALK_PACKET_ADD, MU_TALK_SELF_PACKET, 3, 2, 1, 1, 0, 0);
        emit(out, MU_TALK_PACKET_SEND, MU_TALK_SELF_PACKET, 2, 0, 0, 0, 0, 0);
        return;
    case 0x11: OPEN(out, 0x264); return;                                   /* HarmonyMix (second) */
    case 0x12: return;
    case 0x13: OPEN(out, 0x260); return;                                   /* HarmonyMix */
    case 0x15: mix(out, 8); return;
    case 0x16: mix(out, 9); return;
    case 0x17: OPEN(out, 0x208); return;                                   /* SocketMix */
    case 0x18: if (in->has_ac) CALL0(out, MU_TALK_MIXSEL_18, 0x0ac); return;
    case 0x19:
        CALL1(out, MU_TALK_CALL_19, MU_TALK_SELF_NONE, MU_TALK_SELF_LOCAL);
        CALL0(out, MU_TALK_LOCAL_DTOR, MU_TALK_SELF_LOCAL);
        return;
    case 0x20: OPEN(out, 0x270); return;                                   /* ExchangeLuckCoin */
    case 0x21: CALL0(out, MU_TALK_DUELWATCH, 0x0e0); return;
    case 0x22:                                                             /* NpcShop with the flag object */
        CALL0(out, MU_TALK_SHOP_FLAG_OBJ, MU_TALK_SELF_NONE);
        emit(out, MU_TALK_WRITE, MU_TALK_SELF_NONE, 2, MU_TALK_SELF_SHOP_FLAG, 1, 0, 0, 0);
        OPEN(out, 0x0f4);
        return;
    case 0x23: entrance(in, out); return;
    case 0x24: return;
    case 0x25: CALL0(out, MU_TALK_EC_25, 0x0ec); return;
    /* 0x26/0x27 call MixSel without the null test of 0x18: this = the slot's value */
    case 0x26: CALL0(out, MU_TALK_MIXSEL_26, in->has_ac ? 0x0ac : 0); return;
    case 0x27: CALL0(out, MU_TALK_MIXSEL_27, in->has_ac ? 0x0ac : 0); return;
    case 0x28: dialogue(out, 0x248); return;
    case 0x29: OPEN(out, 0x204); return;                                   /* ElementalMix */
    case 0x30: CALL0(out, MU_TALK_TOGGLE, 0x164); return;                  /* PersonalShop */
    case 0x31: mix(out, 0xd); return;
    case 0x33: CALL0(out, MU_TALK_TOGGLE, 0x1ac); return;                  /* MuunExchange */
    case 0x34: CALL0(out, MU_TALK_TOGGLE, 0x1d4); return;                  /* OrdealSquareBattleEnter */
    case 0x35: OPEN(out, 0x1fc); return;                                   /* RuudShopFrame */
    case 0x36: dialogue(out, 0x2fc); return;
    case 0x37: dialogue(out, 0x2fd); return;
    case 0x38: return;
    case 0x39: dialogue(out, 0x3ab); return;
    case 0x40: dialogue(out, 0x3ac); return;
    case 0xff: return;
    default: shop_default(in, out); return;                                /* 0, 1, 0x0a, 0x0b, 0x0e..0x10, ... */
    }
}

void mu_npc_talk_result(const mu_talk_input *in, mu_talk_output *out)
{
    memset(out, 0, sizeof *out);
    if (!in->encrypted) {
        /* An answer that did not arrive encrypted is reported back: packet
         * 0x4d {2, 0, 0xb2}, return 0 (0x0128067f..0x01280734). */
        emit(out, MU_TALK_PACKET_BEGIN, MU_TALK_SELF_PACKET, 2, 0xc1, 0x4d, 0, 0, 0);
        emit(out, MU_TALK_PACKET_ADD, MU_TALK_SELF_PACKET, 3, 2, 1, 1, 0, 0);
        emit(out, MU_TALK_PACKET_ADD, MU_TALK_SELF_PACKET, 3, 0, 1, 1, 0, 0);
        emit(out, MU_TALK_PACKET_ADD, MU_TALK_SELF_PACKET, 3, 0xb2, 1, 1, 0, 0);
        emit(out, MU_TALK_PACKET_SEND, MU_TALK_SELF_PACKET, 2, 1, 0, 0, 0, 0);
        out->returned = 0;
        return;
    }
    /* Unless EventMapEntranceUI is up, every GFx window and every legacy
     * NewUI window closes first. */
    CALL0(out, MU_TALK_IS_VISIBLE, 0x2ac);
    if (!in->entrance_visible) {
        CALL0(out, MU_TALK_CLOSE_ALL, MU_TALK_SELF_MANAGER);
        CALL0(out, MU_TALK_NEWUI_CLOSE, MU_TALK_SELF_NEWUI);
    }
    dispatch(in, out, byte_at(in, 3));
    /* Common tail: SND_Play(25 iButtonClick), SND_Play(28 iCreateWindow),
     * then the cursor is moved unless [0x01cf0fc0] is set. */
    emit(out, MU_TALK_SND_PLAY, MU_TALK_SELF_NONE, 3, 0x19, 0, 0, 0, 0);
#ifdef MU_MUT_TALK_SOUND
    emit(out, MU_TALK_SND_PLAY, MU_TALK_SELF_NONE, 3, 0x1d, 0, 0, 0, 0);   /* planted mistake */
#else
    emit(out, MU_TALK_SND_PLAY, MU_TALK_SELF_NONE, 3, 0x1c, 0, 0, 0, 0);
#endif
    if (!in->cursor_lock) {
        int32_t t = (int32_t)((uint32_t)in->mouse_x * 0x104u) / 0x280;              /* imul; cdq; idiv */
        uint32_t y = ((uint32_t)in->mouse_y * (uint32_t)in->screen_h) / 0x1e0u;     /* imul; div */
        uint32_t x = ((uint32_t)t * (uint32_t)in->screen_w) / 0x280u;
        emit(out, MU_TALK_SET_CURSOR, MU_TALK_SELF_NONE, 2, x, y, 0, 0, 0);
    }
    out->returned = 1;
}

void mu_npc_talk_window(uint8_t result, mu_talk_window *w)
{
    memset(w, 0, sizeof *w);
    w->movie = "";
    w->arg = -1;
    w->dialogue = -1;
    w->mix_type = -1;
    mu_talk_input in;
    memset(&in, 0, sizeof in);
    uint8_t packet[16] = {0};
    packet[3] = result;
    in.packet = packet;
    in.length = sizeof packet;
    in.encrypted = 1;
    in.entrance_visible = 1;
    in.has_b0 = in.has_b4 = in.has_ac = 1;
    in.cursor_lock = 1;
    mu_talk_output out;
    mu_npc_talk_result(&in, &out);
    for (int i = 1; i < out.count; i++) {   /* events[0] is the visibility test */
        const mu_talk_event *e = &out.events[i];
        if (e->callee == MU_TALK_SND_PLAY)
            break;
        if (e->callee == MU_TALK_WRITE && e->args[0] == MU_TALK_MIX_TYPE)
            w->mix_type = (int32_t)e->args[1];
        else if (e->callee == MU_TALK_VTABLE(0x40) && w->kind != MU_TALK_KIND_DIALOGUE) {
            w->kind = e->self == 0x2ac ? MU_TALK_KIND_ENTRANCE : MU_TALK_KIND_OPEN;
            w->slot = (uint16_t)e->self;
        } else if (e->callee == MU_TALK_TOGGLE) {
            w->kind = MU_TALK_KIND_SHOW;
            w->slot = (uint16_t)e->self;
            w->method = e->callee;
        } else if (e->callee == MU_TALK_DIALOGUE_NPC) {
            w->kind = MU_TALK_KIND_DIALOGUE;
            w->dialogue = (int32_t)e->args[0];
            w->slot = 0x0f0;
        } else if (e->callee == MU_TALK_NEWUI_OPEN) {
            w->kind = MU_TALK_KIND_NEWUI;
            w->arg = (int32_t)e->args[0];
        } else if (e->callee == MU_TALK_ENTRANCE_MODE) {
            w->kind = MU_TALK_KIND_ENTRANCE;
            w->slot = 0x2ac;
            w->arg = (int32_t)e->args[0];
        } else if (e->callee == MU_TALK_PACKET_BEGIN) {
            w->kind = MU_TALK_KIND_PACKET;
        } else if (e->callee == MU_TALK_OBJ_6FC9EB0 || e->callee == MU_TALK_CALL_19) {
            w->kind = MU_TALK_KIND_OTHER;
        } else if (e->self && e->self < 0x1000 && w->kind == MU_TALK_KIND_NONE && e->callee != MU_TALK_SHOP_TABS &&
                   e->callee != MU_TALK_SCALP_FLAG && e->callee != MU_TALK_CLOSE_ALL) {
            w->kind = MU_TALK_KIND_METHOD;
            w->slot = (uint16_t)e->self;
            w->method = e->callee;
        }
    }
    if (w->slot)
        w->movie = mu_npc_slot_movie(w->slot);
    w->shop = w->slot == 0x0f4;
}

int mu_npc_repair_shop(int32_t npc_class)
{
    switch (npc_class) {
    case 243: case 246: case 251: case 416: case 578: case 686: case 687:
        return 1;
    default:
        return 0;
    }
}

int32_t mu_npc_talk_refusal(const mu_talk_gate *g)
{
    if (g->divide_visible)
        return 0x148c;
    if (g->npc_class == 238 && g->hero_level < 10)
        return 0x297;
    if (g->npc_class != 0 && g->mumix_visible)
        return 0xfd8;
    return -1;
}
