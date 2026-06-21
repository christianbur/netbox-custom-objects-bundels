#!/usr/bin/env python3
"""Enterprise DC demo adapted to Security bundle COT slugs.

Run inside netbox-dev::

    python3 /opt/netbox/local/security/demos/enterprise_dc.py apply
    python3 /opt/netbox/local/security/demos/enterprise_dc.py purge --include-dcim

From the repo host::

    ./scripts/security-demo.sh enterprise apply
"""

from __future__ import annotations

if __name__ == "__main__":
    import importlib.util
    from pathlib import Path

    _boot_path = Path(__file__).resolve().with_name("_bootstrap.py")
    _spec = importlib.util.spec_from_file_location("_security_demo_bootstrap", _boot_path)
    _boot = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_boot)
    _boot.setup_django()

from django.db import transaction

from dcim.models import Site
from ipam.models import IPAddress

from security.demos.common import (
    NSM_TO_SECURITY_SLUG,
    SLUG_ACTION,
    SLUG_ADDRESS,
    SLUG_LABEL,
    SLUG_OBJECT_LINK,
    SLUG_SERVICE,
    SLUG_ZONE,
    ensure_prerequisites,
    enterprise_import_path,
    exec_enterprise_script,
    get_cot_model,
    patch_object_link_slug,
)
from security.demos.defaults import seed_defaults

ENTERPRISE_SITE_SLUG = "dc-01"

ZONE_NAMES = (
    "prod",
    "integration-1",
    "integration-2",
    "integration-3",
    "dev-1",
    "dev-2",
    "dev-3",
    "test-1",
    "test-2",
    "test-3",
    "infrastructure",
)

ADDRESS_NAMES = (
    "infrastructure",
    "prod",
    "integration-1",
    "integration-2",
    "integration-3",
    "dev-1",
    "dev-2",
    "dev-3",
    "test-1",
    "test-2",
    "test-3",
    "user-clients",
    "hv-mgmt",
    "oob-mgmt",
    "gcp-dmz",
    "gcp-dmz-web",
    "gcp-dmz-api",
    "gcp-dmz-auth",
    "internet",
)

SERVICE_NAMES = (
    "SSH",
    "HTTPS",
    "HTTP",
    "RDP",
    "DNS-UDP",
    "DNS-TCP",
    "NTP",
    "Syslog-UDP",
    "Syslog-TCP",
    "LDAP",
    "LDAP-UDP",
    "LDAPS",
    "Kerberos-TCP",
    "Kerberos-UDP",
    "SMB",
    "RPC-EPM",
    "Kpasswd-TCP",
    "Kpasswd-UDP",
    "GC-LDAP",
    "GC-LDAPS",
    "RPC-Dyn",
    "MySQL",
    "PostgreSQL",
    "MSSQL",
    "BGP",
    "IPSec-UDP",
    "IPSec-ESP",
)

ACTION_NAMES = ("Permit", "Deny", "Reject")

LABEL_NAMES = (
    "prod",
    "integration-1",
    "integration-2",
    "integration-3",
    "dev-1",
    "dev-2",
    "dev-3",
    "test-1",
    "test-2",
    "test-3",
    "infrastructure",
    "ad",
    "dns",
    "ntp",
    "logging",
    "pki",
    "web",
    "app",
    "db",
    "jump",
    "monitoring",
    "backup",
    "dc",
    "gc",
    "dns-resolver",
    "dns-forwarder",
    "ntp-server",
    "syslog-relay",
    "pki-ca",
    "web-server",
    "app-server",
    "db-primary",
    "db-replica",
    "jump-server",
    "collector",
    "siem",
    "backup-agent",
    "dc-gc",
    "frontend",
    "application",
    "data",
    "management",
)


def _transform_enterprise_source(source: str) -> str:
    verify_start = source.index("# ─── 0. Verify NSM COT types exist ─")
    verify_end = source.index("# ─── 1. Helpers ─")
    preamble = (
        "from security.demos.common import ensure_prerequisites\n"
        "from security.demos.defaults import seed_defaults\n"
        "ensure_prerequisites()\n"
        "seed_defaults(ensure_bundle=False)\n"
        "print('✓ Security bundle COT types present')\n\n"
    )
    source = source[:verify_start] + preamble + source[verify_end:]

    for old_slug, new_slug in NSM_TO_SECURITY_SLUG.items():
        source = source.replace(f'"{old_slug}"', f'"{new_slug}"')

    return source


def run_enterprise_demo(*, recreate: bool = False) -> None:
    """Run the upstream Enterprise DC import against Security bundle COT slugs."""
    ensure_prerequisites()
    seed_defaults(ensure_bundle=False)

    if not recreate and Site.objects.filter(slug=ENTERPRISE_SITE_SLUG).exists():
        raise RuntimeError(
            f"Enterprise demo site {ENTERPRISE_SITE_SLUG!r} already exists. "
            "Use --recreate or purge the demo first."
        )
    if IPAddress.objects.exists() and not recreate:
        raise RuntimeError(
            "Enterprise demo cannot run: IP addresses already exist. "
            "Use --recreate after purge or on an empty IPAM."
        )

    patch_object_link_slug()
    source = _transform_enterprise_source(
        enterprise_import_path().read_text(encoding="utf-8")
    )
    exec_enterprise_script(source)


def _delete_model_rows(model, names: tuple[str, ...]) -> int:
    deleted, _ = model.objects.filter(name__in=names).delete()
    return deleted


def _delete_policy_links_for_zones(link_model, zone_model) -> int:
    zones = {
        zone.pk: zone
        for zone in zone_model.objects.filter(name__in=ZONE_NAMES)
    }
    if not zones:
        return 0
    to_delete = []
    for link in link_model.objects.all().iterator():
        policy = getattr(link, "policy_object", None)
        if policy is not None and policy.pk in zones:
            to_delete.append(link.pk)
    if not to_delete:
        return 0
    deleted, _ = link_model.objects.filter(pk__in=to_delete).delete()
    return deleted


def delete_enterprise_demo(*, include_dcim: bool = False) -> dict[str, int]:
    """Remove Enterprise demo NSM objects; optionally remove site dc-01 and IPAM."""
    ensure_prerequisites(apply_schema=False)
    deleted = {
        "zones": 0,
        "addresses": 0,
        "labels": 0,
        "services": 0,
        "actions": 0,
        "object_links": 0,
        "site": 0,
    }

    zone_model, _ = get_cot_model(SLUG_ZONE)
    addr_model, _ = get_cot_model(SLUG_ADDRESS)
    label_model, _ = get_cot_model(SLUG_LABEL)
    service_model, _ = get_cot_model(SLUG_SERVICE)
    action_model, _ = get_cot_model(SLUG_ACTION)
    link_model, _ = get_cot_model(SLUG_OBJECT_LINK)

    with transaction.atomic():
        deleted["object_links"] = _delete_policy_links_for_zones(link_model, zone_model)
        deleted["zones"] = _delete_model_rows(zone_model, ZONE_NAMES)
        deleted["addresses"] = _delete_model_rows(addr_model, ADDRESS_NAMES)
        deleted["labels"] = _delete_model_rows(label_model, LABEL_NAMES)
        deleted["services"] = _delete_model_rows(service_model, SERVICE_NAMES)
        deleted["actions"] = _delete_model_rows(action_model, ACTION_NAMES)

        if include_dcim:
            site = Site.objects.filter(slug=ENTERPRISE_SITE_SLUG).first()
            if site is not None:
                deleted["site"], _ = site.delete()

    return deleted


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("apply", "purge"))
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="On apply: allow import even if dc-01 / IPs already exist",
    )
    parser.add_argument(
        "--include-dcim",
        action="store_true",
        help="On purge: also delete site dc-01 (DCIM/VM/IPAM cascade)",
    )
    args = parser.parse_args(argv)

    if args.command == "apply":
        run_enterprise_demo(recreate=args.recreate)
        print("Enterprise DC demo import finished.")
    else:
        deleted = delete_enterprise_demo(include_dcim=args.include_dcim)
        print(f"Removed enterprise demo: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
