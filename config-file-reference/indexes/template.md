# template

This index type is used for creating a template instance.

```yaml
indexes:
  my_index:
    template: my_template
    values:
      placeholder1: value1
      placeholder2: value2
```

For a static template instance \(specified in the DipDup config\) there are two fields:

* `template` — template name \(from [templates](../templates.md) section\)
* `values` — concrete values for each [placeholder](../templates.md#placeholders) used in a chosen template

## Similar contracts

Sometimes it's not possible to list all the contracts in advance, e.g. you need to handle all new contract deployments. DipDup can automatically create indexes for each new contract having the same parameter and storage types as the reference one.

```yaml
indexes:
  my_index:
    template: my_template
    similar_to: contract1
```

**NOTE** that in this case _my\_template_ MUST have only one placeholder `<contract>` which will be filled with the originated contract address.

