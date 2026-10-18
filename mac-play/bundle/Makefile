# Mu The Matrix.app (MAC-BUNDLE-001, MAC-FREE-001): a double-clickable macOS installer and launcher.
# Default runtime: the free Wine runtime (no CrossOver); the installer is bundled in Resources/installer.
# Builds from source with the Command Line Tools (swiftc, iconutil, plutil, codesign); ad-hoc signed.
#
#   make                 build/Mu The Matrix.app (B=DIR for another build directory): a DEVELOPMENT build
#   make player-app EMBED_MUGL=... EMBED_MSCOREE=... EMBED_FAST_X87=...
#                        the build to hand to players: refuses to build unless all three are given and valid,
#                        then checks the result with the app's own --check-bundle
#   make test            static checks + dry-run tests (tests/test-bundle.sh)
#   make install         copy the app to $(INSTALL_DIR) (default ~/Applications)
#   make clean
#
# Build-time defaults (used until the settings window saves a settings file):
#   DEFAULT_RUNTIME=free|crossover  DEFAULT_BOTTLE=MuMatrixKit  DEFAULT_FAST_X87=0|1  DEFAULT_TIMEWALKER_DIR=/path/to/rosetta-timewalker
# DLLs bundled for players (Resources/dlls, passed to the installer as --mugl-dll / --mscoree-dll):
#   EMBED_MUGL=/path/opengl32.dll  EMBED_MSCOREE=/path/mscoree.dll   (none by default; never commit them.
#   A private mugl build contains client-derived bytes: distributing it is the server owner's decision.)
#   EMBED_FAST_X87=/dir  rosetta-timewalker translator from ../installer/packaging/package-fast-x87.sh (MIT); the
#   authored main.exe-only wrapper (../x87-main-only-wrapper.c) is compiled into Resources/fast-x87 with it.
SWIFTC ?= xcrun swiftc
ARCH ?= $(shell uname -m)
MIN_MACOS ?= 13.0
VERSION ?= 1.0
BUILD_NUMBER ?= 1
BUNDLE_ID ?= io.github.fryezero.mu-the-matrix.launcher
DEFAULT_RUNTIME ?= free
DEFAULT_BOTTLE ?= MuMatrixKit
DEFAULT_FAST_X87 ?= 0
DEFAULT_TIMEWALKER_DIR ?=
INSTALL_DIR ?= $(HOME)/Applications
EMBED_MUGL ?=
EMBED_MSCOREE ?=
EMBED_FAST_X87 ?=

B ?= build
APP := $(B)/Mu The Matrix.app
APPQ := "$(APP)"
SOURCES := Sources/Core.swift Sources/main.swift
RESOURCES := mu-launch.sh ../installer/lib/mukit.sh ../fast-x87.sh
INSTALLER_FILES := ../installer/setup-mu-mac.sh ../installer/verify-mu-mac.sh ../installer/play-mu.sh \
	../installer/lib/mukit.sh ../installer/registry/mu-mac.reg
STAMP := $(B)/.app-stamp
VARS := $(SWIFTC)|$(ARCH)|$(MIN_MACOS)|$(VERSION)|$(BUILD_NUMBER)|$(BUNDLE_ID)|$(DEFAULT_RUNTIME)|$(DEFAULT_BOTTLE)|$(DEFAULT_FAST_X87)|$(DEFAULT_TIMEWALKER_DIR)|$(EMBED_MUGL)|$(EMBED_MSCOREE)|$(EMBED_FAST_X87)

all: $(STAMP)

$(B)/make-icon: icon/make-icon.swift
	@mkdir -p $(B)
	$(SWIFTC) -O -o $@ $<

$(B)/AppIcon.icns: $(B)/make-icon
	rm -rf $(B)/AppIcon.iconset
	$(B)/make-icon $(B)/AppIcon.iconset
	iconutil -c icns -o $@ $(B)/AppIcon.iconset

# Rebuild when a build variable changes (make does not track them itself). Done at parse time, before make
# looks at any timestamp, so it also works with macOS make 3.81's one-second resolution.
$(shell mkdir -p '$(B)' && { printf '%s\n' '$(VARS)' | cmp -s - '$(B)/.vars' || { printf '%s\n' '$(VARS)' > '$(B)/.vars'; rm -f '$(B)/Info.plist' '$(B)/MuTheMatrix' '$(STAMP)'; }; })

$(B)/MuTheMatrix: $(SOURCES)
	@mkdir -p $(B)
	$(SWIFTC) -O -target $(ARCH)-apple-macos$(MIN_MACOS) -framework AppKit -o $@ $(SOURCES)

$(B)/Info.plist: Info.plist.in Makefile
	@mkdir -p $(B)
	@case "$(DEFAULT_FAST_X87)" in 0) fx=false ;; 1) fx=true ;; *) echo "DEFAULT_FAST_X87 must be 0 or 1" >&2; exit 1 ;; esac; \
	case "$(DEFAULT_RUNTIME)" in free|crossover) ;; *) echo "DEFAULT_RUNTIME must be free or crossover" >&2; exit 1 ;; esac; \
	echo '$(DEFAULT_BOTTLE)' | grep -Eq '^[A-Za-z0-9][A-Za-z0-9_-]*$$' || { echo "bad DEFAULT_BOTTLE" >&2; exit 1; }; \
	sed -e 's|@BUNDLE_ID@|$(BUNDLE_ID)|' -e 's|@VERSION@|$(VERSION)|' -e 's|@BUILD@|$(BUILD_NUMBER)|' \
	    -e 's|@MIN_MACOS@|$(MIN_MACOS)|' -e 's|@DEFAULT_BOTTLE@|$(DEFAULT_BOTTLE)|' -e "s|@DEFAULT_FAST_X87@|$$fx|" \
	    -e 's|@DEFAULT_TIMEWALKER_DIR@|$(DEFAULT_TIMEWALKER_DIR)|' -e 's|@DEFAULT_RUNTIME@|$(DEFAULT_RUNTIME)|' $< > $@
	plutil -lint $@

$(STAMP): $(B)/MuTheMatrix $(B)/Info.plist $(B)/AppIcon.icns $(RESOURCES) $(INSTALLER_FILES)
	rm -rf $(APPQ)
	mkdir -p $(APPQ)/Contents/MacOS $(APPQ)/Contents/Resources
	cp $(B)/Info.plist $(APPQ)/Contents/Info.plist
	printf 'APPL????' > $(APPQ)/Contents/PkgInfo
	cp $(B)/MuTheMatrix $(APPQ)/Contents/MacOS/MuTheMatrix
	cp $(B)/AppIcon.icns $(APPQ)/Contents/Resources/AppIcon.icns
	cp $(RESOURCES) $(APPQ)/Contents/Resources/
	chmod 755 $(APPQ)/Contents/Resources/mu-launch.sh
	mkdir -p $(APPQ)/Contents/Resources/installer/lib $(APPQ)/Contents/Resources/installer/registry
	cp ../installer/setup-mu-mac.sh ../installer/verify-mu-mac.sh ../installer/play-mu.sh $(APPQ)/Contents/Resources/installer/
	cp ../installer/lib/mukit.sh $(APPQ)/Contents/Resources/installer/lib/
	cp ../installer/registry/mu-mac.reg $(APPQ)/Contents/Resources/installer/registry/
	@if [ -n "$(EMBED_MUGL)" ]; then mkdir -p $(APPQ)/Contents/Resources/dlls && cp "$(EMBED_MUGL)" $(APPQ)/Contents/Resources/dlls/opengl32.dll && echo "bundled mugl $(EMBED_MUGL)"; fi
	@if [ -n "$(EMBED_FAST_X87)" ]; then mkdir -p $(APPQ)/Contents/Resources/fast-x87 && \
	  for f in libtimewalker.dylib runtime_loader libRuntimeRosettax87 LICENSE LICENSE-rosettax87_jit THIRD_PARTY_NOTICES.md SOURCE.txt; do \
	    [ ! -f "$(EMBED_FAST_X87)/$$f" ] || cp "$(EMBED_FAST_X87)/$$f" $(APPQ)/Contents/Resources/fast-x87/; done && \
	  xcrun clang -arch arm64 -O2 -o $(APPQ)/Contents/Resources/fast-x87/x87-main-only-wrapper ../x87-main-only-wrapper.c && \
	  echo "bundled fast x87 $(EMBED_FAST_X87)"; fi
	@if [ -n "$(EMBED_MSCOREE)" ]; then mkdir -p $(APPQ)/Contents/Resources/dlls && cp "$(EMBED_MSCOREE)" $(APPQ)/Contents/Resources/dlls/mscoree.dll && echo "bundled mscoree $(EMBED_MSCOREE)"; fi
	codesign --force --sign - --timestamp=none $(APPQ)
	codesign --verify --strict --verbose=1 $(APPQ)
	@touch $@
	@echo "built $(APP)"
	@if [ -z "$(EMBED_MUGL)" ] || [ -z "$(EMBED_MSCOREE)" ] || [ -z "$(EMBED_FAST_X87)" ]; then \
	  echo "NOTE: development build without all of EMBED_MUGL, EMBED_MSCOREE and EMBED_FAST_X87."; \
	  echo "      Do not give it to players (the game would run at about 4 fps); build theirs with make player-app."; fi

# The build for players. Without the pinned DLLs an app installs a game that runs at about 4 fps and whose final check
# fails ("The installation stopped"), so this target refuses to build unless all three embeds are present.
player-app:
	@missing=; \
	if [ -z "$(EMBED_MUGL)" ]; then missing="$$missing\n  EMBED_MUGL=/path/to/opengl32.dll      the mugl build (for example mugl-v76.dll)"; \
	elif [ "$$(head -c 2 "$(EMBED_MUGL)" 2>/dev/null)" != MZ ]; then missing="$$missing\n  EMBED_MUGL=$(EMBED_MUGL): not a DLL (missing or no MZ header)"; fi; \
	if [ -z "$(EMBED_MSCOREE)" ]; then missing="$$missing\n  EMBED_MSCOREE=/path/to/mscoree.dll    the mscoree display-mode proxy"; \
	elif [ "$$(head -c 2 "$(EMBED_MSCOREE)" 2>/dev/null)" != MZ ]; then missing="$$missing\n  EMBED_MSCOREE=$(EMBED_MSCOREE): not a DLL (missing or no MZ header)"; fi; \
	if [ -z "$(EMBED_FAST_X87)" ]; then missing="$$missing\n  EMBED_FAST_X87=/path/to/fast-x87      from ../installer/packaging/package-fast-x87.sh"; \
	else for f in libtimewalker.dylib runtime_loader libRuntimeRosettax87; do \
	  [ -f "$(EMBED_FAST_X87)/$$f" ] || missing="$$missing\n  EMBED_FAST_X87=$(EMBED_FAST_X87): no $$f"; done; fi; \
	if [ -n "$$missing" ]; then \
	  printf '\n*** make player-app: refusing to build an app for players without the pinned files:%b\n\n' "$$missing" >&2; \
	  printf '*** Without them the game runs at about 4 fps and the installation ends with a failed check.\n' >&2; \
	  printf '*** See README.md, "A build for players". (make without player-app builds a development app.)\n\n' >&2; \
	  exit 1; fi
	$(MAKE) all
	"$(APP)/Contents/MacOS/MuTheMatrix" --check-bundle
	@echo "player app ready: $(APP)"

test:
	bash tests/test-bundle.sh

install: all
	mkdir -p "$(INSTALL_DIR)"
	rm -rf "$(INSTALL_DIR)/Mu The Matrix.app"
	ditto $(APPQ) "$(INSTALL_DIR)/Mu The Matrix.app"
	@echo "installed $(INSTALL_DIR)/Mu The Matrix.app"

clean:
	rm -rf $(B)

.PHONY: all player-app test install clean
