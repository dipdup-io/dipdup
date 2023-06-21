.ONESHELL:
.PHONY: $(MAKECMDGOALS)
##
##    🚧 DipDup developer tools
##
## DEV=1                Whether to install dev dependencies
DEV=1
## TAG=latest           Tag for the `image` command
TAG=latest

##

help:           ## Show this help (default)
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

all:            ## Run all checks
	make install lint

install:        ## Install project dependencies
	poetry install \
	`if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`

lint:           ## Lint with all tools
	make isort black ruff mypy

##

isort:          ## Format with isort
	poetry run isort .

black:          ## Format with black
	poetry run black .

ruff:           ## Lint with ruff
	poetry run ruff check .

mypy:           ## Lint with mypy
	poetry run mypy .

build:          ## Build Python wheel package
	poetry build

image:          ## Build Docker image
	docker build . -f deploy/Dockerfile -t demo_big_maps:${TAG}

clean:          ## Remove all files from .gitignore except for `.venv`
	git clean -xdf --exclude=".venv"

##