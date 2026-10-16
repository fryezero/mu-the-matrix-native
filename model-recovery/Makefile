CC = clang
CXX = clang++
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra -Werror -Wconversion
CRYPTOPP_PREFIX ?= $(shell if command -v brew >/dev/null 2>&1; then brew --prefix cryptopp; else echo /usr; fi)

UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
LIBRARY = liblea256.dylib
MODULUS_LIBRARY = libmodulus.dylib
SHARED = -dynamiclib
else
LIBRARY = liblea256.so
MODULUS_LIBRARY = libmodulus.so
SHARED = -shared -fPIC
endif

all: $(LIBRARY) $(MODULUS_LIBRARY)

$(LIBRARY): lea256.c
	$(CC) $(CFLAGS) $(SHARED) $< -o $@

$(MODULUS_LIBRARY): modulus.cpp
	$(CXX) $(CXXFLAGS) $(SHARED) -isystem $(CRYPTOPP_PREFIX)/include $< -L$(CRYPTOPP_PREFIX)/lib -lcryptopp -o $@

clean:
	rm -f liblea256.dylib liblea256.so libmodulus.dylib libmodulus.so

.PHONY: all clean
