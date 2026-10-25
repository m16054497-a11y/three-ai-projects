#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
cd "$ROOT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    printf 'error: %s was not found. Install Python 3.10 or newer.\n' "$PYTHON_BIN" >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    printf 'error: Python 3.10 or newer is required.\n' >&2
    exit 1
fi

printf 'Creating virtual environment in %s/.venv\n' "$ROOT_DIR"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
printf 'Installing the three projects and their dependencies...\n'
.venv/bin/python -m pip install '.[all]'

printf '\nInstallation complete.\n\n'
printf 'Activate the environment:\n'
printf '  source %s/.venv/bin/activate\n\n' "$ROOT_DIR"
printf 'Try the projects:\n'
printf '  three-ai --help\n'
printf '  three-ai researcher topics\n'
printf '  three-ai scientist domains\n'
printf '  three-ai game export --seed 42 --theme dungeon --output dungeon.html\n'
printf '  three-ai game serve\n'
