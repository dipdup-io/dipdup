# Reusing typename for different contracts

In some cases, you may want to make some manual changes in typeclasses and ensure they won't be lost on init. Let's say you want to reuse typename for multiple contracts providing the same interface (like FA1.2 and FA2 tokens) but having different storage structure. You can comment out differing fields which are not important for your index.

`types/contract_typename/storage.py`

```python
# dipdup: ignore

...

class ContractStorage(BaseModel):
    class Config:
        extra = Extra.ignore

    some_common_big_map: Dict[str, str]
    # unique_big_map_a: Dict[str, str]
    # unique_big_map_b: Dict[str, str]
```

Don't forget `Extra.ignore` Pydantic hint, otherwise indexing will fail. Files starting with `# dipdup: ignore` won't be overwritten on init.


# Processing offchain data

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

# Synchronizing multiple handlers/hooks

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.
