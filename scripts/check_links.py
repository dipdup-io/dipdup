#!/usr/bin/env python3
import logging
from pathlib import Path
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

MD_LINK_REGEX = r'\[.*\]\(([0-9a-zA-Z\.\-\_\/\#\:\/\=\?]*)\)'
ANCHOR_REGEX = r'\#\#* [\w ]*'

files, links, http_links, bad_links, bad_anchors = 0, 0, 0, 0, 0

for path in Path('docs').rglob('*.md'):
    logging.info('checking file `%s`', path)
    files += 1
    data = path.read_text()
    for match in re.finditer(MD_LINK_REGEX, data):
        links += 1
        link = match.group(1)
        if link.startswith('http'):
            http_links += 1
            continue

        link, anchor = link.split('#') if '#' in link else (link, None)

        full_path = path.parent.joinpath(link)
        if not full_path.exists():
            logging.error('broken link: `%s`', full_path)
            bad_links += 1
            continue

        if anchor:
            target = full_path.read_text() if link else data

            for match in re.finditer(ANCHOR_REGEX, target):
                header = match.group(0).lower().replace(' ', '-').strip('#-')
                if header == anchor.lower():
                    break
            else:
                logging.error('broken anchor: `%s#%s`', link, anchor)
                bad_anchors += 1
                continue

logging.info('_' * 80)
logging.info('checked %d files and %d links:', files, links)
logging.info('%d URLs, %d bad links, %d bad anchors', http_links, bad_links, bad_anchors)