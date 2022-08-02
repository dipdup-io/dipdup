# Troubleshooting

This page contains tips for troubleshooting DipDup projects.

## Update DipDup to the latest version

DipDup framework evolves rapidly just like Tezos itself does. We recommend keeping your project up-to-date with the latest version of DipDup.

If you're using Poetry, set caret version constraint in `pyproject.toml` to use the latest release of the current major version:

```toml
[tool.poetry.dependencies]
dipdup = "^6.0.0"
```

Run `poetry update dipdup` periodically to update to the latest version.

While building Docker images you can use `X` and `X.Y` tags to lock to specific major/minor releases:

```Dockerfile
FROM dipdup/dipdup:6.0
```

## Ensure that config is correct

DipDup config can be correct syntactically but not necessarily semantically. It's especially easy to make a mistake when actively using templates and environment variables. Use `config export` command to dump config the way DipDup "sees" it, after resolving all links and templates. `config env` command can help you to find missing environment variables.

```shell
dipdup -c dipdup.yml -c dipdup.prod.yml config export
dipdup -c dipdup.yml -c dipdup.prod.yml config env
```

> 💡 **SEE ALSO**
>
> * {{ #summary cli-reference.md#dipdup-config-export }}
> * {{ #summary cli-reference.md#dipdup-config-env }}
> * {{ #summary config/README.md }}

## Enable debug logging and crash reporting

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

## Use linters to find errors in your Python code

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

## Explore contract calls in Better Call Dev

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

## Got stuck? Ask for help

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.
