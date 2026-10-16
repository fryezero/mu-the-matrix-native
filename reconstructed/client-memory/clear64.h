#ifndef MU_CLIENT_CLEAR64_H
#define MU_CLIENT_CLEAR64_H

/* The destination must contain 64 writable bytes. Returns the destination.
 * Models the observed wrapper's scalar/SSE helper paths for valid flat memory. */
void *mu_clear64(void *destination);

#endif
