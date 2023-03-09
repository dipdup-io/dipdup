# syntax=docker/dockerfile:1.3-labs
FROM python:3.11-slim-buster AS compile-image
ARG DIPDUP_DOCKER_IMAGE=default
ENV DIPDUP_DOCKER=1
ENV DIPDUP_DOCKER_IMAGE=${DIPDUP_DOCKER_IMAGE}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt update && \
    apt install -y gcc make git curl `if [[ $DIPDUP_DOCKER_IMAGE = "pytezos" ]]; then echo build-essential pkg-config libsodium-dev libsecp256k1-dev libgmp-dev; fi` && \
    python -m venv --without-pip --system-site-packages /opt/dipdup && \
    mkdir -p /opt/dipdup/src/dipdup/ && \
    touch /opt/dipdup/src/dipdup/__init__.py && \
    rm -r /var/log/* /var/lib/apt/lists/* /var/cache/* /var/lib/dpkg/status*
WORKDIR /opt/dipdup
ENV PATH="/opt/dipdup/bin:$PATH"

COPY pyproject.toml requirements.txt requirements.pytezos.txt README.md /opt/dipdup/

RUN /usr/local/bin/pip install --prefix /opt/dipdup --no-cache-dir --disable-pip-version-check --no-deps -r /opt/dipdup/requirements.`if [[ $DIPDUP_DOCKER_IMAGE = "pytezos" ]]; then echo "pytezos."; fi`txt -e .

FROM python:3.11-slim-buster AS build-image

ARG DIPDUP_DOCKER_IMAGE=default
ENV DIPDUP_DOCKER=1
ENV DIPDUP_DOCKER_IMAGE=${DIPDUP_DOCKER_IMAGE}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN useradd -ms /bin/bash dipdup && \
    pip install --no-cache-dir poetry==1.4.0 setuptools && \
    apt update && \
    apt install -y --no-install-recommends git `if [[ $DIPDUP_DOCKER_IMAGE = "pytezos" ]]; then echo libsodium-dev libsecp256k1-dev libgmp-dev; fi` && \
    rm -r /var/log/* /var/lib/apt/lists/* /var/cache/* /var/lib/dpkg/status*

USER dipdup
ENV PATH="/opt/dipdup/bin:$PATH"
ENV PYTHONPATH="/home/dipdup:/home/dipdup/src:/opt/dipdup/src:/opt/dipdup/lib/python3.11/site-packages:$PYTHONPATH"
WORKDIR /home/dipdup/
ENTRYPOINT ["dipdup"]
CMD ["run"]

COPY --chown=dipdup --chmod=0755 scripts/install_dependencies.sh /opt/dipdup/bin/install_dependencies
COPY --chown=dipdup --chmod=0755 scripts/install_dependencies.sh /opt/dipdup/bin/inject_pyproject
COPY --chown=dipdup --from=compile-image /opt/dipdup /opt/dipdup
COPY --chown=dipdup . /opt/dipdup