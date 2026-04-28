PYTHON ?= python3

.PHONY: validate smoke py-compile

validate: py-compile smoke

py-compile:
	$(PYTHON) -m py_compile skills/harness-engineering-audit/scripts/*.py tests/smoke/run_skill_smoke.py

smoke:
	$(PYTHON) tests/smoke/run_skill_smoke.py
