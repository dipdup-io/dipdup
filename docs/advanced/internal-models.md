# Internal models

<!-- FIXME: missing tables -->
| model | table | description |
| :--- | :--- | :--- |
| `dipdup.models.Schema` | `dipdup_schema` | Hash of database schema to detect changes that require reindexing. |
| `dipdup.models.Index` | `dipdup_index` | Indexing status, level of the latest processed block, template, and template values if applicable. Relates to `Head` when status is `REALTIME` (see `dipdup.models.IndexStatus` for possible values of `status` field) |
| `dipdup.models.Head` | `dipdup_head` | The latest block received by a datasource from a WebSocket connection. |
| `dipdup.models.Contract` | `dipdup_contract` | Nothing useful for us humans. It helps DipDup to keep track of dynamically spawned contracts. A Contract with the same name from the config takes priority over one from this table if {any, exists, provided?}. |

With the help of these tables, you can set up monitoring of DipDup deployment to know when something goes wrong:

```sql
SELECT NOW() - timestamp FROM dipdup_head;
```
