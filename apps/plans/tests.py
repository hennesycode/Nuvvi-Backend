from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User
from .models import Plan, PlanBundle, PlanCategory


class PlanManagementApiTests(APITestCase):
    def setUp(self):
        # Isolate API contracts from historical catalog data migrations.
        PlanBundle.objects.all().delete()
        Plan.objects.all().delete()
        self.admin = User.objects.create_user(email="admin@example.com", full_name="Admin", admin_role=User.ROLE_SUPERADMIN)
        self.client.force_authenticate(self.admin)

    def test_creates_category_and_plan_with_sectioned_features(self):
        category_response = self.client.post("/api/plan-categories/", {"name": "Emprendedores", "description": "Para negocios pequeños"}, format="json")
        self.assertEqual(category_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post("/api/plans/", {
            "code": "inicio", "name": "Plan Inicio", "description": "Para iniciar",
            "monthly_price": "39000", "yearly_price": "390000", "category": category_response.data["id"],
            "features": [{"title": "Facturación", "items": [{"title": "24 documentos al año", "description": "Incluye 24 documentos"}]}],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["features"][0]["items"][0]["title"], "24 documentos al año")

    def test_rejects_feature_sections_without_title(self):
        response = self.client.post("/api/plans/", {"code": "basico", "name": "Básico", "features": [{"title": "", "items": []}]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creates_payroll_addon_with_explicit_limits_and_base_plan_requirement(self):
        response = self.client.post("/api/plans/", {
            "code": "payroll-initial", "name": "Nómina Inicial", "plan_type": "payroll_addon",
            "monthly_price": "9900", "yearly_price": "89000", "max_employees": 2,
            "annual_document_quota": 24, "max_documents_per_month": 2,
            "requires_base_plan": True,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["annual_document_quota"], 24)
        self.assertTrue(response.data["requires_base_plan"])

    def test_payroll_addon_requires_base_plan_even_if_client_omits_flag(self):
        response = self.client.post("/api/plans/", {
            "code": "payroll-invalid", "name": "Nómina sin base", "plan_type": "payroll_addon",
            "monthly_price": "9900", "yearly_price": "89000", "max_employees": 2,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["requires_base_plan"])
        self.assertFalse(response.data["has_inventory"])
        self.assertFalse(response.data["has_cash_register"])

    def test_new_plan_is_published_immediately(self):
        response = self.client.post("/api/plans/", {
            "code": "nuvvi-inicio", "name": "NUVVI Inicio", "monthly_price": "24900",
            "yearly_price": "219000", "annual_document_quota": 120,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["catalog_status"], Plan.CatalogStatus.PUBLISHED)
        self.assertEqual(response.data["visibility"], Plan.Visibility.PUBLIC)
        self.assertTrue(response.data["is_active"])

        publish_response = self.client.post(f"/api/plans/{response.data['id']}/publish/")
        self.assertEqual(publish_response.status_code, status.HTTP_200_OK)

    def test_can_create_published_plan_without_separate_publish_action(self):
        response = self.client.post("/api/plans/", {
            "code": "direct-publish", "name": "Directo", "monthly_price": "1000", "yearly_price": "10000",
            "catalog_status": Plan.CatalogStatus.PUBLISHED,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_non_admin_catalog_only_exposes_published_public_plans(self):
        Plan.objects.create(
            code="public-plan", name="Público", monthly_price="1000",
            catalog_status=Plan.CatalogStatus.PUBLISHED, visibility=Plan.Visibility.PUBLIC,
        )
        Plan.objects.create(
            code="private-plan", name="Privado", monthly_price="1000",
            catalog_status=Plan.CatalogStatus.PUBLISHED, visibility=Plan.Visibility.PRIVATE,
        )
        support = User.objects.create_user(
            email="support-catalog@example.com", full_name="Soporte", admin_role=User.ROLE_SUPPORT,
        )
        self.client.force_authenticate(support)

        response = self.client.get("/api/plans/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["code"] for row in response.data["results"]], ["public-plan"])

    def test_published_plan_can_be_edited(self):
        plan = Plan.objects.create(
            code="nuvvi-negocio", name="NUVVI Negocio", monthly_price="39900",
            yearly_price="359000", catalog_status=Plan.CatalogStatus.PUBLISHED,
            visibility=Plan.Visibility.PUBLIC,
        )

        response = self.client.patch(f"/api/plans/{plan.id}/", {"yearly_price": "399000"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan.refresh_from_db()
        self.assertEqual(str(plan.yearly_price), "399000.00")

    def test_duplicate_creates_an_independent_private_draft(self):
        plan = Plan.objects.create(
            code="nuvvi-crecimiento", name="NUVVI Crecimiento", monthly_price="59900",
            yearly_price="539000", catalog_status=Plan.CatalogStatus.PUBLISHED,
            visibility=Plan.Visibility.PUBLIC,
        )

        response = self.client.post(f"/api/plans/{plan.id}/duplicate/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.data["id"], plan.id)
        self.assertEqual(response.data["catalog_status"], Plan.CatalogStatus.DRAFT)
        self.assertEqual(response.data["visibility"], Plan.Visibility.PRIVATE)
        self.assertTrue(Plan.objects.filter(pk=plan.pk).exists())

    def test_invoicing_policy_and_category_are_applied_by_backend(self):
        response = self.client.post("/api/plans/", {
            "code": "nuvvi-inicio-policy", "name": "NUVVI Inicio",
            "monthly_price": "24900", "yearly_price": "219000",
            "has_inventory": False, "has_cash_register": False,
            "certificate_included_annual": False, "max_issuers": 8,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["has_inventory"])
        self.assertFalse(response.data["has_cash_register"])
        self.assertTrue(response.data["certificate_included_annual"])
        self.assertEqual(response.data["max_issuers"], 1)
        self.assertEqual(response.data["category_name"], "Facturación electrónica")

    def test_enterprise_plan_can_be_saved_without_fixed_prices(self):
        response = self.client.post("/api/plans/", {
            "code": "nuvvi-empresarial", "name": "NUVVI Empresarial",
            "plan_type": "enterprise", "monthly_price": None, "yearly_price": None,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["quote_only"])
        self.assertIsNone(response.data["monthly_price"])
        self.assertIsNone(response.data["yearly_price"])

    def test_new_version_is_a_private_draft_and_publishing_retires_old_catalog_version(self):
        original = Plan.objects.create(
            code="nuvvi-negocio-v1", name="NUVVI Negocio", monthly_price="39900",
            yearly_price="359000", catalog_status=Plan.CatalogStatus.PUBLISHED,
            visibility=Plan.Visibility.PUBLIC,
        )

        version_response = self.client.post(f"/api/plans/{original.id}/new-version/")

        self.assertEqual(version_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(version_response.data["version_number"], 2)
        self.assertEqual(version_response.data["parent_plan"], original.id)
        self.assertEqual(version_response.data["catalog_status"], Plan.CatalogStatus.DRAFT)
        self.assertEqual(version_response.data["name"], original.name)

        new_version = Plan.objects.get(pk=version_response.data["id"])
        new_version.visibility = Plan.Visibility.PUBLIC
        new_version.yearly_price = "399000"
        new_version.commercial_status = Plan.CommercialStatus.APPROVED
        new_version.tax_validation_status = Plan.TaxValidationStatus.VALIDATED
        new_version.save()
        publish_response = self.client.post(f"/api/plans/{new_version.id}/publish/")

        self.assertEqual(publish_response.status_code, status.HTTP_200_OK)
        original.refresh_from_db()
        self.assertEqual(original.catalog_status, Plan.CatalogStatus.RETIRED)
        self.assertEqual(str(original.yearly_price), "359000.00")

    def test_category_with_plans_cannot_be_deleted(self):
        category = PlanCategory.objects.create(name="Contabilidad")
        Plan.objects.create(code="contable", name="Contable", category=category)

        response = self.client.delete(f"/api/plan-categories/{category.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PlanCategory.objects.filter(pk=category.pk).exists())

    def test_non_admin_cannot_manage_plans(self):
        user = User.objects.create_user(email="support@example.com", full_name="Soporte", admin_role=User.ROLE_SUPPORT)
        self.client.force_authenticate(user)

        response = self.client.post("/api/plans/", {"code": "restricted", "name": "Restricted"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_current_catalog_excludes_retired_duplicates_without_deleting_them(self):
        active = Plan.objects.create(code="current", name="Inicio", catalog_status="published", is_active=True)
        old = Plan.objects.create(code="old", name="Inicio", catalog_status="retired", is_active=False)
        response = self.client.get("/api/plans/?current=true")
        self.assertEqual([p["id"] for p in response.data["results"]], [active.pk])
        self.assertTrue(Plan.objects.filter(pk=old.pk).exists())

    def test_quote_preserves_zero_and_null_as_distinct_values(self):
        response = self.client.post("/api/plans/", {
            "code": "custom-payroll", "name": "Personalizado", "plan_type": "payroll_addon",
            "quote_only": True, "max_users": 0, "max_employees": None,
            "annual_document_quota": None, "accountant_users": None,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["plan_type"], "payroll_addon")
        self.assertEqual(response.data["max_users"], 0)
        self.assertIsNone(response.data["annual_document_quota"])
        self.assertIsNone(response.data["monthly_price"])

    def test_edit_does_not_reset_other_commercial_fields(self):
        features = [{"title": "Servicio", "items": [{"title": "Soporte", "description": "Horario guardado", "is_visible": False}]}]
        plan = Plan.objects.create(code="preserve", name="Oferta", monthly_price="100", yearly_price="1000", max_issuers=3, certificate_included_annual=False, features=features)
        response = self.client.patch(f"/api/plans/{plan.pk}/", {"name": "Oferta actualizada"}, format="json")
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.max_issuers, 3)
        self.assertFalse(plan.certificate_included_annual)
        self.assertEqual(plan.features, features)

    def test_bundle_discount_persistence_publication_and_rounding(self):
        from decimal import Decimal
        billing = Plan.objects.create(code="bill", name="Facturación", monthly_price="24900", yearly_price="219000", catalog_status="published")
        payroll = Plan.objects.create(code="pay", name="Nómina", plan_type="payroll_addon", monthly_price="9900", yearly_price="89000", catalog_status="published")
        response = self.client.post("/api/plan-bundles/", {"slug": "test-bundle", "name": "Combo", "billing_plan": billing.pk, "payroll_plan": payroll.pk, "discount_percent": 5}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["monthly_price"], "33060.00")
        self.assertEqual(response.data["yearly_price"], "292600.00")
        self.assertTrue(response.data["is_active"])
        bundle = PlanBundle.objects.get(pk=response.data["id"])
        response = self.client.patch(f"/api/plan-bundles/{bundle.pk}/", {"name": "Combo actualizado"}, format="json")
        bundle.refresh_from_db()
        self.assertEqual(bundle.discount_percent, 5)
        self.assertEqual(bundle.name, "Combo actualizado")
        billing.monthly_price = Decimal("0.01")
        payroll.monthly_price = Decimal("0.00")
        bundle.billing_plan, bundle.payroll_plan, bundle.discount_percent = billing, payroll, 50
        self.assertEqual(bundle.monthly_price, Decimal("0.01"))
        bundle.quote_only = True
        self.assertIsNone(bundle.monthly_price)

    def test_bundle_rejects_unpublished_components_and_invalid_discount(self):
        billing = Plan.objects.create(code="bill", name="Facturación", monthly_price="100", yearly_price="1000")
        payroll = Plan.objects.create(code="pay", name="Nómina", plan_type="payroll_addon", monthly_price="10", yearly_price="100")
        data = {"slug": "invalid", "name": "Combo", "billing_plan": billing.pk, "payroll_plan": payroll.pk, "discount_percent": 101}
        response = self.client.post("/api/plan-bundles/", data, format="json")
        self.assertIn("discount_percent", response.data)
        data["discount_percent"] = 5
        response = self.client.post("/api/plan-bundles/", data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("billing_plan", response.data)

    def test_invalid_prices_do_not_modify_saved_plan(self):
        plan = Plan.objects.create(code="price", name="Precio", monthly_price="100", yearly_price="1000")
        response = self.client.patch(f"/api/plans/{plan.pk}/", {"monthly_price": "-1"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("monthly_price", response.data)
        plan.refresh_from_db()
        self.assertEqual(str(plan.monthly_price), "100.00")
