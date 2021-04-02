.ONESHELL:
.PHONY: docs
.DEFAULT_GOAL: all

DEV ?= 1

all: install lint test cover
lint: isort black pylint mypy

debug:
	pip install . --force --no-deps

install:
	poetry install `if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`

isort:
	poetry run isort src

black:
	poetry run black src

pylint:
	poetry run pylint src || poetry run pylint-exit $$?

mypy:
	poetry run mypy src

test:
	poetry run pytest --cov-report=term-missing --cov=dipdup --cov-report=xml -v tests

cover:
	poetry run diff-cover coverage.xml

build:
	poetry build

image:
	docker build . -t dipdup

release-patch:
	bumpversion patch
	git push --tags
	git push

release-minor:
	bumpversion minor
	git push --tags
	git push

release-major:
	bumpversion major
	git push --tags
	git push