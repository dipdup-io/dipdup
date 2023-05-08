.ONESHELL:
.PHONY: $(MAKECMDGOALS)
##
##    🚧 DipDup developer tools
##
## DEV=1                Install dev dependencies
DEV=1
## TAG=latest           Tag for the `image` command
TAG=latest

##

help:           ## Show this help (default)
	@grep -F -h "##" $(MAKEFILE_LIST) | grep -F -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

all:            ## Run a whole CI pipeline: formatters, linters and tests
	make install lint test docs

install:        ## Install project dependencies
	poetry install \
	`if [ "${DEV}" = "0" ]; then echo "--without dev"; fi`

lint:           ## Lint with all tools
	make isort black ruff mypy

test:           ## Run test suite
	poetry run pytest --cov-report=term-missing --cov=dipdup --cov-report=xml -n auto -s -v tests

docs:           ## Build docs
	scripts/update_cookiecutter.py
	cd docs
	make -s clean build lint

##

isort:          ## Format with isort
	poetry run isort src tests scripts

black:          ## Format with black
	poetry run black src tests scripts

ruff:           ## Lint with ruff
	poetry run ruff check --fix src tests scripts

mypy:           ## Lint with mypy
	poetry run mypy --strict src tests scripts

cover:          ## Print coverage for the current branch
	poetry run diff-cover --compare-branch `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` coverage.xml

build:          ## Build Python wheel package
	poetry build

image:          ## Build Docker image
	docker buildx build . --load --progress plain -t dipdup:${TAG}

##

clean:          ## Remove all files from .gitignore except for `.venv`
	git clean -xdf --exclude=".venv"

update:         ## Update dependencies, export requirements.txt
	poetry update
	poetry export --without-hashes -o requirements.txt
	poetry export --without-hashes -o requirements.dev.txt --with dev

demos:          ## Recreate demos from templates
	python scripts/update_cookiecutter.py
	python scripts/update_demos.py
	make lint

replays:        ## Recreate replays for tests
	rm -r tests/replays/*
	make test

##

DEMO="demo-evm-events"

demo_run:
	dipdup -c demos/${DEMO}/dipdup.yml -e "${DEMO}.env" run | tee ${DEMO}.log

demo_init:
	dipdup -c demos/${DEMO}/dipdup.yml -e "${DEMO}.env" init | tee ${DEMO}.log

profile:
	python tests/profile_abi_decoding.py

unsafe:
	grep -r "type: ignore" src tests scripts | grep -v "import"

##