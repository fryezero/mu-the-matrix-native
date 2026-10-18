CC = clang
CFLAGS := -O2 -arch x86_64 -Wall
all:
	mkdir -p build
	$(CC) $(CFLAGS) stackprof.c -o build/stackprof
	$(CC) $(CFLAGS) stallprof.c -o build/stallprof
	$(CC) $(CFLAGS) memdump.c -o build/memdump
	$(CC) $(CFLAGS) flav.c -o build/flav
# No signing, task attachment or profiling is performed by this target.
.PHONY: all
