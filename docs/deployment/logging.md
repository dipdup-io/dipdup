# Logging

To control the number of logs DipDup produces, set the `logging` field in config:

```yaml
logging: default|verbose|quiet
```

If you need more fined tuning, perform it in the `on_restart` hook:

```python
import logging

async def on_restart(
    ctx: HookContext,
) -> None:
    logging.getLogger('some_logger').setLevel('DEBUG')
```
