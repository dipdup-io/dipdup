# syntax=docker/dockerfile:1.3-labs
FROM python:3.10-slim-buster AS compile-image

ARG EXTRAS
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

RUN <<eot
    apt update
    apt install -y --no-install-recommends gcc gcc-arm-none-eabi make git sudo `if [[ $EXTRAS =~ "pytezos" ]]; then echo build-essential pkg-config libsodium-dev libsecp256k1-dev libgmp-dev; fi`
    rm -r /var/lib/apt/lists/*

    mkdir -p /opt/dipdup
    python -m venv /opt/dipdup/.venv
    pip install --no-cache-dir poetry

    rm -r /var/log/*
eot

WORKDIR /opt/dipdup
ENV PATH="/opt/dipdup/.venv/bin:$PATH"

COPY --chown=dipdup Makefile pyproject.toml poetry.lock README.md /opt/dipdup/
COPY --chown=dipdup inject_pyproject.sh /usr/bin/inject_pyproject.sh

RUN <<eot
    # We want to copy our code at the last layer but not to break poetry's "packages" section
    mkdir -p /opt/dipdup/src/dipdup
    touch /opt/dipdup/src/dipdup/__init__.py

    make install DEV=0 EXTRAS="${EXTRAS}"

    echo 'sudo /usr/bin/inject_pyproject.sh' >> /usr/bin/inject_pyproject
    echo 'dipdup ALL = NOPASSWD: /usr/bin/inject_pyproject.sh' >> /etc/sudoers
    chmod +x /usr/bin/inject_pyproject.sh
    chmod +x /usr/bin/inject_pyproject

    rm -r /root/.cache
eot

FROM python:3.10-slim-buster AS build-image

ARG EXTRAS
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="/opt/dipdup/.venv/bin:$PATH"
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

RUN <<eot
    poetry config virtualenvs.in-project true

    useradd -ms /bin/bash dipdup

    apt update
    apt install -y --no-install-recommends git sudo `if [[ $EXTRAS =~ "pytezos" ]]; then echo build-essential pkg-config libsodium-dev libsecp256k1-dev libgmp-dev; fi`
    rm -r /var/lib/apt/lists/*
eot

COPY --chown=dipdup --from=compile-image /opt/dipdup /opt/dipdup
COPY --chown=dipdup . /opt/dipdup

USER dipdup

WORKDIR /home/dipdup/
ENTRYPOINT ["dipdup"]
CMD ["run"]
