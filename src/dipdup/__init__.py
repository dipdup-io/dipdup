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

spec_version_mapping = {
    '0.1': '<=0.4.3',
    '1.0': '>=1.0.0, <=1.1.2',
    '1.1': '>=2.0.0, <=2.0.9',
    '1.2': '>=3.0.0',
}
spec_reindex_mapping = {
    '0.1': False,
    '1.0': False,
    '1.1': True,
    '1.2': True,
}
