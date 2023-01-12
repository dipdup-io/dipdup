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

docs:
	poetry run make html

	# FIXME: Using generated Sphinx HTML as a source for mdbook; looks terrible 
	echo '<!-- markdownlint-disable first-line-h1 -->' > cli-reference.md
	echo '<!-- markdownlint-disable first-line-h1 no-space-in-emphasis -->' > config/reference.md
	echo '<!-- markdownlint-disable first-line-h1 -->' > include/context-reference.md
	tail -n '+35' _build/html/cli-reference.html | head -n '-63' >> cli-reference.md
	tail -n '+35' _build/html/config-reference.html | head -n '-63' >> config/reference.md
	tail -n '+35' _build/html/context-reference.html | head -n '-63' >> include/context-reference.md

	mdbook build  --dest-dir=dist/docs

homepage:
	npm i
	npm run build

serve:
	mdbook serve -o

wc:
	find . -name \*.md -type f -exec wc {} \;

markdownlint:
	markdownlint -f . --disable line-length --disable no-inline-html

clean:
	git clean -Xdf

orphans:
	cat SUMMARY.md | grep ".md" > mentioned.tmp
	sed -i -E 's@^.*\[(.*)\]\((.*)\).*$$@\2@p' mentioned.tmp
	cat mentioned.tmp | uniq | sort -o mentioned.tmp
	find . | grep ".md" | grep -v \
		-e "node_modules/" \
		-e " book/" \
		-e "placeholders.md" \
		-e "SUMMARY.md" \
		-e "mdbook-summary" \
		-e "mdbook-cookiecutter" \
		-e "include" \
		| cut -c "3-" | sort -o existing.tmp
	diff --color mentioned.tmp existing.tmp
	rm mentioned.tmp existing.tmp
