## ==> DipDup makefile
.ONESHELL:
.PHONY: test build docs
.DEFAULT_GOAL: all

##
## DEV=1           Install dev dependencies
DEV=1
## TAG=latest      Docker tag for images built
TAG=latest
##

all:            ## Run a whole CI pipeline (default)
	make install lint test cover

install:        ## Install project
	poetry install \
	`if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`
	poetry run pip uninstall -y flakehell || true

lint:           ## Lint with all tools
	make isort black flake mypy

isort:          ## Lint with isort
	poetry run isort src tests

black:          ## Lint with black
	poetry run black src tests

flake:          ## Lint with flake8
	poetry run flakeheaven lint src tests

mypy:           ## Lint with mypy
	poetry run mypy src tests

test:           ## Run test suite
	poetry run pytest --cov-report=term-missing --cov={{ cookiecutter.package }} --cov-report=xml -n auto --dist loadscope -s -v tests

cover:          ## Print coverage for the current branch
	poetry run diff-cover --compare-branch `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` coverage.xml

build:          ## Build wheel Python package
	poetry build

image:          ## Build Docker image
	docker buildx build . -t {{ cookiecutter.project_name }}:${TAG}

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

help:           ## Show this help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
