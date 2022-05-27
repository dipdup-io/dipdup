# config export

Print config after resolving all links and variables.

```shell
dipdup config export [--unsafe]
```

Add `--unsafe` option to substitute environment variables. Otherwise, default values from config will be used.

> ⚠ **WARNING**
>
> Avoid sharing `config export --unsafe` output with 3rd-parties as it may contain secrets.
