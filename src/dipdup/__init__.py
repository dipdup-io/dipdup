"""Root DipDup package.

Contains software versions and other metadata.
"""
import importlib.metadata

# NOTE: Load version from package
__version__ = importlib.metadata.version('dipdup')
__spec_version__ = '1.2'

version = tuple(__version__.split('.'))
major_version = version[0]
minor_version = f'{version[0]}.{version[1]}'
