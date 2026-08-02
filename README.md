# LREI

LREI is a production-ready Python foundation with a command-line interface,
environment-based configuration, structured application logging, and a small,
testable SQLite persistence layer.

## Requirements

- Python 3.10 or newer

## Install

Install the package in editable mode along with development tools:

```bash
python -m pip install -e ".[dev]"
```

## Development

```bash
ruff check .
black --check .
mypy src
pytest
```

## Command line

The `lrei` command creates and manages a local SQLite database:

```bash
lrei init-db
lrei add "First entry"
lrei list
lrei config
```

Configuration is supplied through environment variables:

| Variable | Purpose |
| --- | --- |
| `LREI_DATA_DIR` | Directory used for application data. |
| `LREI_DATABASE` | Explicit SQLite database path; overrides `LREI_DATA_DIR`. |
| `LREI_LOG_LEVEL` | Logging level, such as `DEBUG`, `INFO`, or `WARNING`. |

Every command also accepts `--database PATH` to override the database for that
invocation.

## Project layout

```text
src/lrei/
  config.py       # validated environment configuration
  logging.py      # application logging setup
  database.py     # SQLite data access layer
  cli.py          # Typer command-line interface
tests/            # unit and CLI tests
```
