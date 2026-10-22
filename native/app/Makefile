# Mu The Matrix Native Preview.app (NATIVE-APP-001): the native client (mu-client) as a double-clickable,
# ad-hoc signed macOS app with a small launcher. Builds with the Command Line Tools (swiftc, clang, iconutil,
# plutil, codesign, install_name_tool). The app carries no game data; the built app stays local (native/build
# is ignored).
#
#   make -C native preview-app              build native/build/app/Mu The Matrix Native Preview.app
#   make -C native/app install              ... copy it to $(INSTALL_DIR) (default ~/Applications), replacing it,
#                                           and run its first-run data setup (--setup) for this account
#   make -C native/app MUGFX_LIB=/path/libmugfx.dylib   bundle the Ruffle-based GFx library from another build
#
# MUGFX_LIB defaults to native/gfx/mugfx/target/release/libmugfx.dylib (native/gfx/build-mugfx.sh); without it
# the app runs with the GFx stand-ins. SDL3_LIB is sdl2-compat's run-time SDL3 (Homebrew's by default).
SWIFTC ?= xcrun swiftc
CC := clang
ARCH ?= $(shell uname -m)
MIN_MACOS ?= 13.0
VERSION ?= 0.1
BUILD_NUMBER ?= 1
BUNDLE_ID ?= io.github.fryezero.mu-the-matrix.native-preview
INSTALL_DIR ?= $(HOME)/Applications
MUGFX_LIB ?= $(wildcard ../gfx/mugfx/target/release/libmugfx.dylib)
SDL3_LIB ?= $(shell if command -v brew >/dev/null 2>&1; then echo "$$(brew --prefix sdl3 2>/dev/null)/lib/libSDL3.0.dylib"; fi)
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)

B ?= ../build/app
NAME := Mu The Matrix Native Preview
APP := $(B)/$(NAME).app
APPQ := "$(APP)"
SOURCES := Sources/PreviewCore.swift Sources/main.swift
ICON_SRC := ../../mac-play/bundle/icon/make-icon.swift
CLIENT := ../build/mu-client
MODULUS := ../../model-recovery/libmodulus.dylib
STAMP := $(B)/.app-stamp
VARS := $(SWIFTC)|$(ARCH)|$(MIN_MACOS)|$(VERSION)|$(BUILD_NUMBER)|$(BUNDLE_ID)|$(MUGFX_LIB)|$(SDL3_LIB)|$(COMMIT)

all: $(STAMP)

# Rebuild when a build variable changes (make does not track them itself).
$(shell mkdir -p '$(B)' && { printf '%s\n' '$(VARS)' | cmp -s - '$(B)/.vars' || { printf '%s\n' '$(VARS)' > '$(B)/.vars'; rm -f '$(B)/Info.plist' '$(STAMP)'; }; })

$(CLIENT):
	$(MAKE) -C .. client

$(MODULUS): ../../model-recovery/modulus.cpp
	$(MAKE) -C ../../model-recovery libmodulus.dylib

$(B)/MuNativePreview: $(SOURCES)
	@mkdir -p $(B)
	$(SWIFTC) -O -swift-version 5 -target $(ARCH)-apple-macos$(MIN_MACOS) -framework AppKit -o $@ $(SOURCES)

$(B)/libmu-nonet.dylib: nonet/mu_nonet.c
	@mkdir -p $(B)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -arch $(ARCH) -mmacosx-version-min=$(MIN_MACOS) -dynamiclib \
	  -install_name @rpath/libmu-nonet.dylib $< -o $@

$(B)/make-icon: $(ICON_SRC)
	@mkdir -p $(B)
	$(SWIFTC) -O -o $@ $<

$(B)/AppIcon.icns: $(B)/make-icon
	rm -rf $(B)/AppIcon.iconset
	$(B)/make-icon $(B)/AppIcon.iconset >/dev/null
	iconutil -c icns -o $@ $(B)/AppIcon.iconset

$(B)/Info.plist: Info.plist.in Makefile
	@mkdir -p $(B)
	sed -e 's|@BUNDLE_ID@|$(BUNDLE_ID)|' -e 's|@VERSION@|$(VERSION)|' -e 's|@BUILD@|$(BUILD_NUMBER)|' \
	    -e 's|@MIN_MACOS@|$(MIN_MACOS)|' -e 's|@COMMIT@|$(COMMIT)|' -e 's|@GFX@|$(if $(MUGFX_LIB),true,false)|' $< > $@
	plutil -lint $@

$(STAMP): $(CLIENT) $(MODULUS) $(B)/MuNativePreview $(B)/libmu-nonet.dylib $(B)/AppIcon.icns $(B)/Info.plist bundle-dylibs.sh \
          ../client/demo-session.txt ../client/demo-servers.txt ../client/demo-characters.txt \
          ../world/lorencia-demo-placement.txt ../world/lorencia-demo-npc.txt ../world/lorencia-demo-players.txt \
          ../gfx/gfxconvert.py ../gfx/gfxswf.py $(MUGFX_LIB)
	rm -rf $(APPQ)
	mkdir -p $(APPQ)/Contents/MacOS $(APPQ)/Contents/Frameworks $(APPQ)/Contents/Resources/session \
	  $(APPQ)/Contents/Resources/world $(APPQ)/Contents/Resources/converter/native/gfx \
	  $(APPQ)/Contents/Resources/converter/model-recovery
	cp $(B)/Info.plist $(APPQ)/Contents/Info.plist
	printf 'APPL????' > $(APPQ)/Contents/PkgInfo
	cp $(B)/MuNativePreview $(CLIENT) $(APPQ)/Contents/MacOS/
	cp $(B)/libmu-nonet.dylib $(APPQ)/Contents/Frameworks/
	@if [ -n "$(MUGFX_LIB)" ]; then cp "$(MUGFX_LIB)" $(APPQ)/Contents/Frameworks/libmugfx.dylib && echo "bundled libmugfx ($(MUGFX_LIB))"; \
	  else echo "NOTE: no libmugfx (native/gfx/build-mugfx.sh or MUGFX_LIB=...): the app uses the GFx stand-ins"; fi
	cp $(B)/AppIcon.icns $(APPQ)/Contents/Resources/
	cp ../client/demo-session.txt ../client/demo-servers.txt ../client/demo-characters.txt $(APPQ)/Contents/Resources/session/
	cp ../world/lorencia-demo-placement.txt ../world/lorencia-demo-npc.txt ../world/lorencia-demo-players.txt \
	  $(APPQ)/Contents/Resources/world/
	cp ../gfx/gfxconvert.py ../gfx/gfxswf.py $(APPQ)/Contents/Resources/converter/native/gfx/
	cp $(MODULUS) $(APPQ)/Contents/Resources/converter/model-recovery/
	./bundle-dylibs.sh $(APPQ) "$(SDL3_LIB)"
	# inner code first, then the app (ad-hoc, no hardened runtime: the launcher loads the network guard
	# into mu-client with DYLD_INSERT_LIBRARIES)
	for f in $(APPQ)/Contents/Frameworks/*.dylib $(APPQ)/Contents/Resources/converter/model-recovery/*.dylib \
	         $(APPQ)/Contents/MacOS/mu-client; do codesign --force --sign - --timestamp=none "$$f" || exit 1; done
	codesign --force --sign - --timestamp=none $(APPQ)
	codesign --verify --strict --deep --verbose=1 $(APPQ)
	$(APPQ)/Contents/MacOS/MuNativePreview --check-bundle
	@touch $@
	@echo "built $(APP)"

install: all
	mkdir -p "$(INSTALL_DIR)"
	rm -rf "$(INSTALL_DIR)/$(NAME).app"
	ditto $(APPQ) "$(INSTALL_DIR)/$(NAME).app"
	@echo "installed $(INSTALL_DIR)/$(NAME).app"
	# Prepare the owner's Native Data now (from this shell, which may read ~/Documents), so that the app's
	# first run does not have to ask macOS for access to the Documents folder. Keeps what is already there.
	"$(INSTALL_DIR)/$(NAME).app/Contents/MacOS/MuNativePreview" --setup

clean:
	rm -rf $(B)

.PHONY: all install clean
