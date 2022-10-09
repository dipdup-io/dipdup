# spec_version

The DipDup specification version defines the format of the configuration file and available features.

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

If you're getting `MigrationRequiredError` after updating the framework, run the `dipdup migrate` command to perform project migration.

At the moment, `spec_version` has not changed for a very long time. Consider recreating the package from scratch and migrating logic manually if you have another value in your configuration file.
