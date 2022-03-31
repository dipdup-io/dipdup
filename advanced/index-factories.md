# Spawning indexes at runtime

DipDup allows spawning new indexes from a template in runtime. There are two ways to do that:

* From another index (e.g., handling factory originations)
* In [`on_configure` hook](../cli-reference/dipdup-run.md#custom-initialization)

> ⚠ **WARNING**
>
> DipDup is currently not able to automatically generate types and handlers for template indexes unless there is at least one [static instance](indexes/template.md).

DipDup exposes several context methods that extend the current configuration with new contracts and template instances. See [5.8. Handler context](../advanced/handler-context.md) for details.

See [12.13. templates](../config-reference/templates.md) for details.
