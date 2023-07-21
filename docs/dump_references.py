MARKDOWNLINT_HINT = '<!-- markdownlint-disable first-line-h1 no-space-in-emphasis -->\n'

import sys
from pathlib import Path

args = sys.argv[1:]
from_, to = Path(args[0]), Path(args[1])
out = '\n'.join(from_.read_text().split('\n')[32:-63])
if 'config' in str(from_):
    out = out.replace('dipdup.config.', '').replace('dipdup.enums.', '')

head = f"""---
title: {args[2]}
---
"""

to.write_text(head + MARKDOWNLINT_HINT + out)