"""Deprecated import alias: ``blackforest`` re-exports everything from :mod:`bfl`.

The canonical import name is now ``bfl`` (``from bfl import BFL``). Importing
``blackforest`` still works for one release to avoid breaking code written
against 0.1.x, but emits a :class:`DeprecationWarning`. Switch your imports to
``bfl`` (or the ``blackforestlabs`` alias); this shim will be removed in a
future release.
"""

import warnings

from bfl import *  # noqa: F401,F403
from bfl import __all__ as _all
from bfl import __version__  # noqa: F401

warnings.warn(
    "`import blackforest` is deprecated and will be removed in a future "
    "release. Import `bfl` instead, e.g. `from bfl import BFL`.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = list(_all)
