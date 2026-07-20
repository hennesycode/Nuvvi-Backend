from django.urls import path

from .views import MatiasConnectionView, MatiasGeneratePatView, MatiasRevokeTokenView, MatiasSyncCatalogsView, MatiasTestView, MatiasTokenView

urlpatterns = [
    path("matias/connection/", MatiasConnectionView.as_view(), name="matias-connection"),
    path("matias/token/", MatiasTokenView.as_view(), name="matias-token"),
    path("matias/generate-pat/", MatiasGeneratePatView.as_view(), name="matias-generate-pat"),
    path("matias/revoke-token/", MatiasRevokeTokenView.as_view(), name="matias-revoke-token"),
    path("matias/test/", MatiasTestView.as_view(), name="matias-test"),
    path("matias/sync-catalogs/", MatiasSyncCatalogsView.as_view(), name="matias-sync-catalogs"),
]
