#$/bin/bash
export PYTHONPATH=src:$PYTHONPATH
for name in `ls src | grep demo`
do
    dipdup -c src/$name/dipdup.yml init --overwrite-types
    for file in "Dockerfile" "docker-compose.yml" ".dockerignore" "dipdup.dev.yml" "dipdup.prod.yml"
    do
        cat cookiecutter/root/$file | python docs/mdbook-cookiecutter > src/$name/$file
    done
done