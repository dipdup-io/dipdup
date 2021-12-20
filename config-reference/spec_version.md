# spec\_version

DipDup specification version is used to determine the compatibility of the toolkit and configuration file format and/or features.

```yaml
spec_version: 1.2
```

This table shows which DipDup file versions are supported by specific SDK releases.

| `spec_version` value | Supported DipDup versions |
| :--- | :--- |
| 0.1 | &gt;=0.0.1, &lt;= 0.4.3 |
| 1.0 | &gt;=1.0.0, &lt;=1.1.2 |
| 1.1 | &gt;=2.0.0, &lt;=2.0.9 |
| 1.2 | &gt;=3.0.0 |

If you're getting `MigrationRequiredError` after updating the framework, run [`dipdup migrate`](../cli-reference/migrate.md) command to perform project migration.
