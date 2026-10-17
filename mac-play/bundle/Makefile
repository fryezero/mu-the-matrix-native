# Mu The Matrix.app (MAC-BUNDLE-001): a double-clickable macOS front end for the CrossOver launcher.
# Builds from source with the Command Line Tools (swiftc, iconutil, plutil, codesign); ad-hoc signed.
#
#   make                 build/Mu The Matrix.app (B=DIR for another build directory)
#   make test            static checks + dry-run tests (tests/test-bundle.sh)
#   make install         copy the app to $(INSTALL_DIR) (default ~/Applications)
#   make clean
#
# Build-time defaults (used until the settings window saves a settings file):
#   DEFAULT_BOTTLE=MuMatrixKit  DEFAULT_FAST_X87=0|1  DEFAULT_TIMEWALKER_DIR=/path/to/rosetta-timewalker
SWIFTC ?= xcrun swiftc
ARCH ?= $(shell uname -m)
MIN_MACOS ?= 13.0
VERSION ?= 1.0
BUILD_NUMBER ?= 1
BUNDLE_ID ?= io.github.fryezero.mu-the-matrix.launcher
DEFAULT_BOTTLE ?= MuMatrixKit
DEFAULT_FAST_X87 ?= 0
DEFAULT_TIMEWALKER_DIR ?=
INSTALL_DIR ?= $(HOME)/Applications

B ?= build
APP := $(B)/Mu The Matrix.app
APPQ := "$(APP)"
SOURCES := Sources/Core.swift Sources/main.swift
RESOURCES := mu-launch.sh ../installer/lib/mukit.sh ../fast-x87.sh
STAMP := $(B)/.app-stamp
VARS := $(SWIFTC)|$(ARCH)|$(MIN_MACOS)|$(VERSION)|$(BUILD_NUMBER)|$(BUNDLE_ID)|$(DEFAULT_BOTTLE)|$(DEFAULT_FAST_X87)|$(DEFAULT_TIMEWALKER_DIR)

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
	echo '$(DEFAULT_BOTTLE)' | grep -Eq '^[A-Za-z0-9][A-Za-z0-9_-]*$$' || { echo "bad DEFAULT_BOTTLE" >&2; exit 1; }; \
	sed -e 's|@BUNDLE_ID@|$(BUNDLE_ID)|' -e 's|@VERSION@|$(VERSION)|' -e 's|@BUILD@|$(BUILD_NUMBER)|' \
	    -e 's|@MIN_MACOS@|$(MIN_MACOS)|' -e 's|@DEFAULT_BOTTLE@|$(DEFAULT_BOTTLE)|' -e "s|@DEFAULT_FAST_X87@|$$fx|" \
	    -e 's|@DEFAULT_TIMEWALKER_DIR@|$(DEFAULT_TIMEWALKER_DIR)|' $< > $@
	plutil -lint $@

$(STAMP): $(B)/MuTheMatrix $(B)/Info.plist $(B)/AppIcon.icns $(RESOURCES)
	rm -rf $(APPQ)
	mkdir -p $(APPQ)/Contents/MacOS $(APPQ)/Contents/Resources
	cp $(B)/Info.plist $(APPQ)/Contents/Info.plist
	printf 'APPL????' > $(APPQ)/Contents/PkgInfo
	cp $(B)/MuTheMatrix $(APPQ)/Contents/MacOS/MuTheMatrix
	cp $(B)/AppIcon.icns $(APPQ)/Contents/Resources/AppIcon.icns
	cp $(RESOURCES) $(APPQ)/Contents/Resources/
	chmod 755 $(APPQ)/Contents/Resources/mu-launch.sh
	codesign --force --sign - --timestamp=none $(APPQ)
	codesign --verify --strict --verbose=1 $(APPQ)
	@touch $@
	@echo "built $(APP)"

test:
	bash tests/test-bundle.sh

install: all
	mkdir -p "$(INSTALL_DIR)"
	rm -rf "$(INSTALL_DIR)/Mu The Matrix.app"
	ditto $(APPQ) "$(INSTALL_DIR)/Mu The Matrix.app"
	@echo "installed $(INSTALL_DIR)/Mu The Matrix.app"

clean:
	rm -rf $(B)

.PHONY: all test install clean
