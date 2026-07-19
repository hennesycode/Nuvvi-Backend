from django.db.models import Q
from django.utils.dateparse import parse_datetime
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog
from .serializers import AuditLogSerializer


class IsAdministrativeUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class AuditLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AuditLogListView(APIView):
    permission_classes = [IsAdministrativeUser]

    def get(self, request):
        queryset = AuditLog.objects.select_related("actor").all()

        search = (request.query_params.get("search") or "").strip()
        status = (request.query_params.get("status") or "").strip()
        action = (request.query_params.get("action") or "").strip()
        start_date = self._parse_date(request.query_params.get("start_date"))
        end_date = self._parse_date(request.query_params.get("end_date"))

        if search:
            queryset = queryset.filter(
                Q(actor__full_name__icontains=search)
                | Q(actor__email__icontains=search)
                | Q(actor__username__icontains=search)
                | Q(actor__identification_number__icontains=search)
                | Q(action__icontains=search)
                | Q(entity__icontains=search)
                | Q(message__icontains=search)
                | Q(error_message__icontains=search)
                | Q(request_path__icontains=search)
            )

        if status:
            queryset = queryset.filter(status=status)
        if action:
            queryset = queryset.filter(action=action)
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        paginator = AuditLogPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AuditLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def _parse_date(self, value):
        if not value:
            return None
        parsed = parse_datetime(value)
        if parsed is None:
            return None
        return parsed
