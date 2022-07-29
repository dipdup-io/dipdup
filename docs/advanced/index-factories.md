# Index factories

DipDup allows spawning new indexes from a template in runtime. There are two ways to do that:

* From another index (e.g., handling factory originations)
* In `on_configure` hook (see {{ #summary advanced/event-hooks.md}})

> ⚠ **WARNING**
>
> DipDup is currently not able to automatically generate types and handlers for template indexes unless there is at least one [static instance](../config/indexes/template.md).

DipDup exposes several context methods that extend the current configuration with new contracts and template instances. See {{ #summary advanced/context/README.md}} for details.

See {{ #summary config/templates.md}} for details.
