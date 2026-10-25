/* domains/quests.c (sketch) */
#include "../session_internal.h"

static void quests_refresh(mu_session *s)
{
    /* TODO: client.money = s->hero.money; hero_level/hero_level_total/hero_class from the hero records;
     * world/hero_x/hero_y from place + mu_session_hero_motion; time = world time.
     * Outputs: client.log.sink (quest.h:234-237, already in the reconstructed module) receives each line as it is
     * logged: "invoke W M ARGS" / "show W" / "hide W" -> MU_CUE_WINDOW; "notice ..." / "msgbox ..." -> MU_CUE_NOTICE;
     * "send c1 SS BODY | a b" (mu_quest_send, quest_ui.c:963-971) -> mu_packet with BODY, wrapped per (a, b) as the
     * client's Send(a, b) does, mu_session_send. host.path_reset/path_start -> port; host.send_move -> map_walk. */
    (void)s;
    MU_NOT_IMPLEMENTED();
}

mu_apply quests_receive(mu_session *s, const mu_frame *f)
{
    quests_refresh(s);
    /* TODO(SESSION-QUEST-001): F6 0x70/0x71 extra payload XOR (0x00d50954/0x00d509b6/0x00d50b0b) keyed with
     * 3 bytes at 0x06fca280 (third section, never captured): apply it here once the value or its writer is
     * recovered; until then these two subs are journaled as "undecoded" and skipped, not guessed */
    int handled = mu_quest_receive(&s->quests.client, f->bytes, f->length);   /* verified, unchanged */
    if (!handled)
        return MU_APPLY_IGNORED;
    mu_session_touch(s, MU_DOMAIN_QUESTS);
    return MU_APPLY_DONE;
}
