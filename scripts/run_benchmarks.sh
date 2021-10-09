rm tests/benchmarks/config.latest.json
python tests/benchmarks/config.py -o tests/benchmarks/config.latest.json
python -m pyperf compare_to --table tests/benchmarks/config.json tests/benchmarks/config.latest.json