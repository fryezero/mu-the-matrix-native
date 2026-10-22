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
	$(MAKE) -C reconstructed/quest
	$(MAKE) -C reconstructed/skill
	$(MAKE) -C native

test: all
	$(PYTHON) -m unittest discover -s reconstructed/boot -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s asset-recovery -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s model-recovery -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/client-memory -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/record-math -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/model-codec -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/camera -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/path -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/actors -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/audio -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/ui -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/data -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/effects -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/movement -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/renderchar -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/charsel -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/hud -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/objects -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/scene -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/combat -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/environment -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/particles -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/items -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/joints -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/names -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/npc -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/price -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/helpers -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/quest -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/skill -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s native/tests -p 'test_*.py' -v

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
