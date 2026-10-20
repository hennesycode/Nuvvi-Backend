from unittest.mock import patch

from django.test import TestCase

from apps.dian.matias_service import encrypt_secret
from apps.dian.models import MatiasConnection

from .models import Company, CompanyProviderLink
from .services import CompanyApplicationService, MatiasCompanyClient


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
