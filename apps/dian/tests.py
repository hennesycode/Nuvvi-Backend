from datetime import timedelta
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from unittest.mock import patch

from .matias_service import CATALOG_ENDPOINTS, encrypt_secret, extract_generated_pat, get_records, has_data_records, normalize_base_url, revoke_current_pat, sync_catalogs
from .models import MatiasCatalogSync, MatiasConnection
from .serializers import MatiasConnectionSerializer, MatiasGeneratePatSerializer, validate_matias_token_name


class MatiasDocumentationContractTests(SimpleTestCase):
    def test_standard_catalog_envelope_is_readable(self):
        payload = {"dataRecords": {"data": [{"id": 7, "name": "Factura"}]}, "success": True}

        self.assertTrue(has_data_records(payload))
        self.assertEqual(get_records(payload), [{"id": 7, "name": "Factura"}])

    def test_malformed_catalog_envelopes_do_not_crash(self):
        self.assertFalse(has_data_records({"dataRecords": []}))
        self.assertEqual(get_records({"dataRecords": "invalid"}), [])

    def test_list_envelopes_are_extracted_for_company_sync(self):
        payload = {"success": True, "data": {"customers": [{"client_uuid": "client-1"}]}}

        self.assertTrue(has_data_records(payload))
        self.assertEqual(get_records(payload), [{"client_uuid": "client-1"}])

    def test_base_url_is_normalized_to_matias_api_root(self):
        self.assertEqual(
            normalize_base_url("https://sandbox-api.matias-api.com/api/ubl2.1/invoices/"),
            "https://sandbox-api.matias-api.com/api/ubl2.1",
        )

    def test_documented_invoice_catalogs_are_included(self):
        endpoints = {endpoint for endpoint, _ in CATALOG_ENDPOINTS}

        self.assertEqual(len(CATALOG_ENDPOINTS), 20)
        self.assertTrue({"organization-type", "type-item-identifications", "taxes", "quantity-units"}.issubset(endpoints))

    def test_pat_expiration_defaults_to_90_days_and_rejects_more(self):
        self.assertEqual(validate_matias_token_name("  Nuvvi Sandbox  "), "Nuvvi Sandbox")
        default_serializer = MatiasGeneratePatSerializer(data={
            "email": "admin@example.com",
            "password": "not-saved",
            "token_name": "Nuvvi Sandbox",
        })
        self.assertTrue(default_serializer.is_valid(), default_serializer.errors)
        self.assertEqual(default_serializer.validated_data["expires_in_days"], 90)

        maximum_serializer = MatiasGeneratePatSerializer(data={
            "email": "admin@example.com",
            "password": "not-saved",
            "token_name": "Nuvvi Sandbox",
            "expires_in_days": 90,
        })
        self.assertTrue(maximum_serializer.is_valid(), maximum_serializer.errors)

        out_of_range_serializer = MatiasGeneratePatSerializer(data={
            "email": "admin@example.com",
            "password": "not-saved",
            "token_name": "Nuvvi Sandbox",
            "expires_in_days": 91,
        })

        self.assertFalse(out_of_range_serializer.is_valid())
        self.assertIn("expires_in_days", out_of_range_serializer.errors)

    def test_pat_extraction_matches_sandbox_quickstart_response(self):
        payload = {
            "success": True,
            "token": "1|sandbox-pat-value",
            "data": {"name": "Nuvvi Sandbox", "expires_at": "2026-11-01T00:00:00Z"},
        }

        self.assertEqual(extract_generated_pat(payload), "1|sandbox-pat-value")

    def test_pat_extraction_handles_nested_token_envelopes(self):
        payload = {"success": True, "data": {"token": {"plainTextToken": "nested-pat-value"}}}

        self.assertEqual(extract_generated_pat(payload), "nested-pat-value")

    def test_pat_extraction_never_uses_non_string_metadata_as_token(self):
        self.assertEqual(extract_generated_pat({"success": True, "data": {"token": {"id": 12}}}), "")


class MatiasConnectionConfigurationTests(TestCase):
    def test_sandbox_url_cannot_be_changed_to_an_unofficial_host(self):
        serializer = MatiasConnectionSerializer(data={
            "environment": "sandbox",
            "base_url": "https://example.invalid/api/ubl2.1",
            "enabled": True,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("base_url", serializer.errors)

    def test_production_rejects_sandbox_endpoint(self):
        serializer = MatiasConnectionSerializer(data={
            "environment": "production",
            "base_url": "https://sandbox-api.matias-api.com/api/ubl2.1",
            "enabled": True,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("base_url", serializer.errors)


class MatiasCatalogSynchronizationTests(TestCase):
    @patch("apps.dian.matias_service.matias_request")
    def test_sync_persists_catalog_records_per_environment(self, request_mock):
        request_mock.return_value = {
            "ok": True,
            "status_code": 200,
            "headers": {},
            "data": {"dataRecords": {"data": [{"id": 1, "name": "Demo"}]}, "success": True},
            "response_time_ms": 12,
            "error": "",
        }
        connection = MatiasConnection.objects.create(
            environment=MatiasConnection.ENVIRONMENT_SANDBOX,
            base_url="https://sandbox-api.matias-api.com/api/ubl2.1",
        )

        synced = sync_catalogs(connection)

        self.assertEqual(synced.catalogs_status, MatiasConnection.CATALOGS_SYNCED)
        self.assertEqual(synced.catalogs_synced_count, 20)
        first_catalog = MatiasCatalogSync.objects.get(connection=synced, endpoint="/destination-environment")
        self.assertEqual(first_catalog.catalog_data, [{"id": 1, "name": "Demo"}])

    @patch("apps.dian.matias_service.matias_request")
    def test_failed_sync_keeps_previous_successful_catalog_data(self, request_mock):
        request_mock.return_value = {
            "ok": False,
            "status_code": 503,
            "headers": {},
            "data": {},
            "response_time_ms": 12,
            "error": "Service unavailable",
        }
        connection = MatiasConnection.objects.create(
            environment=MatiasConnection.ENVIRONMENT_SANDBOX,
            base_url="https://sandbox-api.matias-api.com/api/ubl2.1",
        )
        previous_data = [{"id": 45, "name": "Colombia"}]
        MatiasCatalogSync.objects.create(
            connection=connection,
            endpoint="/countries",
            catalog_name="Paises",
            status=MatiasConnection.CATALOGS_SYNCED,
            catalog_data=previous_data,
            records_count=1,
        )

        sync_catalogs(connection)

        countries = MatiasCatalogSync.objects.get(connection=connection, endpoint="/countries")
        self.assertEqual(countries.status, MatiasConnection.CATALOGS_ERROR)
        self.assertEqual(countries.catalog_data, previous_data)
        self.assertEqual(countries.records_count, 1)


class MatiasTokenRevocationTests(TestCase):
    @patch("apps.dian.matias_service.matias_request")
    def test_resolves_missing_external_id_from_documented_token_list(self, request_mock):
        created_at = timezone.now()
        connection = MatiasConnection.objects.create(
            environment=MatiasConnection.ENVIRONMENT_SANDBOX,
            base_url="https://sandbox-api.matias-api.com/api/ubl2.1",
            encrypted_access_token=encrypt_secret("active-pat"),
            token_name="Nuvvi Sandbox",
            token_created_at=created_at,
        )
        request_mock.side_effect = [
            {
                "ok": True,
                "data": {"success": True, "data": [
                    {"id": "other-token", "name": "Nuvvi Sandbox", "created_at": (created_at - timedelta(days=1)).isoformat()},
                    {"id": "current-token", "name": "Nuvvi Sandbox", "created_at": (created_at - timedelta(seconds=5)).isoformat()},
                ]},
            },
            {"ok": True, "status_code": 200, "data": {"success": True}},
        ]

        revoke_current_pat(connection)

        self.assertEqual(request_mock.call_args_list[0].args[1], "/tokens")
        self.assertEqual(request_mock.call_args_list[1].args[1], "/tokens/current-token")
        connection.refresh_from_db()
        self.assertFalse(connection.encrypted_access_token)

    @patch("apps.dian.matias_service.matias_request")
    def test_refuses_to_revoke_when_token_identity_is_ambiguous(self, request_mock):
        created_at = timezone.now()
        connection = MatiasConnection.objects.create(
            environment=MatiasConnection.ENVIRONMENT_SANDBOX,
            base_url="https://sandbox-api.matias-api.com/api/ubl2.1",
            encrypted_access_token=encrypt_secret("active-pat"),
            token_name="Nuvvi Sandbox",
            token_created_at=created_at,
        )
        request_mock.return_value = {
            "ok": True,
            "data": {"success": True, "data": [
                {"id": "token-a", "name": "Nuvvi Sandbox", "created_at": created_at.isoformat()},
                {"id": "token-b", "name": "Nuvvi Sandbox", "created_at": created_at.isoformat()},
            ]},
        }

        with self.assertRaisesRegex(ValueError, "de forma única"):
            revoke_current_pat(connection)

        self.assertEqual(request_mock.call_count, 1)
