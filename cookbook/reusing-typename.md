In some cases, you may want to make some manual changes in typeclasses and ensure they won't be lost on init. Let's say you want to reuse typename for multiple contracts providing the same interface (like FA1.2 and FA2 tokens) but having different storage structure. You can comment out differing fields which are not important for your index.

`types/contract_typename/storage.py`

```python
# dipdup: ignore

...

class ContractStorage(BaseModel):
    some_common_big_map: Dict[str, str]
    # unique_big_map_a: Dict[str, str]
    # unique_big_map_b: Dict[str, str]
```

Files starting with `# dipdup: ignore` won't be overwritten on init.


