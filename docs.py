#!/usr/bin/env python3
import logging
import re
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

import click
from watchdog.events import EVENT_TYPE_CREATED
from watchdog.events import EVENT_TYPE_DELETED
from watchdog.events import EVENT_TYPE_MODIFIED
from watchdog.events import EVENT_TYPE_MOVED
from watchdog.events import FileModifiedEvent
from watchdog.events import FileSystemEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from dipdup.project import get_default_answers

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')
_logger = logging.getLogger()

INCLUDE_REGEX = r'{{ #include (.*) }}'
PROJECT_REGEX = r'{{ project.([a-zA-Z_0-9]*) }}'

TEXT = (
    '.md',
    '.yml',
    '.yaml',
)
IMAGES = (
    '.svg',
    '.png',
    '.jpg',
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

    def on_modified(self, event: FileSystemEvent) -> None:
        src_file = Path(event.src_path).relative_to(self._source)
        if src_file.is_dir():
            return

        # NOTE: Sphinx autodoc reference
        if src_file.name.endswith('.rst'):
            Popen(['python3', 'scripts/dump_references.py']).wait()
            return

        # FIXME: front dies otherwise
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
            if src_file.suffix in TEXT:
                data = src_file.read_text()
                for callback in self._callbacks:
                    data = callback(data)
                dst_file.write_text(data)
            elif src_file.suffix in IMAGES:
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


@click.command()
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
def main(source: Path, destination: Path, watch: bool, serve: bool) -> None:
    # TODO: ask before rm -rf, include relative to file not folder, check all relative links are valid
    rmtree(destination, ignore_errors=True)

    event_handler = DocsBuilder(
        source,
        destination,
        callbacks=[
            create_include_callback(source),
            create_project_callback(),
        ],
    )
    for path in source.glob('**/*'):
        event_handler.on_modified(FileModifiedEvent(path))  # type: ignore[no-untyped-call]

    if not (watch or serve):
        return

    with ExitStack() as stack:
        if watch:
            stack.enter_context(observer(source, event_handler))
        if serve:
            stack.enter_context(frontend(destination.parent.parent))

        stack.enter_context(suppress(KeyboardInterrupt))
        while True:
            time.sleep(1)


if __name__ == '__main__':
    main()
