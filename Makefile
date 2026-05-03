PYTHON ?= python3

.PHONY: validate smoke py-compile mirror-parity

validate: py-compile mirror-parity smoke

py-compile:
	$(PYTHON) -m py_compile skills/harness-engineering-audit/scripts/*.py tests/smoke/run_skill_smoke.py tests/check_skill_mirror.py

mirror-parity:
	$(PYTHON) tests/check_skill_mirror.py

smoke:
	$(PYTHON) tests/smoke/run_skill_smoke.py
