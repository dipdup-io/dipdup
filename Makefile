.ONESHELL:
.PHONY: docs
.DEFAULT_GOAL: all

DEV=1
PLUGINS=""
TAG=latest

all: install lint test cover
lint: isort black flake mypy

debug:
	pip install . --force --no-deps

install:
	poetry install \
	`if [ -n "${PLUGINS}" ]; then for i in ${PLUGINS}; do echo "-E $$i "; done; fi` \
	`if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`

isort:
	poetry run isort src tests

black:
	poetry run black src tests

flake:
	poetry run flakehell lint src tests

mypy:
	poetry run mypy src tests

test:
	poetry run pytest --cov-report=term-missing --cov=dipdup --cov-report=xml -v tests

cover:
	poetry run diff-cover coverage.xml

build:
	poetry build

image:
	docker build . -t dipdup:${TAG}
	docker build . -t dipdup:${TAG}-pytezos --build-arg PLUGINS=pytezos

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