#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int c, char **v) { int pid = atoi(v[1]); unsigned lo = strtoul(v[2], 0, 16), hi = strtoul(v[3], 0, 16); task_t t;
 if (task_for_pid(mach_task_self(), pid, &t)) return 1; FILE *f = fopen(v[4], "wb"); unsigned char buf[4096];
 for (unsigned a = lo; a < hi; a += 4096) { mach_vm_size_t g = 0; if (mach_vm_read_overwrite(t, a, 4096, (mach_vm_address_t)buf, &g)) memset(buf, 0, 4096); fwrite(buf, 1, 4096, f); }
 fclose(f); return 0; }
