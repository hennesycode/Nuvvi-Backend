from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"plans", views.PlanViewSet, basename="plan")
router.register(r"plan-categories", views.PlanCategoryViewSet, basename="plan-category")
router.register(r"capabilities", views.CapabilityViewSet, basename="plan-capability")
router.register(r"plan-bundles", views.PlanBundleViewSet, basename="plan-bundle")
urlpatterns = router.urls
