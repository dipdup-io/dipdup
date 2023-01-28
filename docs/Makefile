.ONESHELL:
.PHONY: $(MAKECMDGOALS)

##

help:           ## Show this help (default)
	@grep -F -h "##" $(MAKEFILE_LIST) | grep -F -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

build:
	poetry run sphinx-build -M html . _build

	# FIXME: Using generated Sphinx HTML as a source for mdbook; looks terrible 
	echo '<!-- markdownlint-disable first-line-h1 -->' > cli-reference.md
	echo '<!-- markdownlint-disable first-line-h1 no-space-in-emphasis -->' > config/reference.md
	echo '<!-- markdownlint-disable first-line-h1 -->' > include/context-reference.md
	tail -n '+32' _build/html/cli-reference.html | head -n '-63' >> cli-reference.md
	tail -n '+32' _build/html/config-reference.html | head -n '-63' | sed "s/dipdup.config.//g" | sed "s/dipdup.enums.//g" >> config/reference.md
	tail -n '+32' _build/html/context-reference.html | head -n '-63' >> include/context-reference.md

	mdbook build  --dest-dir=dist/docs

lint: markdownlint orphans

serve:
	make clean build
	mdbook serve

wc:
	find . -name \*.md -type f -exec wc {} \;

markdownlint:
	npx markdownlint-cli -f . --disable line-length --disable no-inline-html

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
		-e "mdbook-admonish" \
		-e "include" \
		| cut -c "3-" | sort -o existing.tmp
	diff --color mentioned.tmp existing.tmp
	rm mentioned.tmp existing.tmp
