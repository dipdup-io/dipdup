FROM dipdup/dipdup:{{ cookiecutter.dipdup_version }}

COPY pyproject.toml poetry.lock ./
# Uncomment the following line if you have dependencies other than dipdup in pyproject.toml
# RUN inject_pyproject

COPY src/{{cookiecutter.package}} {{cookiecutter.package}}