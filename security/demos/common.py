"""Shared helpers for Security bundle demos."""

from __future__ import annotations

import sys
from pathlib import Path

from django.apps import apps
from django.db.utils import OperationalError, ProgrammingError

from netbox_custom_objects import constants
from netbox_custom_objects.cot_views.local_bundles import (
    discover_bundles,
    prefix_schema_document,
)
from netbox_custom_objects.models import Bundle, CustomObjectType

BUNDLE_NAME = "security"
NAME_PREFIX = "security_"

SLUG_ACTION = "security-action"
SLUG_SERVICE = "security-service"
SLUG_SERVICE_GROUP = "security-service-group"
SLUG_ADDRESS = "security-address"
SLUG_ADDRESS_GROUP = "security-address-group"
SLUG_LABEL = "security-label"
SLUG_ZONE = "security-zone"
SLUG_APP_BUSINESS = "security-app-business"
SLUG_APP_NETWORK = "security-app-network"
SLUG_OBJECT_LINK = "security-object-link"
SLUG_RULEBOOK = "security-rulebook"

REQUIRED_DEMO_SLUGS = (
    SLUG_ACTION,
    SLUG_SERVICE,
    SLUG_ADDRESS,
    SLUG_LABEL,
    SLUG_ZONE,
    SLUG_OBJECT_LINK,
    SLUG_RULEBOOK,
)

NSM_TO_SECURITY_SLUG = {
    "nsm_action": SLUG_ACTION,
    "nsm_service": SLUG_SERVICE,
    "nsm_services": SLUG_SERVICE,
    "nsm_service_group": SLUG_SERVICE_GROUP,
    "nsm_address": SLUG_ADDRESS,
    "nsm_addresses": SLUG_ADDRESS,
    "nsm_address_group": SLUG_ADDRESS_GROUP,
    "nsm_label": SLUG_LABEL,
    "nsm_labels": SLUG_LABEL,
    "nsm_zone": SLUG_ZONE,
    "nsm_zones": SLUG_ZONE,
    "nsm_app_business": SLUG_APP_BUSINESS,
    "nsm_app_network": SLUG_APP_NETWORK,
    "nsm_object_link": SLUG_OBJECT_LINK,
    "nsm_rulebook": SLUG_RULEBOOK,
}


def _custom_objects_db_ready() -> bool:
    try:
        CustomObjectType.objects.exists()
        return True
    except (ProgrammingError, OperationalError):
        return False


def _security_bundle_on_disk() -> dict | None:
    for bundle in discover_bundles():
        if bundle["name"] == BUNDLE_NAME:
            return bundle
    return None


def apply_bundle_schema(*, allow_destructive: bool = False) -> None:
    """Apply ``local/security/schema/*.yaml`` with bundle slug/name prefixing."""
    import yaml

    from netbox_custom_objects.schema.executor import apply_document

    bundle = _security_bundle_on_disk()
    if bundle is None:
        raise RuntimeError(f"Security bundle not found under the configured local path.")

    schema_dir = Path(bundle["path"]) / "schema"
    for fname in sorted(schema_dir.iterdir()):
        if fname.suffix not in (".yaml", ".yml"):
            continue
        doc = yaml.safe_load(fname.read_text(encoding="utf-8")) or {}
        doc = prefix_schema_document(doc, bundle["package"])
        apply_document(doc, allow_destructive=allow_destructive)


def ensure_prerequisites(*, apply_schema: bool = True) -> None:
    """Ensure the Security bundle is enabled and all demo COTs exist."""
    if not _custom_objects_db_ready():
        raise RuntimeError(
            "netbox-custom-objects database tables are missing "
            "(run migrate netbox_custom_objects first)."
        )

    bundle = _security_bundle_on_disk()
    if bundle is None:
        raise RuntimeError("Security bundle directory is missing from the local path.")

    Bundle.objects.get_or_create(name=BUNDLE_NAME, defaults={"enabled": True})
    if not Bundle.objects.filter(name=BUNDLE_NAME, enabled=True).exists():
        raise RuntimeError(
            f"Enable the {BUNDLE_NAME!r} bundle in Custom Objects → Bundles, "
            "then restart NetBox workers."
        )

    missing = [
        slug
        for slug in REQUIRED_DEMO_SLUGS
        if not CustomObjectType.objects.filter(slug=slug).exists()
    ]
    if missing and apply_schema:
        apply_bundle_schema()
        missing = [
            slug
            for slug in REQUIRED_DEMO_SLUGS
            if not CustomObjectType.objects.filter(slug=slug).exists()
        ]
    if missing:
        raise RuntimeError(
            "Missing Security bundle COT(s): "
            f"{', '.join(missing)}. Enable the bundle and restart NetBox, "
            "or run: python3 security_demo.py apply --schema-only"
        )

    __import__(bundle["package"])


def get_cot(*slug_candidates: str) -> CustomObjectType:
    for slug in slug_candidates:
        mapped = NSM_TO_SECURITY_SLUG.get(slug, slug)
        cot = CustomObjectType.objects.filter(slug=mapped).first()
        if cot is not None:
            return cot
    raise RuntimeError(
        f"Missing Custom Object Type (tried: {', '.join(slug_candidates)}). "
        "Enable the Security bundle first."
    )


def get_cot_model(*slug_candidates: str):
    cot = get_cot(*slug_candidates)
    return cot.get_model(), cot


def get_through_model(cot: CustomObjectType, field_name: str):
    field = cot.fields.get(name=field_name)
    return apps.get_model(constants.APP_LABEL, field.through_model_name)


def objects_by_lower_name(*slug_candidates: str) -> dict:
    model, _cot = get_cot_model(*slug_candidates)
    return {obj.name.lower(): obj for obj in model.objects.all()}


def patch_object_link_slug() -> None:
    """Point netbox-nsm object-link helpers at ``security-object-link``."""
    import netbox_nsm.objects.object_link_service as ols

    ols.NSM_OBJECT_LINK_SLUG = SLUG_OBJECT_LINK


def enterprise_import_path() -> Path:
    candidates = (
        Path("/opt/netbox-nsm/netbox_nsm/demos/enterprise_dc/import.py"),
        Path(__file__).resolve().parents[3]
        / "netbox-nsm"
        / "netbox_nsm"
        / "demos"
        / "enterprise_dc"
        / "import.py",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Enterprise DC demo script not found. Expected netbox-nsm checkout "
        "at /opt/netbox-nsm or beside docker/netbox_dev."
    )


def exec_enterprise_script(source: str) -> None:
    """Execute transformed enterprise import source."""
    namespace = {"__name__": "__main__", "__file__": str(enterprise_import_path())}
    code = compile(source, namespace["__file__"], "exec")
    exec(code, namespace)  # noqa: S102
