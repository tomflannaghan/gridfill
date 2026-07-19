# Development

See [README.md](README.md) for what gridfill is and how to use it. This
document covers installing from source, the Python API, and running checks.

The Python project lives in [python/](python/); run all commands below from
there.

## Install

```bash
cd python
uv venv
uv pip install -e ".[dev]"
```

## Checks

```bash
ruff check . && ruff format --check .
mypy src
pytest
```
