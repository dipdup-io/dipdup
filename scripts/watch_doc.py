import json
import time
from pathlib import Path
from typing import Callable, Optional, List
import re
import sys

import click
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class MyHandler(FileSystemEventHandler):
    def __init__(self, src_folder: Path, dst_folder: Path, callbacks: Optional[List[Callable[[str], str]]] = None):
        self.src_folder = src_folder
        self.dst_folder = dst_folder
        self.callbacks = callbacks or []

    def on_modified(self, event):
        if not event.is_directory:
            src_file = Path(event.src_path)
            dst_file = self.dst_folder / src_file.name
            with src_file.open('r') as file:
                data = file.read()
            for callback in self.callbacks:
                data = callback(data)
            with dst_file.open('w') as file:
                file.write(data)
            print(f'Modified and copied: {src_file} to {dst_file}')


def include_callback(src_file: Path) -> Callable[[str], str]:
    def callback(data: str) -> str:
        def replacer(match):
            include_file = src_file.parent / Path(match.group(1)).relative_to('..')
            with include_file.open() as file:
                return file.read()
        return re.sub(r'{{ #include (.*?) }}', replacer, data)
    return callback


def create_project_version_callback(json_file: Path) -> Callable[[str], str]:
    with json_file.open() as file:
        project_info = json.load(file)

    def callback(data: str) -> str:
        def replacer(match):
            keys = match.group(1).split('.')
            value = project_info
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, '')
                else:
                    return ''
            return str(value)
        # Exclude the json_file_name from the matched pattern
        return re.sub(r'{{ \w+?\.(.*?) }}', replacer, data)

    return callback



@click.command()
@click.option('--watch', multiple=True, type=click.Path(exists=True, file_okay=False, dir_okay=True), help='List of directories to watch.')
@click.option('--copyto', multiple=True, type=click.Path(file_okay=False, dir_okay=True), help='List of directories to copy files to.')
@click.option('--json', default='project.json', type=click.Path(exists=True, file_okay=True, dir_okay=False), help='JSON file with project information.')
def main(watch: List[str], copyto: List[str], json: str):
    if len(watch) != len(copyto):
        print('Error: The number of watch directories and copyto directories must be the same.')
        sys.exit(1) 

    json_path = Path(json)
    project_version_callback = create_project_version_callback(json_path)
    
    observers = []
    for src_folder, dst_folder in zip(watch, copyto):
        src_path = Path(src_folder)
        include_cb = include_callback(src_path)
        callbacks = [include_cb, project_version_callback]
        event_handler = MyHandler(src_path, Path(dst_folder), callbacks=callbacks)
        observer = Observer()
        observer.schedule(event_handler, path=src_folder, recursive=True)
        observers.append(observer)
        observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()

    for observer in observers:
        observer.join()

if __name__ == '__main__':
    main()
