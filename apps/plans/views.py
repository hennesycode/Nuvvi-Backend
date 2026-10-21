from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import ValidationError
from .models import Plan, PlanCategory
from .serializers import PlanCategorySerializer, PlanSerializer


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.admin_role == "superadmin"))


class PlanViewSet(ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def get_permissions(self):
        permission = IsAuthenticated if self.action in ("list", "retrieve") else IsSuperAdmin
        return [permission()]

    def get_queryset(self):
        queryset = Plan.objects.all()
        user = self.request.user
        if not (user.is_superuser or user.admin_role == "superadmin"):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_destroy(self, instance):
        if instance.subscriptions.exists():
            raise ValidationError("Este plan tiene suscripciones asociadas. Desactívalo para conservar el historial comercial.")
        instance.delete()


class PlanCategoryViewSet(ModelViewSet):
    queryset = PlanCategory.objects.all()
    serializer_class = PlanCategorySerializer
    permission_classes = [IsSuperAdmin]

    def perform_destroy(self, instance):
        if instance.plans.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("No puedes eliminar una categoría que tiene planes. Asigna otra categoría primero.")
        instance.delete()
