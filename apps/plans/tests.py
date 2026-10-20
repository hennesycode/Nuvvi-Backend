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
