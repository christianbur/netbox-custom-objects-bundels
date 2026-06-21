#!/usr/bin/env python3
"""Address bench (50,000 addresses) for the Security bundle.

Wraps ``netbox_nsm.demos.addresses_million_scale`` with Security COT slugs
(``security-address``, ``security-rulebook``, …) instead of ``nsm_*`` /
``nsm_rb_bench_addresses``.

Run inside netbox-dev::

    python3 /opt/netbox/local/security/demos/address_bench.py apply
    python3 /opt/netbox/local/security/demos/address_bench.py purge

From the repo host::

    ./scripts/security-demo.sh address_bench apply
"""

from __future__ import annotations

from typing import Any

if __name__ == "__main__":
    import importlib.util
    from pathlib import Path

    _boot_path = Path(__file__).resolve().with_name("_bootstrap.py")
    _spec = importlib.util.spec_from_file_location("_security_demo_bootstrap", _boot_path)
    _boot = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_boot)
    _boot.setup_django()

from security.demos.common import SLUG_RULEBOOK, ensure_prerequisites, get_cot
from security.demos.defaults import seed_defaults

_PATCHED = False


def _apply_security_patches() -> None:
    """Point the NSM bench generator at Security bundle COTs."""
    global _PATCHED
    if _PATCHED:
        return

    import netbox_nsm.demos.addresses_million_scale as ams
    import netbox_nsm.demos.cot_demo_common as cdc

    from security.demos.common import NSM_TO_SECURITY_SLUG, get_cot_model

    _original_get_cot_model = cdc.get_cot_model
    _original_ensure_prerequisites = cdc.ensure_nsm_prerequisites
    _original_ensure_bench_rulebook = ams._ensure_bench_rulebook

    def security_get_cot_model(*slugs: str):
        mapped = tuple(NSM_TO_SECURITY_SLUG.get(slug, slug) for slug in slugs)
        return get_cot_model(*mapped)

    def security_ensure_prerequisites() -> None:
        ensure_prerequisites()
        seed_defaults(ensure_bundle=False)

    def security_ensure_bench_rulebook(slug: str):
        if slug == SLUG_RULEBOOK:
            return get_cot(SLUG_RULEBOOK)
        return _original_ensure_bench_rulebook(slug)

    cdc.get_cot_model = security_get_cot_model
    cdc.ensure_nsm_prerequisites = security_ensure_prerequisites
    ams.get_cot_model = security_get_cot_model
    ams.ensure_nsm_prerequisites = security_ensure_prerequisites
    ams._ensure_bench_rulebook = security_ensure_bench_rulebook
    _PATCHED = True


def run_address_bench_50k(*, recreate: bool = True) -> dict[str, Any]:
    """Create 50k bench addresses + proportional rules on ``security-rulebook``."""
    from netbox_nsm.demos.addresses_million_scale import (
        SCALE_DEMO_50K_LEAF_COUNT,
        SCALE_DEMO_50K_RULE_COUNT,
    )

    print(
        f"Creating address bench: {SCALE_DEMO_50K_LEAF_COUNT:,} leaves, "
        f"~{SCALE_DEMO_50K_RULE_COUNT:,} rules on {SLUG_RULEBOOK} "
        "(this runs in one DB transaction and can take 15–45 minutes; "
        "RuntimeWarning lines about through-models are harmless).",
        flush=True,
    )
    _apply_security_patches()
    from netbox_nsm.demos.addresses_million_scale import create_addresses_million_scale

    return create_addresses_million_scale(
        rulebook_slug=SLUG_RULEBOOK,
        leaf_count=SCALE_DEMO_50K_LEAF_COUNT,
        rule_count=SCALE_DEMO_50K_RULE_COUNT,
        recreate_rules=recreate,
    )


def delete_address_bench_50k() -> dict[str, Any]:
    """Remove bench-* addresses, groups, zones, rules, and linked IPAM rows."""
    _apply_security_patches()
    from netbox_nsm.demos.addresses_million_scale import purge_bench_data

    return purge_bench_data(rulebook_slug=SLUG_RULEBOOK)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import warnings

    # Harmless when demo scripts call cot.get_model() after types are already loaded.
    warnings.filterwarnings(
        "ignore",
        message=r"Model 'netbox_custom_objects\.through_.*' was already registered.*",
        category=RuntimeWarning,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("apply", "purge"))
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="On apply: replace existing bench-rule-* rows before creating rules",
    )
    args = parser.parse_args(argv)

    if args.command == "apply":
        summary = run_address_bench_50k(recreate=args.recreate)
        print(
            f"Address bench on {summary['rulebook_slug']}: "
            f"{summary['leaves']:,} leaves, {summary['rules']:,} rules, "
            f"{summary['elapsed_s']}s"
        )
        if summary.get("overlap_demo_rules"):
            first = summary["overlap_demo_rules"][0]["name"]
            print(f"Overlap demos: rules 1–20 — open IPA on {first} source/destination")
    else:
        summary = delete_address_bench_50k()
        print(
            "Purged address bench: "
            f"{summary['rules_deleted']} rules, "
            f"{summary['addresses_deleted']} addresses, "
            f"{summary['groups_deleted']} groups, "
            f"{summary['zones_deleted']} zones, "
            f"{summary['ip_addresses_deleted']} IPs, "
            f"{summary['prefixes_deleted']} prefixes "
            f"({summary['elapsed_s']}s)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
