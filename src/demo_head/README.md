# demo_head

<a href="https://dipdup.io"><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="114" height="20" role="img" aria-label="made with: dipdup"><script xmlns=""/><script xmlns=""/><title>made with: dipdup</title><linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient><clipPath id="r"><rect width="114" height="20" rx="3" fill="#fff"/></clipPath><g clip-path="url(#r)"><rect width="67" height="20" fill="#555"/><rect x="67" width="47" height="20" fill="#ff885e"/><rect width="114" height="20" fill="url(#s)"/></g><g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110"><text aria-hidden="true" x="345" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="570">made with</text><text x="345" y="140" transform="scale(.1)" fill="#fff" textLength="570">made with</text><text aria-hidden="true" x="895" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="370">dipdup</text><text x="895" y="140" transform="scale(.1)" fill="#fff" textLength="370">dipdup</text></g></svg></a>

Blockchain indexer built with DipDup

## Installation

This project is based on [DipDup](https://dipdup.io), framework for building featureful dapps.

You need a Linux/macOS system with Python 3.11 installed. Use our installer for easy setup:

```bash
curl -Lsf https://dipdup.io/install.py | python
```

See [Installation](https://docs.dipdup.net/installation) page for all options.

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
cp deploy/.env.example .env
# Edit .env before running
docker-compose -f deploy/docker-compose.yml up
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