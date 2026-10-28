#include "../../../reconstructed/social/social_packets.h"
#include "../session_internal.h"
#ifdef MU_SESSION_SEED
/* Dev loopback identity check only; no fixture state in the product. */
extern int mu_fixture_is_transport(const mu_transport *);
#endif
#include <string.h>
mu_party_view mu_session_party(const mu_session *s)
{
    mu_party_view v = {&s->party.members, s->party.pending, s->party.request_key, s->party.invitations};
    return v;
}
static void notice(mu_session *s, uint32_t handler, int text)
{
    if (!text)
        return;
    mu_cue c = {0};
    c.kind = MU_CUE_NOTICE;
    c.handler = handler;
    c.u.notice.global_text = text;
    mu_session_cue(s, &c);
}
mu_apply party_request(mu_session *s, const mu_frame *f)
{
    if (f->head != 0xc1 || f->length != 5 || s->party.pending)
        return MU_APPLY_IGNORED;
    /* One native pending invitation retains one identity until answered. This
     * guard is UI policy; the original key parser is unchanged. */
    mu_social_party_request(f->bytes, f->length, 0, &s->party.request_key);
    s->party.pending = 1;
    ++s->party.invitations;
    mu_session_touch(s, MU_DOMAIN_PARTY);
    return MU_APPLY_DONE;
}
mu_apply party_result(mu_session *s, const mu_frame *f)
{
    if (f->head != 0xc1 || f->length != 4)
        return MU_APPLY_IGNORED;
    notice(s, 0x0127373e, mu_social_party_notice(f->bytes[3]));
    return MU_APPLY_DONE;
}
mu_apply party_list(mu_session *s, const mu_frame *f)
{
    if (f->head != 0xc2 || f->length < 5 || f->bytes[4] > MU_SOCIAL_PARTY ||
        f->length != 5 + (size_t)f->bytes[4] * 44)
        return MU_APPLY_IGNORED;
    mu_social_party_receive(&s->party.members, f->bytes, f->length);
    mu_session_touch(s, MU_DOMAIN_PARTY);
    return MU_APPLY_DONE;
}
mu_apply party_clear(mu_session *s, const mu_frame *f)
{
    if (f->head != 0xc1 || f->length != 5)
        return MU_APPLY_IGNORED;
    mu_social_party_receive(&s->party.members, f->bytes, f->length);
    notice(s, 0x0127178c, f->bytes[4] == 0 ? 0x1f6 : 0);
    mu_session_touch(s, MU_DOMAIN_PARTY);
    return MU_APPLY_DONE;
}
mu_apply party_update(mu_session *s, const mu_frame *f)
{
    if (f->head != 0xc1 || f->length < 4 || f->length != 4 + (size_t)f->bytes[3] * 13)
        return MU_APPLY_IGNORED;
    mu_social_party_receive(&s->party.members, f->bytes, f->length);
    mu_session_touch(s, MU_DOMAIN_PARTY);
    return MU_APPLY_DONE;
}
static mu_submit send(mu_session *s, const mu_social_packet *p)
{
    /* Send(1,0) remains journaled unsent. Only Send(0,0) can reach the
     * dev loopback's explicit plaintext lane, as in the combat domain. */
    mu_submit r = {MU_SUBMIT_NOT_NOW, -1};
    mu_packet packet;
    mu_packet_begin(&packet, p->data[0], p->data[2]);
    mu_packet_add(&packet, p->data + 3, (size_t)p->size - 3, 0);
#ifdef MU_SESSION_SEED
    if (!p->send0 && mu_fixture_is_transport(s->cfg.transport) &&
        mu_endpoint_is_loopback(&s->cfg.connect_server))
    {
        r.status = mu_session_send(s, &packet, 0) == MU_SEND_OK ? MU_SUBMIT_SENT : MU_SUBMIT_NOT_NOW;
        return r;
    }
#endif
    mu_packet_finish(&packet);
    mu_journal_frame_out(s->cfg.journal, s->tick, s->now, s->conn_main, packet.obj + 2, (uint32_t)p->size,
                         MU_SEND_NEEDS_CRYPTO, p->send0);
    ++s->unsent;
    return r;
}
mu_submit party_invite(mu_session *s, const mu_intent *in)
{
    mu_submit r = {MU_SUBMIT_REFUSED, -1};
    if (in->u.party_invite.key < 0 || in->u.party_invite.key > 65535)
        return r;
    mu_social_packet p;
    mu_social_party_invite(&p, (uint16_t)in->u.party_invite.key, 1, 1);
    return send(s, &p);
}
mu_submit party_answer(mu_session *s, const mu_intent *in)
{
    mu_submit r = {MU_SUBMIT_REFUSED, -1};
    if (!s->party.pending || (in->u.party_answer.accept != 0 && in->u.party_answer.accept != 1))
        return r;
    mu_social_packet p;
    mu_social_party_answer(&p, (uint16_t)s->party.request_key, (uint8_t)in->u.party_answer.accept);
    r = send(s, &p);
    s->party.pending = 0;
    mu_session_touch(s, MU_DOMAIN_PARTY);
    return r;
}
mu_submit party_leave(mu_session *s, const mu_intent *in)
{
    mu_submit r = {MU_SUBMIT_REFUSED, -1};
    int i = in->u.party_leave.member;
    if (i < 0 || i >= s->party.members.count)
        return r;
    const mu_party_member *m = &s->party.members.members[i];
    mu_social_packet p;
    if (!mu_social_party_remove(&p, (uint8_t)m->number, m->name, 1, !*m->name))
        return r;
    return send(s, &p);
}
void mu_dom_party_init(mu_session *s) { memset(&s->party, 0, sizeof s->party); }
void mu_dom_party_free(mu_session *s) { (void)s; }
void mu_dom_party_step(mu_session *s, const mu_sim *sim)
{
    (void)s;
    (void)sim;
}
void mu_dom_party_zones(const mu_session *s, mu_audit_zones *z)
{
    mu_audit_add(z, "party", (const uint8_t *)&s->party, 0, sizeof s->party, MU_ZONE_REPLICATED,
                 "display records and pending identity");
}
#ifdef MU_SESSION_SEED
void mu_dom_party_seed(mu_session *s, const struct mu_session_seed *seed)
{
    (void)s;
    (void)seed;
}
#endif
