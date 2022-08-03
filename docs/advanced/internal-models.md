# Internal models

This page describes the internal models used by DipDup. You shouldn't modify data in these models directly.

| model | table | description |
| :--- | :--- | :--- |
| `Model` | N/A | Base class for all models in DipDup project. Provides advanced transaction management. |
| `Schema` | `dipdup_schema` | Hash of database schema to detect changes that require reindexing. |
| `Head` | `dipdup_head` | The latest block received by a datasource from a WebSocket connection. |
| `Index` | `dipdup_index` | Indexing status, level of the latest processed block, template, and template values if applicable. |
| `Contract` | `dipdup_contract` | Nothing useful for us humans. It helps DipDup to keep track of dynamically spawned contracts. |
| `ModelUpdate` | `dipdup_model_update` | Service table to store model diffs for database rollback. |
| `ContractMetadata` | `dipdup_contract_metadata` | See {{ #summary advanced/metadata-interface.md}} |
| `TokenMetadata` | `dipdup_token_metadata` | See {{ #summary advanced/metadata-interface.md}} |

With the help of these tables, you can set up monitoring of DipDup deployment to know when something goes wrong:

```sql
-- This query will return time since the latest block was received by a datasource.
SELECT NOW() - timestamp FROM dipdup_head;
```
