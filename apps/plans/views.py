from django.db import transaction
from django.db.models import Max, Q
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils.text import slugify
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
            queryset = queryset.filter(
                is_active=True,
                catalog_status=Plan.CatalogStatus.PUBLISHED,
                visibility=Plan.Visibility.PUBLIC,
            )
        plan_type = self.request.query_params.get("plan_type")
        catalog_status = self.request.query_params.get("catalog_status")
        category = self.request.query_params.get("category")
        if plan_type:
            queryset = queryset.filter(plan_type=plan_type)
        if catalog_status and (self.request.user.is_superuser or self.request.user.admin_role == "superadmin"):
            queryset = queryset.filter(catalog_status=catalog_status)
        if category:
            queryset = queryset.filter(category_id=category)
        return queryset

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        plan = self.get_object()
        serializer = self.get_serializer(plan, data={"catalog_status": Plan.CatalogStatus.PUBLISHED}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        root = plan.parent_plan or plan
        Plan.objects.filter(
            Q(pk=root.pk) | Q(parent_plan=root),
            catalog_status=Plan.CatalogStatus.PUBLISHED,
        ).exclude(pk=plan.pk).update(catalog_status=Plan.CatalogStatus.RETIRED)
        if not plan.is_active:
            plan.is_active = True
            plan.save(update_fields=["is_active", "updated_at"])
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        plan = self.get_object()
        plan.catalog_status = Plan.CatalogStatus.RETIRED
        plan.save(update_fields=["catalog_status", "updated_at"])
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        plan = self.get_object()
        plan.catalog_status = Plan.CatalogStatus.ARCHIVED
        plan.is_active = False
        plan.save(update_fields=["catalog_status", "is_active", "updated_at"])
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        source = self.get_object()
        fields = [field.name for field in Plan._meta.concrete_fields if field.name not in {"id", "created_at", "updated_at"}]
        data = {field: getattr(source, field) for field in fields}
        data["code"] = f"{slugify(source.code)[:44] or 'plan'}-copia"
        suffix = 2
        base_code = data["code"]
        while Plan.objects.filter(code=data["code"]).exists():
            data["code"] = f"{base_code[:47]}-{suffix}"
            suffix += 1
        data["name"] = f"{source.name} (copia)"
        data["catalog_status"] = Plan.CatalogStatus.DRAFT
        data["visibility"] = Plan.Visibility.PRIVATE
        data["is_active"] = False
        data["parent_plan"] = None
        data["version_number"] = 1
        duplicate = Plan.objects.create(**data)
        return Response(self.get_serializer(duplicate).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="new-version")
    def new_version(self, request, pk=None):
        source = self.get_object()
        root = source.parent_plan or source
        latest_version = Plan.objects.filter(parent_plan=root).aggregate(value=Max("version_number"))["value"] or root.version_number
        version_number = max(root.version_number, latest_version) + 1

        fields = [field.name for field in Plan._meta.concrete_fields if field.name not in {"id", "created_at", "updated_at"}]
        data = {field: getattr(source, field) for field in fields}
        data["parent_plan"] = root
        data["version_number"] = version_number
        data["code"] = f"{slugify(root.code)[:43]}-v{version_number}"
        suffix = 2
        base_code = data["code"]
        while Plan.objects.filter(code=data["code"]).exists():
            data["code"] = f"{base_code[:46]}-{suffix}"
            suffix += 1
        data["catalog_status"] = Plan.CatalogStatus.DRAFT
        data["visibility"] = Plan.Visibility.PRIVATE
        data["is_active"] = False
        version = Plan.objects.create(**data)
        return Response(self.get_serializer(version).data, status=status.HTTP_201_CREATED)

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
