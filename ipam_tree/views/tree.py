"""IPAM Tree COT view (object-proxy demo).

Renders a live, read-only IPAM hierarchy for a *proxy* Custom Object Type as a
NetBox-style **tree table**:

  * ``ipam/prefix`` objects are the rows (nested by NetBox prefix containment);
    the first column keeps the tree indentation + expand/collapse caret, while
    the remaining columns (Tenant, Status, VRF, Role, VLAN, Children,
    Description) are aligned like a normal table.
  * ``ipam/iprange`` objects are counted per containing prefix.
  * ``ipam/ipaddress`` objects are placed under the smallest prefix that
    contains them and rendered as a per-prefix collapsible sub-list that starts
    collapsed.

Everything is built per-request from RBAC-restricted public querysets — no
folderview internals, no writes.  The COT -> view binding is fully dynamic:
this view is selected via the COT's ``views`` field (``views: ipam_tree`` in the
bundled schema), and the proxied model comes from the COT's ``object_proxy``
field (``related_object_type: ipam/prefix``).

All plugin-specific markup/CSS/JS lives here (inline ``template_string``); none
of it leaks into the netbox-custom-objects core plugin.
"""

import ipaddress

from django.utils.html import format_html
from django.utils.safestring import mark_safe

from netbox_custom_objects.cot_views import COTView, register_cot_view

# Number of data columns after the prefix column (used for colspan on IP rows).
_COLSPAN = 8
# Indentation step per tree level, in rem.
_INDENT_REM = 1.25


def _to_network(value):
    """Return an ``ipaddress`` network for a NetBox prefix value, or ``None``."""
    try:
        return ipaddress.ip_network(str(value), strict=False)
    except (ValueError, TypeError):
        return None


def _to_address(value):
    """Return an ``ipaddress`` address for a NetBox IP value, or ``None``."""
    try:
        # NetBox stores host addresses with a mask (e.g. "10.0.0.1/24").
        return ipaddress.ip_interface(str(value)).ip
    except (ValueError, TypeError):
        return None


def _pluralize(count, singular, plural):
    return singular if count == 1 else plural


@register_cot_view
class IpTreeCOTView(COTView):
    key = "ipam_tree"
    label = "IP Tree"
    weight = 2100

    template_string = """{% extends base_template %}
{% load i18n %}
{% block proxy_content %}
<div class="alert alert-info" role="alert">
  <i class="mdi mdi-file-tree"></i>
  {% blocktrans trimmed %}
    Read-only IPAM tree — prefixes are the rows and IP addresses are collapsible
    leaves. Nothing on this page is stored as a custom object.
  {% endblocktrans %}
</div>
<div class="card">
  <div class="card-header d-flex justify-content-between align-items-center">
    <span>{{ cot_view_label }}</span>
    <span class="d-flex align-items-center gap-3">
      <button type="button" id="ipam-mask-toggle" class="btn btn-sm btn-outline-secondary">
        <i class="mdi mdi-swap-horizontal"></i> {% trans "Show dotted mask" %}
      </button>
      <span class="text-secondary">
        {% blocktrans trimmed count counter=prefix_count %}
          {{ prefix_count }} prefix
        {% plural %}
          {{ prefix_count }} prefixes
        {% endblocktrans %}
        &middot;
        {% blocktrans trimmed count counter=range_count %}
          {{ range_count }} range
        {% plural %}
          {{ range_count }} ranges
        {% endblocktrans %}
        &middot;
        {% blocktrans trimmed count counter=address_count %}
          {{ address_count }} address
        {% plural %}
          {{ address_count }} addresses
        {% endblocktrans %}
      </span>
    </span>
  </div>
  <div class="card-body p-0">
    <style>
      #ipam-tree-root .pfx-dotted { display: none; }
      #ipam-tree-root.mask-dotted .pfx-cidr { display: none; }
      #ipam-tree-root.mask-dotted .pfx-dotted { display: inline; }
      #ipam-tree-root table { margin-bottom: 0; }
      #ipam-tree-root .ipam-col-prefix { white-space: nowrap; }
      #ipam-tree-root .ipam-counter { font-variant-numeric: tabular-nums; white-space: nowrap; }
      #ipam-tree-root .ipam-toggle {
        border: 0; background: none; padding: 0; margin-right: .25rem; line-height: 1;
        color: var(--bs-secondary-color);
      }
      #ipam-tree-root .ipam-toggle .mdi { transition: transform .1s ease; }
      #ipam-tree-root .ipam-toggle.collapsed .mdi { transform: rotate(-90deg); }
      #ipam-tree-root .ipam-toggle-spacer { display: inline-block; width: 1.1em; }
      #ipam-tree-root .ipam-dot {
        display: inline-block; width: .6rem; height: .6rem; border-radius: 50%;
        margin-right: .35rem; vertical-align: middle;
      }
      #ipam-tree-root .ipam-ip-cell ul { list-style: none; margin: 0; padding-left: .5rem; }
      #ipam-tree-root .ipam-pool { font-size: .75rem; }
    </style>
    <div id="ipam-tree-root" class="table-responsive">
      {{ tree_html }}
    </div>
  </div>
</div>
<script>
  (function () {
    var root = document.getElementById('ipam-tree-root');
    if (!root) { return; }

    // --- mask toggle (CIDR <-> dotted), client-side, no reload ---
    var maskBtn = document.getElementById('ipam-mask-toggle');
    if (maskBtn) {
      maskBtn.addEventListener('click', function () {
        var dotted = root.classList.toggle('mask-dotted');
        maskBtn.innerHTML = dotted
          ? '<i class="mdi mdi-swap-horizontal"></i> {% trans "Show CIDR" %}'
          : '<i class="mdi mdi-swap-horizontal"></i> {% trans "Show dotted mask" %}';
      });
    }

    // --- subtree collapse/expand (rows hidden when any ancestor collapsed) ---
    var collapsed = new Set();
    function applyVisibility() {
      root.querySelectorAll('tr[data-ancestors]').forEach(function (tr) {
        var anc = (tr.getAttribute('data-ancestors') || '').split(' ').filter(Boolean);
        var hide = anc.some(function (a) { return collapsed.has(a); });
        tr.style.display = hide ? 'none' : '';
      });
      root.querySelectorAll('.ipam-toggle').forEach(function (b) {
        b.classList.toggle('collapsed', collapsed.has(b.getAttribute('data-target')));
      });
    }
    root.querySelectorAll('.ipam-toggle').forEach(function (b) {
      b.addEventListener('click', function () {
        var id = b.getAttribute('data-target');
        if (collapsed.has(id)) { collapsed.delete(id); } else { collapsed.add(id); }
        applyVisibility();
      });
    });
  })();
</script>
{% endblock %}
"""

    # ------------------------------------------------------------------
    # Context / data fetching
    # ------------------------------------------------------------------

    def get_proxy_context(self, request, cot, field):
        context = super().get_proxy_context(request, cot, field)
        qs = context.get("object_list")
        # Prefetch the FKs we render per row to avoid N+1 queries.
        if qs is not None and hasattr(qs, "select_related"):
            qs = qs.select_related("vrf", "tenant", "role", "vlan")
            context["object_list"] = qs
        prefixes = list(qs) if qs is not None else []
        addresses = self._get_addresses(request)
        ranges = self._get_ranges(request)
        context["prefix_count"] = len(prefixes)
        context["address_count"] = len(addresses)
        context["range_count"] = len(ranges)
        context["tree_html"] = self._build_tree_html(prefixes, addresses, ranges)
        return context

    def _get_addresses(self, request):
        """RBAC-restricted IP addresses (the collapsible leaves)."""
        try:
            from ipam.models import IPAddress
        except ImportError:
            return []
        qs = IPAddress.objects.all()
        if hasattr(qs, "restrict"):
            qs = qs.restrict(request.user, "view")
        return list(qs)

    def _get_ranges(self, request):
        """RBAC-restricted IP ranges, counted under their containing prefix."""
        try:
            from ipam.models import IPRange
        except ImportError:
            return []
        qs = IPRange.objects.all()
        if hasattr(qs, "restrict"):
            qs = qs.restrict(request.user, "view")
        return list(qs)

    # ------------------------------------------------------------------
    # Per-cell rendering helpers (all plugin-local, table cells not badges)
    # ------------------------------------------------------------------

    @staticmethod
    def _prefix_name(p, net):
        """Network address + both CIDR and (IPv4) dotted-mask suffixes."""
        url = p.get_absolute_url() if hasattr(p, "get_absolute_url") else ""
        netaddr = str(net.network_address)
        if net.version == 4:
            suffix = format_html(
                '<span class="pfx-cidr">/{}</span>'
                '<span class="pfx-dotted">/{}</span>',
                net.prefixlen,
                str(net.netmask),
            )
        else:
            # IPv6: dotted masks are unconventional — always show CIDR.
            suffix = format_html('<span class="pfx-static">/{}</span>', net.prefixlen)
        return format_html('<a href="{}"><strong>{}{}</strong></a>', url, netaddr, suffix)

    @staticmethod
    def _link_cell(obj):
        """A plain linked value for a table cell (no badge), or an empty cell."""
        if not obj:
            return mark_safe('<span class="text-secondary">\u2014</span>')
        name = str(obj)
        url = obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else ""
        if url:
            return format_html('<a href="{}">{}</a>', url, name)
        return format_html("{}", name)

    @staticmethod
    def _status_cell(p):
        status = getattr(p, "status", None)
        if not status:
            return mark_safe('<span class="text-secondary">\u2014</span>')
        color = p.get_status_color() if hasattr(p, "get_status_color") else "secondary"
        display = p.get_status_display() if hasattr(p, "get_status_display") else status
        return format_html(
            '<span class="ipam-dot text-bg-{}"></span>{}', color, display
        )

    @staticmethod
    def _counter_text(subnets, ranges, ips):
        return "{} {} \u00b7 {} {} \u00b7 {} {}".format(
            subnets, _pluralize(subnets, "subnet", "subnets"),
            ranges, _pluralize(ranges, "range", "ranges"),
            ips, _pluralize(ips, "IP", "IPs"),
        )

    # ------------------------------------------------------------------
    # Tree construction (flat pre-order rows + indentation in column 1)
    # ------------------------------------------------------------------

    def _build_tree_html(self, prefixes, addresses, ranges):
        nodes = []
        for p in prefixes:
            net = _to_network(getattr(p, "prefix", None))
            if net is not None:
                nodes.append((p, net))

        if not nodes:
            return mark_safe('<p class="text-secondary p-3">No prefixes to display.</p>')

        # Most-specific first makes "find smallest containing" a simple scan.
        nodes.sort(key=lambda item: (item[1].version, item[1].prefixlen), reverse=True)

        children = {id(p): [] for p, _ in nodes}
        roots = []

        def _find_parent(idx, net):
            best = None
            best_len = -1
            for j, (cand_p, cand_net) in enumerate(nodes):
                if j == idx:
                    continue
                if cand_net.version != net.version:
                    continue
                if cand_net.prefixlen >= net.prefixlen:
                    continue
                if net.subnet_of(cand_net) and cand_net.prefixlen > best_len:
                    best = cand_p
                    best_len = cand_net.prefixlen
            return best

        for idx, (p, net) in enumerate(nodes):
            parent = _find_parent(idx, net)
            if parent is None:
                roots.append((p, net))
            else:
                children[id(parent)].append((p, net))

        def _smallest_containing(ip):
            best = None
            best_len = -1
            for p, net in nodes:
                if net.version != ip.version:
                    continue
                if ip in net and net.prefixlen > best_len:
                    best = p
                    best_len = net.prefixlen
            return best

        leaves = {id(p): [] for p, _ in nodes}
        for addr in addresses:
            ip = _to_address(getattr(addr, "address", None))
            if ip is None:
                continue
            best = _smallest_containing(ip)
            if best is not None:
                leaves[id(best)].append(addr)

        range_counts = {id(p): 0 for p, _ in nodes}
        for r in ranges:
            ip = _to_address(getattr(r, "start_address", None))
            if ip is None:
                continue
            best = _smallest_containing(ip)
            if best is not None:
                range_counts[id(best)] += 1

        def _sort_key(item):
            return (item[1].version, int(item[1].network_address), item[1].prefixlen)

        roots.sort(key=_sort_key)

        # Assign a stable per-prefix uid in pre-order for the collapse JS.
        uids = {}
        counter = {"n": 0}

        rows = []

        def _emit(p, net, depth, ancestors):
            uids[id(p)] = counter["n"]
            counter["n"] += 1
            uid = uids[id(p)]
            anc_attr = " ".join(str(a) for a in ancestors)

            child_items = sorted(children[id(p)], key=_sort_key)
            has_children = bool(child_items) or bool(leaves[id(p)])
            indent = "%.2f" % (depth * _INDENT_REM)

            if has_children:
                toggle = format_html(
                    '<button type="button" class="ipam-toggle" data-target="{}" '
                    'aria-label="Toggle">'
                    '<i class="mdi mdi-chevron-down"></i></button>',
                    uid,
                )
            else:
                toggle = mark_safe('<span class="ipam-toggle-spacer"></span>')

            pool_marker = (
                mark_safe(' <span class="ipam-pool text-secondary">&middot; pool</span>')
                if getattr(p, "is_pool", False) else ""
            )
            desc = (getattr(p, "description", "") or "").strip()

            rows.append(format_html(
                '<tr class="ipam-prefix-row" data-id="{uid}" data-ancestors="{anc}">'
                '<td class="ipam-col-prefix" style="padding-left:{indent}rem">'
                '{toggle}{name}{pool}</td>'
                '<td>{tenant}</td><td>{status}</td><td>{vrf}</td>'
                '<td>{role}</td><td>{vlan}</td>'
                '<td class="ipam-counter text-secondary">{counter}</td>'
                '<td class="text-secondary">{desc}</td>'
                '</tr>',
                uid=uid,
                anc=anc_attr,
                indent=indent,
                toggle=toggle,
                name=self._prefix_name(p, net),
                pool=pool_marker,
                vrf=self._link_cell(getattr(p, "vrf", None)),
                tenant=self._link_cell(getattr(p, "tenant", None)),
                status=self._status_cell(p),
                role=self._link_cell(getattr(p, "role", None)),
                vlan=self._link_cell(getattr(p, "vlan", None)),
                counter=self._counter_text(
                    len(child_items), range_counts[id(p)], len(leaves[id(p)])
                ),
                desc=desc,
            ))

            # Host IPs: a collapsed sub-list row (kept out of the data columns
            # via colspan); hidden together with this prefix when it collapses.
            if leaves[id(p)]:
                leaf_count = len(leaves[id(p)])
                leaf_html = "".join(
                    format_html(
                        '<li><i class="mdi mdi-circle-small"></i> {} '
                        '<a href="{}">{}</a></li>',
                        str(getattr(a, "address", "")),
                        a.get_absolute_url() if hasattr(a, "get_absolute_url") else "",
                        (getattr(a, "description", "") or getattr(a, "dns_name", "") or ""),
                    )
                    for a in addresses_key(leaves[id(p)])
                )
                rows.append(format_html(
                    '<tr class="ipam-ip-row" data-ancestors="{anc}">'
                    '<td colspan="{span}" class="ipam-ip-cell" '
                    'style="padding-left:{indent}rem">'
                    '<details><summary>{count} {label}</summary><ul>{items}</ul></details>'
                    '</td></tr>',
                    anc=anc_attr + (" " if anc_attr else "") + str(uid),
                    span=_COLSPAN + 1,
                    indent="%.2f" % ((depth + 1) * _INDENT_REM),
                    count=leaf_count,
                    label=_pluralize(leaf_count, "IP address", "IP addresses"),
                    items=mark_safe(leaf_html),
                ))

            child_ancestors = ancestors + [uid]
            for cp, cnet in child_items:
                _emit(cp, cnet, depth + 1, child_ancestors)

        for p, net in roots:
            _emit(p, net, 0, [])

        body = mark_safe("".join(rows))
        return format_html(
            '<table class="table table-sm table-hover">'
            '<thead><tr>'
            '<th>{}</th><th>{}</th><th>{}</th><th>{}</th>'
            '<th>{}</th><th>{}</th><th>{}</th><th>{}</th>'
            '</tr></thead><tbody>{}</tbody></table>',
            "Prefix", "Tenant", "Status", "VRF", "Role", "VLAN", "Children", "Description",
            body,
        )


def addresses_key(addresses):
    """Sort IP addresses by their numeric value for stable tree output."""
    def _key(a):
        ip = _to_address(getattr(a, "address", None))
        return (ip.version, int(ip)) if ip is not None else (0, 0)

    return sorted(addresses, key=_key)
