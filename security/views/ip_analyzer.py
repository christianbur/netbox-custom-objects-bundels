"""IP Analyzer COT view.

A self-contained analogue of the netbox-nsm IP analysis
(``netbox_nsm.analysis`` — address merge / IP-tree building): for an Address COT
it resolves every Address object's referenced NetBox IPAM object
(IPAddress / IPRange / Prefix) and merges them into a containment tree
(prefixes as parents, contained hosts / ranges / sub-prefixes as children),
plus a type summary.

The analysis runs over the *real* objects of the Address COT the tab is shown
on, and the currently-viewed address is highlighted in the tree.

Bound dynamically via the COT ``views`` field (``nsm_ip_analyzer``).
"""

import ipaddress

from netbox_custom_objects.cot_views import COTView, register_cot_view

from .helpers import object_link, object_value, rule_queryset

ADDRESS_FIELD = "address"


def _ipam_node(addr_obj):
    """Resolve one Address object into an analysis node (or ``None``)."""
    ipam = object_value(addr_obj, ADDRESS_FIELD)
    node = {
        "pk": addr_obj.pk,
        "label": object_link(addr_obj)["label"],
        "url": object_link(addr_obj)["url"],
        "kind": "unresolved",
        "cidr": "",
        "ipam_url": "",
        "net": None,        # ip_network for prefixes
        "host": None,       # ip_address for hosts
        "range": None,      # (start, end) ip_address tuple for ranges
    }
    if ipam is None:
        return node

    node["ipam_url"] = object_link(ipam)["url"]
    model_name = getattr(getattr(ipam, "_meta", None), "model_name", "")
    try:
        if model_name == "prefix":
            cidr = str(ipam.prefix)
            node["kind"] = "prefix"
            node["cidr"] = cidr
            node["net"] = ipaddress.ip_network(cidr, strict=False)
        elif model_name == "iprange":
            start = str(ipam.start_address).split("/")[0]
            end = str(ipam.end_address).split("/")[0]
            node["kind"] = "range"
            node["cidr"] = f"{start} – {end}"
            node["range"] = (ipaddress.ip_address(start), ipaddress.ip_address(end))
        elif model_name == "ipaddress":
            cidr = str(ipam.address)
            host = cidr.split("/")[0]
            node["kind"] = "ip"
            node["cidr"] = cidr
            node["host"] = ipaddress.ip_address(host)
    except Exception:
        node["kind"] = "unresolved"
    return node


def _node_in_net(node, net):
    """Whether *node* falls entirely within prefix network *net*."""
    if net is None:
        return False
    try:
        if node["host"] is not None:
            return node["host"] in net
        if node["range"] is not None:
            return node["range"][0] in net and node["range"][1] in net
        if node["net"] is not None and node["net"] is not net:
            return node["net"].version == net.version and node["net"].subnet_of(net)
    except Exception:
        return False
    return False


@register_cot_view
class IPAnalyzerCOTView(COTView):
    key = "security_ip_analyzer"
    label = "IP Analyzer"
    weight = 2300

    def _build_tree(self, cot, current_pk):
        nodes = [_ipam_node(obj) for obj in rule_queryset(cot)]
        for node in nodes:
            node["is_current"] = node["pk"] == current_pk

        prefixes = [n for n in nodes if n["kind"] == "prefix"]
        # Smallest (longest-prefix) containers first so children attach to the
        # most specific covering prefix.
        prefixes.sort(key=lambda n: n["net"].prefixlen, reverse=True)

        children = {id(p): [] for p in prefixes}
        contained = set()

        def _smallest_container(node):
            for prefix in prefixes:
                if _node_in_net(node, prefix["net"]):
                    return prefix
            return None

        for node in nodes:
            if node["kind"] == "unresolved":
                continue
            container = _smallest_container(node)
            if container is not None:
                children[id(container)].append(node)
                contained.add(node["pk"])

        # Roots: prefixes with no containing prefix + non-prefix orphans.
        roots = [
            n
            for n in nodes
            if n["kind"] != "unresolved" and n["pk"] not in contained
        ]
        roots.sort(key=lambda n: (n["kind"] != "prefix", n["cidr"]))

        rows = []

        def _emit(node, depth):
            rows.append({"depth": depth, "node": node})
            kids = children.get(id(node), [])
            kids.sort(key=lambda n: (n["kind"] != "prefix", n["cidr"]))
            for kid in kids:
                _emit(kid, depth + 1)

        for root in roots:
            _emit(root, 0)

        summary = {
            "prefixes": sum(1 for n in nodes if n["kind"] == "prefix"),
            "ranges": sum(1 for n in nodes if n["kind"] == "range"),
            "ips": sum(1 for n in nodes if n["kind"] == "ip"),
            "unresolved": sum(1 for n in nodes if n["kind"] == "unresolved"),
            "total": len(nodes),
        }
        return rows, summary

    def get_context(self, request, cot, instance):
        context = super().get_context(request, cot, instance)
        rows, summary = self._build_tree(cot, instance.pk)
        context["tree_rows"] = rows
        context["summary"] = summary
        return context

    def get_collection_context(self, request, cot, queryset):
        context = super().get_collection_context(request, cot, queryset)
        rows, summary = self._build_tree(cot, None)
        context["tree_rows"] = rows
        context["summary"] = summary
        return context

    template_string = """{% extends base_template %}
{% load i18n %}
{% block content %}
<div class="row mb-3">
  <div class="col"><div class="card text-center"><div class="card-body"><h3 class="mb-0">{{ summary.total }}</h3><small class="text-muted">{% trans "Addresses" %}</small></div></div></div>
  <div class="col"><div class="card text-center"><div class="card-body"><h3 class="mb-0">{{ summary.prefixes }}</h3><small class="text-muted">{% trans "Prefixes" %}</small></div></div></div>
  <div class="col"><div class="card text-center"><div class="card-body"><h3 class="mb-0">{{ summary.ranges }}</h3><small class="text-muted">{% trans "Ranges" %}</small></div></div></div>
  <div class="col"><div class="card text-center"><div class="card-body"><h3 class="mb-0">{{ summary.ips }}</h3><small class="text-muted">{% trans "IPs" %}</small></div></div></div>
  <div class="col"><div class="card text-center"><div class="card-body"><h3 class="mb-0">{{ summary.unresolved }}</h3><small class="text-muted">{% trans "Unresolved" %}</small></div></div></div>
</div>
<div class="card">
  <h5 class="card-header"><i class="mdi mdi-file-tree"></i> {{ cot_view_label }} — {% trans "Merged IP tree" %}</h5>
  <div class="table-responsive">
  <table class="table table-hover">
    <thead>
      <tr>
        <th>{% trans "Address object" %}</th>
        <th>{% trans "Type" %}</th>
        <th>{% trans "Network / IP" %}</th>
      </tr>
    </thead>
    <tbody>
      {% for row in tree_rows %}
        <tr{% if row.node.is_current %} class="table-active"{% endif %}>
          <td style="padding-left: {{ row.depth }}.5rem;">
            {% if row.depth %}<i class="mdi mdi-subdirectory-arrow-right text-muted"></i> {% endif %}
            {% if row.node.url %}<a href="{{ row.node.url }}">{{ row.node.label }}</a>{% else %}{{ row.node.label }}{% endif %}
          </td>
          <td>
            {% if row.node.kind == "prefix" %}<span class="badge text-bg-blue">{% trans "Prefix" %}</span>
            {% elif row.node.kind == "range" %}<span class="badge text-bg-cyan">{% trans "Range" %}</span>
            {% elif row.node.kind == "ip" %}<span class="badge text-bg-green">{% trans "IP" %}</span>
            {% else %}<span class="badge text-bg-grey">{% trans "Unresolved" %}</span>{% endif %}
          </td>
          <td>{% if row.node.ipam_url %}<a href="{{ row.node.ipam_url }}">{{ row.node.cidr }}</a>{% else %}<span class="text-muted">{{ row.node.cidr|default:"—" }}</span>{% endif %}</td>
        </tr>
      {% empty %}
        <tr><td colspan="3" class="text-muted">{% trans "No address objects resolve to a NetBox IPAM object yet." %}</td></tr>
      {% endfor %}
    </tbody>
  </table>
  </div>
</div>
{% endblock %}
"""
