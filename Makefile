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

image:
	make image-default
	make image-pytezos
	make image-slim

image-default:          ## Build Docker image
	docker buildx build . --progress plain -t dipdup:${TAG}

image-pytezos:
	docker buildx build . --progress plain -t dipdup:${TAG}-pytezos --build-arg PYTEZOS=1

image-slim:
	docker buildx build . --progress plain -t dipdup:${TAG}-slim -f Dockerfile.slim

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

requirements:   ## Update dependencies, export requirements.txt
	make install
	poetry update
	cp pyproject.toml pyproject.toml.bak
	cp poetry.lock poetry.lock.bak
	poetry export -o requirements.txt
	poetry export -o requirements.pytezos.txt -E pytezos
	poetry export -o requirements.dev.txt --dev
	poetry remove datamodel-code-generator
	poetry export -o requirements.slim.txt
	mv pyproject.toml.bak pyproject.toml
	mv poetry.lock.bak poetry.lock
	make install
