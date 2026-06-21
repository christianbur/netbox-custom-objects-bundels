"""Zone / Policy matrix COT view.

A self-contained analogue of the netbox-nsm zone-matrix analyzer
(``netbox_nsm.matrix`` / ``analyzer/zone-matrix``): it renders a Source-zone ×
Destination-zone grid for a rulebook, where each cell lists the rules (and their
actions) that connect that ordered zone pair.

The matrix is derived from the *real* rules of the Rulebook COT the tab is shown
on: every rule's polymorphic Source/Destination columns are scanned for Zone
objects and crossed against each other.

Bound dynamically via the COT ``views`` field (``nsm_matrix``).
"""

from netbox_custom_objects.cot_views import COTView, register_cot_view

from .helpers import (
    MAX_MATRIX_AXIS,
    cot_slug,
    multiobject_values,
    object_link,
    rule_queryset,
)

ZONE_SLUGS = frozenset({"security-zone", "nsm_zone"})


@register_cot_view
class ZoneMatrixCOTView(COTView):
    key = "security_matrix"
    label = "Zone Matrix"
    weight = 2200

    def _zones_of(self, rule, field_name):
        return [obj for obj in multiobject_values(rule, field_name) if cot_slug(obj) in ZONE_SLUGS]

    def _build_matrix(self, cot, *, max_axis=MAX_MATRIX_AXIS):
        zones = {}  # pk -> link dict
        cells = {}  # (src_pk, dst_pk) -> [entry, ...]

        for rule in rule_queryset(cot):
            src_zones = self._zones_of(rule, "source")
            dst_zones = self._zones_of(rule, "destination")
            if not src_zones or not dst_zones:
                continue
            actions = [object_link(a)["label"] for a in multiobject_values(rule, "actions")]
            entry = {
                "index": getattr(rule, "index", None),
                "name": getattr(rule, "name", "") or "",
                "status": bool(getattr(rule, "status", False)),
                "actions": actions,
                "url": object_link(rule)["url"],
            }
            for src in src_zones:
                zones.setdefault(src.pk, object_link(src))
                for dst in dst_zones:
                    zones.setdefault(dst.pk, object_link(dst))
                    cells.setdefault((src.pk, dst.pk), []).append(entry)

        ordered = sorted(zones.items(), key=lambda kv: kv[1]["label"].lower())
        axis = [{"pk": pk, **link} for pk, link in ordered]
        truncated = len(axis) > max_axis
        if truncated:
            axis = axis[:max_axis]
        rows = []
        for src in axis:
            row_cells = []
            for dst in axis:
                row_cells.append({"entries": cells.get((src["pk"], dst["pk"]), [])})
            rows.append({"zone": src, "cells": row_cells})
        return axis, rows, truncated

    def _apply_matrix_context(self, context, cot):
        axis, rows, truncated = self._build_matrix(cot)
        context["matrix_axis"] = axis
        context["matrix_rows"] = rows
        context["has_matrix"] = bool(axis)
        context["matrix_truncated"] = truncated
        context["matrix_axis_limit"] = MAX_MATRIX_AXIS
        return context

    def get_context(self, request, cot, instance):
        context = super().get_context(request, cot, instance)
        return self._apply_matrix_context(context, cot)

    def get_collection_context(self, request, cot, queryset):
        context = super().get_collection_context(request, cot, queryset)
        return self._apply_matrix_context(context, cot)

    template_string = """{% extends base_template %}
{% load i18n %}
{% block content %}
<div class="card">
  <h5 class="card-header"><i class="mdi mdi-grid"></i> {{ cot_view_label }} — {{ cot.verbose_name }}</h5>
  <div class="card-body">
    <p class="text-muted">
      {% trans "Source zones (rows) crossed with destination zones (columns). Each cell lists the rules connecting that ordered zone pair." %}
    </p>
    {% if matrix_truncated %}
      <div class="alert alert-warning mb-0" role="alert">
        {% blocktrans trimmed with limit=matrix_axis_limit %}
          The matrix has more zones than can be rendered at once. Showing the first {{ limit }} zones only.
        {% endblocktrans %}
      </div>
    {% endif %}
  </div>
  {% if has_matrix %}
  <div class="table-responsive">
  <table class="table table-bordered text-center" style="vertical-align: middle;">
    <thead>
      <tr>
        <th class="text-end">{% trans "Src ╲ Dst" %}</th>
        {% for dst in matrix_axis %}
          <th>{% if dst.url %}<a href="{{ dst.url }}">{{ dst.label }}</a>{% else %}{{ dst.label }}{% endif %}</th>
        {% endfor %}
      </tr>
    </thead>
    <tbody>
      {% for row in matrix_rows %}
        <tr>
          <th class="text-end table-light">{% if row.zone.url %}<a href="{{ row.zone.url }}">{{ row.zone.label }}</a>{% else %}{{ row.zone.label }}{% endif %}</th>
          {% for cell in row.cells %}
            <td>
              {% for entry in cell.entries %}
                <a href="{{ entry.url }}" class="badge {% if entry.status %}text-bg-green{% else %}text-bg-red{% endif %}"
                   title="{{ entry.name }}">#{{ entry.index }}{% for a in entry.actions %} · {{ a }}{% endfor %}</a>
              {% empty %}
                <span class="text-muted">·</span>
              {% endfor %}
            </td>
          {% endfor %}
        </tr>
      {% endfor %}
    </tbody>
  </table>
  </div>
  {% else %}
  <div class="card-body">
    <div class="alert alert-info mb-0" role="alert">
      {% trans "No zone-to-zone rules found in this rulebook. Add rules whose Source and Destination reference Zone objects to populate the matrix." %}
    </div>
  </div>
  {% endif %}
</div>
{% endblock %}
"""
