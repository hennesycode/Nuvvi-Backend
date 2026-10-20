from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"plans", views.PlanViewSet, basename="plan")
router.register(r"plan-categories", views.PlanCategoryViewSet, basename="plan-category")
urlpatterns = router.urls
