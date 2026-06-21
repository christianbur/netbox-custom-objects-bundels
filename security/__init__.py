"""Security bundle — policy-object COTs, rulebook, and COT views.

Importing the package registers its COT views (import side effect). The bundled
COT schema lives under ``schema/`` and is applied by the host plugin's loader.
Demo import/purge: ``scripts/security_demo.py``.
"""

from .bundle_support import ensure_bundle_resources

ensure_bundle_resources()

from . import views  # noqa: F401  (registers COT views)
