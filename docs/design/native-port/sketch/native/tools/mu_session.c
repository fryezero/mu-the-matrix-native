/* native/tools/mu_session.c (sketch): the session's CLI, for validators and humans.
 *
 *   mu-session routes                         the dispatcher rows as TSV (validate_dispatch.py)
 *   mu-session replay JOURNAL [--at T,...]    feed a recorded inbound stream into a fresh session over
 *                                             mu_transport_replay; dump every domain in client layout at
 *                                             the given ticks (session_compare.py); report divergence of
 *                                             outbound bytes (strict or observe)
 *   mu-session fixture SCENARIO [--seconds N] a headless session against an in-process fixture (no world):
 *                                             login, list, join; prints the journal summary
 *   mu-session decode HEXFRAME --key ...      one frame through mu_decode (debugging the CryptoModule)
 *
 * No subcommand connects to a non-loopback endpoint; live runs go through mu-client only.
 */
int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    MU_NOT_IMPLEMENTED();
}
