# netbox-custom-objects-bundles

> **Technologie-Prototyp — ohne Gewähr**
>
> Dieses Repository ist **nur ein Prototyp**. Es dient dazu, Ideen für Erweiterungen
> des [netbox-custom-objects](https://github.com/christianbur/netbox-custom-objects)-Plugins
> zu zeigen (COT Views, drop-in Bundles, erweiterte Metadaten). Es wird **nicht**
> fehlerfrei betrieben, **nicht** produktionsreif gepflegt und **legt keinen Anspruch**
> auf Vollständigkeit, Stabilität oder Korrektheit. Nutzung auf eigenes Risiko.
>
> Die **Beispiel-Bundles** für den Prototyp liegen **in diesem Repository**:
> [github.com/christianbur/netbox-custom-objects-bundels](https://github.com/christianbur/netbox-custom-objects-bundels)

---

## Was sind Bundles?

Bundles sind Python-Pakete auf dem Dateisystem, die das Custom-Objects-Plugin beim
Start laden kann — ohne separates PyPI-Plugin. Jedes Unterverzeichnis mit
`bundle.yaml` und `__init__.py` ist ein Bundle.

Typischer Mount-Punkt in NetBox:

```text
/opt/netbox/local   ← Inhalt dieses Repos (oder `bundles_path` in PLUGINS_CONFIG)
```

Aktivierung: **Plugins → Custom Objects → Bundles** — danach NetBox-Worker
**neu starten** (Views und URLs werden beim Start registriert).

## Enthaltene Beispiel-Bundles

| Verzeichnis | Kurzbeschreibung |
|-------------|------------------|
| [`security/`](security/) | Policy-COTs (Action, Zone, Address, …), Rulebook-/Matrix-/IP-Analyzer-COT-Views, vendored Rule-Layout und IP-Analysis-APIs |
| [`ipam_tree/`](ipam_tree/) | IPAM-Baum als COT-View |
| [`cisco_aci/`](cisco_aci/) | Cisco ACI COT-Schema (Demonstration) |
| [`cisco_catalyst_center/`](cisco_catalyst_center/) | Cisco Catalyst Center COT-Schema |
| [`cisco_meraki/`](cisco_meraki/) | Cisco Meraki COT-Schema |

Demos für das Security-Bundle (sofern vorhanden): Skripte unter
`security/demos/` — siehe Homelab-Setup bzw. Plugin-Prototyp-Doku.

## Voraussetzungen

- Prototyp-Build von [netbox-custom-objects](https://github.com/christianbur/netbox-custom-objects)
  (Branch `main`, Commit mit COT Views + Bundle-Support)
- `bundles_path` in `PLUGINS_CONFIG` zeigt auf das Bundle-Root (Default:
  `/opt/netbox/local`)
- `PYTHONPATH` enthält das Bundle-Root, damit Pakete wie `security` importierbar sind

## Installation (Kurz)

```bash
git clone https://github.com/christianbur/netbox-custom-objects-bundels.git /opt/netbox/local
# oder: nur Unterverzeichnisse symlinken / bind-mounten
```

NetBox-Migrationen für `netbox_custom_objects` ausführen, gewünschte Bundles in der
UI aktivieren, Worker neu starten.

## Lizenz / Herkunft

Teile des `security/`-Bundles stammen konzeptionell aus netbox-nsm-Demo-Logik und
wurden für den Prototyp vendored. Cisco-Schemas sind Illustrationsmaterial für
portable-schema-Bundles — keine offizielle Cisco-Unterstützung.
