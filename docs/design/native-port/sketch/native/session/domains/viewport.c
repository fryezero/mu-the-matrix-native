/* domains/viewport.c (sketch) */
#include "../session_internal.h"

mu_apply viewport_players(mu_session *s, const mu_frame *f)
{
    /* TODO
     *   count = f->bytes[4] (layout from the 0x12 handler); p = first record
     *   for each record:
     *       mu_rp_viewport v; size = mu_rp_viewport_record(p, avail, &v)   // static reading, parse only
     *       i = find key or allocate the client's way; ++generation[i] on allocate
     *       mu_rp_character_create(&chars[i], v.key, model, v.x, v.y, angle) when created
     *       mu_session_rp_env(s, &env)          // world-port-backed PathFinding2, SetAction ...
     *       mu_rp_viewport_apply(&v, &chars[i], &env, &calls)
     *       mu_rp_change_equipment(&chars[i], v.equipment, 0, &env, &calls)
     *       calls -> cues (helper models, effect 0x24e6 ...) in order
     *   touch VIEWPORT
     */
    (void)s; (void)f;
    MU_NOT_IMPLEMENTED();
}

mu_apply viewport_move(mu_session *s, const mu_frame *f)
{
    /* TODO
     *   i = key at +3/+4 (big endian) -> index; unknown or dead: MU_APPLY_IGNORED (the handler's rule)
     *   env.is_hero / hero_key_match / hero_moving from the hero index and the world port's hero motion
     *   mu_rp_move_packet(f->bytes, &chars[i], &env, &calls)   // verified; sets the path through PathFinding2
     *   the hero branch only records its calls (handler rule): turn them into cues, do not move mu_walk
     *   no revision bump: motion is read every frame; the path is consumed by the next lease
     */
    (void)s; (void)f;
    MU_NOT_IMPLEMENTED();
}

/* Projection adapters. reconstructed/progress addresses characters as 0x400-byte client records,
 * reconstructed/players as mu_rp_character. When a progress handler looks a character up by key
 * (env->character), this projects the mu_rp_character into a scratch record at the client offsets
 * of the fields the verified family reads (+0x23 dead, +0x38 movement, ...), runs the handler, and
 * writes back the fields it writes. The field list is NOT written here: it is generated from the
 * layout manifest (native/session/layout/*.def, merged per record -> build/gen/layout_character.h), the same
 * source that drives the lease audit, the journal's record dump, layout.json for memread and the
 * validators. All of them agree by construction. test_viewport_projection.py round-trips every
 * field the manifest binds to a mu_rp_character member and fails on any unbound byte range the
 * verified families touch. */
#include "layout_character.h"   /* generated: MU_CHARACTER_FIELDS[], mu_char_field */
