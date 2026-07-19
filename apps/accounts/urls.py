from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .login_view import LoginView

router = DefaultRouter()
router.register(r"admin-users", views.AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("auth/token/", LoginView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/set-password/<str:token>/", views.PasswordSetupView.as_view(), name="auth-set-password"),
    path("locations/colombia/", views.ColombiaLocationsView.as_view(), name="colombia-locations"),
] + router.urls
