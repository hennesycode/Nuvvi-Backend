from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.plans.views import IsSuperAdmin
from .models import (
    BillingAlert, DigitalCertificateRecord, DocumentConsumptionRule,
    DocumentRechargePackage, DocumentUsageRecord, ProviderCapacityPool,
    SubscriptionModuleBalance,
)
from .serializers import (
    BillingAlertSerializer, DigitalCertificateRecordSerializer,
    DocumentConsumptionRuleSerializer, DocumentRechargePackageSerializer,
    DocumentUsageRecordSerializer, ProviderCapacityPoolSerializer,
    SubscriptionModuleBalanceSerializer,
)
from .services import create_module_balance, record_document_usage, require_valid_certificate


class AdminReadOnlyViewSet(ModelViewSet):
    def get_permissions(self):
        return [IsSuperAdmin()]


class ProviderCapacityPoolViewSet(AdminReadOnlyViewSet):
    queryset = ProviderCapacityPool.objects.all()
    serializer_class = ProviderCapacityPoolSerializer

    def get_queryset(self):
        from .services import get_capacity_pool
        get_capacity_pool()
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        raise ValidationError("El pool Matías es único; actualiza el registro existente.")

    @action(detail=True, methods=["post"], url_path="check-transmission")
    def check_transmission(self, request, pk=None):
        certificate = require_valid_certificate(tenant_id=request.data.get("tenant"), nit=request.data.get("nit", ""))
        return Response({"can_transmit": True, "certificate_id": certificate.id})


class SubscriptionModuleBalanceViewSet(AdminReadOnlyViewSet):
    queryset = SubscriptionModuleBalance.objects.select_related("tenant", "subscription", "company")
    serializer_class = SubscriptionModuleBalanceSerializer

    def perform_create(self, serializer):
        balance = create_module_balance(data=serializer.validated_data)
        serializer.instance = balance


class DocumentConsumptionRuleViewSet(AdminReadOnlyViewSet):
    queryset = DocumentConsumptionRule.objects.all()
    serializer_class = DocumentConsumptionRuleSerializer

    def perform_update(self, serializer):
        values = serializer.validated_data
        if values.get("confirmed_with_provider"):
            values["reviewed_at"] = timezone.now()
        serializer.save(**values)


class DocumentUsageRecordViewSet(AdminReadOnlyViewSet):
    queryset = DocumentUsageRecord.objects.select_related("balance", "tenant")
    serializer_class = DocumentUsageRecordSerializer

    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data
        record, created = record_document_usage(
            balance_id=data["balance"].id, tenant_id=data["tenant"].id,
            company_nit=data["company_nit_snapshot"], document_type=data["document_type"],
            operation_identifier=data["operation_identifier"], quantity=data.get("quantity", 1),
            status=data.get("status", DocumentUsageRecord.Status.SUCCEEDED),
            response_reference=data.get("response_reference", ""),
        )
        return Response(self.get_serializer(record).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class BillingAlertViewSet(AdminReadOnlyViewSet):
    queryset = BillingAlert.objects.select_related("tenant", "balance")
    serializer_class = BillingAlertSerializer


class DigitalCertificateViewSet(AdminReadOnlyViewSet):
    queryset = DigitalCertificateRecord.objects.select_related("tenant", "company")
    serializer_class = DigitalCertificateRecordSerializer

    @action(detail=False, methods=["get"], url_path="upcoming-renewals")
    def upcoming_renewals(self, request):
        from datetime import timedelta
        from django.utils import timezone

        today = timezone.now()
        horizon = today + timedelta(days=30)
        certificates = self.get_queryset().filter(
            is_current=True,
            expires_at__gt=today,
            expires_at__lte=horizon,
        )
        return Response(self.get_serializer(certificates, many=True).data)


class DocumentRechargePackageViewSet(AdminReadOnlyViewSet):
    queryset = DocumentRechargePackage.objects.all()
    serializer_class = DocumentRechargePackageSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (self.request.user.is_superuser or self.request.user.admin_role == "superadmin"):
            queryset = queryset.filter(is_available_for_sale=True)
        return queryset
