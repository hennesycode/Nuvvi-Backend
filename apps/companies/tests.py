from unittest.mock import patch

from django.test import TestCase

from apps.dian.matias_service import encrypt_secret
from apps.dian.models import MatiasConnection
from apps.accounts.models import User
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import Company, CompanyProviderLink, CompanySyncAttempt
from .services import CompanyApplicationService, MatiasCompanyClient
from .views import CompanyIdentityCheckView


class MatiasCompanySyncTests(TestCase):
    def setUp(self):
        self.connection = MatiasConnection.objects.create(
            environment=MatiasConnection.ENVIRONMENT_SANDBOX,
            base_url="https://sandbox-api.matias-api.com/api/ubl2.1",
            parent_company_uuid="parent-uuid",
            encrypted_access_token=encrypt_secret("test-pat"),
            enabled=True,
            operational_status=MatiasConnection.OP_READY,
        )
        self.service = CompanyApplicationService(environment=MatiasConnection.ENVIRONMENT_SANDBOX)

    @patch("apps.companies.services.matias_request")
    def test_reconcile_imports_remote_customer_into_local_company_list(self, request_mock):
        request_mock.return_value = {
            "ok": True,
            "status_code": 200,
            "data": {"success": True, "dataRecords": {"data": [{
                "id": 42,
                "client_uuid": "client-uuid-42",
                "company_name": "Empresa de prueba",
                "dni": "900123456",
                "email": "facturacion@example.test",
                "active": 1,
            }]}},
            "response_time_ms": 18,
            "error": "",
            "endpoint": "/company/customers",
        }

        result = self.service.synchronize_remote_companies()

        self.assertEqual(result, {"remote_count": 1, "imported": 1, "updated": 0, "skipped": 0})
        company = Company.objects.get(environment="sandbox", nit="900123456")
        link = company.provider_links.get(environment="sandbox")
        self.assertEqual(company.legal_name, "Empresa de prueba")
        self.assertEqual(company.onboarding_status, Company.ONBOARDING_TAX_INFORMATION_PENDING)
        self.assertIsNone(company.owner_user)
        self.assertEqual(link.matias_client_uuid, "client-uuid-42")
        self.assertEqual(link.provider_status, CompanyProviderLink.STATUS_REGISTERED)

    @patch("apps.companies.services.matias_request")
    def test_reconcile_is_idempotent_for_an_already_imported_customer(self, request_mock):
        payload = {"success": True, "dataRecords": {"data": [{
            "id": 42, "client_uuid": "client-uuid-42", "company_name": "Empresa de prueba",
            "dni": "900123456", "email": "facturacion@example.test", "active": 1,
        }]}}
        request_mock.return_value = {"ok": True, "status_code": 200, "data": payload, "response_time_ms": 10, "error": "", "endpoint": "/company/customers"}

        self.service.synchronize_remote_companies()
        result = self.service.synchronize_remote_companies()

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(Company.objects.filter(environment="sandbox", nit="900123456").count(), 1)

    def test_company_endpoints_follow_published_client_uuid_routes(self):
        client = MatiasCompanyClient(self.connection)
        with patch.object(client, "_request", return_value={"ok": True}) as request_mock:
            client.update_company(client_uuid="client-uuid", payload={"name": "Updated"})
            self.assertEqual(request_mock.call_args.args[0], "/company/customers/client-uuid")
            self.assertEqual(request_mock.call_args.kwargs["method"], "PUT")
            client.enable_company(client_uuid="client-uuid")
            self.assertEqual(request_mock.call_args.args[0], "/company/customers/client-uuid/enable")
            client.disable_company(client_uuid="client-uuid")
            self.assertEqual(request_mock.call_args.args[0], "/company/customers/client-uuid")
            self.assertEqual(request_mock.call_args.kwargs["method"], "DELETE")

    @patch("apps.companies.services.write_audit_log")
    @patch.object(MatiasCompanyClient, "disable_company")
    def test_delete_archives_locally_only_after_provider_confirms_disable(self, disable_mock, _audit_mock):
        owner = User.objects.create_user(email="owner@example.test", full_name="Company Owner")
        company = Company.objects.create(
            environment="sandbox", legal_name="Empresa para eliminar", nit="900123456",
            email="owner@example.test", owner_first_name="Company", owner_last_name="Owner",
            owner_user=owner, country_id="1", city_id="1", address="Calle 1", mobile="+573001234567",
        )
        link = CompanyProviderLink.objects.create(company=company, environment="sandbox", matias_client_uuid="client-uuid")
        disable_mock.return_value = {"ok": True, "status_code": 200, "data": {"success": True}}

        self.service.archive_company(company)

        company.refresh_from_db()
        owner.refresh_from_db()
        link.refresh_from_db()
        self.assertEqual(company.local_status, Company.LOCAL_ARCHIVED)
        self.assertFalse(owner.is_active)
        self.assertFalse(link.enabled_in_provider)
        self.assertEqual(link.provider_status, CompanyProviderLink.STATUS_REMOTE_DISABLED)
        disable_mock.assert_called_once_with(client_uuid="client-uuid")

    @patch.object(MatiasCompanyClient, "disable_company")
    def test_delete_does_not_archive_when_provider_rejects_disable(self, disable_mock):
        company = Company.objects.create(
            environment="sandbox", legal_name="Empresa activa", nit="900123457",
            email="active@example.test", owner_first_name="Company", owner_last_name="Owner",
            country_id="1", city_id="1", address="Calle 1", mobile="+573001234567",
        )
        CompanyProviderLink.objects.create(company=company, environment="sandbox", matias_client_uuid="client-uuid")
        disable_mock.return_value = {"ok": False, "status_code": 503, "error": "Proveedor no disponible", "data": {}}

        with self.assertRaisesRegex(ValueError, "Proveedor no disponible"):
            self.service.archive_company(company)

        company.refresh_from_db()
        self.assertIsNone(company.archived_at)
        self.assertEqual(company.local_status, Company.LOCAL_ACTIVE)

    def test_identity_check_returns_duplicate_flags_without_company_payload(self):
        admin = User.objects.create_superuser(email="admin@example.test", full_name="Admin", password="safe-password")
        Company.objects.create(
            environment="sandbox", legal_name="Empresa existente", nit="900123458",
            email="existing@example.test", owner_first_name="Empresa", owner_last_name="Existente",
            country_id="1", city_id="1", address="Calle 1", mobile="+573001234567",
        )
        request = APIRequestFactory().get("/api/admin/companies/identity-check/", {
            "environment": "sandbox", "nit": "900123458", "email": "EXISTING@example.test",
        })
        force_authenticate(request, user=admin)

        response = CompanyIdentityCheckView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"nit_exists": True, "email_exists": True})

        CompanySyncAttempt.objects.create(company=Company.objects.get(nit="900123458"), operation="CREATE", request_identifier="retry-key")
        retry_request = APIRequestFactory().get("/api/admin/companies/identity-check/", {
            "environment": "sandbox", "request_id": "retry-key", "nit": "900123458", "email": "existing@example.test",
        })
        force_authenticate(retry_request, user=admin)

        retry_response = CompanyIdentityCheckView.as_view()(retry_request)

        self.assertEqual(retry_response.data, {"nit_exists": False, "email_exists": False})
