/* domains/account.c (sketch) */
#include "../session_internal.h"

mu_apply account_server_connect(mu_session *s, const mu_frame *f)
{
    /* TODO (F4 03, 0x0127ea69): 15-byte address at bytes[4], port at bytes[0x14] -> game_server;
     *   mu_link_allow (the transport allowlist learns it), mu_net_close(CONNECT), mu_net_connect(GAME),
     *   phase HOPPING. Idempotent: a second F4 03 while HOPPING to the same endpoint does nothing. */
    (void)s; (void)f;
    MU_NOT_IMPLEMENTED();
}

mu_submit account_login(mu_session *s, const mu_intent *in)
{
    /* TODO(NET-ACCOUNT-001)
     *   phase != ACCOUNT -> NOT_NOW
     *   until the login builder is reconstructed: return mu_session_unrecovered(s, in, "login body")
     *   then: for each field of the reconstructed body, by provenance:
     *       user        account, password (mu_secret, consumed and wiped here)
     *       build       s->cfg.build->version / serial (from the restored text)
     *       launcher    s->cfg.proof->fetch(field_tag): NOT_REQUIRED -> field as the client leaves it
     *                   without a launcher session; UNAVAILABLE -> close MU_CLOSE_NEEDS_OPERATOR_CONTRACT
     *   the C3 wrap, mu_session_send; phase LOGGING_IN
     *   the journal records "login sent", never the frame bytes */
    (void)s; (void)in;
    MU_NOT_IMPLEMENTED();
}

mu_submit account_join(mu_session *s, const mu_intent *in)
{
    /* TODO: phase CHARACTERS only (a second JOIN while JOINING is NOT_NOW: idempotent Enter);
     * the join request with the character's name (scene.c:260 records its send); phase JOINING */
    (void)s; (void)in;
    MU_NOT_IMPLEMENTED();
}

mu_submit account_keepalive(mu_session *s, const mu_intent *in)
{
    /* The dispatcher tail's packet (scene.c:125, SendCounter > 31). Body not reconstructed:
     * UNRECOVERED until NET-ACCOUNT-001. If its content turns out to come from IGC.dll (an integrity
     * heartbeat), it is a protection-boundary item: the operator contract must say what a native
     * client sends instead. */
    return mu_session_unrecovered(s, in, "dispatcher tail packet");
}
