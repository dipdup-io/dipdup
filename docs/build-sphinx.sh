#!/bin/bash

cli_reference=7.references/1.cli.md
config_reference=7.references/2.config.md
context_reference=7.references/3.context.md
cli_reference_title="CLI"
config_reference_title="Config"
context_reference_title="Context (ctx)"

sphinx-build -M html . _build

python dump_references.py _build/html/cli-reference.html $cli_reference "$cli_reference_title"
python dump_references.py _build/html/config-reference.html $config_reference "$config_reference_title"
python dump_references.py _build/html/context-reference.html $context_reference "$context_reference_title"