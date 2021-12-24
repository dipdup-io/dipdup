# Common issues

## `MigrationRequiredError`

### Reason

DipDup was updated to release which `spec_version` differs from the value in the config file. You need to perform an automatic migration before starting indexing again.

### Solution

  1. Run [`dipdup migrate`](../cli-reference/migrate.md) command.
  2. Review and commit changes.
