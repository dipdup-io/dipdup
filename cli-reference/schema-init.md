# schema init

Prepare a database for running DipDip. This command will create tables based on your models, then call `on_reindex` SQL hook to finish preparation - the same things DipDup does when run on a clean database.

```shell
dipdup schema init
```
