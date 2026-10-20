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
