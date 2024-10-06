import warnings

from .fetchers.legacy import (  # noqa: F401
    InsecureHTTPAdapter,
    InsecureMixin,
    PyPISession,
)

warnings.warn(
    "unearth.session has been deprecated and will be removed "
    "in the next minor release. Please import from unearth.fetchers instead.",
    DeprecationWarning,
    stacklevel=1,
)
