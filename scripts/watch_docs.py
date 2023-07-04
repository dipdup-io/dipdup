#!/usr/bin/env python3
import re
import time
from contextlib import suppress
from pathlib import Path
from shutil import rmtree
from subprocess import Popen
from typing import Callable

import click
from watchdog.events import FileSystemEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from dipdup.project import DEFAULT_ANSWERS

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
    ):
        self._source = source
        self._destination = destination
        self._callbacks = callbacks or []

    def on_modified(self, event: FileSystemEvent) -> None:
        src_file = Path(event.src_path).relative_to(self._source)
        if src_file.is_dir():
            return

        # FIXME: front dies otherwise
        if not (src_file.name[0] == '_' or src_file.name[0].isdigit()):
            return

        src_file = self._source / src_file
        dst_file = (self._destination / src_file.relative_to(self._source)).resolve()
        # NOTE: Make sure the destination directory exists
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        print(f'`{src_file}` has been modified; copying to {dst_file}')

        if src_file.suffix in TEXT:
            data = src_file.read_text()
            for callback in self._callbacks:
                data = callback(data)
            dst_file.write_text(data)
        elif src_file.suffix in IMAGES:
            dst_file.write_bytes(src_file.read_bytes())
        else:
            pass


def create_include_callback(source: Path) -> Callable[[str], str]:
    def callback(data: str) -> str:
        def replacer(match: re.Match[str]) -> str:
            # FIXME: Slices are not handled yet
            included_file = source / match.group(1).split(':')[0]
            print(f'reading from {included_file}')
            return included_file.read_text()

        return re.sub(r'{{ #include (.*) }}', replacer, data)

    return callback


def create_project_callback() -> Callable[[str], str]:
    def callback(data: str) -> str:
        for match in re.finditer(r'{{ project.(.*) }}', data):
            key = match.group(1)
            value = DEFAULT_ANSWERS[key]  # type: ignore[literal-required]
            data = data.replace(match.group(0), str(value))
        return data

    return callback


@click.command()
@click.option(
    '--source',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help='docs/ directory path to watch.',
)
@click.option(
    '--destination',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help='content/ dirertory path to copy to.',
)
@click.option(
    '--run',
    is_flag=True,
    help='Run frontend server',
)
def main(source: Path, destination: Path, run: bool) -> None:
    event_handler = DocsBuilder(
        source,
        destination,
        callbacks=[
            create_include_callback(source),
            create_project_callback(),
        ],
    )
    rmtree(destination, ignore_errors=True)
    for path in source.glob('**/*'):
        event_handler.on_modified(FileSystemEvent(path))  # type: ignore[no-untyped-call]

    observer = Observer()
    observer.schedule(event_handler, path=source, recursive=True)  # type: ignore[no-untyped-call]
    observer.start()  # type: ignore[no-untyped-call]

    process = Popen(['npm', 'run', 'dev'], cwd=destination.parent.parent) if run else None
    if process:
        time.sleep(3)
        click.launch('http://localhost:3000/docs')

    with suppress(KeyboardInterrupt):
        while True:
            time.sleep(1)

    observer.stop()  # type: ignore[no-untyped-call]
    observer.join()

    if process:
        process.terminate()


if __name__ == '__main__':
    main()
