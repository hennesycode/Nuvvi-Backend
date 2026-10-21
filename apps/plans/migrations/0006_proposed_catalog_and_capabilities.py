import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


CAPABILITIES = {
    "electronic_invoicing": "Facturación electrónica",
    "credit_notes": "Notas crédito",
    "debit_notes": "Notas débito",
    "support_document": "Documento soporte",
    "electronic_pos": "Documento equivalente POS",
    "radian_events": "Eventos RADIAN",
    "customer_management": "Clientes",
    "product_management": "Productos y servicios",
    "quotations": "Cotizaciones",
    "document_archive": "Consulta y descarga de documentos",
    "email_delivery": "Envío por correo",
    "digital_certificate": "Firma con certificado digital",
    "inventory_management": "Gestión de inventario",
    "cash_register": "Gestión de caja",
    "sales_reports": "Reportes de ventas",
    "receivables": "Cartera y cuentas por cobrar",
    "user_permissions": "Permisos de usuarios",
    "user_roles": "Roles de usuario",
    "multiple_branches": "Sucursales del mismo NIT",
    "priority_support": "Soporte prioritario",
    "onboarding_session": "Orientación inicial de hasta 30 minutos",
    "payroll_workers": "Registro de trabajadores",
    "payroll_values": "Ingreso de valores previamente calculados",
    "payroll_documents": "Generación de documentos de nómina electrónica",
    "payroll_signature_transmission": "Firma y transmisión de nómina electrónica",
    "payroll_adjustments": "Notas de ajuste de nómina",
    "payroll_history": "Historial de nóminas emitidas",
}

PLANS = [
    {
        "slug": "nuvvi_inicio", "name": "NUVVI Inicio", "plan_type": "invoicing",
        "short_description": "Factura electrónicamente de forma sencilla, segura y desde cualquier lugar.",
        "description": "Diseñado para profesionales independientes, emprendedores y pequeños negocios que necesitan gestionar su facturación electrónica y cumplir con sus obligaciones desde una plataforma en la nube.",
        "monthly_price": "24900", "yearly_price": "219000", "max_documents_per_month": 10,
        "annual_document_quota": 120, "max_users": 1, "accountant_users": 1, "max_branches": 1,
        "max_issuers": 1, "support_level": "standard", "has_inventory": False, "has_cash_register": False,
        "certificate_included_annual": True, "monthly_certificate_fee": "119000",
    },
    {
        "slug": "nuvvi_negocio", "name": "NUVVI Negocio", "plan_type": "invoicing",
        "short_description": "Más documentos, más usuarios y mejor control de las operaciones de tu negocio.",
        "description": "Ideal para microempresas y comercios que necesitan administrar sus ventas, facturación electrónica, clientes y productos desde un mismo lugar.",
        "monthly_price": "39900", "yearly_price": "359000", "max_documents_per_month": 50,
        "annual_document_quota": 600, "max_users": 3, "accountant_users": 1, "max_branches": 1,
        "max_issuers": 1, "support_level": "standard", "has_inventory": True, "has_cash_register": True,
        "certificate_included_annual": True, "monthly_certificate_fee": "119000",
    },
    {
        "slug": "nuvvi_crecimiento", "name": "NUVVI Crecimiento", "plan_type": "invoicing",
        "short_description": "Más capacidad y herramientas de gestión para empresas que están creciendo.",
        "description": "Pensado para empresas con mayor movimiento comercial que necesitan facturar, gestionar sus operaciones y consultar información desde una plataforma centralizada.",
        "monthly_price": "59900", "yearly_price": "539000", "max_documents_per_month": 100,
        "annual_document_quota": 1200, "max_users": 5, "accountant_users": 1, "max_branches": 2,
        "max_issuers": 1, "support_level": "priority", "has_inventory": True, "has_cash_register": True,
        "certificate_included_annual": True, "monthly_certificate_fee": "119000",
    },
    {
        "slug": "nuvvi_empresarial", "name": "NUVVI Empresarial", "plan_type": "enterprise",
        "short_description": "Una solución adaptada a empresas con mayores necesidades de facturación y gestión comercial.",
        "description": "Cotización personalizada para más de 1.200 documentos anuales, varias sedes, más usuarios o integraciones específicas. La venta depende de verificar capacidad.",
        "monthly_price": None, "yearly_price": None, "quote_only": True, "visibility": "quote",
        "max_documents_per_month": None, "annual_document_quota": None, "max_users": None,
        "accountant_users": None, "max_branches": None, "max_issuers": 1,
        "support_level": "custom", "has_inventory": False, "has_cash_register": False,
        "certificate_included_annual": False, "monthly_certificate_fee": "0",
        "quotation_scope": {"document_volume": "custom", "users": "custom", "branches": "custom", "certificate": "custom", "implementation": "custom", "support": "custom", "capacity_check_required": True},
    },
    {
        "slug": "payroll_initial", "name": "Nómina Inicial", "plan_type": "payroll_addon",
        "short_description": "Transmisión de nómina electrónica para equipos de hasta 2 empleados.",
        "description": "Registro de trabajadores, ingreso de valores previamente calculados, generación, firma y transmisión de documentos electrónicos, notas de ajuste dentro del cupo e historial. No incluye liquidación laboral integral, prestaciones automáticas, PILA, pagos salariales ni asesoría laboral.",
        "monthly_price": "9900", "yearly_price": "89000", "max_documents_per_month": 2,
        "annual_document_quota": 24, "max_employees": 2, "max_users": 0, "accountant_users": 0,
        "max_branches": 1, "max_issuers": 1, "support_level": "standard", "requires_base_plan": True,
        "has_inventory": False, "has_cash_register": False, "certificate_included_annual": False,
        "monthly_certificate_fee": "0",
    },
    {
        "slug": "payroll_business", "name": "Nómina Negocio", "plan_type": "payroll_addon",
        "short_description": "Transmisión de nómina electrónica para equipos de hasta 10 empleados.",
        "description": "Registro de trabajadores, ingreso de valores previamente calculados, generación, firma y transmisión de documentos electrónicos, notas de ajuste dentro del cupo e historial. No incluye liquidación laboral integral, prestaciones automáticas, PILA, pagos salariales ni asesoría laboral.",
        "monthly_price": "14900", "yearly_price": "134000", "max_documents_per_month": 10,
        "annual_document_quota": 120, "max_employees": 10, "max_users": 0, "accountant_users": 0,
        "max_branches": 1, "max_issuers": 1, "support_level": "standard", "requires_base_plan": True,
        "has_inventory": False, "has_cash_register": False, "certificate_included_annual": False,
        "monthly_certificate_fee": "0",
    },
    {
        "slug": "payroll_plus", "name": "Nómina Plus", "plan_type": "payroll_addon",
        "short_description": "Transmisión de nómina electrónica para equipos de hasta 25 empleados.",
        "description": "Registro de trabajadores, ingreso de valores previamente calculados, generación, firma y transmisión de documentos electrónicos, notas de ajuste dentro del cupo e historial. No incluye liquidación laboral integral, prestaciones automáticas, PILA, pagos salariales ni asesoría laboral.",
        "monthly_price": "29900", "yearly_price": "269000", "max_documents_per_month": 25,
        "annual_document_quota": 300, "max_employees": 25, "max_users": 0, "accountant_users": 0,
        "max_branches": 1, "max_issuers": 1, "support_level": "standard", "requires_base_plan": True,
        "has_inventory": False, "has_cash_register": False, "certificate_included_annual": False,
        "monthly_certificate_fee": "0",
    },
]

ASSIGNMENTS = {
    "nuvvi_inicio": ["electronic_invoicing", "credit_notes", "debit_notes", "support_document", "electronic_pos", "radian_events", "customer_management", "product_management", "quotations", "document_archive", "email_delivery", "digital_certificate", ("sales_reports", "basic")],
    "nuvvi_negocio": ["electronic_invoicing", "credit_notes", "debit_notes", "support_document", "electronic_pos", "radian_events", "customer_management", "product_management", "quotations", "document_archive", "email_delivery", "digital_certificate", ("sales_reports", "expanded"), ("inventory_management", "basic"), ("cash_register", "basic"), "receivables", "user_permissions"],
    "nuvvi_crecimiento": ["electronic_invoicing", "credit_notes", "debit_notes", "support_document", "electronic_pos", "radian_events", "customer_management", "product_management", "quotations", "document_archive", "email_delivery", "digital_certificate", ("sales_reports", "advanced"), ("inventory_management", "expanded"), ("cash_register", "expanded"), "receivables", "user_permissions", "user_roles", "multiple_branches", "priority_support", "onboarding_session"],
    "nuvvi_empresarial": ["electronic_invoicing", "credit_notes", "debit_notes", "support_document", "electronic_pos", "radian_events", "customer_management", "product_management", "quotations", "document_archive", "email_delivery", "digital_certificate"],
    "payroll_initial": ["payroll_workers", "payroll_values", "payroll_documents", "payroll_signature_transmission", "payroll_adjustments", "payroll_history", "document_archive"],
    "payroll_business": ["payroll_workers", "payroll_values", "payroll_documents", "payroll_signature_transmission", "payroll_adjustments", "payroll_history", "document_archive"],
    "payroll_plus": ["payroll_workers", "payroll_values", "payroll_documents", "payroll_signature_transmission", "payroll_adjustments", "payroll_history", "document_archive"],
}


def seed_proposed_catalog(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    PlanCategory = apps.get_model("plans", "PlanCategory")
    Capability = apps.get_model("plans", "Capability")
    PlanCapability = apps.get_model("plans", "PlanCapability")
    PlanBundle = apps.get_model("plans", "PlanBundle")
    database = schema_editor.connection.alias
    categories = {
        "invoicing": PlanCategory.objects.using(database).get_or_create(name="Facturación electrónica")[0],
        "payroll_addon": PlanCategory.objects.using(database).get_or_create(name="Nómina electrónica")[0],
        "enterprise": PlanCategory.objects.using(database).get_or_create(name="Empresarial")[0],
    }

    capability_objects = {}
    for code, name in CAPABILITIES.items():
        capability_objects[code], _ = Capability.objects.using(database).get_or_create(
            code=code,
            defaults={"name": name, "validation_status": "pending", "validation_notes": ""},
        )

    products = {}
    for index, spec in enumerate(PLANS, start=1):
        slug = spec["slug"]
        if Plan.objects.using(database).filter(slug=slug).exists():
            products[slug] = Plan.objects.using(database).get(slug=slug)
            continue
        code = slug
        suffix = 2
        while Plan.objects.using(database).filter(code=code).exists():
            candidate = f"{slug[:44]}_proposal_{suffix}"
            code = candidate[:50]
            suffix += 1
        values = {key: value for key, value in spec.items() if key not in {"slug", "name", "plan_type", "visibility"}}
        products[slug] = Plan.objects.using(database).create(
            code=code,
            slug=slug,
            name=spec["name"],
            plan_type=spec["plan_type"],
            category=categories[spec["plan_type"]],
            display_order=index,
            catalog_status="draft",
            visibility="private",
            commercial_status="proposal",
            tax_validation_status="pending",
            is_active=False,
            features=[],
            **values,
        )

    for plan_slug, codes in ASSIGNMENTS.items():
        plan = products[plan_slug]
        for entry in codes:
            code, level = entry if isinstance(entry, tuple) else (entry, "")
            PlanCapability.objects.using(database).get_or_create(
                plan=plan,
                capability=capability_objects[code],
                defaults={"scope_level": level, "included_in_proposal": True},
            )

    bundles = [
        ("bundle_emprendedor", "Emprendedor", "nuvvi_inicio", "payroll_initial", 1),
        ("bundle_comercial", "Comercial", "nuvvi_negocio", "payroll_business", 2),
        ("bundle_empresarial", "Empresarial", "nuvvi_crecimiento", "payroll_plus", 3),
    ]
    for slug, name, billing_slug, payroll_slug, order in bundles:
        PlanBundle.objects.using(database).get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "short_description": "Composición de facturación más nómina; se cobra un certificado por NIT.",
                "billing_plan": products[billing_slug],
                "payroll_plan": products[payroll_slug],
                "display_order": order,
                "commercial_status": "proposal",
                "is_active": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0005_plan_pricing_and_versions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Capability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=80, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("validation_status", models.CharField(choices=[("pending", "Pendiente de validación"), ("available", "Disponible y validada"), ("unavailable", "No disponible")], default="pending", max_length=16)),
                ("validation_notes", models.TextField(blank=True, default="")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_plan_capabilities", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AlterField(model_name="plan", name="annual_document_quota", field=models.PositiveIntegerField(blank=True, default=0, null=True)),
        migrations.AlterField(model_name="plan", name="max_users", field=models.PositiveIntegerField(blank=True, default=1, null=True)),
        migrations.AlterField(model_name="plan", name="accountant_users", field=models.PositiveIntegerField(blank=True, default=0, null=True)),
        migrations.AlterField(model_name="plan", name="max_branches", field=models.PositiveIntegerField(blank=True, default=1, null=True)),
        migrations.AlterField(model_name="plan", name="max_documents_per_month", field=models.PositiveIntegerField(blank=True, default=0, null=True)),
        migrations.AlterField(model_name="plan", name="max_employees", field=models.PositiveIntegerField(blank=True, default=0, null=True)),
        migrations.AddField(model_name="plan", name="slug", field=models.SlugField(blank=True, max_length=60, null=True, unique=True)),
        migrations.AddField(model_name="plan", name="commercial_status", field=models.CharField(choices=[("legacy", "Oferta anterior"), ("proposal", "Propuesta"), ("approved", "Aprobada")], default="legacy", max_length=12)),
        migrations.AddField(model_name="plan", name="tax_validation_status", field=models.CharField(choices=[("unknown", "Sin validar"), ("pending", "Pendiente de contador"), ("validated", "Validación tributaria aprobada")], default="unknown", max_length=12)),
        migrations.AddField(model_name="plan", name="tax_validation_note", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="plan", name="quotation_scope", field=models.JSONField(blank=True, default=dict)),
        migrations.CreateModel(
            name="PlanBundle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("short_description", models.CharField(blank=True, default="", max_length=255)),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("commercial_status", models.CharField(choices=[("proposal", "Propuesta"), ("approved", "Aprobada")], default="proposal", max_length=12)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("billing_plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="billing_bundles", to="plans.plan")),
                ("payroll_plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_bundles", to="plans.plan")),
            ],
            options={"ordering": ["display_order", "name"]},
        ),
        migrations.CreateModel(
            name="PlanCapability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope_level", models.CharField(blank=True, default="", max_length=40)),
                ("included_in_proposal", models.BooleanField(default=True)),
                ("capability", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="plan_assignments", to="plans.capability")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="plan_capabilities", to="plans.plan")),
            ],
            options={"ordering": ["capability__name"]},
        ),
        migrations.AddField(model_name="plan", name="capabilities", field=models.ManyToManyField(blank=True, related_name="plans", through="plans.PlanCapability", to="plans.capability")),
        migrations.AddConstraint(model_name="plancapability", constraint=models.UniqueConstraint(fields=("plan", "capability"), name="plans_unique_plan_capability")),
        migrations.RunPython(seed_proposed_catalog, migrations.RunPython.noop),
    ]
