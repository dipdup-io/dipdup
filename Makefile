wc:
	find . -name \*.md -type f -exec wc {} \;

lint:
	markdownlint -f . --disable="MD013"

orphans:
	cat SUMMARY.md| grep ".md" | cut -f2 -d"(" | cut -f1 -d")" | sort > mentioned.tmp
	find . | grep ".md" | cut -c "3-" | sort > existing.tmp                          
	diff existing.tmp mentioned.tmp                                                  