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
	make install lint test

install:        ## Install project dependencies
	poetry install \
	`if [ "${DEV}" = "0" ]; then echo "--without dev"; fi`

lint:           ## Lint with all tools
	make isort black ruff mypy

test:           ## Run test suite
	poetry run pytest --cov-report=term-missing --cov=dipdup --cov-report=xml -n auto -s -v tests

##

isort:          ## Format with isort
	poetry run isort src tests scripts

black:          ## Format with black
	poetry run black src tests scripts

ruff:           ## Lint with ruff
	poetry run ruff check --fix src tests scripts

mypy:           ## Lint with mypy
	poetry run mypy src tests scripts

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
	python scripts/update_project.py
	python scripts/update_demos.py
	python scripts/init_demos.py
	make lint

replays:        ## Recreate replays for tests
	rm -r tests/replays/*
	make test

##

DEMO= ?= demo_evm_events
FRONT_PATH ?= ../interface

demo_run:       ## Run demo
	dipdup -c ${DEMO}/dipdup.yaml -e "${DEMO}.env" run | tee ${DEMO}.log

demo_init:      ## Initialize demo
	dipdup -c ${DEMO}/dipdup.yaml -e "${DEMO}.env" init | tee ${DEMO}.log

profile:        ## Run profiling
	python tests/profile_abi_decoding.py

unsafe:         ## Print type-ignores
	grep -r "type: ignore" src tests scripts | grep -v "import"

todo:           ## Print TODOs and FIXMEs
	grep -r -e "TODO:" -e "FIXME:" src tests scripts

docs_serve:     ## Build docs, watch for changes and start dev server
	sh -c 'cd ${FRONT_PATH} && npm run dev' & NPM_PID=$$!
	make docs_watch
	kill $$NPM_PID

docs_watch:     ## Watch for docs changes
	scripts/watch_docs.py --source docs --destination ${FRONT_PATH}/content/docs

##