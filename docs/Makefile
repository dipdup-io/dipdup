FRONT_PATH ?= ../../interface

serve:
	sh -c 'cd ${FRONT_PATH} && npm run dev' & NPM_PID=$$!
	make watch
	kill $$NPM_PID

watch:
	python ../scripts/watch_docs.py --watch ../docs --copy-to ${FRONT_PATH}/content/docs

clean:
	git clean -Xdf
