from rest_framework import serializers

from .models import (
    BillingAlert, DigitalCertificateRecord, DocumentConsumptionRule,
    DocumentRechargePackage, DocumentUsageRecord, ProviderCapacityPool,
    SubscriptionModuleBalance,
)


class ProviderCapacityPoolSerializer(serializers.ModelSerializer):
    sellable_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProviderCapacityPool
        fields = "__all__"
        read_only_fields = ["provider", "documents_consumed", "updated_at"]

    def validate(self, attrs):
        if attrs.get("capacity_verified", getattr(self.instance, "capacity_verified", False)):
            starts = attrs.get("provider_period_starts_at", getattr(self.instance, "provider_period_starts_at", None))
            ends = attrs.get("provider_period_ends_at", getattr(self.instance, "provider_period_ends_at", None))
            if not starts or not ends:
                raise serializers.ValidationError("Para verificar capacidad se requieren fechas confirmadas del período del proveedor.")
            if ends <= starts:
                raise serializers.ValidationError({"provider_period_ends_at": "La fecha de renovación debe ser posterior al inicio del período."})
            if not attrs.get("verification_notes", getattr(self.instance, "verification_notes", "")).strip():
                raise serializers.ValidationError({"verification_notes": "Indica la referencia de la confirmación de Matías."})
        return attrs

    def update(self, instance, validated_data):
        if validated_data.get("capacity_verified", instance.capacity_verified):
            from django.utils import timezone
            validated_data["verified_at"] = timezone.now()
        return super().update(instance, validated_data)


class SubscriptionModuleBalanceSerializer(serializers.ModelSerializer):
    remaining_documents = serializers.IntegerField(read_only=True)

    class Meta:
        model = SubscriptionModuleBalance
        fields = "__all__"
        read_only_fields = ["id", "consumed_documents", "created_at", "updated_at"]


class DocumentConsumptionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentConsumptionRule
        fields = "__all__"
        read_only_fields = ["id", "reviewed_at", "updated_at"]

    def validate(self, attrs):
        if attrs.get("confirmed_with_provider", getattr(self.instance, "confirmed_with_provider", False)) and not attrs.get("confirmation_notes", getattr(self.instance, "confirmation_notes", "")).strip():
            raise serializers.ValidationError({"confirmation_notes": "Documenta la confirmación de Matías."})
        return attrs


class DocumentUsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentUsageRecord
        fields = "__all__"
        read_only_fields = ["id", "created_at", "counted_at"]

    def validate(self, attrs):
        if attrs.get("quantity", 1) < 1:
            raise serializers.ValidationError({"quantity": "La cantidad debe ser positiva."})
        return attrs


class BillingAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingAlert
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class DigitalCertificateRecordSerializer(serializers.ModelSerializer):
    is_valid_for_transmission = serializers.BooleanField(read_only=True)

    class Meta:
        model = DigitalCertificateRecord
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DocumentRechargePackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRechargePackage
        fields = "__all__"
        read_only_fields = ["id", "created_at", "is_available_for_sale"]
