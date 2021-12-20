# DipDup

DipDup is a Python framework for building indexers of Tezos smart-contracts. It helps developers focus on the business logic instead of writing data storing and serving boilerplate. DipDup-based indexers are selective, which means only required data is requested. This approach allows to achieve faster indexing times and decreased load on APIs DipDup uses.

## Features

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

## Alternatives

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

||dipdup|dipdup-metadata|dipdup-mempool|dappetizer|tezos-indexer|tzstats|
|-|-|-|-|-|-|-|
|**General**|
|maintainer|Baking Bad|Baking Bad|Baking Bad||Nomadic Labs|Blockwatch Data Inc.|
|kind|selective|selective|selective|selective|full|full|
|language|Python|Go|Go|TypeScript|OCaml|Go|
|supported databases|SQLite, PostgreSQL\*|PostgreSQL\*|PostgreSQL\*|PostgreSQL|PostgreSQL|
|**Requirements**|
|CPU|1 core||||2GHz+, preferably multicore| 2+ cores\*\*\*|
|RAM|256M||||4G (8G recommended) | 4-24G\*\*\*|
|storage|||||50G|22G (17G light mode)\*\*\*|
|**Indexing capabilities**|
|main data source|TzKT|Tezos RPC|Tezos RPC|Tezos RPC|
|user-defined handlers|✅
| typed storage and parameter|✅
| operations|✅|❌|❌
| big map diffs|✅|❌|❌
| head|✅|❌|❌
| blocks|✅|❌|❌||✅
| metadata|❌|✅|❌||✅
| mempool|❌|❌|✅|❌|✅|
|**integrations**|
|Hasura|
|PostgREST|
|Sentry|
|Prometheus|

\* - PostgreSQL-compatible databases like TimescaleDB should work fine too.

\*\* - https://gitlab.com/nomadic-labs/tezos-indexer#hardware-requirements

\*\*\* - https://github.com/blockwatch-cc/tzindex
