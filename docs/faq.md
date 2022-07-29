# F.A.Q

## How to index different contracts that share the same interface?

Multiple contracts can provide the same interface (like FA1.2 and FA2 standard tokens) but have a different storage structure. If you try to use the same typename for them, indexing will fail. However, you can modify typeclasses manually. Modify `types/<typename>/storage.py` file and comment out unique fields that are not important for your index:

```python
# dipdup: ignore

...

class ContractStorage(BaseModel):
    class Config:
        extra = Extra.ignore

    common_ledger: Dict[str, str]
    # unique_field_foo: str
    # unique_field_bar: str
```

Note the `# dipdup: ignore` comment on the first line. It tells DipDup not to overwrite this file on `init --overwrite-types` command.

Don't forget `Extra.ignore` Pydantic hint, otherwise, storage deserialization will fail.

## What is the correct way to process off-chain data?

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

## One of my indexes depends on another one's indexed data. How to process them in a specific order?

Indexes of all kinds are fully independent. They are processed in parallel, have their message queues and don't share any state. It is one of the essential DipDup concepts, so there's no "official" way to manage the order of indexing.

Avoid waiting for sync primitives like `asyncio.Event` or `asyncio.Lock` in handlers. Indexing will be stuck forever waiting for the database transaction to complete.

Instead, save raw data in handlers and process it later with hooks when all conditions are met. For example, process data batch only when all indexes in the `dipdup_index` table have reached a specific level.
