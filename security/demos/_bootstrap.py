"""Bootstrap Django + PYTHONPATH for standalone demo scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidate_paths() -> tuple[Path, Path]:
    """Return ``(netbox_dir, local_root)`` for container or dev checkout."""
    here = Path(__file__).resolve().parent
    local_from_file = here.parent.parent  # …/local

    pairs = (
        (Path("/opt/netbox/netbox"), Path("/opt/netbox/local")),
        (local_from_file.parent / "netbox" / "netbox", local_from_file),
    )
    for netbox_dir, local_root in pairs:
        if netbox_dir.is_dir() and local_root.is_dir():
            return netbox_dir, local_root

    raise RuntimeError(
        "NetBox paths not found. Run this script inside the netbox-dev container, e.g.\n"
        "  docker compose exec netbox python3 /opt/netbox/local/security/demos/defaults.py apply\n"
        "or from the repo host:\n"
        "  ./scripts/security-demo.sh defaults apply"
    )


def setup_django() -> None:
    """Configure ``sys.path`` and call ``django.setup()`` once."""
    try:
        import django  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Django is not installed in this Python environment. "
            "Demo scripts must run inside the netbox-dev container:\n"
            "  docker compose exec netbox python3 "
            "/opt/netbox/local/security/demos/defaults.py apply\n"
            "or:\n"
            "  ./scripts/security-demo.sh defaults apply"
        ) from exc

    netbox_dir, local_root = _candidate_paths()
    for path in (netbox_dir, local_root):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netbox.settings")

    from django.conf import settings

    if not settings.configured:
        import django

        django.setup()


def bootstrap_script(caller: str) -> None:
    """Load this module without importing the ``security`` package, then setup Django."""
    import importlib.util

    bootstrap_path = Path(caller).resolve().with_name("_bootstrap.py")
    spec = importlib.util.spec_from_file_location("_security_demo_bootstrap", bootstrap_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load bootstrap from {bootstrap_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.setup_django()
