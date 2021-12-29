#$/bin/bash
cd tests/test_dipdup
for name in "asdf" "qwer" "hjkl" "zxcv"
do
    dipdup -c $name.yml init
    mv $name/types/$name/storage.py types/$name/storage.py
    rm -r $name
done