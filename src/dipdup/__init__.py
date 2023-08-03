"""Root DipDup package.

Contains software versions and other metadata.
"""
import importlib.metadata

# NOTE: Load version from package
__version__ = importlib.metadata.version('dipdup')
__spec_version__ = '2.0'


def discover(name: str, file: str) -> None:
    import sys
    from importlib.util import module_from_spec
    from importlib.util import spec_from_file_location
    from pathlib import Path

    package_root = Path(file).parent / '__init__.py'
    spec = spec_from_file_location(name, package_root)
    if spec is None:
        package_root.write_text('')
        spec = spec_from_file_location(name, package_root)
    if not spec or not spec.loader:
        raise ImportError
    
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
