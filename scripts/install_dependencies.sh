#!/bin/sh
if [ $# -eq 0 ]; then
    echo "Installing requirements from 'pyproject.toml'"
    sed -i  -e 's/dipdup = .*/dipdup = {path = "\/opt\/dipdup", develop = true}/' pyproject.toml
    ln -s /opt/dipdup/.venv .venv
    poetry install --no-dev
else
    for arg in $@; do
        echo "Installing requirements from '$arg'"
        /usr/local/bin/pip install -U --prefix /opt/dipdup --no-cache-dir --disable-pip-version-check -r $arg
    done
fi
