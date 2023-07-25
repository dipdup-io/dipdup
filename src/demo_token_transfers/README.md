# demo_token_transfers

TzBTC FA1.2 token transfers

## Installation

This project is based on [DipDup](https://dipdup.io), a framework for building featureful dapps.

You need a Linux/macOS system with Python 3.11 installed. Use our installer for easy setup:

```bash
curl -Lsf https://dipdup.io/install.py | python3
```

See the [Installation](https://dipdup.io/docs/installation) page for all options.

## Usage

Run the indexer in-memory:

```bash
dipdup run
```

Store data in SQLite database:

```bash
dipdup -c . -c configs/dipdup.sqlite.yml run
```

Or spawn a docker-compose stack:

```bash
cp deploy/.env.default deploy/.env
# Edit .env before running
docker-compose -f deploy/compose.yaml up
```

## Development setup

We recommend [PDM](https://pdm.fming.dev/latest/) for managing Python projects. To set up the development environment:

```bash
pdm install
pdm venv activate
```

Some tools are included to help you keep the code quality high: black, ruff and mypy.

```bash
# Format code
pdm fmt

# Lint code
pdm lint

# Build Docker image
pdm image
```

Inspect the `pyproject.toml` file. It contains all the dependencies and tools used in the project.