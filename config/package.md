# package

DipDup uses this field to discover the Python package of your project.

```yaml
package: my_indexer_name
```

DipDup will search for a module named `my_module_name` in **`PYTHONPATH`**

This field allows to decouple DipDup configuration file from the indexer implementation and gives more flexibility in managing the source code.

See [4.4. Project structure](../getting-started/project-structure.md) for details.
