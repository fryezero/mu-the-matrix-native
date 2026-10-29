PYTHON ?= python3

all:
	$(MAKE) -C reconstructed/boot
	$(MAKE) -C model-recovery
	$(MAKE) -C reconstructed/client-memory
	$(MAKE) -C reconstructed/record-math
	$(MAKE) -C reconstructed/model-codec
	$(MAKE) -C reconstructed/camera
	$(MAKE) -C reconstructed/path
	$(MAKE) -C reconstructed/actors
	$(MAKE) -C reconstructed/audio
	$(MAKE) -C reconstructed/ui
	$(MAKE) -C reconstructed/data
	$(MAKE) -C reconstructed/effects
	$(MAKE) -C reconstructed/movement
	$(MAKE) -C reconstructed/renderchar
	$(MAKE) -C reconstructed/charsel
	$(MAKE) -C reconstructed/hud
	$(MAKE) -C reconstructed/objects
	$(MAKE) -C reconstructed/scene
	$(MAKE) -C reconstructed/combat
	$(MAKE) -C reconstructed/environment
	$(MAKE) -C reconstructed/particles
	$(MAKE) -C reconstructed/joints
	$(MAKE) -C reconstructed/names
	$(MAKE) -C reconstructed/npc
	$(MAKE) -C reconstructed/price
	$(MAKE) -C reconstructed/helpers
	$(MAKE) -C reconstructed/raven
	$(MAKE) -C reconstructed/pets
	$(MAKE) -C reconstructed/quest
	$(MAKE) -C reconstructed/skill
	$(MAKE) -C reconstructed/map
	$(MAKE) -C reconstructed/social
	$(MAKE) -C reconstructed/progress
	$(MAKE) -C native

# The unittest discoveries `make test` runs, one directory each, in this order. This is the only list:
# scripts/run_test_suites.py runs it (a pool of MU_GATE_JOBS workers; MU_GATE_JOBS=1 is one after another,
# stopping at the first failure) and tests/test_run_test_suites.py checks nothing is discovered elsewhere.
TEST_SUITES = \
	reconstructed/boot \
	asset-recovery \
	model-recovery \
	tests \
	reconstructed/client-memory \
	reconstructed/record-math \
	reconstructed/model-codec \
	reconstructed/camera \
	reconstructed/path \
	reconstructed/actors \
	reconstructed/audio \
	reconstructed/ui \
	reconstructed/data \
	reconstructed/effects \
	reconstructed/movement \
	reconstructed/renderchar \
	reconstructed/charsel \
	reconstructed/hud \
	reconstructed/objects \
	reconstructed/scene \
	reconstructed/combat \
	reconstructed/environment \
	reconstructed/particles \
	reconstructed/items \
	reconstructed/joints \
	reconstructed/names \
	reconstructed/npc \
	reconstructed/price \
	reconstructed/mix \
	reconstructed/helpers \
	reconstructed/raven \
	reconstructed/pets \
	reconstructed/quest \
	reconstructed/skill \
	reconstructed/map \
	reconstructed/social \
	reconstructed/progress \
	native/tests

test: all
	$(PYTHON) scripts/run_test_suites.py $(TEST_SUITES)

native-viewer:
	$(MAKE) -C native viewer

# Read-only live-state readers for the running client (macOS host tools, ad-hoc signed).
live-readers:
	$(MAKE) -C live-readers

integration:
	MU_RECOVERY_INTEGRATION=1 $(MAKE) test

windows:
	$(MAKE) -C windows-capture

.PHONY: all test integration windows native-viewer live-readers
