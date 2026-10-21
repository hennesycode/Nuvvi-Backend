from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.billing.views import BillingAlertViewSet, DigitalCertificateViewSet, DocumentConsumptionRuleViewSet, DocumentRechargePackageViewSet, DocumentUsageRecordViewSet, ProviderCapacityPoolViewSet, SubscriptionModuleBalanceViewSet

billing_router = DefaultRouter()
billing_router.register("billing/provider-capacity", ProviderCapacityPoolViewSet, basename="provider-capacity")
billing_router.register("billing/module-balances", SubscriptionModuleBalanceViewSet, basename="module-balance")
billing_router.register("billing/consumption-rules", DocumentConsumptionRuleViewSet, basename="consumption-rule")
billing_router.register("billing/document-usage", DocumentUsageRecordViewSet, basename="document-usage")
billing_router.register("billing/alerts", BillingAlertViewSet, basename="billing-alert")
billing_router.register("billing/certificates", DigitalCertificateViewSet, basename="digital-certificate")
billing_router.register("billing/recharge-packages", DocumentRechargePackageViewSet, basename="recharge-package")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.tenants.urls")),
    path("api/", include("apps.plans.urls")),
    path("api/", include("apps.subscriptions.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.dian.urls")),
    path("api/", include("apps.companies.urls")),
    path("api/", include(billing_router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
