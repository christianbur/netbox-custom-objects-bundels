"""Serve Security bundle static assets from ``local/security/plugin_assets/``."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control

_ASSET_ROOT = Path(__file__).resolve().parent.parent / "plugin_assets"
_ALLOWED_PREFIXES = ("css/", "js/")


class SecurityBundleAssetView(LoginRequiredMixin, View):
    """GET …/bundle-assets/security/<path> — CSS/JS for Security COT views."""

    @method_decorator(cache_control(public=True, max_age=3600))
    def get(self, request, asset_path: str, *args, **kwargs):
        rel = asset_path.lstrip("/")
        if not rel or ".." in rel.split("/"):
            raise Http404
        if not any(rel.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
            raise Http404
        base = _ASSET_ROOT.resolve()
        full_path = (base / rel).resolve()
        try:
            full_path.relative_to(base)
        except ValueError as exc:
            raise Http404 from exc
        if not full_path.is_file():
            raise Http404
        content_type, _ = mimetypes.guess_type(full_path.name)
        return FileResponse(
            full_path.open("rb"),
            content_type=content_type or "application/octet-stream",
        )
