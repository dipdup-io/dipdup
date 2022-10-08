# spec_version

DipDup specification version is used to determine the compatibility of the toolkit and configuration file format and/or features.

```yaml
spec_version: 1.2
```

This table shows which specific SDK releases support which DipDup file versions.

| `spec_version` value | Supported DipDup versions |
| :--- | :--- |
| 0.1 | >=0.0.1, <= 0.4.3 |
| 1.0 | >=1.0.0, <=1.1.2 |
| 1.1 | >=2.0.0, <=2.0.9 |
| 1.2 | >=3.0.0 |

If you're getting `MigrationRequiredError` after updating the framework, run [`dipdup migrate`](../cli-reference.md#migrate) command to perform project migration.
