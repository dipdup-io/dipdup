# migrate

DipDup is evolving rapidly, and breaking changes are inevitable. When a DipDup release introduces changes that require your attention, [`spec_version`](../config-reference/spec_version.md) field is bumped. You need to perform a project migration if you're getting `MigrationRequiredError` after updating DipDup. To fix imports and type annotations to match current [`spec_version`](../config-reference/spec_version.md), run this command:

```shell
dipdup [-c dipdup.yml] migrate
```

Review and commit changes before proceeding.
