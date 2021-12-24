# init

This command generates type classes and handler templates based on the DipDup configuration file. It's an idempotent command meaning that it won't overwrite previously generated files unless asked explicitly.

```shell
dipdup [-c dipdup.yml] init [--overwrite-types]
```

DipDup will generate all the necessary directories and files inside the project's root. Those include contracts' type definitions and callback stubs to be implemented by the developer. See [4.4. Project structure](../getting-started/project-structure.md) page to learn more about the project structure.

`init` command does not overwrite typeclasses already generated. Use the `--overwrite-types` flag if it's not the desired behavior. Also, you can mark some files as immune from rewriting; see [8.2. Reusing typename for different contracts](../cookbook/reusing-typenames.md).
