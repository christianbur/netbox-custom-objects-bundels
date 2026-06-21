"""Resolve ``nsm_config`` from Security bundle ``metadata`` (+ NSM ``comments``).

The bundled rulebook schema stores ``nsm_config`` in ``CustomObjectType.metadata``
(see ``schema/security_rulebook.yaml``).  NSM's rule viewer still parses the same
keys from ``comments`` by default — this module merges both sources so row grouping
(``rulebook.row_group_by_col_id``), matrix tab flags, and parent slug work on
``security-*`` and ``nsm_rb_*`` rulebooks alike.
"""

from __future__ import annotations

from typing import Any

import yaml


def _load_yaml_document(text: str) -> dict[str, Any]:
    if not (text or "").strip():
        return {}
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _nsm_config_list(document: dict[str, Any]) -> list:
    raw = document.get("nsm_config")
    if isinstance(raw, list):
        return raw
    return []


def rulebook_block_from_document(document: dict[str, Any]) -> dict[str, Any]:
    """Return the ``rulebook:`` segment from an ``nsm_config`` document."""
    for entry in _nsm_config_list(document):
        if isinstance(entry, dict) and len(entry) == 1 and "rulebook" in entry:
            block = entry.get("rulebook")
            if isinstance(block, dict):
                return block
    return {}


def rulebook_block_from_metadata(cot) -> dict[str, Any]:
    return rulebook_block_from_document(_load_yaml_document(getattr(cot, "metadata", "") or ""))


def merged_rulebook_config_for_cot(cot) -> dict[str, Any]:
    """Merge ``comments`` rulebook config with ``metadata`` (metadata keys win)."""
    from security.objects.rulebook_config import (
        normalize_rulebook_config,
        parse_rulebook_config_from_comments,
    )

    merged = parse_rulebook_config_from_comments(getattr(cot, "comments", "") or "")
    meta_block = rulebook_block_from_metadata(cot)
    if not meta_block:
        return merged

    normalized = normalize_rulebook_config(meta_block)
    for key in ("parent_slug", "matrix_tab_enabled", "row_group_by_col_id"):
        if key in meta_block:
            merged[key] = normalized[key]
    return merged


def resolve_rulebook_config_for_slug(slug: str) -> dict[str, Any]:
    """Like NSM's helper, but resolves any COT slug and reads ``metadata``."""
    from copy import deepcopy

    from netbox_custom_objects.models import CustomObjectType
    from security.objects.rulebook_config import DEFAULT_RULEBOOK_CONFIG

    if not slug:
        return deepcopy(DEFAULT_RULEBOOK_CONFIG)
    cot = CustomObjectType.objects.filter(slug=slug).first()
    if cot is None:
        return deepcopy(DEFAULT_RULEBOOK_CONFIG)
    return merged_rulebook_config_for_cot(cot)
