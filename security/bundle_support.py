"""Register Security bundle templates, assets, and API URLs at import time."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("security.bundle")

_BUNDLE_ROOT = Path(__file__).resolve().parent
_TEMPLATE_DIR = str(_BUNDLE_ROOT / "templates")
_ASSET_URL_NAME = "security_bundle_asset"
_REGISTERED = False


def ensure_bundle_resources() -> None:
    """Append template dir, asset URLs, and IP-analysis APIs once per worker."""
    global _REGISTERED
    if _REGISTERED:
        return
    _register_template_dir()
    _register_asset_url()
    _register_api_urls()
    _REGISTERED = True


def _register_template_dir() -> None:
    try:
        from django.conf import settings
    except ImportError:
        return
    if not settings.configured:
        return
    for cfg in settings.TEMPLATES:
        dirs = cfg.setdefault("DIRS", [])
        if _TEMPLATE_DIR not in dirs:
            dirs.insert(0, _TEMPLATE_DIR)


def _register_asset_url() -> None:
    try:
        from django.urls import path

        import netbox_custom_objects.urls as co_urls
        from security.views.assets import SecurityBundleAssetView
    except ImportError:
        logger.debug("Security bundle asset URL not registered (custom-objects unavailable)")
        return

    existing = {p.name for p in co_urls.urlpatterns if getattr(p, "name", None)}
    if _ASSET_URL_NAME in existing:
        return
    co_urls.urlpatterns.insert(
        0,
        path(
            "bundle-assets/security/<path:asset_path>",
            SecurityBundleAssetView.as_view(),
            name=_ASSET_URL_NAME,
        ),
    )


def _register_api_urls() -> None:
    try:
        import netbox_custom_objects.urls as co_urls
        from security.api_urls import urlpatterns as security_api_patterns
    except ImportError:
        logger.debug("Security bundle API URLs not registered (custom-objects unavailable)")
        return

    existing = {p.name for p in co_urls.urlpatterns if getattr(p, "name", None)}
    for pattern in security_api_patterns:
        if pattern.name and pattern.name not in existing:
            co_urls.urlpatterns.insert(0, pattern)
