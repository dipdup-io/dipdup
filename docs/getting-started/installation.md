# Installation

This page covers the installation of DipDup in different environments.

## Host requirements

A *Linux*/*MacOS* environment with *Python 3.10* installed is required to use DipDup. Other UNIX-like systems should work but are not supported officially.

Minimum hardware requirements are *256 MB RAM*, *1 CPU core*, and some disk space for the database. RAM requirements increase with the number of indexes.

### Non-UNIX environments

Windows is not officially supported, but there's a possibility everything will work fine. In case of issues throw us a message and use WSL or Docker.

We aim to improve cross-platform compatibility in future releases ([issue](https://github.com/dipdup-net/dipdup/issues?q=is%3Aopen+label%3A%22%F0%9F%9A%A2+ci%2Fcd%22+sort%3Aupdated-desc+)).

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/performance.md }}
> * [What is the Windows Subsystem for Linux?](https://docs.microsoft.com/en-us/windows/wsl/about)

## Local installation

### Interactively (recommended)

The following command will install DipDup for the current user:

```shell
python -c "$(curl -sSL https://dipdup.io/install.py)"
```

This script uses pipx under the hood to install `dipdup` and `datamodel-codegen` as CLI tools. Then you can use any package manager of your choice to manage versions of DipDup and other project dependencies.

### Manually

Currently, we mainly use [Poetry](https://python-poetry.org) for dependency management in DipDup. If you prefer hatch, pdb, piptools or others — use them instead. Below are some snippets to get you started.

```shell
# Create a new project directory
mkdir dipdup-indexer; cd dipdup-indexer

# Plain pip
python -m venv .venv
. .venv/bin/activate
pip install dipdup

# or Poetry
poetry init --python ">=3.10,<3.11"
poetry add dipdup
poetry shell
```

## Docker

See {{ #summary deployment/docker.md }} page.
