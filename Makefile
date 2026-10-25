BASE_PYTHON ?= python3
PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo $(BASE_PYTHON); fi)
VERSION := 2.0.0

.PHONY: help install venv test lint format check run-researcher run-scientist \
	run-game game-export docker docker-run package clean clean-venv

help:
	@printf '%s\n' \
		'make install          Create .venv and install the full development environment' \
		'make test             Run the full test suite' \
		'make lint             Run Ruff' \
		'make format           Format the Python sources' \
		'make check            Run lint and tests' \
		'make run-researcher   Show the built-in research corpus' \
		'make run-scientist    List the scientist domains' \
		'make run-game         Start the game API with auto-reload' \
		'make game-export      Export a sample playable HTML game' \
		'make docker           Build the game Docker image' \
		'make package          Build the distribution zip' \
		'make clean            Remove caches and generated artifacts' \
		'make clean-venv       Remove the local virtual environment'

install: venv

venv:
	$(BASE_PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e '.[dev]'
	@printf '\nInstalled. Activate with:\n  source .venv/bin/activate\nThen run:\n  three-ai --help\n'

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -t . -v

lint:
	$(PYTHON) -m ruff check src tests

format:
	$(PYTHON) -m ruff format src tests

check: lint test

run-researcher:
	PYTHONPATH=src $(PYTHON) -m three_ai_suite researcher topics

run-scientist:
	PYTHONPATH=src $(PYTHON) -m three_ai_suite scientist domains

run-game:
	PYTHONPATH=src $(PYTHON) -m three_ai_suite game serve --reload

game-export:
	PYTHONPATH=src $(PYTHON) -m three_ai_suite game export --seed 42 --theme dungeon --output dungeon.html

docker:
	docker build -t three-ai-game .

docker-run:
	docker run --rm -p 8000:8000 three-ai-game

package:
	mkdir -p dist
	rm -f dist/three-ai-suite-v$(VERSION).zip
	cd .. && zip -r three-ai-suite/dist/three-ai-suite-v$(VERSION).zip three-ai-suite \
		-x 'three-ai-suite/.git/*' 'three-ai-suite/.venv/*' '*/__pycache__/*' '*.pyc' \
		'three-ai-suite/.ruff_cache/*' 'three-ai-suite/.pytest_cache/*' \
		'three-ai-suite/.mypy_cache/*' 'three-ai-suite/dist/*' 'three-ai-suite/build/*' \
		'three-ai-suite/*.egg-info/*' 'three-ai-suite/src/*.egg-info/*'

clean:
	rm -rf .ruff_cache .pytest_cache .mypy_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

clean-venv:
	rm -rf .venv
