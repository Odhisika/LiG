from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import envelope
from apps.suppliers.serializers import SupplierSerializer
from apps.suppliers.services import SupplierService


class SupplierListCreateView(APIView):
    """GET  /api/suppliers/  — list the current user's suppliers.
    POST /api/suppliers/  — create a new supplier.
    """

    serializer_class = SupplierSerializer

    @extend_schema(responses=SupplierSerializer(many=True))
    def get(self, request: Request) -> Response:
        suppliers = SupplierService.list_for_owner(request.user)
        return Response(envelope(data=SupplierSerializer(suppliers, many=True).data))

    @extend_schema(request=SupplierSerializer, responses=SupplierSerializer)
    def post(self, request: Request) -> Response:
        supplier = SupplierService.create(request.user, request.data)
        return Response(
            envelope(data=SupplierSerializer(supplier).data),
            status=status.HTTP_201_CREATED,
        )


class SupplierDetailView(APIView):
    """GET/PATCH/DELETE /api/suppliers/{id}/ — scoped to the current user."""

    serializer_class = SupplierSerializer

    @extend_schema(responses=SupplierSerializer)
    def get(self, request: Request, supplier_id) -> Response:
        supplier = SupplierService.get_for_owner(request.user, supplier_id)
        return Response(envelope(data=SupplierSerializer(supplier).data))

    @extend_schema(request=SupplierSerializer, responses=SupplierSerializer)
    def patch(self, request: Request, supplier_id) -> Response:
        supplier = SupplierService.update(request.user, supplier_id, request.data, partial=True)
        return Response(envelope(data=SupplierSerializer(supplier).data))

    @extend_schema(responses=None)
    def delete(self, request: Request, supplier_id) -> Response:
        SupplierService.delete(request.user, supplier_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
