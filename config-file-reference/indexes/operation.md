# operation



## Filters

DipDup supports filtering operations by `kind`, `source`_,_ `destination` __\(if applicable\), and `originated_contracts` \(if applicable\).

#### contracts

```yaml
indexes:
  my_index:
    kind: operation
    contracts:
      - contract1
      - contract2
```

In this example DipDup will fetch all the operations where any of source and destination is equal to either _contract1_ or _contract2_ address. `contracts` field is obligatory, there has to be at least one contract alias \(from the [inventory](../contracts.md)\).

#### types

By default DipDup works only with transactions, but you can explicitly list operation types you want to subscribe to \(currently `transaction` and `origination` types are supported\):

```yaml
indexes:
  my_index:
    kind: operation
    contracts:
      - contract1
    types:
      - transaction
      - origination
```

Note, that in case of origination DipDup will query operations where either source or originated contract address is equal to _contract1._

## Handlers



