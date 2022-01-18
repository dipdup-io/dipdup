#$/bin/bash
cd tests/test_dipdup
for name in "asdf" "qwer" "hjkl" "zxcv" "rewq" "hen_subjkt" "kolibri_ovens" "yupana"
do
    dipdup -c $name.yml init --keep-schemas
    mkdir -p types/$name/
    mkdir -p schemas/$name/
    mv $name/types/$name/storage.py types/$name/storage.py
    touch types/$name/__init__.py
    mv $name/schemas/$name/storage.json schemas/$name/storage.json
    mv $name/types/$name/parameter/set_delegate.py types/$name/set_delegate.py || true
    rm -r $name
done