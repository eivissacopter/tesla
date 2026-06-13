"""No-op Streamlit shim for headless (ETL / cron / CI) use.

The shared reference modules decorate functions with ``@st.cache_data`` etc.
On the home server we want to import that reference brain *without* installing
Streamlit. Calling ``install()`` registers a minimal stand-in under the
``streamlit`` name so those imports succeed; the decorators become pass-through
and caching is simply disabled (fine for a once-a-week batch job).
"""

from __future__ import annotations

import sys
import types


def install() -> None:
    if "streamlit" in sys.modules:
        return
    try:  # prefer the real thing if it happens to be installed
        import streamlit  # noqa: F401
        return
    except Exception:
        pass

    st = types.ModuleType("streamlit")

    def _passthrough_decorator(*dargs, **dkwargs):
        # Supports both @st.cache_data and @st.cache_data(ttl=...)
        if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def wrap(func):
            return func

        return wrap

    st.cache_data = _passthrough_decorator
    st.cache_resource = _passthrough_decorator

    class _Secrets(dict):
        def __getattr__(self, item):
            raise KeyError(item)

    st.secrets = _Secrets()
    st.error = lambda *a, **k: None
    st.warning = lambda *a, **k: None
    st.info = lambda *a, **k: None
    st.stop = lambda *a, **k: None

    sys.modules["streamlit"] = st
