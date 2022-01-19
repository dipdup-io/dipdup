# init

This command generates type classes and handler templates based on the DipDup configuration file. It's an idempotent command meaning that it won't overwrite previously generated files unless asked explicitly.

```shell
dipdup [-c dipdup.yml] init [--overwrite-types]
```

DipDup will generate all the necessary directories and files inside the project's root. Those include contracts' type definitions and callback stubs to be implemented by the developer. See [4.4. Project structure](../getting-started/project-structure.md) page to learn more about the project structure.

`init` command does not overwrite typeclasses already generated. Use the `--overwrite-types` flag if it's not the desired behavior. Also, you can mark some files as immune from rewriting; see [8.2. Reusing typename for different contracts](../cookbook/reusing-typenames.md).

### Nested packages for hooks and handlers

Callback modules don't have to be in top-level `hooks`/`handlers` directories. Add one or multiple dots to callback name to define nested packages:

```yaml
package: indexer
hooks:
  foo.bar:
    callback: foo.bar
```

After running `init` command, you'll get the following directory tree (shortened for readability):

```
indexer
├── hooks
│   ├── foo
│   │   ├── bar.py
│   │   └── __init__.py
│   └── __init__.py
└── sql
    └── foo
        └── bar
            └── .keep
```

The same rules apply to handler callbacks. Note that `callback` field must be a valid Python package name - lowercase letters, underscores, and dots.
