from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"tenants", views.TenantViewSet, basename="tenant")
router.register(r"tenant-users", views.TenantUserViewSet, basename="tenant-user")
urlpatterns = router.urls
