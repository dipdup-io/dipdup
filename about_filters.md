## Matching originations

| name                            | description                                                                                                                            | supported | typed |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |:---------:|:-----:|
| `originated_contract.address`   | Origination of exact contract.                                                                                                         |     ✅     |   ✅   |
| `originated_contract.code_hash` | Originations of all contracts having the same code.                                                                                    |     ✅     |   ✅   |
| `source.address`                | Special cases only. This filter is very slow and doesn't support strict typing. Usually, `originated_contract.code_hash` suits better. |     ⚠     |   ❌   |
| `source.code_hash`              | Currently not supported.                                                                                                               |     ❌     |   ❌   |
| `similar_to.address`            | Compatibility alias to `originated_contract.code_hash`. Can be removed some day.                                                       |     ➡️    |   ➡️  |
| `similar_to.code_hash`          | Compatibility alias to `originated_contract.code_hash`. Can be removed some day.                                                       |     ➡️    |   ➡️  |

## Matching operations

| name                     | description | supported | typed |
| ------------------------ | ----------- |:---------:|:-----:|
| `source.address`         |             |     ✅     |  N/A  |
| `source.code_hash`       |             |     ✅     |  N/A  |
| `destination.address`    |             |     ✅     |   ✅   |
| `destination.code_hash`  |             |     ✅     |   ✅   |
| `destination.entrypoint` |             |     ✅     |   ✅   |
