set -e

cd ../dipdup-lts/src

if ! git diff --quiet; then
    echo "Git is not clean, please commit your changes before running this script"
    exit 1
fi

for name in $(ls); do
    if [ $name == "dipdup" ]; then
        continue
    fi
    if [ $name == "demo_blank" ]; then
        continue
    fi

    echo "Checkout to current"
    git checkout current $name

    echo "Migrating $name"
    DIPDUP_TEST=1 dipdup -c $name migrate

    echo "Verifying $name"
    DIPDUP_TEST=1 dipdup -c $name package tree

done