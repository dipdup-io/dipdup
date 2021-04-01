FROM python:3.7-slim-buster

RUN apt update && \
    apt install -y build-essential pkg-config libsodium-dev libsecp256k1-dev libgmp-dev make curl git && \
    rm -rf /var/lib/apt/lists/*
RUN pip install poetry
RUN useradd -ms /bin/bash pytezos_dapps

RUN mkdir /home/pytezos_dapps/source
COPY Makefile pyproject.toml poetry.lock README.md /home/pytezos_dapps/source/
# We want to copy our code at the last layer but not to break poetry's "packages" section
RUN mkdir -p /home/pytezos_dapps/source/src/pytezos_dapps && \
    touch /home/pytezos_dapps/source/src/pytezos_dapps/__init__.py && \

WORKDIR /home/pytezos_dapps/source
RUN poetry config virtualenvs.create false
RUN make install DEV=0

COPY . /home/pytezos_dapps/source/
RUN chown -R pytezos_dapps /home/pytezos_dapps/

USER pytezos_dapps

WORKDIR /home/pytezos_dapps/
EXPOSE 8888
ENTRYPOINT [ "python", "-m", "pytezos_dapps"]
