.PHONY: $(MAKECMDGOALS)
MAKEFLAGS += --no-print-directory
##
##  🚧 DipDup developer tools
##
PACKAGE=dipdup
TAG=latest
SOURCE=src tests scripts
DEMO=''
FRONTEND_PATH=../interface


help:           ## Show this help (default)
	@grep -Fh "##" $(MAKEFILE_LIST) | grep -Fv grep -F | sed -e 's/\\$$//' | sed -e 's/##//'

##
##-- CI
##

all:            ## Run an entire CI pipeline
	make format lint test

format:         ## Format with all tools
	make black

lint:           ## Lint with all tools
	make ruff mypy

test:           ## Run tests
	COVERAGE_CORE=sysmon pytest --cov-report=term-missing --cov=dipdup --cov-report=xml -n auto -s -v tests

image:          ## Build Docker image
	docker buildx build . -t ${PACKAGE}:${TAG} --load

##

black:          ## Format with black
	black ${SOURCE}

ruff:           ## Lint with ruff
	ruff check --fix --unsafe-fixes ${SOURCE}

mypy:           ## Lint with mypy
	mypy ${SOURCE}

##
##-- Docs
##

docs_build: docs
docs:           ## Build docs
	python scripts/docs.py check-links --source docs
	python scripts/docs.py dump-references
	python scripts/docs.py dump-demos
	python scripts/docs.py dump-jsonschema
	python scripts/docs.py merge-changelog
	python scripts/docs.py markdownlint
	python scripts/docs.py build --source docs --destination ${FRONTEND_PATH}/content/docs

docs_serve:     ## Build docs and start frontend server
	python scripts/docs.py build --source docs --destination ${FRONTEND_PATH}/content/docs --watch --serve

docs_watch:     ## Build docs and watch for changes
	python scripts/docs.py build --source docs --destination ${FRONTEND_PATH}/content/docs --watch

docs_publish:   ## Tag and push `docs-next` ref
	git tag -d docs-next && git tag docs-next && git push --force origin docs-next
	
##

fixme: todo
todo:           ## Find FIXME and TODO comments
	grep -r -e 'FIXME: ' -e 'TODO: ' -n src/dipdup --color

typeignore:     ## Find type:ignore comments
	grep -r -e 'type: ignore' -n src/dipdup --color

##
##-- Release
##

update:         ## Update dependencies and dump requirements.txt
	pdm update
	pdm export --without-hashes -f requirements --prod -o requirements.txt

demos:          ## Recreate demo projects from templates
	python scripts/demos.py render ${DEMO}
	python scripts/demos.py init ${DEMO}
	make format lint

before_release: ## Prepare for a new release after updating version in pyproject.toml
	make format
	make lint
	make update
	make demos
	make test
	make docs

jsonschemas:    ## Dump config JSON schemas
	python scripts/docs.py dump-jsonschema
	git checkout current schema.json
	mv schema.json schemas/dipdup-2.0.json

##