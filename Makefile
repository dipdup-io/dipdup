serve:
	mdbook serve -o

wc:
	find . -name \*.md -type f -exec wc {} \;

lint:
	markdownlint -f . --disable=MD013 --disable=MD033

orphans:
	cat SUMMARY.md | grep ".md" | cut -f2 -d"(" | cut -f1 -d")" | sort > mentioned.tmp
	find . | grep ".md" | cut -c "3-" | sort > existing.tmp
	diff --color mentioned.tmp existing.tmp