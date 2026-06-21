#!/usr/bin/env python3
"""Starter demo: 250×250 zone matrix on ``security-rulebook`` (random Permit/Deny).

Run inside netbox-dev::

    python3 /opt/netbox/local/security/demos/starter.py apply
    python3 /opt/netbox/local/security/demos/starter.py purge

From the repo host::

    ./scripts/security-demo.sh starter apply --recreate
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

import random

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from security.demos.common import (
    SLUG_ACTION,
    SLUG_RULEBOOK,
    SLUG_ZONE,
    ensure_prerequisites,
    get_cot,
    get_cot_model,
    get_through_model,
    objects_by_lower_name,
)
from security.demos.defaults import seed_defaults

DEMO_GRID_SIZE = 250
DEMO_ZONE_COUNT = 250
DEMO_RULE_COUNT = DEMO_GRID_SIZE * DEMO_GRID_SIZE
DEMO_ACTION_RANDOM_SEED = 7
DEMO_ZONE_NAME_PREFIX = "zone_"
DEMO_RULE_NAME_PREFIX = "demo-rule-"
DEMO_M2M_BATCH_SIZE = 5000
DEMO_RULE_BATCH_SIZE = 1000
DEMO_MARKER = "security-demo:starter"


def _zone_name_width() -> int:
    return max(2, len(str(DEMO_ZONE_COUNT)))


def zone_name(zone_idx: int) -> str:
    return f"{DEMO_ZONE_NAME_PREFIX}{zone_idx + 1:0{_zone_name_width()}d}"


def _matrix_indices(rule_idx: int) -> tuple[int, int]:
    return rule_idx // DEMO_GRID_SIZE, rule_idx % DEMO_GRID_SIZE


def _starter_rule_queryset(model):
    return model.objects.filter(description=DEMO_MARKER)


def _ensure_demo_zones():
    zone_model, _ = get_cot_model(SLUG_ZONE)
    zones = []
    for zone_idx in range(DEMO_ZONE_COUNT):
        zone, _ = zone_model.objects.get_or_create(
            name=zone_name(zone_idx),
            defaults={"comments": DEMO_MARKER},
        )
        zones.append(zone)
    return zones


def _bulk_seed_matrix_relations(
    *,
    cot,
    rules,
    zones,
    actions_by_name: dict,
    act_rng: random.Random,
) -> None:
    zone_ct_id = ContentType.objects.get_for_model(zones[0]).pk
    fallback_action = next(iter(actions_by_name.values()), None)

    for field_name, zone_index in (("source", 0), ("destination", 1)):
        through = get_through_model(cot, field_name)
        rows = [
            through(
                source_id=rule.pk,
                content_type_id=zone_ct_id,
                object_id=zones[_matrix_indices(rule_idx)[zone_index]].pk,
            )
            for rule_idx, rule in enumerate(rules)
        ]
        through.objects.bulk_create(rows, batch_size=DEMO_M2M_BATCH_SIZE)

    if not fallback_action:
        return

    actions_through = get_through_model(cot, "actions")
    action_rows = []
    for rule in rules:
        action_key = "permit" if act_rng.random() < 0.5 else "deny"
        action = actions_by_name.get(action_key) or fallback_action
        action_rows.append(
            actions_through(source_id=rule.pk, target_id=action.pk)
        )
    actions_through.objects.bulk_create(action_rows, batch_size=DEMO_M2M_BATCH_SIZE)


def _create_starter_rules(*, recreate: bool):
    cot = get_cot(SLUG_RULEBOOK)
    model = cot.get_model()
    if recreate:
        _starter_rule_queryset(model).delete()

    if _starter_rule_queryset(model).exists():
        return cot

    zones = _ensure_demo_zones()
    actions_by_name = objects_by_lower_name(SLUG_ACTION)
    if not actions_by_name:
        seed_defaults(ensure_bundle=False)
        actions_by_name = objects_by_lower_name(SLUG_ACTION)

    act_rng = random.Random(DEMO_ACTION_RANDOM_SEED)
    rules = model.objects.bulk_create(
        [
            model(
                index=rule_idx + 1,
                status=True,
                name=(
                    f"{DEMO_RULE_NAME_PREFIX}"
                    f"{zone_name(src_i)}-to-{zone_name(dst_i)}"
                ),
                description=DEMO_MARKER,
            )
            for rule_idx in range(DEMO_RULE_COUNT)
            for src_i, dst_i in [_matrix_indices(rule_idx)]
        ],
        batch_size=DEMO_RULE_BATCH_SIZE,
    )

    _bulk_seed_matrix_relations(
        cot=cot,
        rules=rules,
        zones=zones,
        actions_by_name=actions_by_name,
        act_rng=act_rng,
    )
    return cot


def run_starter_demo(*, recreate: bool = False):
    """Seed defaults (if needed) and populate ``security-rulebook`` with the matrix."""
    ensure_prerequisites()
    seed_defaults(ensure_bundle=False)
    with transaction.atomic():
        return _create_starter_rules(recreate=recreate)


def delete_starter_demo(*, include_zones: bool = True) -> dict[str, int]:
    """Remove starter matrix rules and optionally the generated demo zones."""
    ensure_prerequisites(apply_schema=False)
    deleted = {"rules": 0, "zones": 0}

    rule_model, _ = get_cot_model(SLUG_RULEBOOK)
    deleted["rules"], _ = _starter_rule_queryset(rule_model).delete()

    if include_zones:
        zone_model, _ = get_cot_model(SLUG_ZONE)
        deleted["zones"], _ = zone_model.objects.filter(comments=DEMO_MARKER).delete()

    return deleted


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("apply", "purge"))
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="On apply: delete existing starter demo rows first",
    )
    parser.add_argument(
        "--keep-zones",
        action="store_true",
        help="On purge: remove rules but keep zone_* rows",
    )
    args = parser.parse_args(argv)

    if args.command == "apply":
        cot = run_starter_demo(recreate=args.recreate)
        print(
            f"Starter demo ready on {cot.slug}: "
            f"{DEMO_ZONE_COUNT} zones, {DEMO_RULE_COUNT} rules."
        )
    else:
        deleted = delete_starter_demo(include_zones=not args.keep_zones)
        print(f"Removed starter demo: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
