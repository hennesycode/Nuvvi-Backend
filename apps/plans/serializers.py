import re

from django.db import transaction
from django.db.models import Max
from rest_framework import serializers
from .models import Plan, PlanCategory


class PlanCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanCategory
        fields = ["id", "name", "description", "display_order", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class PlanSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)

    class Meta:
        model = Plan
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "parent_plan", "version_number"]

    def validate_code(self, value):
        value = value.strip()
        if self.instance and value == self.instance.code:
            return value
        if self.instance and self.instance.catalog_status != Plan.CatalogStatus.DRAFT:
            raise serializers.ValidationError("Solo se puede cambiar el código de un borrador.")
        value = value.lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise serializers.ValidationError("Usa letras minúsculas, números y guiones; no puede iniciar ni terminar con guion.")
        return value

    def validate_features(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Las características deben organizarse en secciones.")
        for section in value:
            if not isinstance(section, dict) or not str(section.get("title", "")).strip():
                raise serializers.ValidationError("Cada sección debe tener un título.")
            if not isinstance(section.get("items", []), list):
                raise serializers.ValidationError("Los elementos de cada sección deben ser una lista.")
            for item in section.get("items", []):
                if not isinstance(item, dict) or not str(item.get("title", "")).strip():
                    raise serializers.ValidationError("Cada beneficio debe tener un título.")
        return value

    def validate(self, attrs):
        plan_type = attrs.get("plan_type", getattr(self.instance, "plan_type", Plan.PlanType.INVOICING))
        requires_base_plan = attrs.get("requires_base_plan", getattr(self.instance, "requires_base_plan", False))
        max_employees = attrs.get("max_employees", getattr(self.instance, "max_employees", 0))
        quote_only = attrs.get("quote_only", getattr(self.instance, "quote_only", False))
        catalog_status = attrs.get("catalog_status", getattr(self.instance, "catalog_status", Plan.CatalogStatus.DRAFT))
        visibility = attrs.get("visibility", getattr(self.instance, "visibility", Plan.Visibility.PRIVATE))
        monthly_price = attrs.get("monthly_price", getattr(self.instance, "monthly_price", None))
        yearly_price = attrs.get("yearly_price", getattr(self.instance, "yearly_price", None))

        if self.instance and self.instance.catalog_status != Plan.CatalogStatus.DRAFT:
            contract_fields = set(attrs) - {"is_active", "catalog_status"}
            changed_fields = {
                field for field in contract_fields
                if getattr(self.instance, field) != attrs[field]
            }
            if changed_fields:
                raise serializers.ValidationError({
                    "catalog_status": "Solo se pueden editar borradores. Crea una nueva versión para cambiar una oferta publicada y conservar las condiciones contratadas."
                })
        if catalog_status == Plan.CatalogStatus.PUBLISHED and (
            not self.instance or self.instance.catalog_status != Plan.CatalogStatus.PUBLISHED
        ) and getattr(self.context.get("view"), "action", None) != "publish":
            raise serializers.ValidationError({"catalog_status": "Publica los planes mediante la acción de publicación después de revisar su configuración."})

        if plan_type == Plan.PlanType.INVOICING:
            attrs.update({
                "has_inventory": True,
                "has_cash_register": True,
                "max_issuers": 1,
                "requires_base_plan": False,
                "certificate_included_annual": True,
            })
        elif plan_type == Plan.PlanType.PAYROLL_ADDON:
            attrs.update({
                "has_inventory": False,
                "has_cash_register": False,
                "has_api_access": False,
                "max_issuers": 0,
                "requires_base_plan": True,
                "certificate_included_annual": False,
                "monthly_certificate_fee": 0,
            })
        elif plan_type == Plan.PlanType.ENTERPRISE:
            attrs.update({"quote_only": True, "monthly_price": None, "yearly_price": None})
            quote_only = True

        if plan_type == Plan.PlanType.PAYROLL_ADDON and max_employees < 1:
            raise serializers.ValidationError({"max_employees": "Define el máximo de empleados del complemento de nómina."})
        monthly_price = attrs.get("monthly_price", monthly_price)
        yearly_price = attrs.get("yearly_price", yearly_price)
        quote_only = attrs.get("quote_only", quote_only)
        if catalog_status == Plan.CatalogStatus.PUBLISHED:
            errors = {}
            if not quote_only and (monthly_price is None or monthly_price <= 0) and (yearly_price is None or yearly_price <= 0):
                errors["monthly_price"] = "Un plan publicado debe tener al menos un precio, salvo que sea por cotización."
            if not self.instance and not attrs.get("name", "").strip():
                errors["name"] = "El nombre es obligatorio para publicar."
            if visibility == Plan.Visibility.QUOTE and not quote_only:
                errors["quote_only"] = "La visibilidad de cotización requiere activar precio bajo cotización."
            if errors:
                raise serializers.ValidationError(errors)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        if not validated_data.get("category"):
            category_name = {
                Plan.PlanType.INVOICING: "Facturación electrónica",
                Plan.PlanType.PAYROLL_ADDON: "Nómina electrónica",
                Plan.PlanType.ENTERPRISE: "Empresarial",
            }.get(validated_data.get("plan_type"), "Complementos")
            category, _ = PlanCategory.objects.get_or_create(name=category_name)
            validated_data["category"] = category

        if not validated_data.get("display_order"):
            latest_order = Plan.objects.filter(category=validated_data["category"]).aggregate(value=Max("display_order"))["value"] or 0
            validated_data["display_order"] = latest_order + 1
        return super().create(validated_data)
