# netbox-custom-objects-bundles

Local bundle packages for [netbox-custom-objects](https://github.com/christianbur/netbox-custom-objects).

Mount this repository at `/opt/netbox/local` (see `bundles_path` in plugin config).

## Bundles

| Directory | Description |
|-----------|-------------|
| `security/` | Policy COTs, rulebook/matrix/IP-analyzer views, NSM rule layout vendored |
| `ipam_tree/` | IPAM tree COT view |
| `cisco_aci/` | Cisco ACI integration bundle |
| `cisco_catalyst_center/` | Cisco Catalyst Center bundle |
| `cisco_meraki/` | Cisco Meraki bundle |

Enable bundles in NetBox under **Plugins → Custom Objects → Bundles**.
