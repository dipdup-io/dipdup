SHELL=/usr/bin/zsh
DEMO=demo_evm_events

run_in_memory:
	time dipdup -c ../src/${DEMO} -c ./oneshot_${DEMO}.yaml run

run_in_postgres:
	touch ../src/${DEMO}/deploy/.env && \
		echo "HASURA_SECRET=test" > ../src/${DEMO}/deploy/.env && \
		echo "POSTGRES_PASSWORD=test" >> ../src/${DEMO}/deploy/.env && \
		cd ../src/${DEMO}/deploy && docker-compose --env-file .env up -d db

	export POSTGRES_PORT=`docker port ${DEMO}-db-1 5432 | cut -d: -f2` && \
		time dipdup -c ../src/${DEMO} -c ./oneshot_${DEMO}.yaml -c ./local_postgres.yaml run

down:
	cd ../src/${DEMO}/deploy && docker-compose down && rm .env
	docker volume rm -f ${DEMO}_db

cpu_up:
	echo 1 | sudo tee /sys/devices/system/cpu/cpufreq/boost
	sudo cpupower frequency-set -g performance

cpu_down:
	echo 0 | sudo tee /sys/devices/system/cpu/cpufreq/boost
	sudo cpupower frequency-set -g schedutil

shortstat:
	dipdup report show latest | grep -e levels_nonempty: -e time_passed: