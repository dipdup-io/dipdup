# demo_raw

Process raw operations without filtering and strict typing

## Installation

This project is based on [DipDup](https://dipdup.io), a framework for building featureful dapps.

You need a Linux/macOS system with Python 3.11 installed. Use our installer for easy setup:

```shell
curl -Lsf https://dipdup.io/install.py | python3
```

See the [Installation](https://dipdup.io/docs/installation) page for all options.

## Usage

Run the indexer in-memory:

```shell
dipdup run
```

Store data in SQLite database:

```shell
dipdup -c . -c configs/dipdup.sqlite.yml run
```

Or spawn a Compose stack:

```shell
cd deploy
cp .env.default .env
# Edit .env file before running
docker-compose up
```

## Development setup

We recommend [PDM](https://pdm.fming.dev/latest/) for managing Python projects. To set up the development environment:

```shell
pdm install
$(pdm venv activate)
```

Some tools are included to help you keep the code quality high: black, ruff and mypy. Use scripts from the `pyproject.toml` to run checks manually or in CI:

```shell
# Format code
pdm format

# Lint code
pdm lint

# Build Docker image
pdm image

# Show all available scripts
pdm run --list
```