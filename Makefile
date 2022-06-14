## DEV=1                Whether to install dev dependencies
DEV=1

install:        ## Install project dependencies
	poetry install \
	`if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`
