FROM dipdup/dipdup:{{ cookiecutter.dipdup_version }}

COPY src/{{cookiecutter.package}} {{cookiecutter.package}}
COPY dipdup*.yml ./

# Uncomment the following lines if you have dependencies other than dipdup in pyproject.toml
# COPY pyproject.toml poetry.lock ./
# RUN inject_pyproject
