from django.urls import path

from .views import CompanyArchiveView, CompanyCatalogsView, CompanyDetailView, CompanyDisableProviderView, CompanyEnableProviderView, CompanyListCreateView, CompanyProviderSyncStatusView, CompanyReconcileView, CompanySettingsView, CompanyStatsView, CompanySyncView

urlpatterns = [
    path("admin/companies/", CompanyListCreateView.as_view(), name="admin-companies"),
    path("admin/companies/catalogs/", CompanyCatalogsView.as_view(), name="admin-company-catalogs"),
    path("admin/companies/provider-sync-status/", CompanyProviderSyncStatusView.as_view(), name="admin-company-provider-sync-status"),
    path("admin/companies/reconcile/", CompanyReconcileView.as_view(), name="admin-company-reconcile"),
    path("admin/companies/<uuid:pk>/", CompanyDetailView.as_view(), name="admin-company-detail"),
    path("admin/companies/<uuid:pk>/sync/", CompanySyncView.as_view(), name="admin-company-sync"),
    path("admin/companies/<uuid:pk>/enable-provider/", CompanyEnableProviderView.as_view(), name="admin-company-enable-provider"),
    path("admin/companies/<uuid:pk>/disable-provider/", CompanyDisableProviderView.as_view(), name="admin-company-disable-provider"),
    path("admin/companies/<uuid:pk>/archive/", CompanyArchiveView.as_view(), name="admin-company-archive"),
    path("admin/companies/<uuid:pk>/stats/", CompanyStatsView.as_view(), name="admin-company-stats"),
    path("admin/companies/<uuid:pk>/settings/", CompanySettingsView.as_view(), name="admin-company-settings"),
]
