#ifndef MU_CLIENT_COPY64_H
#define MU_CLIENT_COPY64_H

/* Both spans must contain 64 accessible bytes. Overlap is permitted.
 * Copies in increasing address order, reading four bytes before each write.
 * Models the observed x86 routine only with the direction flag clear. */
void *mu_copy64_forward_words(void *destination, const void *source);

#endif
