"""Full Rulebook COT view — NSM rule viewer parity.

Uses the vendored Security rule layout, cell modes (comma / lines / +N), grouped
columns, row grouping, pagination, and the floating IP Analyzer applet.
Templates, static assets, and analysis APIs live under ``local/security/``.
"""

from netbox_custom_objects.cot_views import COTView, register_cot_view


@register_cot_view
class RulebookCOTView(COTView):
    key = "security_rulebook"
    label = "Rulebook"
    weight = 2100
    template_name = "security/cot_rulebook_rules.html"

    def _rules_tab_context(self, request, cot):
        from security.rulebooks.cot_hierarchy import build_virtual_cot_rulebook_with_hierarchy
        from security.rulebooks.rules_tab.context import build_cot_rulebook_rules_tab_context

        virtual_rb = build_virtual_cot_rulebook_with_hierarchy(cot, rule_count=0)
        return build_cot_rulebook_rules_tab_context(request, virtual_rb)

    def get_context(self, request, cot, instance):
        context = super().get_context(request, cot, instance)
        context.update(self._rules_tab_context(request, cot))
        return context

    def get_collection_context(self, request, cot, queryset):
        context = super().get_collection_context(request, cot, queryset)
        context.update(self._rules_tab_context(request, cot))
        return context
