set -e

cd ../dipdup-lts/src

export DIPDUP_TEST=1
export DIPDUP_DEBUG=1

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
    dipdup -c $name migrate

    echo "Verifying $name config"
    dipdup -c $name config export --unsafe
    dipdup -c $name config export --raw

    echo "Verifying $name package"
    DIPDUP_PACKAGE_PATH=$name dipdup -c $name package tree
    # TODO: Reenable after implementing 3.0 spec migration
    # DIPDUP_PACKAGE_PATH=$name dipdup -c $name package verify

done