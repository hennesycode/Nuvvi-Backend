import re

from rest_framework import serializers
from .models import Plan, PlanCategory


class PlanCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanCategory
        fields = ["id", "name", "description", "display_order", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value):
        value = value.strip()
        if self.instance and value == self.instance.code:
            return value
        if self.instance:
            raise serializers.ValidationError("El código interno no se puede cambiar después de crear el plan.")
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
        monthly_price = attrs.get("monthly_price", getattr(self.instance, "monthly_price", 0))
        yearly_price = attrs.get("yearly_price", getattr(self.instance, "yearly_price", 0))

        if self.instance and self.instance.catalog_status == Plan.CatalogStatus.PUBLISHED:
            contract_fields = set(attrs) - {"is_active", "catalog_status"}
            changed_fields = {
                field for field in contract_fields
                if getattr(self.instance, field) != attrs[field]
            }
            if changed_fields:
                raise serializers.ValidationError({
                    "catalog_status": "Un plan publicado no se puede editar directamente. Duplícalo para preparar una nueva oferta y conserva las condiciones contratadas."
                })
        if catalog_status == Plan.CatalogStatus.PUBLISHED and (
            not self.instance or self.instance.catalog_status != Plan.CatalogStatus.PUBLISHED
        ) and getattr(self.context.get("view"), "action", None) != "publish":
            raise serializers.ValidationError({"catalog_status": "Publica los planes mediante la acción de publicación después de revisar su configuración."})

        if plan_type == Plan.PlanType.PAYROLL_ADDON and not requires_base_plan:
            raise serializers.ValidationError({"requires_base_plan": "El complemento de nómina debe requerir un plan principal de facturación."})
        if plan_type == Plan.PlanType.PAYROLL_ADDON and max_employees < 1:
            raise serializers.ValidationError({"max_employees": "Define el máximo de empleados del complemento de nómina."})
        if not quote_only and monthly_price <= 0 and yearly_price <= 0:
            raise serializers.ValidationError("Define un precio mensual o anual, o marca el plan como cotización personalizada.")
        if catalog_status == Plan.CatalogStatus.PUBLISHED:
            errors = {}
            if not quote_only and monthly_price <= 0 and yearly_price <= 0:
                errors["monthly_price"] = "Un plan publicado debe tener al menos un precio, salvo que sea por cotización."
            if not self.instance and not attrs.get("name", "").strip():
                errors["name"] = "El nombre es obligatorio para publicar."
            if visibility == Plan.Visibility.QUOTE and not quote_only:
                errors["quote_only"] = "La visibilidad de cotización requiere activar precio bajo cotización."
            if errors:
                raise serializers.ValidationError(errors)
        return attrs
