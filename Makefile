PYTHON ?= python3
VERSION := 1.0.0

.PHONY: help test lint format run-researcher run-scientist run-game package clean

help:
	@printf '%s\n' \
		'make test             Run the full test suite' \
		'make lint             Run Ruff' \
		'make format           Format the Python sources' \
		'make run-researcher   Show the built-in corpus' \
		'make run-scientist    Run a sample experiment loop' \
		'make run-game         Start the game API on port 8000' \
		'make package          Build the distribution zip' \
		'make clean            Remove caches and generated artifacts'

test:
	$(PYTHON) -m unittest discover -s tests -t . -v

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

run-researcher:
	$(PYTHON) ai_researcher.py topics

run-scientist:
	$(PYTHON) ai_scientist.py run "How can we improve checkout conversion?"

run-game:
	$(PYTHON) -m uvicorn ai_game_developer:app --reload

package:
	mkdir -p dist
	rm -f dist/three-ai-suite-v$(VERSION).zip
	cd .. && zip -r three-ai-suite/dist/three-ai-suite-v$(VERSION).zip three-ai-suite \
		-x 'three-ai-suite/.venv/*' '*/__pycache__/*' '*.pyc' 'three-ai-suite/dist/*'

clean:
	rm -rf .ruff_cache .pytest_cache .mypy_cache dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
