.ONESHELL:
.PHONY: $(MAKECMDGOALS)
##
##    🚧 DipDup developer tools
##
## DEV=1                Install dev dependencies
DEV=1
## PYTEZOS=0            Install PyTezos
PYTEZOS=0
## TAG=latest           Tag for the `image` command
TAG=latest

##

help:           ## Show this help (default)
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

all:            ## Run a whole CI pipeline: lint, run tests, build docs
	make install lint test docs

install:        ## Install project dependencies
	poetry install \
	`if [ "${PYTEZOS}" = "1" ]; then echo "-E pytezos "; fi` \
	`if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`

lint:           ## Lint with all tools
	make isort black flake mypy

test:           ## Run test suite
	poetry run pytest --cov-report=term-missing --cov=dipdup --cov-report=xml -n auto --dist loadscope -s -v tests

docs:           ## Build docs
	cd docs
	make -s clean docs markdownlint orphans || true

homepage:       ## Build homepage
	cd docs
	make homepage

##

isort:          ## Format with isort
	poetry run isort src tests

black:          ## Format with black
	poetry run black src tests

flake:          ## Lint with flake8
	poetry run flakeheaven lint src tests

mypy:           ## Lint with mypy
	poetry run mypy src tests

cover:          ## Print coverage for the current branch
	poetry run diff-cover --compare-branch `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` coverage.xml

build:          ## Build Python wheel package
	poetry build

image:          ## Build Docker image
	docker buildx build . -t dipdup:${TAG}

image-pytezos:
	docker buildx build . -t dipdup:${TAG}-pytezos --build-arg PYTEZOS=1

release-patch:  ## Release patch version
	bumpversion patch
	git push --tags
	git push

release-minor:  ## Release minor version
	bumpversion minor
	git push --tags
	git push

release-major:  ## Release major version
	bumpversion major
	git push --tags
	git push

clean:          ## Remove all files from .gitignore except for `.venv`
	git clean -xdf --exclude=".venv"

##