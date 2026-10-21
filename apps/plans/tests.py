from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User
from .models import Plan, PlanCategory


class PlanManagementApiTests(APITestCase):
    def setUp(self):
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

    def test_rejects_payroll_addon_without_base_plan(self):
        response = self.client.post("/api/plans/", {
            "code": "payroll-invalid", "name": "Nómina sin base", "plan_type": "payroll_addon",
            "monthly_price": "9900", "yearly_price": "89000", "max_employees": 2,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("requires_base_plan", response.data)

    def test_new_plan_is_private_draft_until_explicitly_published(self):
        response = self.client.post("/api/plans/", {
            "code": "nuvvi-inicio", "name": "NUVVI Inicio", "monthly_price": "24900",
            "yearly_price": "219000", "annual_document_quota": 120,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["catalog_status"], Plan.CatalogStatus.DRAFT)
        self.assertEqual(response.data["visibility"], Plan.Visibility.PRIVATE)

        publish_response = self.client.post(f"/api/plans/{response.data['id']}/publish/")
        self.assertEqual(publish_response.status_code, status.HTTP_200_OK)
        self.assertEqual(publish_response.data["catalog_status"], Plan.CatalogStatus.PUBLISHED)

    def test_cannot_create_published_plan_without_explicit_publish_action(self):
        response = self.client.post("/api/plans/", {
            "code": "direct-publish", "name": "Directo", "monthly_price": "1000",
            "catalog_status": Plan.CatalogStatus.PUBLISHED,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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

    def test_published_plan_contract_fields_cannot_be_overwritten(self):
        plan = Plan.objects.create(
            code="nuvvi-negocio", name="NUVVI Negocio", monthly_price="39900",
            yearly_price="359000", catalog_status=Plan.CatalogStatus.PUBLISHED,
            visibility=Plan.Visibility.PUBLIC,
        )

        response = self.client.patch(f"/api/plans/{plan.id}/", {"yearly_price": "399000"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        plan.refresh_from_db()
        self.assertEqual(str(plan.yearly_price), "359000.00")

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
