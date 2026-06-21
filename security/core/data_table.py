"""Reusable "rich client-side table" model (``nsm-orf`` component).

This is the server-side data contract for the shared NetBox-style data table
rendered by ``templates/netbox_nsm/inc/nsm_data_table.html`` and driven by
``plugin_assets/js/nsm_data_table.js`` (quick search, attribute filters,
configure-table column toggles, header sorting and 50-row client pagination).

The whole (bounded) row set is rendered into the DOM once and all interaction
runs client-side — so callers MUST cap their row list (``total`` vs. the rendered
``rows``) to keep the page bounded; ``build_data_table`` flags ``truncated``
automatically when ``total`` exceeds the rendered rows.

The model is intentionally plain dicts (JSON-ish) so it is trivial to build,
test and template. Labels are expected to be already localized by the caller
(``gettext`` at request time).
"""

from __future__ import annotations

from typing import Any

__all__ = (
    "dt_cell",
    "dt_column",
    "dt_filter",
    "dt_row",
    "build_data_table",
)


def dt_column(
    key: str,
    label: str,
    *,
    sortable: bool = True,
    toggle: bool = True,
    align: str = "",
) -> dict[str, Any]:
    """One column definition (header + sort/toggle/alignment flags)."""
    return {
        "key": key,
        "label": label,
        "sortable": sortable,
        "toggle": toggle,
        "align": align,
    }


def dt_filter(
    attr: str,
    label: str,
    all_label: str,
    options: list[dict[str, Any]],
) -> dict[str, Any]:
    """A dropdown filter over a row ``data-<attr>`` value.

    ``options`` is a list of ``{value, label, count}``. ``all_label`` is the
    leading "show everything" option.
    """
    return {
        "attr": attr,
        "label": label,
        "all_label": all_label,
        "options": list(options),
    }


def dt_cell(
    col: str,
    text: str = "",
    *,
    kind: str = "text",
    url: str = "",
    css: str = "",
) -> dict[str, Any]:
    """A single table cell.

    ``kind`` is one of ``text`` / ``muted`` / ``link`` / ``badge`` and selects
    how the generic template renders it. ``text`` is always plain text (escaped
    by the template); ``url`` is used for ``link`` cells; ``css`` adds badge
    classes for ``badge`` cells.
    """
    return {"col": col, "text": str(text), "kind": kind, "url": url, "css": css}


def dt_row(
    attrs: dict[str, Any],
    cells: list[dict[str, Any]],
    *,
    search: str | None = None,
) -> dict[str, Any]:
    """One table row.

    ``attrs`` maps filter/sort dimension -> value (rendered as ``data-<attr>``
    and used by the JS for filtering and attribute-based sorting). ``search`` is
    the pre-computed lowercase blob powering quick search; if omitted it is
    derived from the cell texts.
    """
    if search is None:
        search = " ".join(c.get("text", "") for c in cells if c.get("text")).lower()
    return {"attrs": dict(attrs), "cells": list(cells), "search": search}


def build_data_table(
    *,
    dom_id: str,
    title: str,
    columns: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    total: int | None = None,
    filters: list[dict[str, Any]] | None = None,
    page_size: int = 50,
    search_placeholder: str = "",
    empty_text: str = "",
    truncated_note: str = "",
    count_label_attr: str | None = None,
) -> dict[str, Any]:
    """Assemble the table model consumed by ``inc/nsm_data_table.html``.

    ``total`` is the number of rows that *exist* (before any DOM cap); when it
    exceeds the rendered ``rows`` the table is flagged ``truncated`` so the
    template can show ``truncated_note``. ``columns`` length drives the empty-row
    ``colspan``.
    """
    shown = len(rows)
    if total is None:
        total = shown
    return {
        "id": dom_id,
        "title": title,
        "columns": list(columns),
        "filters": list(filters or []),
        "rows": rows,
        "colspan": max(1, len(columns)),
        "page_size": page_size,
        "total": total,
        "shown": shown,
        "truncated": total > shown,
        "search_placeholder": search_placeholder,
        "empty_text": empty_text,
        "truncated_note": truncated_note,
    }
