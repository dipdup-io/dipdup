import logging
import sys
import warnings
from pathlib import Path

# NOTE: Updated by bumpversion
__version__ = '6.2.0'
__spec_version__ = '1.2'

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

# NOTE: Some ugly hacks acceptable for a CLI app
# NOTE: Better discoverability of DipDup packages and configs
sys.path.append(str(Path.cwd()))
sys.path.append(str(Path.cwd() / 'src'))
# NOTE: Format warnings as normal log messages
logging.captureWarnings(True)
warnings.simplefilter('always', DeprecationWarning)
warnings.formatwarning = lambda msg, *a, **kw: str(msg)
