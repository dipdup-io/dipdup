#$/bin/bash
cd tests/test_dipdup
for name in "asdf" "qwer" "hjkl" "zxcv" "rewq" "hen_subjkt" "kolibri_ovens"
do
    dipdup -c $name.yml init
    mkdir -p types/$name/
    mv $name/types/$name/storage.py types/$name/storage.py
    mv $name/types/$name/parameter/set_delegate.py types/$name/set_delegate.py || true
    rm -r $name
done