#!/usr/bin/env python3
"""Seed bundled Security defaults (Permit, Deny, UDP/TCP services, …).

Run inside netbox-dev::

    python3 /opt/netbox/local/security/demos/defaults.py apply
    python3 /opt/netbox/local/security/demos/defaults.py purge

From the repo host (no local Django required)::

    ./scripts/security-demo.sh defaults apply
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

from security.demos.common import (
    SLUG_ACTION,
    SLUG_SERVICE,
    SLUG_ZONE,
    ensure_prerequisites,
    get_cot_model,
)

DEFAULT_ACTIONS = (
    {"name": "Permit", "status": "active", "color": "#28a745"},
    {"name": "Deny", "status": "active", "color": "#dc3545"},
    {"name": "Drop", "status": "active", "color": "#6c757d"},
)

DEFAULT_SERVICES = (
    {"name": "HTTP", "status": "active", "protocol": "tcp", "port": 80},
    {"name": "HTTPS", "status": "active", "protocol": "tcp", "port": 443},
    {"name": "DNS-UDP", "status": "active", "protocol": "udp", "port": 53},
    {"name": "DNS-TCP", "status": "active", "protocol": "tcp", "port": 53},
    {"name": "NTP", "status": "active", "protocol": "udp", "port": 123},
    {"name": "SSH", "status": "active", "protocol": "tcp", "port": 22},
    {"name": "RDP", "status": "active", "protocol": "tcp", "port": 3389},
    {"name": "SNMP", "status": "active", "protocol": "udp", "port": 161},
    {"name": "Syslog-UDP", "status": "active", "protocol": "udp", "port": 514},
    {"name": "ICMP", "status": "active", "protocol": "icmp", "port": None},
)

DEFAULT_MARKER = "security-demo-default"


def _upsert(model, *, name: str, payload: dict):
    defaults = dict(payload)
    defaults.setdefault("comments", DEFAULT_MARKER)
    obj, created = model.objects.update_or_create(name=name, defaults=defaults)
    if not created and (obj.comments or "").strip() != DEFAULT_MARKER:
        obj.comments = DEFAULT_MARKER
        for key, value in payload.items():
            setattr(obj, key, value)
        obj.save()
    return obj, created


def seed_defaults(*, ensure_bundle: bool = True) -> dict[str, int]:
    """Create/update default actions and services on Security bundle COTs."""
    if ensure_bundle:
        ensure_prerequisites()

    action_model, _ = get_cot_model(SLUG_ACTION)
    service_model, _ = get_cot_model(SLUG_SERVICE)

    created = {"actions": 0, "services": 0}
    for entry in DEFAULT_ACTIONS:
        _obj, was_created = _upsert(action_model, name=entry["name"], payload=entry)
        created["actions"] += int(was_created)

    for entry in DEFAULT_SERVICES:
        payload = {k: v for k, v in entry.items() if k != "name"}
        _obj, was_created = _upsert(service_model, name=entry["name"], payload=payload)
        created["services"] += int(was_created)

    return created


def delete_defaults(*, ensure_bundle: bool = True) -> dict[str, int]:
    """Remove demo-seeded default actions/services (marked via comments)."""
    if ensure_bundle:
        ensure_prerequisites(apply_schema=False)

    deleted = {"actions": 0, "services": 0}
    action_model, _ = get_cot_model(SLUG_ACTION)
    service_model, _ = get_cot_model(SLUG_SERVICE)

    deleted["actions"], _ = action_model.objects.filter(comments=DEFAULT_MARKER).delete()
    deleted["services"], _ = service_model.objects.filter(comments=DEFAULT_MARKER).delete()
    return deleted


def ensure_starter_zones_exist(zone_count: int, *, name_prefix: str, name_fn) -> list:
    """Create matrix demo zones if missing (does not delete existing rows)."""
    zone_model, _ = get_cot_model(SLUG_ZONE)
    zones = []
    for zone_idx in range(zone_count):
        zone, _ = zone_model.objects.get_or_create(name=name_fn(zone_idx))
        zones.append(zone)
    return zones


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("apply", "purge"))
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="On apply: purge marked defaults before seeding",
    )
    args = parser.parse_args(argv)

    if args.command == "apply":
        if args.recreate:
            deleted = delete_defaults()
            print(f"Removed defaults: {deleted}")
        created = seed_defaults()
        print(f"Seeded defaults: {created}")
    else:
        deleted = delete_defaults()
        print(f"Removed defaults: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
