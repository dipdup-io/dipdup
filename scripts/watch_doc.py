import shutil
import time
from pathlib import Path

import click
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class MyHandler(FileSystemEventHandler):
    def __init__(self, src_folder, dst_folder):
        self.src_folder = src_folder
        self.dst_folder = dst_folder

    def on_modified(self, event):
        if not event.is_directory:
            src_file = Path(event.src_path)
            dst_file = Path(self.dst_folder) / src_file.name
            shutil.copy2(src_file, dst_file)
            print(f'Copied: {src_file} to {dst_file}')

@click.command()
@click.option('--watch', multiple=True, help='List of directories to watch.')
@click.option('--copyto', multiple=True, help='List of directories to copy files to.')
def main(watch, copyto):
    if len(watch) != len(copyto):
        print('Error: The number of watch directories and copyto directories must be the same.')
        exit(1)

    observers = []
    for src_folder, dst_folder in zip(watch, copyto):
        event_handler = MyHandler(src_folder, dst_folder)
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
