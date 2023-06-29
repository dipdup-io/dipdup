FRONT_PATH=../../interface

serve:
	sh -c 'cd ${FRONT_PATH} && npm run dev' & NPM_PID=$$!
	python ../scripts/watch_docs.py --watch ../docs --copy-to ${FRONT_PATH}/content/docs
	kill $$NPM_PID

clean:
	git clean -Xdf
