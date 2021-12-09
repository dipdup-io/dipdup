---
description: Header block
---

# package

This is a language-specific field used by the DipDup CLI tool to discover your implementation files.

```yaml
package: my_indexer_name
```

{% tabs %}
{% tab title="Python" %}
DipDup will search for a module named `my_module_name` in **`PYTHONPATH`**
{% endtab %}
{% endtabs %}

This allows to decouple DipDup configuration file from the indexer implementation and gives more flexibility in managing the source code.

## Package structure

DipDup expects a certain folder structure of the package — this is a framework requirement.

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

