---
description: Jobs block
---

# jobs

In addition to indexing DipDup allows you to execute arbitrary tasks according to schedule. 

```text
jobs:
  midnight_cleanup:
    callback: cleanup_database
    crontab: "0 0 * * *"
    args:
      foo: bar 
    atomic: True
```

Run `dipdup init` after defining jobs in config to generate placeholders in `jobs` directory of your project.

When `atomic` argument is set job will be wrapped in SQL transaction and rolled back in case of failure.

If you're not familiar with crontab syntax there's an online service [crontab.guru](https://crontab.guru) to help you to compose desired expression. 

