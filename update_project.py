#!/usr/bin/env python3
from pathlib import Path

from dipdup.project import DEFAULT_ANSWERS
from dipdup.project import write_project_json

path = Path(__file__).parent.parent / 'docs' / 'project.json'
write_project_json(DEFAULT_ANSWERS, path)
