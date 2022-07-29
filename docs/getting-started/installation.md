# Installation

This page covers the installation of DipDup in different environments.

## Host requirements

A Linux environment with **Python 3.10** installed is required to use DipDup.

Minimum hardware requirements are 256 MB RAM, 1 CPU core, and some disk space for the database.

### Non-Linux environments

Other UNIX-like systems (macOS, FreeBSD, etc.) should work but are not supported officially.

DipDup currently doesn't work in Windows environments due to incompatibilities in libraries it depends on. Please use WSL or Docker.

We [aim to improve](https://github.com/dipdup-net/dipdup-py/pull/358) cross-platform compatibility in future releases.

> 💡 **SEE ALSO**
>
> * {{ #summary advanced/performance.md }}
> * [What is the Windows Subsystem for Linux?](https://docs.microsoft.com/en-us/windows/wsl/about)

## Local installation

To begin with, create a new directory for your project and enter it. Now choose one way of managing virtual environments:

### Poetry (recommended)

Initialize a new PEP 518 project and add DipDip to dependencies.

```shell
poetry init
poetry add dipdup
```

### pip

Create a new virtual environment and install DipDup in it.

```shell
python -m venv .venv
source .venv/bin/activate
pip install dipdup
```

## Other options

> 💡 **SEE ALSO**
>
> * {{ #summary deployment/docker.md }}
