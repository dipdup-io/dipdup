FROM python:3.8-slim-buster

RUN apt update && \
    apt install -y make git && \
    rm -rf /var/lib/apt/lists/*
RUN pip install poetry
RUN useradd -ms /bin/bash dipdup

RUN mkdir /home/dipdup/source
COPY Makefile pyproject.toml poetry.lock README.md /home/dipdup/source/
# We want to copy our code at the last layer but not to break poetry's "packages" section
RUN mkdir -p /home/dipdup/source/src/dipdup && \
    touch /home/dipdup/source/src/dipdup/__init__.py

WORKDIR /home/dipdup/source
RUN poetry config virtualenvs.create false
RUN make install DEV=0

COPY . /home/dipdup/source/
RUN chown -R dipdup /home/dipdup/

USER dipdup

WORKDIR /home/dipdup/
EXPOSE 8888
ENTRYPOINT ["python", "-m", "dipdup"]
CMD ["-c", "dipdup.yml", "run"]