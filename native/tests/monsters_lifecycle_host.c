/* Synthetic loopback-frame/cache lifecycle check, no original client. */
#define MU_WORLD_NO_GL
#define MU_SESSION_SEED
#include "../world/world_rt_internal.h"
#include "../session/mu_session.h"
#include "../session/mu_session_seed.h"
#include "../fixture/mu_fixture.h"
#include <stdio.h>
void world_rt_actors_sync(mu_world_rt *a);
int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    mu_world_rt_options o; mu_world_rt_default_options(&o);
    o.root = argv[1]; o.placement = argv[2]; o.audio = 0; o.tile[0] = 120; o.tile[1] = 120;
    char error[1024]; mu_world_rt *a = mu_world_rt_open(&o, error, sizeof error);
    if (!a) { fprintf(stderr, "%s\n", error); return 2; }
    if (a->actors.count != 3 || a->actors.effect_instances != 1) return 3;
    /* Replace the actor-side test feed with a separately scheduled loopback.
     * characters_close retains its original session; actors_close owns this one. */
    mu_fixture_options options = {argv[3], NULL, 1};
    mu_fixture *fixture = mu_fixture_open(&options, error, sizeof error);
    if (!fixture) return 4;
    mu_transport *transport = mu_fixture_transport(fixture);
    mu_session_config cfg = {0}; cfg.transport = transport;
    mu_fixture_endpoint(fixture, "game", &cfg.connect_server);
    cfg.build = &MU_PINNED_BUILD; cfg.proof = mu_proof_not_required();
    mu_session_seed seed = {0};
    mu_session *session = mu_session_open_seeded(&cfg, &seed, error, sizeof error);
    if (!session) return 4;
    a->actors.session = session; a->actors.fixture = fixture; a->actors.transport = transport;
    for (unsigned tick = 1; tick <= 3; ++tick) {
        mu_transport_poll(transport, tick * 40); mu_session_pump(session, tick * 40);
        world_rt_actors_sync(a);
        if (tick == 2 && (a->actors.count != 2 || a->actors.effect_instances != 0)) return 5;
    }
    if (a->actors.count != 3 || a->actors.list[2].server_class != 251 || a->actors.effect_instances != 0) return 6;
    mu_world_rt_close(a);
    puts("{\"lifecycle\":3,\"destroyed_effects\":1,\"reused_identity\":1}"); return 0;
}
