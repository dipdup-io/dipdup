"""Root DipDup package.

Contains software versions and other metadata.
"""
import importlib.metadata

# NOTE: Load version from package
__version__ = importlib.metadata.version('dipdup')
# __version__ = '0.0.0'
__spec_version__ = '2.0'
