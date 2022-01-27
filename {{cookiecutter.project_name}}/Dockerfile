FROM dipdup-net/dipdup-py:{{ cookiecutter.dipdup_version }}

COPY pyproject.toml poetry.lock ./
RUN inject_pyproject

COPY src/{{cookiecutter.package}} {{cookiecutter.package}}