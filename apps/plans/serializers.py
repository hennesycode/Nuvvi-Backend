import re

from django.db import transaction
from django.db.models import Max
from rest_framework import serializers
from .models import Capability, Plan, PlanBundle, PlanCategory


class PlanCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanCategory
        fields = ["id", "name", "description", "display_order", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class CapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Capability
        fields = ["id", "code", "name", "description", "validation_status", "validation_notes", "reviewed_at"]
        read_only_fields = ["id", "reviewed_at"]

    def validate(self, attrs):
        status = attrs.get("validation_status", getattr(self.instance, "validation_status", Capability.ValidationStatus.PENDING))
        notes = attrs.get("validation_notes", getattr(self.instance, "validation_notes", ""))
        if status == Capability.ValidationStatus.AVAILABLE and not notes.strip():
            raise serializers.ValidationError({"validation_notes": "Registra qué validación técnica respalda la disponibilidad."})
        return attrs

    def update(self, instance, validated_data):
        from django.utils import timezone

        validated_data["reviewed_by"] = self.context["request"].user
        validated_data["reviewed_at"] = timezone.now()
        return super().update(instance, validated_data)


class PlanSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    validated_capabilities = serializers.SerializerMethodField()
    plan_capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "parent_plan", "version_number", "commercial_status", "tax_validation_status"]

    def validate_code(self, value):
        value = value.strip()
        if self.instance and value == self.instance.code:
            return value
        if self.instance and self.instance.catalog_status != Plan.CatalogStatus.DRAFT:
            raise serializers.ValidationError("Solo se puede cambiar el código de un borrador.")
        value = value.lower()
        if not re.fullmatch(r"[a-z0-9]+(?:[_-][a-z0-9]+)*", value):
            raise serializers.ValidationError("Usa letras minúsculas, números, guiones o guiones bajos.")
        return value

    def validate_slug(self, value):
        value = value.strip()
        if not re.fullmatch(r"[a-z0-9]+(?:[_-][a-z0-9]+)*", value):
            raise serializers.ValidationError("El slug debe usar minúsculas, números, guiones o guiones bajos.")
        return value

    def get_validated_capabilities(self, obj):
        return [
            {"code": assignment.capability.code, "name": assignment.capability.name, "level": assignment.scope_level}
            for assignment in obj.plan_capabilities.select_related("capability").filter(
                included_in_proposal=True,
                capability__validation_status=Capability.ValidationStatus.AVAILABLE,
            )
        ]

    def get_plan_capabilities(self, obj):
        return [{
            "id": assignment.id,
            "scope_level": assignment.scope_level,
            "included_in_proposal": assignment.included_in_proposal,
            "capability": {
                "code": assignment.capability.code,
                "name": assignment.capability.name,
                "validation_status": assignment.capability.validation_status,
            },
        } for assignment in obj.plan_capabilities.select_related("capability").all()]

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
        attrs.setdefault("plan_type", plan_type)
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
        if "capabilities" in attrs and self.instance and self.instance.catalog_status != Plan.CatalogStatus.DRAFT:
            raise serializers.ValidationError({"capabilities": "Crea una nueva versión para cambiar capacidades de una oferta existente."})
        if catalog_status == Plan.CatalogStatus.PUBLISHED and (
            not self.instance or self.instance.catalog_status != Plan.CatalogStatus.PUBLISHED
        ) and getattr(self.context.get("view"), "action", None) != "publish":
            raise serializers.ValidationError({"catalog_status": "Publica los planes mediante la acción de publicación después de revisar su configuración."})

        if plan_type == Plan.PlanType.INVOICING:
            attrs.update({
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
        publishing = catalog_status == Plan.CatalogStatus.PUBLISHED and (
            not self.instance or self.instance.catalog_status != Plan.CatalogStatus.PUBLISHED
        )
        if publishing:
            errors = {}
            commercial_status = attrs.get("commercial_status", getattr(self.instance, "commercial_status", Plan.CommercialStatus.PROPOSAL))
            tax_status = attrs.get("tax_validation_status", getattr(self.instance, "tax_validation_status", Plan.TaxValidationStatus.PENDING))
            if self.instance and commercial_status != Plan.CommercialStatus.APPROVED:
                errors["commercial_status"] = "La propuesta necesita aprobación administrativa antes de publicarse."
            if self.instance and tax_status != Plan.TaxValidationStatus.VALIDATED:
                errors["tax_validation_status"] = "Valida el tratamiento tributario antes de publicar precios."
            pending_capabilities = obj_pending_capabilities(self.instance, attrs)
            if pending_capabilities:
                errors["capabilities"] = "Hay funcionalidades propuestas sin validación técnica: " + ", ".join(pending_capabilities)
            if self.instance and self.instance.commercial_status == Plan.CommercialStatus.PROPOSAL and self.instance.features and not self.instance.plan_capabilities.filter(included_in_proposal=True).exists():
                errors["capabilities"] = "Asocia y valida técnicamente las capacidades antes de publicar esta propuesta."
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
        capabilities = validated_data.pop("capabilities", [])
        validated_data.setdefault("catalog_status", Plan.CatalogStatus.DRAFT)
        validated_data.setdefault("visibility", Plan.Visibility.PRIVATE)
        validated_data.setdefault("is_active", False)
        validated_data.setdefault("commercial_status", Plan.CommercialStatus.PROPOSAL)
        validated_data.setdefault("tax_validation_status", Plan.TaxValidationStatus.PENDING)
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
        instance = super().create(validated_data)
        if capabilities:
            instance.capabilities.set(capabilities)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        capabilities = validated_data.pop("capabilities", None)
        instance = super().update(instance, validated_data)
        if capabilities is not None:
            instance.capabilities.set(capabilities)
        return instance


def obj_pending_capabilities(instance, attrs):
    if not instance:
        return []
    return list(instance.plan_capabilities.filter(
        included_in_proposal=True,
    ).exclude(capability__validation_status=Capability.ValidationStatus.AVAILABLE).values_list("capability__name", flat=True))


class PlanBundleSerializer(serializers.ModelSerializer):
    billing_plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    payroll_plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    billing_plan_details = PlanSerializer(source="billing_plan", read_only=True)
    payroll_plan_details = PlanSerializer(source="payroll_plan", read_only=True)
    monthly_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    yearly_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PlanBundle
        fields = ["id", "slug", "name", "short_description", "billing_plan", "payroll_plan", "billing_plan_details", "payroll_plan_details", "monthly_price", "yearly_price", "display_order", "commercial_status", "is_active"]
        read_only_fields = ["id", "commercial_status", "is_active"]

    def validate(self, attrs):
        billing_plan = attrs.get("billing_plan", getattr(self.instance, "billing_plan", None))
        payroll_plan = attrs.get("payroll_plan", getattr(self.instance, "payroll_plan", None))
        if billing_plan and billing_plan.plan_type != Plan.PlanType.INVOICING:
            raise serializers.ValidationError({"billing_plan": "El componente debe ser facturación electrónica."})
        if payroll_plan and payroll_plan.plan_type != Plan.PlanType.PAYROLL_ADDON:
            raise serializers.ValidationError({"payroll_plan": "El componente debe ser nómina electrónica."})
        return attrs
