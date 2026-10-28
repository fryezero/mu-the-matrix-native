#include "../fixture/mu_fixture.h"
#include "../session/mu_session.h"
#include "../session/mu_session_seed.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void pump(mu_session *s, mu_transport *t, unsigned tick)
{
    mu_transport_poll(t, tick * 40);
    mu_session_pump(s, tick * 40);
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    char error[512];
    mu_fixture_options opt = {argv[1], NULL, 1};
    mu_fixture *f = mu_fixture_open(&opt, error, sizeof error);
    assert(f);
    mu_transport *t = mu_fixture_transport(f);
    mu_session_config cfg = {.transport = t};
    mu_fixture_endpoint(f, "game", &cfg.connect_server);
    mu_session_seed seed = {.level = 10};
    mu_session *s = mu_session_open_seeded(&cfg, &seed, error, sizeof error);
    assert(s);
    mu_hero_stats before, after;
    mu_session_hero(s, &before);
    mu_cue_cursor a = mu_session_cue_cursor(s), b = a;
    uint32_t lost = 0;
    mu_cue ca[4], cb[4];
    pump(s, t, 1);
    assert(mu_session_party(s).members->count == 2);
    mu_party saved = *mu_session_party(s).members;
    mu_session_detach_world(s);
    pump(s, t, 2);
    assert(!memcmp(&saved, mu_session_party(s).members, sizeof saved));
    pump(s, t, 3);
    assert(!memcmp(&saved, mu_session_party(s).members, sizeof saved));
    pump(s, t, 4);
    assert(!memcmp(&saved, mu_session_party(s).members, sizeof saved));
    pump(s, t, 5);
    assert(mu_session_party(s).pending && mu_session_party(s).request_key == 0x1234);
    pump(s, t, 6);
    assert(mu_session_party(s).request_key == 0x1234 && mu_session_party(s).invitations == 1);
    pump(s, t, 7);
    assert(mu_session_party(s).members->members[0].hp_percent == 100);
    assert(mu_session_party(s).members->members[0].mp_percent == 61);
    pump(s, t, 8);
    assert(mu_session_cues(s, &a, ca, 4, &lost) == 1 && !lost);
    assert(mu_session_cues(s, &b, cb, 4, &lost) == 1 && !lost);
    assert(!memcmp(ca, cb, sizeof *ca) && ca[0].u.notice.global_text == 0x1263);
    assert(!mu_session_cues(s, &a, ca, 4, &lost));
    mu_intent in = {.kind = MU_INTENT_PARTY_ANSWER};
    in.u.party_answer.accept = 1;
    assert(mu_session_submit(s, &in).status == MU_SUBMIT_NOT_NOW);
    assert(!mu_session_party(s).pending && mu_session_party(s).request_key == 0x1234);
    assert(mu_session_submit(s, &in).status == MU_SUBMIT_REFUSED);
    pump(s, t, 9);
    assert(!mu_session_party(s).members->count && mu_session_party(s).request_key == 0x1234);
    mu_world_port port = {0};
    mu_session_attach_world(s, &port);
    assert(!mu_session_party(s).members->count && !mu_session_cues(s, &b, cb, 4, &lost));
    mu_session_hero(s, &after);
    assert(!memcmp(&before, &after, sizeof before));
    mu_session_status st;
    mu_session_status_get(s, &st);
    assert(!st.unhandled && !st.undecodable);
    mu_session_close(s);
    mu_transport_free(t);
    mu_fixture_close(f);
    puts("party atomicity, identity, cursors, detach/rebind, display-only passed");
    return 0;
}
