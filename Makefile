PYTHON ?= python3

all:
	$(MAKE) -C reconstructed/boot
	$(MAKE) -C model-recovery
	$(MAKE) -C reconstructed/client-memory

test: all
	$(PYTHON) -m unittest discover -s reconstructed/boot -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s asset-recovery -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s model-recovery -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s reconstructed/client-memory -p 'test_*.py' -v

integration:
	MU_RECOVERY_INTEGRATION=1 $(MAKE) test

windows:
	$(MAKE) -C windows-capture

.PHONY: all test integration windows
