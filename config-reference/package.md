# package

DipDup uses this field to discover the Python package of your project.

```yaml
package: my_indexer_name
```

DipDup will search for a module named `my_module_name` in **`PYTHONPATH`**

This field allows to decouple DipDup configuration file from the indexer implementation and gives more flexibility in managing the source code.

## Package structure

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

DipDup expects an exact structure of the package — this is a framework requirement.

```bash
my_module_name/
├── models.*
├── handlers
│   ├── hander_1.*
│   ├── hander_n.*
│   └── on_rollback.*
└── types
    ├── contract_1_typename
    │   ├── storage.*
    │   └── parameter
    │       └── entrypoint_1.*
    │       └── entrypoint_n.*
    └── contract_n_typename
        ├── storage.*
        └── parameter
            └── entrypoint_1.*
            └── entrypoint_n.*
```

You don't have to create this hierarchy yourself — all the folders and most files are generated automatically by the CLI.

`*` — is an according file extension \(_py_, _ts_, etc\)
