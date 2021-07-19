#$/bin/bash
if test -f "/home/dipdup/pyproject.toml"; then
    cd /home/dipdup/
    sed -i  -e 's/dipdup = .*/dipdup = {path = "\/home\/dipdup\/source", develop = true}/' pyproject.toml
    poetry install --no-dev
fi
