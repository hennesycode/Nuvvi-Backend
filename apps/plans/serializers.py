from rest_framework import serializers
from .models import Plan, PlanCategory


class PlanCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanCategory
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

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
        monthly_price = attrs.get("monthly_price", getattr(self.instance, "monthly_price", 0))
        yearly_price = attrs.get("yearly_price", getattr(self.instance, "yearly_price", 0))

        if plan_type == Plan.PlanType.PAYROLL_ADDON and not requires_base_plan:
            raise serializers.ValidationError({"requires_base_plan": "El complemento de nómina debe requerir un plan principal de facturación."})
        if plan_type == Plan.PlanType.PAYROLL_ADDON and max_employees < 1:
            raise serializers.ValidationError({"max_employees": "Define el máximo de empleados del complemento de nómina."})
        if not quote_only and monthly_price <= 0 and yearly_price <= 0:
            raise serializers.ValidationError("Define un precio mensual o anual, o marca el plan como cotización personalizada.")
        return attrs
