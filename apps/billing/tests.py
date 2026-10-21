from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.tenants.models import Tenant
from .models import (
    DocumentConsumptionRule, DocumentUsageRecord, ProviderCapacityPool,
    SubscriptionModuleBalance,
)
from .services import check_capacity_for_commitment, record_document_usage


class ProviderCapacityTests(TestCase):
    def test_unverified_or_untracked_provider_period_blocks_commitment(self):
        with self.assertRaises(ValidationError):
            check_capacity_for_commitment(1)

    def test_4500_document_commitment_is_the_maximum_sellable_amount(self):
        now = timezone.now()
        pool, _ = ProviderCapacityPool.objects.get_or_create(provider="matias")
        pool.capacity_verified = True
        pool.provider_period_starts_at = now - timedelta(days=1)
        pool.provider_period_ends_at = now + timedelta(days=365)
        pool.verification_notes = "Capacidad y calendario verificados con el proveedor."
        pool.save()
        result = check_capacity_for_commitment(4500)
        self.assertTrue(result["can_commit"])
        with self.assertRaises(ValidationError):
            check_capacity_for_commitment(4501)


class DocumentConsumptionTests(TestCase):
    def setUp(self):
        now = timezone.now()
        tenant = Tenant.objects.create(name="Empresa de prueba", nit="900123456")
        plan = Plan.objects.create(code="test-billing", name="Plan de prueba")
        subscription = Subscription.objects.create(
            tenant=tenant, plan=plan, status=Subscription.Status.ACTIVE,
            billing_cycle=Subscription.BillingCycle.MONTHLY,
            current_period_start=now, current_period_end=now + timedelta(days=30),
        )
        self.balance = SubscriptionModuleBalance.objects.create(
            subscription=subscription, tenant=tenant, company_nit_snapshot=tenant.nit,
            module=SubscriptionModuleBalance.Module.INVOICING, quota=10,
            committed_documents=10, period_starts_at=now,
            period_ends_at=now + timedelta(days=30),
        )
        self.tenant = tenant
        self.rule, _ = DocumentConsumptionRule.objects.get_or_create(document_type="invoice")
        self.rule.provider_counts_as_consumption = False
        self.rule.confirmed_with_provider = False
        self.rule.confirmation_notes = ""
        self.rule.save()

    def test_operation_is_not_counted_until_provider_rule_is_confirmed(self):
        with self.assertRaises(ValidationError):
            record_document_usage(
                balance_id=self.balance.id, tenant_id=self.tenant.id,
                company_nit=self.tenant.nit, document_type="invoice",
                operation_identifier="invoice-op-pending",
            )
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.consumed_documents, 0)

    def test_confirmed_retry_is_idempotent_and_counts_once(self):
        self.rule.confirmed_with_provider = True
        self.rule.provider_counts_as_consumption = True
        self.rule.confirmation_notes = "Confirmado con Matías."
        self.rule.save()
        kwargs = {
            "balance_id": self.balance.id,
            "tenant_id": self.tenant.id,
            "company_nit": self.tenant.nit,
            "document_type": "invoice",
            "operation_identifier": "invoice-op-1",
        }
        first, created = record_document_usage(**kwargs)
        retry, retry_created = record_document_usage(**kwargs)
        self.balance.refresh_from_db()
        self.assertTrue(created)
        self.assertFalse(retry_created)
        self.assertEqual(first.id, retry.id)
        self.assertEqual(self.balance.consumed_documents, 1)

    def test_failed_attempt_can_be_retried_successfully_under_same_operation_id(self):
        self.rule.confirmed_with_provider = True
        self.rule.provider_counts_as_consumption = True
        self.rule.confirmation_notes = "Confirmado con Matías."
        self.rule.save()
        kwargs = {
            "balance_id": self.balance.id,
            "tenant_id": self.tenant.id,
            "company_nit": self.tenant.nit,
            "document_type": "invoice",
            "operation_identifier": "invoice-op-retry",
        }
        record_document_usage(**kwargs, status=DocumentUsageRecord.Status.FAILED)
        record, created = record_document_usage(**kwargs, status=DocumentUsageRecord.Status.SUCCEEDED)
        self.balance.refresh_from_db()
        self.assertFalse(created)
        self.assertEqual(record.status, DocumentUsageRecord.Status.SUCCEEDED)
        self.assertEqual(self.balance.consumed_documents, 1)
