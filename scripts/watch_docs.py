import json
import re
import sys
import time
from pathlib import Path
from typing import Callable

import click
from watchdog.events import FileSystemEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class DocsUpdateHandler(FileSystemEventHandler):
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
        if event.is_directory:
            return

        src_file = Path(event.src_path).resolve()
        rel_path = src_file.relative_to(self._source.resolve())
        dst_file = self._destination / rel_path
        print(f'`{rel_path}` has been modified; copying to {dst_file}')

        # NOTE: Make sure the destination directory exists
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        data = src_file.read_text()
        for callback in self._callbacks:
            data = callback(data)
        dst_file.write_text(data)


def include_callback(src_file: Path) -> Callable[[str], str]:
    def callback(data: str) -> str:
        def replacer(match: re.Match[str]) -> str:
            include_file = src_file.parent / Path(match.group(1)).relative_to('..')
            with include_file.open() as file:
                return file.read()

        return re.sub(r'{{ #include (.*?) }}', replacer, data)

    return callback


def create_project_version_callback(json_file: Path) -> Callable[[str], str]:
    with json_file.open() as file:
        project_info = json.load(file)

    def callback(data: str) -> str:
        def replacer(match: re.Match[str]) -> str:
            keys = match.group(1).split('.')
            value = project_info
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, '')
                else:
                    return ''
            return str(value)

        # NOTE: Exclude the json_file_name from the matched pattern
        return re.sub(r'{{ \w+?\.(.*?) }}', replacer, data)

    return callback


@click.command()
@click.option(
    '--watch',
    multiple=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help='List of directories to watch.',
)
@click.option(
    '--copy-to',
    multiple=True,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help='List of directories to copy files to.',
)
@click.option(
    '--json',
    default='project.json',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help='JSON file with project information.',
)
def main(watch: list[Path], copy_to: list[Path], json: Path) -> None:
    if len(watch) != len(copy_to):
        print('Error: The number of `watch` and `copy_to` arguments must be the same.')
        sys.exit(1)

    json_path = Path(json)
    project_version_callback = create_project_version_callback(json_path)

    observers = []
    for source, destination in zip(watch, copy_to):
        # NOTE: uncomment when the docs will be fully ready for front copytree(src_path, dst_path, dirs_exist_ok=True)

        event_handler = DocsUpdateHandler(
            source,
            destination,
            callbacks=[
                include_callback(source),
                project_version_callback,
            ],
        )
        observer = Observer()
        observer.schedule(event_handler, path=source, recursive=True)  # type: ignore[no-untyped-call]
        observers.append(observer)
        observer.start()  # type: ignore[no-untyped-call]

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()  # type: ignore

    for observer in observers:
        observer.join()


if __name__ == '__main__':
    main()
