wc:
	find . -name \*.md -type f -exec wc {} \;

lint:
	markdownlint -f . --disable="MD013"
