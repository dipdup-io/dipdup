## ==> DipDup makefile
.ONESHELL:
.PHONY: test build docs

##
## DEV=1           Install dev dependencies
DEV=1
## EXTRAS=""       Install extras (`pytezos` only)
EXTRAS=""
## TAG=latest      Docker tag for images built
TAG=latest
##

help:           ## Show this help (default)
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

all:            ## Run a whole CI pipeline
	make install lint test docs

install:        ## Install project
	poetry install \
	`if [ -n "${EXTRAS}" ]; then for i in ${EXTRAS}; do echo "-E $$i "; done; fi` \
	`if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`
	poetry run pip uninstall -y flakehell || true

lint:           ## Lint with all tools
	make isort black flake mypy

test:           ## Run test suite
	poetry run pytest --cov-report=term-missing --cov=dipdup --cov-report=xml -n auto --dist loadscope -s -v tests

docs:           ## Build docs
	cd docs
	npm i
	npm run build
	poetry run make lint orphans build

##


isort:          ## Lint with isort
	poetry run isort src tests

black:          ## Lint with black
	poetry run black src tests

flake:          ## Lint with flake8
	poetry run flakeheaven lint src tests

mypy:           ## Lint with mypy
	poetry run mypy src tests


cover:          ## Print coverage for the current branch
	poetry run diff-cover --compare-branch `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` coverage.xml

build:          ## Build wheel Python package
	poetry build

image:          ## Build Docker image
	docker buildx build . -t dipdup:${TAG}
	docker buildx build . -t dipdup:${TAG}-pytezos --build-arg EXTRAS=pytezos

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

clean:          ## Remove all files and directories ignored by git
	git clean -xdf --exclude=".venv"
