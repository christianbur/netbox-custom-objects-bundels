"""Importing this package registers every NSM COT view (import side effect)."""

from . import ip_analyzer  # noqa: F401  (registers IPAnalyzerCOTView)
from . import matrix  # noqa: F401  (registers ZoneMatrixCOTView)
from . import rulebook  # noqa: F401  (registers RulebookCOTView)
