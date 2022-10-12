# syntax=docker/dockerfile:1.3-labs
FROM python:3.10-slim-buster AS compile-image
ARG PYTEZOS=0
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

RUN <<eot
    apt update
    apt install -y gcc make git `if [[ $PYTEZOS = "1" ]]; then echo build-essential pkg-config libsodium-dev libsecp256k1-dev libgmp-dev; fi`

    pip install --no-cache-dir poetry==1.2.2

    mkdir -p /opt/dipdup
 
    rm -r /var/log/* /var/lib/apt/lists/* /var/cache/* /var/lib/dpkg/status*
eot

WORKDIR /opt/dipdup
ENV PATH="/opt/dipdup/.venv/bin:$PATH"

COPY --chown=dipdup Makefile pyproject.toml poetry.lock README.md /opt/dipdup/

RUN <<eot
    # We want to copy our code at the last layer but not to break poetry's "packages" section
    mkdir -p /opt/dipdup/src/dipdup
    touch /opt/dipdup/src/dipdup/__init__.py

    make install DEV=0 PYTEZOS="${PYTEZOS}"

    rm -r /root/.cache/
eot

FROM python:3.10-slim-buster AS build-image
ARG PYTEZOS=0
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
SHELL ["/bin/bash", "-c"]

RUN <<eot
    useradd -ms /bin/bash dipdup
    pip install --no-cache-dir poetry==1.2.2 setuptools

    apt update
    apt install -y --no-install-recommends git `if [[ $PYTEZOS = "1" ]]; then echo libsodium-dev libsecp256k1-dev libgmp-dev; fi`

    rm -r /var/log/* /var/lib/apt/lists/* /var/cache/* /var/lib/dpkg/status*
eot

USER dipdup
ENV PATH="/opt/dipdup/.venv/bin:$PATH"
ENV PYTHONPATH="/home/dipdup:/home/dipdup/src:/opt/dipdup/src:/opt/dipdup/lib/python3.10/site-packages:$PYTHONPATH"
WORKDIR /home/dipdup/
ENTRYPOINT ["dipdup"]
CMD ["run"]

COPY --chown=dipdup --chmod=0755 scripts/install_dependencies.sh /opt/dipdup/.venv/bin/install_dependencies
COPY --chown=dipdup --chmod=0755 scripts/install_dependencies.sh /opt/dipdup/.venv/bin/inject_pyproject
COPY --chown=dipdup --from=compile-image /opt/dipdup /opt/dipdup
COPY --chown=dipdup . /opt/dipdup