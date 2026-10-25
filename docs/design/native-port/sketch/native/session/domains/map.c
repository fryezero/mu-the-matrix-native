/* domains/map.c (sketch) */
#include "../session_internal.h"

mu_apply map_teleport(mu_session *s, const mu_frame *f)
{
    /* TODO
     *   mu_teleport t; if (!mu_teleport_parse(f->bytes, f->length, &t)) return MU_APPLY_IGNORED;
     *   (f->encrypted is 1: the frame came through Decrypt - the demo's plaintext C3 is gone)
     *   changes = mu_teleport_changes_world(&t, s->map.world)
     *   s->map = {t.number ? t.world : s->map.world, {t.x, t.y}, mu_teleport_angle(&t), ++seq}
     *   cue MU_CUE_NOTICE map name + GlobalText[484]  (MU_TELEPORT_TEXT_MOVED)
     *   touch MAP
     *   if changes: return MU_APPLY_WORLD_CHANGE        // world runtime travels, then attach_world
     *   s->port.place_hero(&place); return MU_APPLY_DONE  // same-map: the world moves its hero now
     */
    (void)s; (void)f;
    MU_NOT_IMPLEMENTED();
}

mu_submit map_walk(mu_session *s, const mu_intent *in)
{
    /* SendMove 0x016b5cd0. Today mu_path.c:118-123 only counts calls and this build has no classic 0xd4.
     * UNRECOVERED until SESSION-COMBAT-001 reconstructs the body from the restored text. The world walks
     * locally regardless (client-side movement), so fixture runs stay playable while the server would
     * not yet see the hero move - the journal makes that gap visible in every run. */
    return mu_session_unrecovered(s, in, "SendMove body");
}

mu_place mu_session_place(const mu_session *s)
{
    mu_place p = {s->map.world, {s->map.tile[0], s->map.tile[1]}, s->map.angle, s->map.seq};
    return p;
}
