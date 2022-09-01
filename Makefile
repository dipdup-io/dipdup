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
	`if [ "${DEV}" = "1" ]; then echo "--with dev"; fi`

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
	poetry run isort src tests scripts

black:          ## Format with black
	poetry run black src tests scripts

flake:          ## Lint with flake8
	poetry run flakeheaven lint src tests scripts

mypy:           ## Lint with mypy
	poetry run mypy src tests scripts

cover:          ## Print coverage for the current branch
	poetry run diff-cover --compare-branch `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` coverage.xml

build:          ## Build Python wheel package
	poetry build

image:          ## Build all Docker images
	make image-default
	make image-pytezos
	make image-slim

image-default:  ## Build default Docker image
	docker buildx build . --progress plain -t dipdup:${TAG}

image-pytezos:  ## Build pytezos Docker image
	docker buildx build . --progress plain -t dipdup:${TAG}-pytezos --build-arg PYTEZOS=1

image-slim:     ## Build slim Docker image
	docker buildx build . --progress plain -t dipdup:${TAG}-slim -f Dockerfile.slim

##

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

##

clean:          ## Remove all files from .gitignore except for `.venv`
	git clean -xdf --exclude=".venv"

update:         ## Update dependencies, export requirements.txt (wait an eternity)
	make install
	poetry update

	cp pyproject.toml pyproject.toml.bak
	cp poetry.lock poetry.lock.bak

	# NOTE: 1.2.0 spells
	poetry export --without-hashes -o requirements.txt
	poetry export --without-hashes -o requirements.pytezos.txt -E pytezos
	poetry export --without-hashes -o requirements.dev.txt --with dev
	poetry remove datamodel-code-generator
	poetry export --without-hashes -o requirements.slim.txt

	mv pyproject.toml.bak pyproject.toml
	mv poetry.lock.bak poetry.lock

	make install

	scripts/update_demos.sh

##