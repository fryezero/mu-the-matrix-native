#ifndef MU_NATIVE_DATA_MANIFEST_H
#define MU_NATIVE_DATA_MANIFEST_H

/* Check managed data paths in argv and the consumer environment before work.
 * Raw authored fixtures and explicit research inputs retain their existing APIs.
 * Failure prints a user-facing diagnostic and returns 0; callers must stop. */
#ifdef __cplusplus
extern "C" {
#endif
int mu_native_data_check_args(int argc, char **argv);
#ifdef __cplusplus
}
#endif
#endif
