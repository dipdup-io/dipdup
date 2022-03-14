FROM python:3.10-slim-buster

ARG PLUGINS

SHELL ["/bin/bash", "-x", "-v", "-c"]
RUN apt update && \
    apt install -y make git sudo `if [[ $PLUGINS =~ "pytezos" ]]; then echo build-essential pkg-config libsodium-dev libsecp256k1-dev libgmp-dev; fi` && \
    rm -rf /var/lib/apt/lists/*
RUN pip install poetry
RUN useradd -ms /bin/bash dipdup

RUN mkdir /home/dipdup/source
COPY --chown=dipdup Makefile pyproject.toml poetry.lock README.md /home/dipdup/source/
# We want to copy our code at the last layer but not to break poetry's "packages" section
RUN mkdir -p /home/dipdup/source/src/dipdup && \
    touch /home/dipdup/source/src/dipdup/__init__.py

WORKDIR /home/dipdup/source
RUN poetry config virtualenvs.create false
RUN make install DEV=0 PLUGINS="${PLUGINS}"

COPY --chown=dipdup inject_pyproject.sh /usr/bin/inject_pyproject.sh
RUN echo 'sudo /usr/bin/inject_pyproject.sh' >> /usr/bin/inject_pyproject
RUN echo 'dipdup ALL = NOPASSWD: /usr/bin/inject_pyproject.sh' >> /etc/sudoers
RUN chmod +x /usr/bin/inject_pyproject.sh
RUN chmod +x /usr/bin/inject_pyproject

COPY --chown=dipdup src /home/dipdup/source/src

USER dipdup
RUN poetry config virtualenvs.create false

WORKDIR /home/dipdup/
ENTRYPOINT ["dipdup"]
CMD ["run"]
