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
##-- Dependencies
##

install:        ## Install dependencies
	uv sync --all-extras --all-groups --link-mode symlink --locked

update:         ## Update dependencies and dump requirements.txt
	uv sync -U --all-extras --all-groups --link-mode symlink
	uv export --all-extras --locked --no-group lint --no-group test --no-group docs --no-group perf > requirements.txt


##
##-- CI
##

all:            ## Run an entire CI pipeline
	make format lint test

format:         ## Format with all tools
	ruff format ${SOURCE}

lint:           ## Lint with all tools
	ruff check --fix --unsafe-fixes ${SOURCE}
	mypy ${SOURCE}

test:           ## Run tests
	COVERAGE_CORE=sysmon pytest tests

image:          ## Build Docker image
	docker buildx build . -t ${PACKAGE}:${TAG} --load

##
##-- Docs
##

docs_build: docs
docs:           ## Build docs
	python scripts/docs.py check-links --source docs
	python scripts/docs.py dump-references
	python scripts/docs.py dump-demos
	python scripts/docs.py dump-ref-tables
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

docstrings:     ## Find missing docstrings in public API
	ruff check --select D1 src/dipdup/models/ src/dipdup/config src/dipdup/exceptions src/dipdup/context

##
##-- Release
##

demos:          ## Recreate demo projects from templates
	DIPDUP_NO_SYMLINK=1 python scripts/demos.py render ${DEMO}
	DIPDUP_NO_SYMLINK=1 python scripts/demos.py init ${DEMO}

demos_refresh:  ## Run `init --force` in all demo projects
	for demo in `ls src | grep demo | grep -v etherlink`; do DIPDUP_NO_SYMLINK=1 dipdup -c src/$$demo init --force --no-types; done

before_release: ## Prepare for a new release after updating version in pyproject.toml
	make format lint update demos test docs

jsonschemas:    ## Dump config JSON schemas
	python scripts/docs.py dump-jsonschema

##