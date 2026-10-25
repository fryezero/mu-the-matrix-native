/* NET-LINK-001: the replay transport - a clean stub.
 *
 * mu_transport_replay will feed a recorded journal's inbound link bytes at their recorded ticks and
 * compare the session's outbound bytes with the recording (strict or observe). It needs the
 * journal reader (native/session/mu_journal.h) to carry each FRAME record's connection and link
 * bytes, and a recording to replay (CAPTURE-KIT-001). Until then it refuses with an explanation
 * instead of aborting, so tools can report the gap. */
#include "mu_link.h"

#include <stdio.h>
#include <string.h>

mu_transport *mu_transport_replay(const char *journal_path, mu_replay_mode mode, char *error, size_t error_size)
{
    (void)mode;
    snprintf(error, error_size, "replay transport not implemented (NET-LINK-001 stub): cannot replay %s",
             journal_path ? journal_path : "(null)");
    return NULL;
}

void mu_transport_replay_report(const mu_transport *t, mu_replay_report *out)
{
    (void)t;
    memset(out, 0, sizeof *out);
}
