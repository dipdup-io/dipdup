#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
from shutil import rmtree

import click

from dipdup.cli import green_echo
from dipdup.project import answers_from_replay
from dipdup.project import render_project

projects_path = Path(__file__).parent.parent / 'projects'


projects_path = Path(__file__).parent.parent / 'projects'
demos_path = Path(__file__).parent.parent / 'src'


def _get_demos() -> dict[str, Path]:
    paths = {}
    for path in demos_path.iterdir():
        if path.is_dir() and path.name.startswith('demo_'):
            paths[path.name] = path
    return paths


def _get_projects() -> dict[str, Path]:
    paths = {}
    for path in projects_path.iterdir():
        if path.is_dir() and path.name.startswith('demo_'):
            paths[path.name] = path
    return paths


def _render_demo(path: Path) -> None:
    package = path.name
    answers = answers_from_replay(path / 'replay.yaml')
    answers['package'] = package
    answers['template'] = package

    render_project(answers, force=True)

    Path(package).replace(f'src/{package}')


def _init_demo(path: Path) -> None:
    package = path.name
    package_path = Path(__file__).parent.parent / 'src' / package
    subprocess.run(
        [
            'dipdup',
            'init',
            # '--force',
        ],
        cwd=package_path,
        check=True,
        env={
            **dict(os.environ),
            'STACK': '',
            'POSTGRES_PASSWORD': '',
            'HASURA_SECRET': '',
        },
    )
    Path(package_path).joinpath(package).unlink()


def _rm_demo(path: Path) -> None:
    rmtree(path, ignore_errors=True)
    rmtree(path.parent / 'src' / path.name, ignore_errors=True)


@click.group(help='Various tools to generate demo projects from templates. Read the script source!')
def main() -> None:
    pass


@main.command(help='Initialize rendered demo projects')
@click.argument('package', required=False)
def init(package: str | None) -> None:
    if package:
        projects = {package: projects_path / package}
    else:
        projects = _get_projects()

    for package, path in projects.items():
        green_echo(f'=> Initializing `{package}`')
        _init_demo(path)


@main.command(help='Render demo projects from templates')
@click.argument('package', required=False)
def render(package: str | None) -> None:
    if package:
        demos = {package: demos_path / package}
        projects = {package: projects_path / package}
    else:
        demos = _get_demos()
        projects = _get_projects()

    for package, path in demos.items():
        green_echo(f'=> Removing `{package}`')
        _rm_demo(path)

    for package, path in projects.items():
        green_echo(f'=> Rendering `{package}`')
        _render_demo(path)


if __name__ == '__main__':
    main()
