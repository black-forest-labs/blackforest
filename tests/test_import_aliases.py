"""The canonical import is ``bfl``. ``blackforestlabs`` is a quiet back-compat
alias; ``blackforest`` is a deprecated alias that still works but warns. This
locks all three behaviors in so a rename can't silently regress.
"""

from __future__ import annotations

import importlib
import warnings

import bfl


def test_canonical_bfl_import():
    from bfl import BFL, AsyncBFL  # noqa: F401

    assert bfl.__version__


def test_blackforestlabs_alias_is_quiet_and_reexports():
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # no warning expected from this alias
        import blackforestlabs

    assert blackforestlabs.BFL is bfl.BFL
    assert blackforestlabs.AsyncBFL is bfl.AsyncBFL
    assert blackforestlabs.__version__ == bfl.__version__


def test_blackforest_alias_warns_but_still_works():
    # Force a fresh import so the module-level warning fires.
    import sys

    sys.modules.pop("blackforest", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        blackforest = importlib.import_module("blackforest")

    assert any(
        issubclass(w.category, DeprecationWarning) for w in caught
    ), "importing `blackforest` should emit a DeprecationWarning"
    assert blackforest.BFL is bfl.BFL
    assert blackforest.__version__ == bfl.__version__


def test_aliases_expose_full_public_surface():
    import blackforest
    import blackforestlabs

    for name in bfl.__all__:
        assert hasattr(blackforestlabs, name), f"blackforestlabs missing {name}"
        assert hasattr(blackforest, name), f"blackforest missing {name}"
