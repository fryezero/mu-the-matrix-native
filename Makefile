PYTHON ?= python3

all:
	$(MAKE) -C reconstructed/boot
	$(MAKE) -C model-recovery
	$(MAKE) -C reconstructed/client-memory
	$(MAKE) -C reconstructed/record-math
	$(MAKE) -C reconstructed/model-codec

test: all
	$(PYTHON) -m unittest discover -s reconstructed/boot -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s asset-recovery -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s model-recovery -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/client-memory -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/record-math -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/model-codec -p 'test_*.py' -v

integration:
	MU_RECOVERY_INTEGRATION=1 $(MAKE) test

windows:
	$(MAKE) -C windows-capture

.PHONY: all test integration windows
