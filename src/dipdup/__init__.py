import logging
import os
import sys
import warnings

__version__ = '5.0.0-rc4'
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

sys.path.append(os.getcwd())
logging.captureWarnings(True)
warnings.simplefilter('always', DeprecationWarning)
warnings.formatwarning = lambda msg, *a, **kw: str(msg)
