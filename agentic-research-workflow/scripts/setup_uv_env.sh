#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Creating uv virtual environment"
uv venv --seed

echo "Installing dependencies"
uv sync --locked

echo "Registering Jupyter kernel"
uv run ipython kernel install \
  --user \
  --env VIRTUAL_ENV "$ROOT_DIR/.venv" \
  --name agentic-workflow \
  --display-name "Python (agentic-workflow)"

echo "Environment setup complete"
