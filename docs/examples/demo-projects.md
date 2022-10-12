# Demo projects

<!-- TODO: More demo descriptions -->

The DipDup repository contains several minimal examples of how to use various features for real-case scenarios. Please, do not use these examples in production unmodified. We have not put a production-grade amount of effort into developing them, so they may contain flaws in indexing logic.

Some projects that started as a demo now evolved into full-fledged applications running in production. Check out {{ #summary examples/built-with-dipdup.md }} page.

## TzBTC token

source: [demo_tzbtc](https://github.com/dipdup-net/dipdup/tree/master/src/demo_tzbtc)

The most basic indexer used in Quickstart. A single `operation` index to track balances of TzBTC token holders, nothing else.

## hic et nunc

source: [demo_hic_et_nunc](https://github.com/dipdup-net/dipdup/tree/master/src/demo_hic_et_nunc)

Indexes trades and swaps of "hic et nunc", one of the most popular NFT marketplaces on Tezos.

## Quipuswap

source: [demo_quipuswap](https://github.com/dipdup-net/dipdup/tree/master/src/demo_quipuswap)

Covers all available operations of Quipuswap DEX contracts: trades, transfers, moving liquidity. A more complex example with index templates.

## Homebase RegistryDAO

source: [demo_registrydao](https://github.com/dipdup-net/dipdup/tree/master/src/demo_registrydao)

Homebase enables users to create DAO contracts. In this example indexes are spawned in runtime ({{ #summary advanced/index-factories.md }}) for all contracts having the same script.

## Tezos Domains (`operation`)

source: [demo_domains](https://github.com/dipdup-net/dipdup/tree/master/src/demo_domains)

Tezos Domains is a distributed naming system. You probably have seen those fancy `user.tez` names while browsing explorers. This is a pretty basic example of how to index them.

## Tezos Domains (`big_map`)

source: [demo_domains_big_map](https://github.com/dipdup-net/dipdup/tree/master/src/demo_domains_big_map)

The same as above, but uses `big_map` index instead of `operation` one. The storage structure of this contract is pretty straightforward; we only need to track a single big map. This example contains `skip_history: once` directive to index only the current state of the contract before switching to realtime processing. It allows to speed up indexing even more.

## TzColors

source: [demo_tzcolors](https://github.com/dipdup-net/dipdup/tree/master/src/demo_tzcolors)

A very basic indexer of TzColors NFT token and marketplace. Unlike `hic et nunc` this marketplace provides auction functionality. Other than that, it is pretty much the same.
