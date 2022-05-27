# Building Docker images

```Dockerfile
FROM dipdup/dipdup:5.0.0

# Uncomment if you have an additional dependencies in pyproject.toml
# COPY pyproject.toml poetry.lock ./
# RUN inject_pyproject

COPY indexer indexer
COPY dipdup.yml dipdup.prod.yml ./
```
