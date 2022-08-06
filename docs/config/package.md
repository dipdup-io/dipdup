# package

DipDup uses this field to discover the Python package of your project.

```yaml
package: my_indexer_name
```

DipDup will search for a module named `my_module_name` in [`PYTHONPATH`](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH)

This field helps to decouple DipDup configuration file from the indexer implementation and gives more flexibility in managing the source code.

See {{ #summary getting-started/project-structure.md}} for details.
