#$/bin/bash
cd tests/test_dipdup
for name in "asdf" "qwer" "hjkl" "zxcv" "rewq" "hen_subjkt"
do
    dipdup -c $name.yml init
    mkdir -p types/$name/
    mv $name/types/$name/storage.py types/$name/storage.py
    rm -r $name
done