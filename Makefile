.PHONY: test lint smoke

test:
	python3 -m pytest

lint:
	python3 -m compileall -q src tests

smoke:
	python3 -m pytest tests/smoke
