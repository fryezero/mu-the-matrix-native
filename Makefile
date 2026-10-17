PYTHON ?= python3

all:
	$(MAKE) -C reconstructed/boot
	$(MAKE) -C model-recovery
	$(MAKE) -C reconstructed/client-memory
	$(MAKE) -C reconstructed/record-math
	$(MAKE) -C reconstructed/model-codec
	$(MAKE) -C native

test: all
	for script in mac-play/automation/*.sh; do bash -n "$$script" || exit; done
	bash -n mac-play/setup-crossover-32bit.sh
	bash -n mac-play/cxwine
	bash -n mac-play/cxwineserver
	bash -n mac-play/start-launcher.sh
	bash -n mac-play/gl-batching.sh
	bash -n mac-play/diagnostics/run-eipprof.sh
	bash -n mac-play/fast-x87.sh
	bash -n mac-play/install-fast-x87.sh
	bash -n mac-play/diagnostics/bottle.sh
	bash -n mac-play/diagnostics/run-fpbench.sh
	bash -n mac-play/diagnostics/run-glbench.sh
	bash mac-play/installer/tests/test-mukit.sh
	bash mac-play/bundle/tests/test-bundle.sh
	$(PYTHON) -m unittest discover -s reconstructed/boot -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s asset-recovery -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s model-recovery -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/client-memory -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/record-math -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/model-codec -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s native/tests -p 'test_*.py' -v

mugl:
	$(MAKE) -C mac-play/mugl

native-viewer:
	$(MAKE) -C native viewer

mac-hotpatch:
	$(MAKE) -C mac-play/hotpatch

mac-bundle:
	$(MAKE) -C mac-play/bundle

mac-diagnostics:
	$(MAKE) -C mac-play/diagnostics

integration:
	MU_RECOVERY_INTEGRATION=1 $(MAKE) test

windows:
	$(MAKE) -C windows-capture

.PHONY: all test integration windows mugl mac-bundle mac-diagnostics mac-hotpatch native-viewer
