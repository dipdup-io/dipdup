MARKDOWNLINT_HINT = '<!-- markdownlint-disable first-line-h1 no-space-in-emphasis -->\n'

import subprocess
from pathlib import Path




cli_path, cli_html='docs/7.references/1.cli.md', 'cli-reference.html'
cli_header="""---
title: "CLI"
description: "Command-line interface reference"
---

# CLI reference

"""

config_path, config_html='docs/7.references/2.config.md', 'config-reference.html'
config_header="""---
title: "Config"
description: "Config file reference"
---

# Config reference

"""

context_path, context_html='docs/7.references/3.context.md', 'context-reference.html'
context_header="""---
title: "Context (ctx)"
description: "Context reference"
---

# Context reference

"""

subprocess.run(
    args=('sphinx-build', '-M', 'html', '.', '_build'),
    cwd='docs',
    check=True,
)

for path, html, header in ((cli_path, cli_html, cli_header), (config_path, config_html, config_header), (context_path, context_html, context_header)):
    to = Path(path)
    from_ = Path(f'docs/_build/html/{html}')

    out = '\n'.join(from_.read_text().split('\n')[32:-63])
    if 'config' in str(from_):
        out = out.replace('dipdup.config.', '').replace('dipdup.enums.', '')



    to.write_text(header + MARKDOWNLINT_HINT + out)