"""Root DipDup package.

Contains software versions and other metadata.
"""

import importlib.metadata as _pkg

__version__ = _pkg.version('dipdup')
__editable__ = _pkg.PackagePath('dipdup.pth') in (_pkg.files('dipdup') or ())
__spec_version__ = '3.0'
