"""Security bundle JSON APIs (IP Analyzer applet)."""

from django.urls import path

from security.api_views.ip_analysis_add_object_api import IpAnalysisAddObjectTypesApiView
from security.api_views.ip_analysis_api import IpAnalysisApiView
from security.api_views.ip_analysis_category_api import IpAnalysisCategoryApiView
from security.api_views.ip_analysis_object_api import IpAnalysisObjectDrilldownApiView

urlpatterns = [
    path(
        "bundle-api/security/ip-analysis/",
        IpAnalysisApiView.as_view(),
        name="security_ip_analysis_api",
    ),
    path(
        "bundle-api/security/ip-analysis/category/",
        IpAnalysisCategoryApiView.as_view(),
        name="security_ip_analysis_category_api",
    ),
    path(
        "bundle-api/security/ip-analysis/object/",
        IpAnalysisObjectDrilldownApiView.as_view(),
        name="security_ip_analysis_object_api",
    ),
    path(
        "bundle-api/security/ip-analysis/add-object-types/",
        IpAnalysisAddObjectTypesApiView.as_view(),
        name="security_ip_analysis_add_object_types_api",
    ),
]
