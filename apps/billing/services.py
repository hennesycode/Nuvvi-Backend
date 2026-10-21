from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    BillingAlert, DocumentConsumptionRule, DocumentUsageRecord,
    DigitalCertificateRecord, ProviderCapacityPool, SubscriptionModuleBalance,
)


def get_capacity_pool(*, lock=False):
    manager = ProviderCapacityPool.objects
    if lock:
        manager = manager.select_for_update()
    return manager.get_or_create(provider="matias")[0]


@transaction.atomic
def check_provider_transmission_capacity(quantity=1):
    pool = get_capacity_pool(lock=True)
    if not pool.capacity_verified or not pool.provider_period_starts_at or not pool.provider_period_ends_at:
        raise ValidationError("Transmisión bloqueada: verifica con Matías la capacidad y las fechas de renovación del proveedor.")
    now = timezone.now()
    if not pool.provider_period_starts_at <= now < pool.provider_period_ends_at:
        raise ValidationError("Transmisión bloqueada: el período confirmado de capacidad no está vigente.")
    projected = pool.documents_consumed + quantity
    if projected > min(pool.documents_purchased - pool.reserve_documents, pool.sales_block_threshold):
        raise ValidationError("Transmisión bloqueada para proteger la reserva de capacidad del proveedor.")
    for threshold, code, level, message in (
        (pool.review_threshold, "provider_usage_review", BillingAlert.Level.INFO, "El consumo global llegó a 3.500 documentos; revisa la capacidad."),
        (pool.expansion_threshold, "provider_usage_expansion", BillingAlert.Level.WARNING, "El consumo global llegó a 4.000 documentos; prepara la ampliación."),
        (pool.sales_block_threshold, "provider_usage_block", BillingAlert.Level.BLOCK, "El consumo global llegó a 4.500 documentos; protege la reserva y amplía capacidad."),
    ):
        if projected >= threshold:
            BillingAlert.objects.get_or_create(
                code=code, level=level, resolved_at__isnull=True,
                defaults={"message": message, "committed_documents": projected},
            )
    return {"remaining_documents": max(0, pool.sellable_capacity - pool.documents_consumed), "period_ends_at": pool.provider_period_ends_at}


@transaction.atomic
def check_capacity_for_commitment(additional_documents=0):
    pool = get_capacity_pool(lock=True)
    if not pool.capacity_verified or not pool.provider_period_starts_at or not pool.provider_period_ends_at:
        raise ValidationError("Capacidad bloqueada: verifica con Matías el cupo y su calendario de vigencia/renovación.")
    if pool.provider_period_ends_at <= timezone.now():
        raise ValidationError("El período de capacidad del proveedor venció; verifica la renovación antes de comprometer cupos.")
    committed = SubscriptionModuleBalance.objects.filter(status=SubscriptionModuleBalance.Status.ACTIVE).aggregate(
        total=Sum("committed_documents")
    )["total"] or 0
    projected = committed + additional_documents
    if projected > pool.sales_block_threshold or projected > pool.sellable_capacity:
        level, code, message = BillingAlert.Level.BLOCK, "provider_capacity_block", "La venta superaría el máximo preventivo de documentos comprometidos; amplía capacidad antes de vender."
        BillingAlert.objects.get_or_create(code=code, level=level, resolved_at__isnull=True, defaults={"message": message, "committed_documents": committed})
        raise ValidationError({"capacity": message})
    if projected >= pool.sales_block_threshold:
        level, code, message = BillingAlert.Level.BLOCK, "provider_capacity_block", "Se alcanzó el máximo preventivo de documentos comprometidos; no se venderá capacidad adicional."
    elif projected >= pool.expansion_threshold:
        level, code, message = BillingAlert.Level.WARNING, "provider_capacity_expansion", "Prepara la ampliación de capacidad del proveedor."
    elif projected >= pool.review_threshold:
        level, code, message = BillingAlert.Level.INFO, "provider_capacity_review", "Revisa la capacidad global disponible del proveedor."
    else:
        return {"committed": committed, "projected": projected, "sellable_capacity": pool.sellable_capacity, "can_commit": True}
    BillingAlert.objects.get_or_create(code=code, level=level, resolved_at__isnull=True, defaults={"message": message, "committed_documents": projected})
    return {"committed": committed, "projected": projected, "sellable_capacity": pool.sellable_capacity, "can_commit": True, "alert": message}


@transaction.atomic
def create_module_balance(*, data):
    # Keep the pool lock until the commitment row exists, so concurrent admin
    # actions cannot both pass against the same remaining capacity.
    check_capacity_for_commitment(data["committed_documents"])
    return SubscriptionModuleBalance.objects.create(**data)


def _record_balance_alert(balance, code, percent):
    BillingAlert.objects.get_or_create(
        code=code, balance=balance, resolved_at__isnull=True,
        defaults={
            "level": BillingAlert.Level.WARNING,
            "tenant": balance.tenant,
            "committed_documents": balance.committed_documents,
            "message": f"El módulo {balance.module} alcanzó {percent}% de su cupo ({balance.consumed_documents}/{balance.quota}).",
        },
    )


@transaction.atomic
def record_document_usage(*, balance_id, tenant_id, company_nit, document_type, operation_identifier, quantity=1, status=DocumentUsageRecord.Status.SUCCEEDED, response_reference=""):
    # Serialize idempotency keys globally, including retries that arrive through
    # different workers or balance rows.
    pool = get_capacity_pool(lock=True)
    balance = SubscriptionModuleBalance.objects.select_for_update().get(pk=balance_id)
    if balance.tenant_id != tenant_id or balance.company_nit_snapshot != company_nit:
        raise ValidationError("El saldo no corresponde a la empresa/NIT de la operación.")
    rule = DocumentConsumptionRule.objects.filter(document_type=document_type).first()
    if not rule or not rule.confirmed_with_provider:
        raise ValidationError({"document_type": "Consumo bloqueado: Matías aún no confirma si este tipo de operación consume capacidad."})
    if quantity < 1:
        raise ValidationError({"quantity": "La cantidad debe ser positiva."})

    record = DocumentUsageRecord.objects.select_for_update().filter(operation_identifier=operation_identifier).first()
    created = record is None
    if record:
        if (record.balance_id != balance.id or record.tenant_id != tenant_id
                or record.company_nit_snapshot != company_nit or record.document_type != document_type
                or record.quantity != quantity):
            raise ValidationError({"operation_identifier": "Este identificador ya se usó con otros datos; usa una clave distinta."})
        if record.status in (DocumentUsageRecord.Status.SUCCEEDED, DocumentUsageRecord.Status.REVERSED):
            return record, False
        record.status = status
        record.response_reference = response_reference
        if status == DocumentUsageRecord.Status.SUCCEEDED and rule.provider_counts_as_consumption:
            record.counted_at = timezone.now()
        record.save(update_fields=["status", "response_reference", "counted_at"])
    else:
        record = DocumentUsageRecord.objects.create(
            balance=balance, tenant_id=tenant_id, company_nit_snapshot=company_nit,
            document_type=document_type, operation_identifier=operation_identifier,
            status=status, quantity=quantity, response_reference=response_reference,
            counted_at=timezone.now() if status == DocumentUsageRecord.Status.SUCCEEDED and rule.provider_counts_as_consumption else None,
        )
    if record.counted_at:
        # The check above is intentionally applied only once, when the operation
        # transitions to a confirmed success or is first recorded as successful.
        if balance.consumed_documents + quantity > balance.quota:
            raise ValidationError("El consumo excedería el saldo del módulo.")
        balance.consumed_documents += quantity
        balance.save(update_fields=["consumed_documents", "updated_at"])
        pool.documents_consumed += quantity
        pool.save(update_fields=["documents_consumed", "updated_at"])
        for threshold in (70, 85, 95):
            if balance.consumed_documents * 100 >= balance.quota * threshold:
                _record_balance_alert(balance, f"usage_{threshold}", threshold)
    return record, created


def require_valid_certificate(*, tenant_id, nit):
    check_provider_transmission_capacity()
    certificate = DigitalCertificateRecord.objects.filter(tenant_id=tenant_id, nit_snapshot=nit, is_current=True).first()
    if certificate is None or not certificate.is_valid_for_transmission:
        raise ValidationError("No se puede transmitir: registra y verifica un certificado vigente para el NIT.")
    return certificate
