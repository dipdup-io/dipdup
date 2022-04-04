# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

patch:
	cp ../.venv/lib/python3.10/site-packages/sphinx_click/ext.py ../.venv/lib/python3.10/site-packages/sphinx_click/ext.py.bak
	echo "import asyncclick as click" > ../.venv/lib/python3.10/site-packages/sphinx_click/ext.py
	cat ../.venv/lib/python3.10/site-packages/sphinx_click/ext.py.bak | grep -v 'import click' >> ../.venv/lib/python3.10/site-packages/sphinx_click/ext.py

install:
	make html
	tail -n '+33' _build/html/cli-reference.html | head -n '-63' > ../../dipdup-docs/cli/reference.md
	tail -n '+33' _build/html/config-reference.html | head -n '-63' > ../../dipdup-docs/config/reference.md
	cp ../CHANGELOG.md ../../dipdup-docs/release-notes/changelog.md
	cp ../README.md ../../dipdup-docs/README.md
