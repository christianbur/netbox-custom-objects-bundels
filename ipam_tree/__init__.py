"""IPAM Tree demo local plugin.

Importing the package registers its COT views (import side effect). The bundled
proxy COT schema lives under ``schema/`` and is applied by the host plugin's
loader.
"""

from . import views  # noqa: F401  (registers COT views)
