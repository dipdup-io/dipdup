#!/usr/bin/env python3
#
# 🧙 Greetings, traveler!
#
# Why are you here?.. Wait, let me guess! You're a DipDup maintainer, something has broken in CI, and you have no idea how the docs are
# built, right? Good news: everything related to building, formatting and linting documentation is in this file. Bad news: we do everything
# with custom scripts, and it's DOOM on Nightmare. There are comments where possible tho. Read them carefully and you'll be fine.
#
# To run `build --serve` command you need to clone and install frontend from private `dipdup-io/interface` repo first.
#
import importlib
import logging
import re
import subprocess
import time
from collections.abc import Callable
from collections.abc import Iterator
from contextlib import ExitStack
from contextlib import contextmanager
from contextlib import suppress
from pathlib import Path
from shutil import rmtree
from subprocess import Popen
from typing import Any
from typing import TypedDict

import click
import orjson
from watchdog.events import EVENT_TYPE_CREATED
from watchdog.events import EVENT_TYPE_DELETED
from watchdog.events import EVENT_TYPE_MODIFIED
from watchdog.events import EVENT_TYPE_MOVED
from watchdog.events import FileModifiedEvent
from watchdog.events import FileSystemEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from dipdup.cli import green_echo
from dipdup.cli import red_echo
from dipdup.config import DipDupConfig
from dipdup.project import get_default_answers
from dipdup.sys import set_up_logging

_logger = logging.getLogger(__name__)


class ReferencePage(TypedDict):
    title: str
    description: str
    h1: str
    md_path: str
    html_path: str


REFERENCE_MARKDOWNLINT_HINT = (
    '<!-- markdownlint-disable first-line-h1 no-space-in-emphasis no-inline-html no-multiple-blanks -->\n'
)
REFERENCE_STRIP_HEAD_LINES = 32
REFERENCE_STRIP_TAIL_LINES = 63
REFERENCE_HEADER_TEMPLATE = """---
title: "{title}"
description: "{description}"
---

# {h1}

"""
REFERENCES: tuple[ReferencePage, ...] = (
    ReferencePage(
        title='CLI',
        description='Command-line interface reference',
        h1='CLI reference',
        md_path='docs/7.references/1.cli.md',
        html_path='cli-reference.html',
    ),
    ReferencePage(
        title='Config',
        description='Config file reference',
        h1='Config reference',
        md_path='docs/7.references/2.config.md',
        html_path='config-reference.html',
    ),
    ReferencePage(
        title='Context (ctx)',
        description='Context reference',
        h1='Context reference',
        md_path='docs/7.references/3.context.md',
        html_path='context-reference.html',
    ),
)


# {{ #include ../LICENSE }}
INCLUDE_REGEX = r'{{ #include (.*) }}'

# {{ project.package }}
PROJECT_REGEX = r'{{ project.([a-zA-Z_0-9]*) }}'

# [DipDup](https://dipdup.io)
MD_LINK_REGEX = r'\[.*\]\(([0-9a-zA-Z\.\-\_\/\#\:\/\=\?]*)\)'

# ## Title
MD_HEADING_REGEX = r'\#\#* [\w ]*'

# class AbiDatasourceConfig(DatasourceConfig):
CONFIG_CLASS_REGEX = r'class (.*Config)[:\(].*'

TEXT_EXTENSIONS = (
    '.md',
    '.yml',
    '.yaml',
)
IMAGE_EXTENSIONS = (
    '.svg',
    '.png',
    '.jpg',
)

# Global markdownlint ignore list. We have to duplicate H1's due to how our NextJS frontend works.
MARKDOWNLINT_IGNORE = (
    'line-length',
    'single-title',
    'single-h1',
)


class DocsBuilder(FileSystemEventHandler):
    def __init__(
        self,
        source: Path,
        destination: Path,
        callbacks: list[Callable[[str], str]] | None = None,
    ) -> None:
        self._source = source
        self._destination = destination
        self._callbacks = callbacks or []

    def on_rst_modified(self) -> None:
        subprocess.run(
            ('python3', 'scripts/docs.py', 'dump-references'),
            check=True,
        )

    def on_modified(self, event: FileSystemEvent, with_rst: bool = True) -> None:
        src_file = Path(event.src_path).relative_to(self._source)
        if src_file.is_dir():
            return

        # NOTE: Sphinx autodoc reference; rebuild HTML
        if src_file.name.endswith('.rst'):
            if with_rst:
                self.on_rst_modified()
            return

        # FIXME: Frontend dies otherwise
        if not (src_file.name[0] == '_' or src_file.name[0].isdigit()):
            return

        if event.event_type == EVENT_TYPE_DELETED:
            dst_file = (self._destination / src_file.relative_to(self._source)).resolve()
            dst_file.unlink(True)
            return

        if event.event_type not in (EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED, EVENT_TYPE_MOVED):
            return

        src_file = self._source / src_file
        dst_file = (self._destination / src_file.relative_to(self._source)).resolve()
        # NOTE: Make sure the destination directory exists
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        _logger.info('`%s` has been %s; copying', src_file, event.event_type)

        try:
            if src_file.suffix in TEXT_EXTENSIONS:
                data = src_file.read_text()
                for callback in self._callbacks:
                    data = callback(data)
                dst_file.write_text(data)
            elif src_file.suffix in IMAGE_EXTENSIONS:
                dst_file.write_bytes(src_file.read_bytes())
            else:
                pass
        except Exception as e:
            _logger.error('Failed to copy %s: %s', src_file.name, e)


def create_include_callback(source: Path) -> Callable[[str], str]:
    def callback(data: str) -> str:
        def replacer(match: re.Match[str]) -> str:
            # FIXME: Slices are not handled yet
            included_file = source / match.group(1).split(':')[0]
            _logger.info('including `%s`', included_file.name)
            return included_file.read_text()

        return re.sub(INCLUDE_REGEX, replacer, data)

    return callback


def create_project_callback() -> Callable[[str], str]:
    answers = get_default_answers()

    def callback(data: str) -> str:
        for match in re.finditer(PROJECT_REGEX, data):
            key = match.group(1)
            value = answers[key]  # type: ignore[literal-required]
            data = data.replace(match.group(0), str(value))
        return data

    return callback


@contextmanager
def observer(path: Path, handler: Any) -> Iterator[BaseObserver]:
    observer = Observer()
    observer.schedule(handler, path=path, recursive=True)  # type: ignore[no-untyped-call]
    observer.start()  # type: ignore[no-untyped-call]

    yield observer

    observer.stop()  # type: ignore[no-untyped-call]
    observer.join()


@contextmanager
def frontend(path: Path) -> Iterator[Popen[Any]]:
    # NOTE: pnpm is important! Regular npm fails to resolve deps.
    process = Popen(['pnpm', 'run', 'dev'], cwd=path)
    time.sleep(3)
    click.launch('http://localhost:3000/docs')

    yield process

    process.terminate()


@click.group(help='Various tools to build and maintain DipDup documentation. Read the script source!')
def main() -> None:
    set_up_logging()


@main.command('build', help='Build and optionally serve docs')
@click.option(
    '--source',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True, path_type=Path),
    help='docs/ directory path to watch.',
)
@click.option(
    '--destination',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help='content/ dirertory path to copy to.',
)
@click.option(
    '--watch',
    is_flag=True,
    help='Watch for changes.',
)
@click.option(
    '--serve',
    is_flag=True,
    help='Start frontend.',
)
def build(source: Path, destination: Path, watch: bool, serve: bool) -> None:
    green_echo('=> Building docs')
    rmtree(destination, ignore_errors=True)

    event_handler = DocsBuilder(
        source,
        destination,
        callbacks=[
            create_include_callback(source),
            create_project_callback(),
        ],
    )
    event_handler.on_rst_modified()
    for path in source.glob('**/*'):
        event_handler.on_modified(FileModifiedEvent(path), with_rst=False)  # type: ignore[no-untyped-call]

    if not (watch or serve):
        return

    with ExitStack() as stack:
        if watch:
            green_echo('=> Watching for changes')
            stack.enter_context(observer(source, event_handler))
        if serve:
            green_echo('=> Starting frontend')
            stack.enter_context(frontend(destination.parent.parent))

        stack.enter_context(suppress(KeyboardInterrupt))
        while True:
            time.sleep(1)


@main.command('check-links', help='Check relative links in docs')
@click.option(
    '--source',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True, path_type=Path),
    help='docs/ directory path to check.',
    default='docs',
)
@click.option('--http', is_flag=True, help='Check HTTP links too.')
def check_links(source: Path, http: bool) -> None:
    green_echo('=> Checking relative links')
    files, links, bad_paths, bad_anchors, bad_http = 0, 0, 0, 0, 0
    http_links: set[str] = set()

    for path in source.rglob('*.md'):
        _logger.info('checking file `%s`', path)
        files += 1
        data = path.read_text()
        for match in re.finditer(MD_LINK_REGEX, data):
            links += 1
            link = match.group(1)

            if link.startswith('http'):
                http_links.add(link)
                continue

            link, anchor = link.split('#') if '#' in link else (link, None)

            full_path = path.parent.joinpath(link)
            if not full_path.exists():
                logging.error('broken link: `%s`', full_path)
                bad_paths += 1
                continue

            if anchor:
                target = full_path.read_text() if link else data

                for match in re.finditer(MD_HEADING_REGEX, target):
                    header = match.group(0).lower().replace(' ', '-').strip('#-')
                    if header == anchor.lower():
                        break
                else:
                    logging.error('broken anchor: `%s#%s`', link, anchor)
                    bad_anchors += 1
                    continue

    if http:
        green_echo('=> Checking HTTP links')

        for link in http_links:
            green_echo(f'checking link `{link}`')
            try:
                res = subprocess.run(
                    ('curl', '-s', '-L', '-o', '/dev/null', '-w', '%{http_code}', link),
                    check=True,
                    capture_output=True,
                )
                status_code = int(res.stdout.decode().strip())
                if status_code != 200:
                    raise subprocess.CalledProcessError(status_code, 'curl')
            except subprocess.CalledProcessError:
                red_echo(f'broken http link: `{status_code}`')
                bad_http += 1

    _logger.info('_' * 80)
    _logger.info('checked %d files and %d links:', files, links)
    _logger.info('paths: %d bad links, %d bad anchors', bad_paths, bad_anchors)
    _logger.info('http: %d bad links', bad_http)

    if bad_paths or bad_anchors or bad_http:
        red_echo('=> Fix broken links and try again')
        exit(1)


@main.command('dump-jsonschema', help='Dump config JSON schema to schema.json')
def dump_jsonschema() -> None:
    green_echo('=> Dumping JSON schema')

    dc_schema = importlib.import_module('dc_schema')
    schema_dict = dc_schema.get_schema(DipDupConfig)

    # NOTE: EVM addresses correctly parsed by Pydantic even if specified as integers
    schema_dict['$defs']['EvmContractConfig']['properties']['address']['anyOf'] = [
        {'type': 'integer'},
        {'type': 'string'},
        {'type': 'null'},
    ]

    # NOTE: Environment configs don't have package/spec_version fields, but can't be loaded directly anyway.
    schema_dict['required'] = []

    # NOTE: Dump to the project root
    schema_path = Path(__file__).parent.parent / 'schema.json'
    schema_path.write_bytes(orjson.dumps(schema_dict, option=orjson.OPT_INDENT_2))


@main.command('dump-references', help='Dump Sphinx references to ugly Markdown files')
def dump_references() -> None:
    green_echo('=> Dumping Sphinx references')
    config_rst = Path('docs/config-reference.rst').read_text().splitlines()
    classes_in_rst = {line.split('.')[-1] for line in config_rst if line.startswith('.. autoclass::')}
    classes_in_config = set()
    for file in Path('src/dipdup/config').glob('*.py'):
        for match in re.finditer(CONFIG_CLASS_REGEX, file.read_text()):
            classes_in_config.add(match.group(1))

    green_echo('=> Verifying that config reference is up to date')
    diff = classes_in_config - classes_in_rst
    diff -= {'Config'}
    if diff:
        red_echo('=> Config reference is outdated! Update `docs/config-reference.rst` and try again.')
        red_echo(f'=> Missing classes: {diff}')
        exit(1)

    green_echo('=> Building Sphinx docs')
    subprocess.run(
        args=('sphinx-build', '-M', 'html', '.', '_build'),
        cwd='docs',
        check=True,
    )

    green_echo('=> Converting to ugly Markdown files')
    for page in REFERENCES:
        to = Path(page['md_path'])
        from_ = Path(f"docs/_build/html/{page['html_path']}")

        # NOTE: Strip HTML boilerplate
        out = '\n'.join(from_.read_text().split('\n')[REFERENCE_STRIP_HEAD_LINES:-REFERENCE_STRIP_TAIL_LINES])

        header = REFERENCE_HEADER_TEMPLATE.format(**page)
        to.write_text(header + REFERENCE_MARKDOWNLINT_HINT + out)


@main.command('markdownlint', help='Lint Markdown files')
def markdownlint() -> None:
    green_echo('=> Running markdownlint')
    try:
        subprocess.run(
            ('markdownlint', '--disable', *MARKDOWNLINT_IGNORE, '--', 'docs'),
            check=True,
        )
    except subprocess.CalledProcessError:
        red_echo('=> Fix markdownlint errors and try again')
        exit(1)


if __name__ == '__main__':
    main()
