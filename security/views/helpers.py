"""Shared, self-contained helpers for the NSM COT views.

Everything the rulebook / matrix / ip-analyzer views need to read real Custom
Object instances and their (possibly polymorphic) object fields lives here, so
the bundle depends only on the public COT-views API and never on the CO core
internals.
"""

from django.core.paginator import Paginator

DEFAULT_RULEBOOK_PAGE_SIZE = 100
MAX_MATRIX_AXIS = 64


def object_link(obj):
    """Return ``{"label", "url", "obj"}`` for a model instance (URL may be "")."""
    label = ""
    try:
        label = str(obj)
    except Exception:
        label = repr(obj)
    url = ""
    getter = getattr(obj, "get_absolute_url", None)
    if callable(getter):
        try:
            url = getter() or ""
        except Exception:
            url = ""
    return {"label": label, "url": url, "obj": obj}


def multiobject_values(instance, field_name):
    """Resolve a (polymorphic or plain) MULTIOBJECT field to a list of objects.

    Polymorphic managers return a heterogeneous list from ``.all()``; plain ones
    return a queryset. Both iterate. Any error yields an empty list so a single
    malformed row can never break the rendered tab.
    """
    manager = getattr(instance, field_name, None)
    if manager is None:
        return []
    try:
        return list(manager.all())
    except Exception:
        try:
            return list(manager)
        except Exception:
            return []


def object_value(instance, field_name):
    """Resolve a single OBJECT field to its instance (or ``None``)."""
    try:
        return getattr(instance, field_name, None)
    except Exception:
        return None


def cot_slug(obj):
    """Return the owning CustomObjectType slug for a CO instance ("" otherwise)."""
    cot = getattr(obj, "custom_object_type", None)
    return (getattr(cot, "slug", "") or "") if cot is not None else ""


def rule_queryset(cot):
    """All rows of a rulebook COT, ordered by ``index`` then ``pk``.

    Falls back to ``pk`` ordering when the type has no ``index`` field so the
    helper also works for non-rulebook collections.
    """
    model = cot.get_model()
    qs = model.objects.all()
    field_names = {f.name for f in model._meta.get_fields()}
    order = ["index", "pk"] if "index" in field_names else ["pk"]
    try:
        return qs.order_by(*order)
    except Exception:
        return qs


def paginate_queryset(request, queryset, *, per_page=DEFAULT_RULEBOOK_PAGE_SIZE):
    """Return ``(page_obj, paginator)`` for a collection COT view."""
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page", 1)), paginator
