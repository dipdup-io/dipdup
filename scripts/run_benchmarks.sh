for i in config index; do
    rm tests/benchmarks/$i.latest.json;
    python tests/benchmarks/$i.py -o tests/benchmarks/$i.latest.json;
    python -m pyperf compare_to --table tests/benchmarks/$i.json tests/benchmarks/$i.latest.json;
done;