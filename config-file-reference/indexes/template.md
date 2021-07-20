# template

This index type is used for creating a static template instance.

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

