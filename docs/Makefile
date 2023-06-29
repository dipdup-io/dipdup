ifndef FRONTPATH
export FRONTPATH = ../../interface
endif

serve:
	python ../scripts/watch_docs.py --watch ../docs --copyto $(FRONTPATH)/content/docs &
	cd $(FRONTPATH) && npm run dev

clean:
	git clean -Xdf
