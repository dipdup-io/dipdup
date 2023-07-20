#!/bin/bash

cli_reference=7.reference/1.cli-reference.md
config_reference=7.reference/2.reference.md
context_reference=7.reference/3.context-reference.md
cli_reference_title=cli
config_reference_title=config
context_reference_title=context

sphinx-build -M html . _build

python dump_references.py _build/html/cli-reference.html $cli_reference $cli_reference_title
python dump_references.py _build/html/config-reference.html $config_reference $config_reference_title
python dump_references.py _build/html/context-reference.html $context_reference $context_reference_title