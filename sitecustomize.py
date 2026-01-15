# sitecustomize.py
# Auto-loaded by Python if present on sys.path.
# Provides safe fallbacks for ctypes.windll / ctypes.wintypes on non-Windows.
import sys
import types
import ctypes

if not (sys.platform.startswith("win32") or sys.platform.startswith("cygwin")):
    # Dummy object that returns no-op callables for any attribute
    class _WinDllDummy:
        def __getattr__(self, name):
            def _noop(*args, **kwargs):
                return None
            return _noop

    # Inject windll if missing
    if not hasattr(ctypes, "windll"):
        ctypes.windll = _WinDllDummy()  # type: ignore[attr-defined]

    # Inject wintypes minimal namespace if missing
    if not hasattr(ctypes, "wintypes"):
        ctypes.wintypes = types.SimpleNamespace()  # type: ignore[attr-defined]
