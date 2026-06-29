"""Back-compat alias: ``blackforestlabs`` re-exports everything from :mod:`bfl`.

The canonical import name is now ``bfl`` (``from bfl import BFL``). This thin
shim keeps the historical ``from blackforestlabs import ...`` form working so
neither legacy name breaks. New code should import ``bfl``.
"""

from bfl import *  # noqa: F401,F403
from bfl import __all__ as _all
from bfl import __version__  # noqa: F401

__all__ = list(_all)
