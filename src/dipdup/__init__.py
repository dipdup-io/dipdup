"""Root DipDup package.

Contains software versions and other metadata.
"""
import importlib.metadata

__version__ = importlib.metadata.version('dipdup')
__spec_version__ = '2.0'


def workdir(file: str) -> None:
    """A little hack to use Python package as a working directory."""
    import sys
    from importlib.util import module_from_spec
    from importlib.util import spec_from_file_location
    from pathlib import Path

    package_path = Path(file).parent
    name = package_path.name
    package_root = package_path / '__init__.py'
    if not package_root.exists():
        raise ImportError(f'`{name}` is not a valid DipDup package')

    spec = spec_from_file_location(name, package_root)
    if not spec or not spec.loader:
        raise ImportError(f'`{name}` is not a valid DipDup package')

    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
