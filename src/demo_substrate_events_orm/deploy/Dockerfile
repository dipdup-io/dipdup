FROM dipdup/dipdup:8
# FROM ghcr.io/dipdup-io/dipdup:8
FROM ghcr.io/dipdup-io/dipdup:feat-substrate

# COPY --chown=dipdup pyproject.toml README.md .
# RUN pip install .

COPY --chown=dipdup . demo_substrate_events_orm
WORKDIR demo_substrate_events_orm