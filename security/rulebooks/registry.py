"""Lookup helpers for deployed COT rulebooks (``nsm_rb_<name>``)."""

from __future__ import annotations

__all__ = (
    "cot_rulebook_instance_count",
    "get_deployed_cot_rulebook",
    "iter_deployed_cot_rulebooks",
)

from security.rulebooks.templates import (
    RULEBOOK_GROUP,
    get_rulebook_template_slugs,
    is_deployed_rulebook_slug,
)


def iter_deployed_cot_rulebooks():
    """Yield ``CustomObjectType`` rows for concrete rulebooks."""
    from netbox_custom_objects.models import CustomObjectType

    seen: set[int] = set()
    template_slugs = set(get_rulebook_template_slugs())

    for cot in CustomObjectType.objects.filter(group_name=RULEBOOK_GROUP).order_by(
        "name", "slug"
    ):
        if is_deployed_rulebook_slug(cot.slug):
            seen.add(cot.pk)
            yield cot

    for cot in (
        CustomObjectType.objects.filter(slug__startswith="nsm_rb_")
        .exclude(slug__in=template_slugs)
        .exclude(pk__in=seen)
        .order_by("name", "slug")
    ):
        if is_deployed_rulebook_slug(cot.slug):
            seen.add(cot.pk)
            yield cot

    yield from (
        CustomObjectType.objects.filter(slug__endswith="-rulebook")
        .exclude(pk__in=seen)
        .order_by("name", "slug")
    )


def get_deployed_cot_rulebook(slug: str):
    from netbox_custom_objects.models import CustomObjectType

    if not slug or not is_deployed_rulebook_slug(slug):
        return None
    return CustomObjectType.objects.filter(slug=slug).first()


def cot_rulebook_instance_count(cot) -> int:
    try:
        model = cot.get_model()
    except Exception:
        return 0
    return model.objects.count()
