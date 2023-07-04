# syntax=docker/dockerfile:1.3-labs
FROM python:3.11-slim-buster AS compile-image
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt update && \
    apt install -y build-essential && \
    python -m venv --without-pip --system-site-packages /opt/dipdup && \
    mkdir -p /opt/dipdup/src/dipdup/ && \
    touch /opt/dipdup/src/dipdup/__init__.py && \
    rm -r /var/log/* /var/lib/apt/lists/* /var/cache/* /var/lib/dpkg/status*
WORKDIR /opt/dipdup
ENV PATH="/opt/dipdup/.venv/bin:$PATH"
ENV PATH="/root/.cargo/bin:$PATH"

COPY pyproject.toml README.md /opt/dipdup/

RUN /usr/local/bin/pip install --prefix /opt/dipdup --no-cache-dir --disable-pip-version-check -e .

FROM python:3.11-slim-buster AS build-image
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN useradd -ms /bin/bash dipdup
USER dipdup
ENV DIPDUP_DOCKER=1
ENV PATH="/opt/dipdup/bin:$PATH"
ENV PYTHONPATH="/home/dipdup:/home/dipdup/src:/opt/dipdup/src:/opt/dipdup/lib/python3.11/site-packages:$PYTHONPATH"
WORKDIR /home/dipdup/
ENTRYPOINT ["dipdup"]
CMD ["run"]

COPY --chown=dipdup --from=compile-image /opt/dipdup /opt/dipdup
COPY --chown=dipdup . /opt/dipdup