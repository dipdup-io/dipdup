#!/bin/bash

cli_reference=7.reference/16.cli-reference.md
config_reference=7.reference/17.reference.md
context_reference=7.reference/18.context-reference.md

sphinx-build -M html . _build

python dump_references.py _build/html/cli-reference.html $cli_reference
python dump_references.py _build/html/config-reference.html $config_reference
python dump_references.py _build/html/context-reference.html $context_reference