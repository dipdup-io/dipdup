#$/bin/bash
set -e 
set -o pipefail

echo "==> Welcome to the DipDup Installer"
CURR_PWD=`pwd`
DUPDUP_RUN_CACHE_DIR=~/.cache/dipdup_run
mkdir -p $DUPDUP_RUN_CACHE_DIR
cd $DUPDUP_RUN_CACHE_DIR

echo "==> Checking for dependencies"
for dep in python git make poetry; do
    if ! command -v $dep &> /dev/null
    then
        echo "`$dep` not found. Please install it and try again."
        exit
    fi
done

echo "==> Installing cookiecutter"
python -m venv .venv
source .venv/bin/activate
pip install -qU pip
pip install -qU cookiecutter
cd $CURR_PWD

echo "==> Creating DipDup project"
bash -c 'cookiecutter -f https://github.com/dipdup-net/cookiecutter-dipdup'
deactivate

for dir in `ls -d */ | grep -v cookiecutter`; do
    if [[ -f "$dir/dipdup.yml" ]] && [[ ! -f "$dir/poetry.lock" ]]; then
        echo "==> Running initial DipDup setup"
        cd $dir
        git init | sed -e 's/^/> /;'
        make install | sed -e 's/^/> /;'
        echo "==> Verifying DipDup setup"
        make lint | sed -e 's/^/> /;'
        break
    fi
done

echo "==> Cleaning up"
rm -r $DUPDUP_RUN_CACHE_DIR

echo "==> Done! DipDup is ready to use."
